"""Coordenadas y distancias en el universo, respetando el donut (universo circular)."""

import re

_COORDS = re.compile(r"^\s*(\d+):(\d+):(\d+)\s*$")


def parsear_coords(texto: str) -> tuple[int, int, int]:
    """Convierte 'G:S:P' en (galaxia, sistema, planeta)."""
    m = _COORDS.match(texto or "")
    if not m:
        raise ValueError(f"Coordenadas no válidas: {texto!r}. Formato esperado: G:S:P")
    return tuple(int(x) for x in m.groups())


def distancia_circular(a: int, b: int, total: int, circular: bool) -> int:
    """Diferencia entre dos índices. Si el universo es circular, se toma el camino más corto."""
    diferencia = abs(a - b)
    if circular and total > 0:
        diferencia = min(diferencia, total - diferencia)
    return diferencia


def distancia_entre(origen: str, destino: str, servidor: dict) -> dict:
    """Diferencia en galaxias y sistemas entre dos coordenadas según la configuración del servidor."""
    g1, s1, _ = parsear_coords(origen)
    g2, s2, _ = parsear_coords(destino)
    return {
        "galaxias": distancia_circular(g1, g2, servidor["galaxias"], servidor["donut_galaxia"]),
        "sistemas": distancia_circular(s1, s2, servidor["sistemas"], servidor["donut_sistema"]),
    }
