"""Almacén local (un único .json) de los informes de espionaje analizados."""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from .espionaje import filas_planas, reparar_cabecera

NOMBRE_ARCHIVO = "informes.json"
_cerrojo = threading.Lock()


def _leer(archivo: Path) -> list[dict]:
    if not archivo.exists():
        return []
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except ValueError:
        raise ValueError(f"{archivo} está dañado; arréglalo o bórralo para empezar de nuevo.")
    return _reparar(datos) if isinstance(datos, list) else []


def _reparar(registros: list[dict]) -> list[dict]:
    for r in registros:
        r["informe"]["cabecera"] = reparar_cabecera(r["informe"]["cabecera"])
    return registros


def guardar_informe(archivo: Path, informe: dict, ahora: Optional[datetime] = None) -> tuple[bool, int]:
    """Añade el informe. Devuelve (guardado, total de informes de ese jugador).

    Un informe idéntico a uno ya guardado del mismo jugador no se duplica.
    El archivo se mantiene ordenado por la fecha y hora de la cabecera del informe
    (si no la trae, por la de guardado), de más antiguo a más reciente.
    """
    jugador = informe["cabecera"].get("Jugador", "").strip()
    if not jugador:
        raise ValueError("El informe no tiene nombre de jugador; no se puede guardar.")
    ahora = ahora or datetime.now()
    with _cerrojo:
        registros = _leer(archivo)
        del_jugador = [r for r in registros if r["jugador"].lower() == jugador.lower()]
        if any(r["informe"] == informe for r in del_jugador):
            return False, len(del_jugador)
        registros.append({"jugador": jugador, "guardado": ahora.isoformat(timespec="seconds"), "informe": informe})
        registros.sort(key=_momento)
        archivo.parent.mkdir(parents=True, exist_ok=True)
        temporal = archivo.with_suffix(".tmp")
        temporal.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporal, archivo)
        return True, len(del_jugador) + 1


def _momento(registro: dict) -> datetime:
    """Fecha del informe si la trae; si no, cuándo se guardó."""
    fecha = registro["informe"]["cabecera"].get("Fecha del informe")
    if fecha:
        try:
            return datetime.strptime(fecha, "%d.%m.%Y %H:%M:%S")
        except ValueError:
            pass
    return datetime.fromisoformat(registro["guardado"])


def ultimo_informe(archivo: Path, texto: str) -> dict:
    """Informe más reciente del jugador cuyo nombre coincida (exacto o parcial, sin distinguir mayúsculas)."""
    registros = _leer(archivo)
    if not registros:
        raise ValueError("Aún no hay informes guardados. Pega alguno con la opción del formulario de espionaje.")
    buscado = texto.strip().lower()
    nombres = {r["jugador"] for r in registros}
    exactos = {n for n in nombres if n.lower() == buscado}
    elegidos = exactos or {n for n in nombres if buscado in n.lower()}
    if not elegidos:
        raise ValueError(f"No hay informes de {texto!r}. Jugadores guardados: {', '.join(sorted(nombres))}")
    if len(elegidos) > 1:
        raise ValueError(f"{texto!r} coincide con varios jugadores: {', '.join(sorted(elegidos))}")
    nombre = elegidos.pop()
    return max((r for r in registros if r["jugador"] == nombre), key=_momento)


def filas_ultima_flota(registro: dict) -> list[dict]:
    """Cabecera del informe (tal como se muestra al analizarlo), la flota y el resto de secciones (recursos, defensa, edificios, investigación...)."""
    informe = registro["informe"]
    filas = [{"concepto": "Guardado", "valor": datetime.fromisoformat(registro["guardado"]).strftime("%d/%m/%Y %H:%M")}]
    for f in filas_planas(informe):
        if f["seccion"] == "Cabecera":
            filas.append({"concepto": f["concepto"], "valor": f["valor"]})
    flota = informe["secciones"].get("Flotas", {})
    filas.append({"concepto": "— Flota —", "valor": ""})
    filas += [{"concepto": nave, "valor": cantidad} for nave, cantidad in flota.items()]
    for seccion, datos in informe["secciones"].items():
        if seccion == "Flotas":
            continue
        filas.append({"concepto": f"— {seccion} —", "valor": ""})
        filas += [{"concepto": concepto, "valor": cantidad} for concepto, cantidad in datos.items()]
    return filas
