"""Seguimiento en vivo de los puntos militares destruidos y perdidos (highscore de OGame).

La API regenera el highscore cada hora y cada respuesta lleva su `timestamp`. En lugar de consultar
sin parar, se calcula cuándo toca la siguiente actualización y se sondea con frecuencia solo a partir
de ese momento, descargando los datos en cuanto cambia el timestamp.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from . import normalizacion as n
from .cliente import ErrorApi

TIPO_DESTRUIDOS = 6
TIPO_PERDIDOS = 4
VERSION_CAPTURA = 3  # 2: tipos 6 y 4; 3: marcas de tiempo por tipo. Las capturas anteriores se descartan
INTERVALO_API = 3600  # el highscore se regenera cada hora (Expires = Last-Modified + 1 h)
MARGEN = 3  # segundos de cortesía tras la hora esperada
SONDEO_ESPERA = 300  # comprobación de seguridad mientras se espera la próxima actualización
SONDEO_ACTIVO = 15  # frecuencia al pasar la hora esperada hasta que aparezcan datos nuevos
REINTENTO_ERROR = 30
ARCHIVO_CAPTURA = "puntos_ultima_captura.json"


def formatear_puntos(valor: int) -> str:
    return f"{valor:+,}".replace(",", ".")


def formatear_hora(marca: float) -> str:
    return datetime.fromtimestamp(marca).strftime("%H:%M")


def formatear_fecha(marca: float) -> str:
    return datetime.fromtimestamp(marca).strftime("%d/%m/%Y")


def _puntuaciones(data: Any) -> dict[int, int]:
    return {e["id"]: e["score"] or 0 for e in n.parsear_highscore(data)}


def descargar_captura(contexto) -> dict:
    """Highscore de puntos destruidos y perdidos de todos los jugadores, con la marca de tiempo de la API."""
    cliente = contexto.cliente
    destruidos = cliente.get_json("highscore.xml", category=1, type=TIPO_DESTRUIDOS)
    perdidos = cliente.get_json("highscore.xml", category=1, type=TIPO_PERDIDOS)
    ts_destruidos = n.marca_tiempo(destruidos) or int(time.time())
    ts_perdidos = n.marca_tiempo(perdidos) or int(time.time())
    return {
        "universo": contexto.universo.clave,
        "version": VERSION_CAPTURA,
        # cada tipo se regenera en un segundo distinto (el de perdidos va el último)
        "timestamp": max(ts_destruidos, ts_perdidos),
        "ts_destruidos": ts_destruidos,
        "ts_perdidos": ts_perdidos,
        "destruidos": _puntuaciones(destruidos),
        "perdidos": _puntuaciones(perdidos),
    }


def es_nueva(previa: dict, nueva: dict) -> bool:
    """Una captura es nueva solo cuando se han regenerado los dos rankings."""
    return nueva["ts_destruidos"] > previa["ts_destruidos"] and nueva["ts_perdidos"] > previa["ts_perdidos"]


def leer_captura(archivo: Optional[Path], clave_universo: str) -> Optional[dict]:
    """Última captura guardada; se descarta si es de otro universo o no se puede leer."""
    if not archivo or not archivo.exists():
        return None
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        if datos.get("universo") != clave_universo or datos.get("version") != VERSION_CAPTURA:
            return None
        return {
            "universo": clave_universo,
            "version": VERSION_CAPTURA,
            "timestamp": int(datos["timestamp"]),
            "ts_destruidos": int(datos["ts_destruidos"]),
            "ts_perdidos": int(datos["ts_perdidos"]),
            "destruidos": {int(k): v for k, v in datos["destruidos"].items()},
            "perdidos": {int(k): v for k, v in datos["perdidos"].items()},
        }
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def guardar_captura(archivo: Optional[Path], captura: dict) -> None:
    if not archivo:
        return
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps(captura), encoding="utf-8")


def calcular_cambios(
    anterior: dict,
    nueva: dict,
    top: int = 10,
    ids_incluidos: Optional[set[int]] = None,
) -> list[dict]:
    """Puntos ganados entre dos capturas: positivos (destruidos) primero y negativos (perdidos) después.

    Cada lado se ordena de mayor a menor magnitud y se limita a `top` jugadores.
    Los jugadores que no estaban en la captura anterior se ignoran (no hay base de comparación).
    Si se indica `ids_incluidos`, solo se consideran esos jugadores antes de aplicar el límite.
    """
    ganados: list[dict] = []
    perdidos: list[dict] = []
    for clave, destino, signo in (("destruidos", ganados, 1), ("perdidos", perdidos, -1)):
        antes = anterior[clave]
        for pid, puntos in nueva[clave].items():
            if ids_incluidos is not None and pid not in ids_incluidos:
                continue
            if pid in antes and puntos > antes[pid]:
                destino.append({"id": pid, "puntos": signo * (puntos - antes[pid])})
    ganados.sort(key=lambda c: -c["puntos"])
    perdidos.sort(key=lambda c: c["puntos"])
    return ganados[:top] + perdidos[:top]


def espera_hasta_siguiente(marca: float, ahora: float) -> float:
    """Segundos hasta la próxima comprobación según la hora a la que se generaron los últimos datos."""
    restante = marca + INTERVALO_API + MARGEN - ahora
    if restante > SONDEO_ESPERA:
        return SONDEO_ESPERA
    if restante > 0:
        return restante
    return SONDEO_ACTIVO


def aplanar_historial(historial: list[dict]) -> list[dict]:
    """Convierte las actualizaciones recibidas en filas planas, aptas para exportar."""
    return [
        {
            "fecha": f"{formatear_fecha(a['hora'])} {formatear_hora(a['hora'])}",
            "jugador": f["nombre"],
            "alianza": f["alianza"],
            "tipo": "destruidos" if f["puntos"] > 0 else "perdidos",
            "puntos": f["puntos"],
        }
        for a in historial
        for f in a["filas"]
    ]


class Seguimiento:
    """Descarga el highscore en cuanto la API lo actualiza y avisa de los cambios.

    `al_actualizar(actualizacion)` y `al_estado(texto)` se llaman desde el hilo de `ejecutar`.
    """

    def __init__(
        self,
        contexto,
        top: int,
        al_actualizar: Callable[[dict], None],
        al_estado: Callable[[str], None],
    ):
        self.contexto = contexto
        self.top = top
        self.al_actualizar = al_actualizar
        self.al_estado = al_estado
        self.parar = threading.Event()
        self.historial: list[dict] = []

    def _archivo(self) -> Optional[Path]:
        carpeta = self.contexto.carpeta_estado
        return carpeta / ARCHIVO_CAPTURA if carpeta else None

    def _descargar(self) -> Optional[dict]:
        try:
            return descargar_captura(self.contexto)
        except ErrorApi as exc:
            self.al_estado(f"Error al consultar la API: {exc}. Reintentando...")
            return None

    def _nombres(self, ids: list[int]) -> tuple[dict, dict]:
        jugadores = {j["id"]: j for j in self.contexto.jugadores()}
        if any(i not in jugadores for i in ids):
            self.contexto.refrescar_listas()
            jugadores = {j["id"]: j for j in self.contexto.jugadores()}
        tags = {a["id"]: a.get("tag") for a in self.contexto.alianzas()}
        return jugadores, tags

    def _publicar(self, previa: dict, nueva: dict) -> None:
        cambios = calcular_cambios(previa, nueva, self.top)
        jugadores, tags = self._nombres([c["id"] for c in cambios])
        filas = []
        for c in cambios:
            jugador = jugadores.get(c["id"], {})
            filas.append({
                "puntos": c["puntos"],
                "id": c["id"],
                "nombre": jugador.get("name") or f"#{c['id']}",
                "alianza": tags.get(jugador.get("alliance")) if jugador.get("alliance") is not None else None,
            })
        actualizacion = {"hora": nueva["timestamp"], "desde": previa["timestamp"], "filas": filas}
        self.historial.append(actualizacion)
        self.al_actualizar(actualizacion)

    def _informar(self, captura: dict) -> None:
        proxima = captura["timestamp"] + INTERVALO_API + MARGEN
        self.al_estado(
            f"Comprobado a las {datetime.now():%H:%M:%S} · datos de la API de las "
            f"{formatear_hora(captura['timestamp'])} · próxima actualización esperada hacia las {formatear_hora(proxima)}"
        )

    def ejecutar(self) -> None:
        """Bucle principal; termina cuando se activa `parar`."""
        try:
            actual = None
            while actual is None:
                actual = self._descargar()
                if actual is None and self.parar.wait(REINTENTO_ERROR):
                    return
            previa = leer_captura(self._archivo(), self.contexto.universo.clave)
            if previa and es_nueva(previa, actual):
                self._publicar(previa, actual)
            guardar_captura(self._archivo(), actual)
            self._informar(actual)
            while not self.parar.wait(espera_hasta_siguiente(actual["timestamp"], time.time())):
                nueva = self._descargar()
                if nueva is None:
                    continue
                if es_nueva(actual, nueva):
                    self._publicar(actual, nueva)
                    guardar_captura(self._archivo(), nueva)
                    actual = nueva
                self._informar(actual)
        except Exception as exc:  # el hilo no debe morir en silencio
            self.al_estado(f"Error inesperado, seguimiento detenido: {exc}")
