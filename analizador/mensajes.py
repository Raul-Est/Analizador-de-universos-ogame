"""Mensajes del juego pegados a mano: análisis, almacén por universo y vínculo con el id del jugador."""

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

from . import normalizacion as n
from .cliente import ErrorApi

NOMBRE_ARCHIVO = "mensajes.json"
FORMATO_FECHA = "%d.%m.%Y %H:%M:%S"
_cerrojo = threading.Lock()

_CABECERA = re.compile(r"^\s*-?\s*(?P<resto>.*?)(?P<fecha>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})\s*$")
_CABECERA_CONVERSACION = re.compile(
    r"^\s*(?P<remitente>.+?)(?P<fecha>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})\s*$"
)
_PLANETA = re.compile(r"\[!\[\]\([^)]*\)\s*\[(?P<coords>\d+:\d+:\d+)\]\]\([^)]*\)")
_ALIANZA = re.compile(r"\[(?P<nombre>[^\]]*)\]\([^)\s]*allianceInfo[^)\s]*\)")
_COORDENADAS = re.compile(r"^\s*\[?(?P<coords>\d+:\d+:\d+)\]?\s*$")


def analizar_mensajes(texto: str) -> list[dict]:
    """Separa mensajes copiados individualmente o una conversación completa del juego.

    En una conversación se ignora el texto anterior a `Imperio`; las líneas con un nombre pegado a una fecha
    inician cada mensaje y su contenido continúa hasta la siguiente. Las coordenadas de la cabecera de
    conversación solo se asignan al jugador indicado allí.
    """
    lineas = texto.splitlines()
    conversacion = _analizar_conversacion(lineas)
    if conversacion is not None:
        return conversacion

    bloques: list[tuple[re.Match, list[str]]] = []
    for linea in lineas:
        cabecera = _CABECERA.match(linea)
        if cabecera:
            bloques.append((cabecera, []))
        elif bloques:
            bloques[-1][1].append(linea)
        elif linea.strip():
            raise ValueError("El texto debe empezar con la cabecera del mensaje: '- remitente dd.mm.aaaa hh:mm:ss'")
    return [_mensaje(cabecera, cuerpo) for cabecera, cuerpo in bloques]


def _analizar_conversacion(lineas: list[str]) -> Optional[list[dict]]:
    """Analiza el formato de conversación con `Imperio<jugador>`, coordenadas y bloques nombre-fecha."""
    inicios = [
        indice for indice, linea in enumerate(lineas)
        if _CABECERA_CONVERSACION.match(linea)
    ]
    if not inicios:
        return None
    primer_inicio = inicios[0]
    perfil = None
    indice_perfil = None
    for indice, linea in enumerate(lineas[:primer_inicio]):
        marca = re.search(r"Imperio", linea, re.IGNORECASE)
        if marca:
            perfil = linea[marca.end():].strip()
            indice_perfil = indice
            break
    if indice_perfil is None or not perfil:
        return None

    coords = None
    for linea in lineas[indice_perfil + 1:primer_inicio]:
        coincidencia = _COORDENADAS.match(linea)
        if coincidencia:
            coords = coincidencia.group("coords")
            break

    mensajes = []
    remitente = None
    fecha = None
    cuerpo: list[str] = []

    def guardar_actual() -> None:
        if remitente is None or fecha is None:
            return
        try:
            momento = datetime.strptime(fecha, FORMATO_FECHA).isoformat(timespec="seconds")
        except ValueError as exc:
            raise ValueError(f"Fecha no válida en el mensaje de {remitente}: {fecha}") from exc
        mensajes.append({
            "fecha": momento,
            "remitente": remitente,
            "alianza": None,
            "coords": coords if remitente.casefold() == perfil.casefold() else None,
            "texto": "\n".join(cuerpo).strip(),
            "jugador_id": None,
        })

    for linea in lineas[primer_inicio:]:
        cabecera = _CABECERA_CONVERSACION.match(linea)
        if cabecera:
            guardar_actual()
            remitente = cabecera.group("remitente").strip()
            fecha = cabecera.group("fecha")
            cuerpo = []
        elif remitente is not None:
            cuerpo.append(linea)
    guardar_actual()
    participantes = list(dict.fromkeys(
        mensaje["remitente"] for mensaje in mensajes
    ))
    for mensaje in mensajes:
        otros = [
            nombre for nombre in participantes
            if nombre.casefold() != mensaje["remitente"].casefold()
        ]
        if not otros and perfil.casefold() != mensaje["remitente"].casefold():
            otros = [perfil]
        mensaje["destinatario"] = ", ".join(otros) or None
    return mensajes


def _mensaje(cabecera: re.Match, cuerpo: list[str]) -> dict:
    fecha = cabecera.group("fecha")
    aviso = f"mensaje del {fecha}"
    trozo = "\n".join(cuerpo)
    planeta = _PLANETA.search(trozo)
    if not planeta:
        raise ValueError(f"Falta el planeta del remitente (coordenadas del enlace) en el {aviso}")
    antes = trozo[: planeta.start()]
    alianzas = list(_ALIANZA.finditer(antes))
    nombre_cabecera = cabecera.group("resto").strip()
    if alianzas:
        alianza = alianzas[-1]
        alianza_nombre = alianza.group("nombre")
        remitente = antes[alianza.end():].strip() or nombre_cabecera
        texto = antes[: alianza.start()]
    else:
        alianza_nombre = None
        remitente = nombre_cabecera
        texto = antes
    if not remitente:
        raise ValueError(f"No se reconoce el remitente en el {aviso}")
    texto = texto.strip()
    if texto.endswith(remitente):
        texto = texto[: -len(remitente)].strip()
    return {
        "fecha": datetime.strptime(fecha, FORMATO_FECHA).isoformat(timespec="seconds"),
        "remitente": remitente,
        "alianza": alianza_nombre,
        "coords": planeta.group("coords"),
        "texto": texto,
        "destinatario": None,
        "jugador_id": None,
    }


