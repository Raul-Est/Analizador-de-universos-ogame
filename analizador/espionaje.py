"""Lectura de informes de espionaje de OGame pegados como texto."""

import re
from typing import Any, Optional

# Títulos con los que puede empezar el cuerpo del informe. Una vez dentro, cualquier otro título
# (p. ej. "Campo de escombros") se detecta porque va seguido de una línea que no es un número.
SECCIONES_CONOCIDAS = {
    "recursos": "Recursos",
    "flotas": "Flotas",
    "defensa": "Defensa",
    "edificio": "Edificio",
    "edificios": "Edificio",
    "investigación": "Investigación",
    "investigacion": "Investigación",
    "investigación de forma de vida": "Investigación de forma de vida",
    "campo de escombros": "Campo de escombros",
}
_NUMERO = re.compile(r"-?\d[\d.,\s]*")
_ESTADO = re.compile(r"\((.*)\)")
_JUGADOR_Y_ESTADO = re.compile(r"(.*?)\s*\(([^()]*)\)")
_IMAGEN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_UBICACION = re.compile(r"\ben\s+(\S+)\s*\[?\s*(.*?)\s*\[(\d+:\d+:\d+)\]")
_FECHA = re.compile(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})")
# Al copiar desde la página el título de sección puede venir pegado al primer dato ("FlotasNave pequeña de carga").
# Va de mayor a menor longitud y se distingue mayúsculas para no partir "EdificioSensor Phalanx".
TITULOS_PEGADOS = ("Investigación de forma de vida", "Campo de escombros", "Investigación", "Recursos", "Flotas", "Defensa", "Edificio")
ORDEN_CABECERA = ("Jugador", "Estado", "Coordenadas", "Ubicación", "Fecha del informe")
MAX_CLAVE = 45


def _es_numero(texto: str) -> bool:
    return _NUMERO.fullmatch(texto) is not None


def _numero(texto: str) -> int:
    return int(re.sub(r"[.,\s]", "", texto))


def _separar_titulo(linea: str) -> list[str]:
    for titulo in TITULOS_PEGADOS:
        if linea.startswith(titulo) and len(linea) > len(titulo) and linea[len(titulo)] not in ": ":
            return [titulo, linea[len(titulo):].strip()]
    return [linea]


def _leer_titulo(titulo: Optional[str]) -> dict[str, str]:
    """Coordenadas, lugar y fecha del título («Informe de espionaje en Luna Nombre [G:S:P] dd.mm.aaaa hh:mm:ss»).

    Tolera que falte «Informe de espionaje en», el nombre del lugar o que la fecha venga en otra línea.
    """
    datos: dict[str, str] = {}
    if not titulo:
        return datos
    coordenadas = re.search(r"\[(\d+:\d+:\d+)\]", titulo)
    if coordenadas:
        datos["Coordenadas"] = coordenadas.group(1)
        antes = titulo[:coordenadas.start()]
        antes = re.sub(r"^.*?\ben\s+", "", antes) if re.search(r"\ben\s", antes) else antes
        antes = re.sub(r"[\[\]()]", " ", antes)
        ubicacion = " ".join(antes.split())
        if ubicacion:
            datos["Ubicación"] = ubicacion
    fecha = _FECHA.search(titulo)
    if fecha:
        datos["Fecha del informe"] = f"{fecha.group(1)} {fecha.group(2)}"
    return datos


def _preparar(texto: str) -> tuple[list[str], dict[str, str]]:
    """Líneas limpias (sin imágenes ni vacías, títulos separados) y datos de la línea de título."""
    lineas: list[str] = []
    titulo: list[str] = []
    en_cabecera = True
    for crudo in (texto or "").replace("\r", "").split("\n"):
        linea = _IMAGEN.sub("", crudo).strip()
        if not linea:
            continue
        if en_cabecera and linea.lower().startswith("jugador"):
            en_cabecera = False
        if en_cabecera and (linea.startswith("Informe de espionaje") or re.search(r"\[\d+:\d+:\d+\]", linea) or _FECHA.fullmatch(linea)):
            titulo.append(linea)
            continue
        lineas.extend(_separar_titulo(linea))
    return lineas, _leer_titulo(" ".join(titulo))


