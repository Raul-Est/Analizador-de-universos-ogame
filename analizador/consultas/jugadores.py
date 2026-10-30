"""Consultas sobre jugadores y alianzas."""

import json
from collections import Counter
from datetime import datetime

from ..normalizacion import describir_estado, en_vacaciones, es_inactivo, nombre_jugador, nuevos_inactivos, parsear_planetas
from .registro import Parametro, Resultado, consulta

ARCHIVO_INACTIVOS = "inactivos_ultima_captura.json"


def _filas(contexto, jugadores):
    tags = {a["id"]: a.get("tag") for a in contexto.alianzas()}
    return [
        {
            "id": j["id"],
            "nombre": j["name"],
            "estado": describir_estado(j["status"]),
            "alianza": tags.get(j["alliance"]) if j["alliance"] is not None else None,
        }
        for j in jugadores
    ]


def _resumen_estados(filas):
    cuenta = Counter(f["estado"] for f in filas)
    return [f"Total: {len(filas)}"] + [f"{estado}: {n}" for estado, n in cuenta.most_common()]


@consulta("jugadores", "TODOS los jugadores del universo (activos, inactivos, vacaciones...)")
def jugadores(contexto):
    filas = _filas(contexto, contexto.jugadores())
    return Resultado(datos=filas, titulo="Todos los jugadores del universo", resumen=_resumen_estados(filas))


@consulta(
    "jugadores_inactivos",
    "Jugadores INACTIVOS ahora mismo (7 días o 28+ días)",
    (Parametro("incluir_vacaciones", "¿Incluir inactivos en modo vacaciones? (s/n)", bool, True),),
)
def jugadores_inactivos(contexto, incluir_vacaciones=True):
    seleccion = [
        j for j in contexto.jugadores()
        if es_inactivo(j["status"]) and (incluir_vacaciones or not en_vacaciones(j["status"]))
    ]
    filas = _filas(contexto, seleccion)
    return Resultado(datos=filas, titulo="Jugadores inactivos", resumen=_resumen_estados(filas))


@consulta(
    "jugadores_nuevos_inactivos",
    "NUEVOS inactivos desde la última vez que se ejecutó esta opción (sin vacaciones)",
)
def jugadores_nuevos_inactivos(contexto):
    """Compara con la captura guardada en la ejecución anterior y la sustituye por la actual."""
    jugadores_ = contexto.jugadores()
    actuales = [j["id"] for j in jugadores_ if es_inactivo(j["status"])]
    archivo = contexto.carpeta_estado / ARCHIVO_INACTIVOS if contexto.carpeta_estado else None

    anterior = None
    if archivo and archivo.exists():
        try:
            anterior = json.loads(archivo.read_text(encoding="utf-8"))
        except ValueError:
            anterior = None
    clave = contexto.universo.clave
    descartada = anterior is not None and anterior.get("universo") != clave
    if descartada:
        anterior = None

    if archivo:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        captura = {
            "universo": clave,
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "inactivos": actuales,
        }
        archivo.write_text(json.dumps(captura), encoding="utf-8")

    if anterior is None:
        aviso = ["La captura anterior no correspondía a este universo (o no tenía cabecera) y se ha descartado."] if descartada else []
        return Resultado(
            datos=[],
            titulo="Nuevos inactivos",
            resumen=aviso + [
                f"Primera ejecución en {clave}: no hay captura anterior con la que comparar.",
                f"Captura guardada ({len(actuales)} inactivos). La próxima vez se mostrarán los nuevos.",
            ],
        )

    nuevos = nuevos_inactivos(set(anterior["inactivos"]), jugadores_)
    desde = datetime.fromisoformat(anterior["fecha"]).strftime("%d/%m/%Y %H:%M")
    filas = _filas(contexto, nuevos)
    return Resultado(
        datos=filas,
        titulo=f"Nuevos inactivos en {clave} desde {desde}",
        resumen=[f"Nuevos inactivos (sin vacaciones): {len(filas)}", "Captura actualizada para la próxima comparación."],
    )


@consulta("alianzas", "Lista de todas las alianzas del universo")
def alianzas(contexto):
    datos = contexto.alianzas()
    return Resultado(datos=datos, titulo="Alianzas", resumen=[f"Total: {len(datos)}"])


@consulta(
    "alianza_miembros",
    "Miembros de una alianza con puntos militares y naves",
    (Parametro("alianza", "Id o nombre (parcial) de la alianza", str, obligatorio=True),),
)
def alianza_miembros(contexto, alianza):
    al = contexto.resolver_alianza(alianza)
    datos = contexto.miembros_alianza(al["id"])
    return Resultado(
        datos=datos,
        titulo=f"Miembros de {al.get('name')} [{al.get('tag')}]",
        resumen=[f"Miembros: {len(datos)}"],
    )


@consulta(
    "jugador_detalle",
    "Planetas y lunas de un jugador",
    (Parametro("jugador", "Id o nombre (parcial) del jugador", str, obligatorio=True),),
)
def jugador_detalle(contexto, jugador):
    pid = contexto.resolver_jugador(jugador)
    detalle = contexto.detalle_jugador(pid)
    planetas = parsear_planetas(detalle)
    lunas = sum(p["lunas"] for p in planetas)
    return Resultado(
        datos={"id": pid, "nombre": nombre_jugador(detalle), "planetas": planetas},
        titulo=f"Jugador {nombre_jugador(detalle)} ({pid})",
        resumen=[f"Planetas: {len(planetas)}", f"Lunas: {lunas}"],
    )