def _planetas(detalle: Optional[dict]) -> set[str]:
    return {p["coords"] for p in n.parsear_planetas(detalle)}


def identificar_jugador(contexto, nombre: str, coords: Optional[str]) -> Optional[int]:
    """Id del jugador cuyo planeta principal está en `coords`.

    Primero se prueba con los jugadores que se llaman igual; si ninguno tiene las coordenadas (p. ej. cambió
    de nombre), se recorren todos. Si no hay coordenadas, solo se acepta un nombre exacto y único.
    """
    jugadores = contexto.jugadores()
    mismos = [j["id"] for j in jugadores if (j.get("name") or "").lower() == nombre.lower()]
    if not coords:
        return mismos[0] if len(mismos) == 1 else None
    for pid in mismos:
        try:
            if coords in _planetas(contexto.detalle_jugador(pid)):
                return pid
        except ErrorApi:
            continue
    resto = [j["id"] for j in jugadores if j["id"] not in set(mismos)]
    generador = contexto.detalles(resto)
    try:
        for pid, detalle, _error in generador:
            if detalle is not None and coords in _planetas(detalle):
                return pid
    finally:
        generador.close()
    return None


def crear_resolutor(contexto) -> Callable[[str, Optional[str]], Optional[int]]:
    """Resolutor con memoria (nombre, coordenadas) → id, para no repetir búsquedas al pegar varios mensajes."""
    memoria: dict[tuple[str, Optional[str]], Optional[int]] = {}

    def resolver(nombre: str, coords: Optional[str]) -> Optional[int]:
        clave = (nombre.lower(), coords)
        if clave not in memoria:
            memoria[clave] = identificar_jugador(contexto, nombre, coords)
        return memoria[clave]

    return resolver


def _leer(archivo: Path) -> list[dict]:
    if not archivo.exists():
        return []
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except ValueError:
        raise ValueError(f"{archivo} está dañado; arréglalo o bórralo para empezar de nuevo.")
    return datos if isinstance(datos, list) else []


def _clave(registro: dict) -> tuple[str, str, str]:
    return registro["fecha"], registro["remitente"], registro["texto"]


def guardar_mensajes(
    archivo: Path,
    mensajes: list[dict],
    resolver: Callable[[str, Optional[str]], Optional[int]],
    ahora: Optional[datetime] = None,
) -> tuple[int, int]:
    """Añade los mensajes que no estén ya guardados. Devuelve (nuevos, ya_guardados).

    Cada mensaje se vincula al id de jugador con `resolver`; si no se encuentra, queda sin id (None).
    """
    ahora = ahora or datetime.now()
    with _cerrojo:
        registros = _leer(archivo)
        conocidos = {_clave(r): r for r in registros}
        nuevos = repetidos = 0
        enriquecidos = False
        for mensaje in mensajes:
            clave = _clave(mensaje)
            if clave in conocidos:
                repetidos += 1
                existente = conocidos[clave]
                if mensaje.get("destinatario") and not existente.get("destinatario"):
                    existente["destinatario"] = mensaje["destinatario"]
                    enriquecidos = True
                continue
            registro = dict(mensaje)
            registro["jugador_id"] = resolver(mensaje["remitente"], mensaje["coords"])
            registro["guardado"] = ahora.isoformat(timespec="seconds")
            registros.append(registro)
            conocidos[clave] = registro
            nuevos += 1
        if nuevos or enriquecidos:
            registros.sort(key=_clave)
            archivo.parent.mkdir(parents=True, exist_ok=True)
            temporal = archivo.with_suffix(".tmp")
            temporal.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporal, archivo)
        return nuevos, repetidos


def buscar(archivo: Path, jugador: str, ids_por_nombre: Iterable[int] = ()) -> list[dict]:
    """Mensajes de un jugador, por id (número) o por nombre (parcial, sin distinguir mayúsculas), ordenados por fecha.

    Por nombre se incluyen los mensajes de los ids dados (jugadores que se llaman así ahora) y los de cualquier
    id que hubiera guardado con ese nombre (así siguen apareciendo tras un cambio de nombre).
    Los mensajes sin id se buscan por el nombre con el que se recibieron.
    """
    registros = _leer(archivo)
    texto = jugador.strip()
    if texto.isdigit():
        pid = int(texto)
        elegidos = [r for r in registros if r.get("jugador_id") == pid]
    else:
        buscado = texto.lower()
        por_nombre = {r["remitente"].lower() for r in registros if buscado in r["remitente"].lower()}
        ids = set(ids_por_nombre) | {r["jugador_id"] for r in registros if r.get("jugador_id") is not None and buscado in r["remitente"].lower()}
        elegidos = [
            r for r in registros
            if (r.get("jugador_id") in ids) or (r.get("jugador_id") is None and r["remitente"].lower() in por_nombre)
        ]
    return sorted(elegidos, key=lambda r: (r["fecha"], r.get("guardado", "")))