def reparar_cabecera(cabecera: dict) -> dict:
    """Corrige cabeceras guardadas con un título mal leído («Luna [5» = «499:9]», «30.10.2026 18» = «19:35»)."""
    arreglada: dict = {}
    for clave, valor in cabecera.items():
        lugar = re.fullmatch(r"(?:(\S+)\s*)?\[(\d+)", clave)
        fecha = re.fullmatch(r"(\d{2}\.\d{2}\.\d{4} \d{2})", clave)
        if lugar and re.fullmatch(r"\d+:\d+\]", str(valor)):
            arreglada["Coordenadas"] = f"{lugar.group(2)}:{str(valor)[:-1]}"
            if lugar.group(1):
                arreglada["Ubicación"] = lugar.group(1)
        elif fecha and re.fullmatch(r"\d{2}:\d{2}", str(valor)):
            arreglada["Fecha del informe"] = f"{clave}:{valor}"
        else:
            arreglada[clave] = valor
    ordenada = {k: arreglada[k] for k in ORDEN_CABECERA if k in arreglada}
    ordenada.update({k: v for k, v in arreglada.items() if k not in ordenada})
    return ordenada


def _leer_cabecera(lineas: list[str], i: int, cabecera: dict, mensajes: list) -> int:
    linea = lineas[i]
    if linea.endswith(":"):
        clave = linea[:-1].strip()
        valor = lineas[i + 1] if i + 1 < len(lineas) else ""
        i += 2
        if clave.lower() == "jugador" and i < len(lineas) and _ESTADO.fullmatch(lineas[i]):
            cabecera[clave] = valor
            cabecera["Estado"] = _ESTADO.fullmatch(lineas[i]).group(1).strip()
            return i + 1
        cabecera[clave] = valor
        return i
    clave, separador, valor = linea.partition(":")
    if separador and len(clave) <= MAX_CLAVE:
        clave, valor = clave.strip(), valor.strip()
        con_estado = _JUGADOR_Y_ESTADO.fullmatch(valor)
        if clave.lower() == "jugador" and con_estado:
            cabecera[clave] = con_estado.group(1)
            cabecera["Estado"] = con_estado.group(2).strip()
        else:
            cabecera[clave] = valor
    else:
        mensajes.append(linea)
    return i + 1


def parsear_informe(texto: str) -> dict[str, Any]:
    """Devuelve {'cabecera': {...}, 'mensajes': [...], 'secciones': {titulo: {concepto: cantidad}}}.

    Acepta el texto copiado con o sin la línea de título (que aporta coordenadas, lugar y fecha del informe).
    """
    lineas, datos_titulo = _preparar(texto)
    cabecera: dict[str, str] = {}
    mensajes: list[str] = []
    secciones: dict[str, dict[str, int]] = {}
    actual = None
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        conocida = SECCIONES_CONOCIDAS.get(linea.lower())
        if actual is None and not conocida:
            i = _leer_cabecera(lineas, i, cabecera, mensajes)
            continue
        siguiente = lineas[i + 1] if i + 1 < len(lineas) else None
        if conocida or (not _es_numero(linea) and siguiente is not None and not _es_numero(siguiente)):
            actual = conocida or linea
            secciones.setdefault(actual, {})
            i += 1
        elif siguiente is not None and _es_numero(siguiente) and not _es_numero(linea):
            secciones[actual][linea] = _numero(siguiente)
            i += 2
        else:
            i += 1
    if "Jugador" not in cabecera and not secciones:
        raise ValueError("No se reconoce un informe de espionaje en el texto pegado.")
    todo = {**cabecera, **datos_titulo}
    ordenada = {k: todo[k] for k in ORDEN_CABECERA if k in todo}
    ordenada.update({k: v for k, v in todo.items() if k not in ordenada})
    return {"cabecera": ordenada, "mensajes": mensajes, "secciones": secciones}


def filas_planas(informe: dict) -> list[dict]:
    """Una fila por dato (seccion, concepto, valor), apta para CSV y Markdown."""
    filas = [{"seccion": "Cabecera", "concepto": k, "valor": v} for k, v in informe["cabecera"].items()]
    filas += [{"seccion": "Cabecera", "concepto": "Mensaje", "valor": m} for m in informe["mensajes"]]
    for titulo, datos in informe["secciones"].items():
        filas += [{"seccion": titulo, "concepto": c, "valor": v} for c, v in datos.items()]
    return filas
