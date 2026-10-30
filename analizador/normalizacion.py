"""Conversión de las respuestas JSON (toJson=1) de la API de OGame a estructuras simples."""

from typing import Any, Optional


def elementos(data: Any, clave: str) -> list:
    """Devuelve `data[clave]` como lista.

    OGame devuelve un objeto en lugar de una lista cuando solo hay un elemento,
    por eso siempre se normaliza a lista. Si `data` ya es una lista, se devuelve tal cual.
    """
    if isinstance(data, dict):
        data = data.get(clave)
    if data is None or data == "":
        return []
    return data if isinstance(data, list) else [data]


def atributos(entrada: Any) -> dict:
    """Devuelve el bloque '@attributes' de una entrada, o la propia entrada si no lo tiene."""
    if not isinstance(entrada, dict):
        return {}
    attrs = entrada.get("@attributes")
    return attrs if isinstance(attrs, dict) else entrada


def entero(valor: Any) -> Optional[int]:
    if valor is None or valor == "":
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def parsear_servidor(data: dict) -> dict:
    """Resumen del universo a partir de serverData.xml."""
    return {
        "idioma": data.get("language"),
        "numero": entero(data.get("number")),
        "nombre": data.get("name"),
        "dominio": data.get("domain"),
        "version": data.get("version"),
        "galaxias": entero(data.get("galaxies")),
        "sistemas": entero(data.get("systems")),
        "donut_galaxia": str(data.get("donutGalaxy")) == "1",
        "donut_sistema": str(data.get("donutSystem")) == "1",
        "velocidad_economia": entero(data.get("speed")),
        "velocidad_flota_guerra": entero(data.get("speedFleetWar")),
        "factor_escombros": data.get("debrisFactor"),
        "tamano_campos_bonus": entero(data.get("bonusFields")),
    }


def parsear_jugadores(data: Any) -> list[dict]:
    resultado = []
    for entrada in elementos(data, "player"):
        attrs = atributos(entrada)
        pid = entero(attrs.get("id"))
        if pid is None:
            continue
        resultado.append({
            "id": pid,
            "name": attrs.get("name"),
            "status": attrs.get("status", ""),
            "alliance": entero(attrs.get("alliance")),
        })
    return resultado


def parsear_alianzas(data: Any) -> list[dict]:
    resultado = []
    for entrada in elementos(data, "alliance"):
        attrs = atributos(entrada)
        aid = entero(attrs.get("id"))
        if aid is None:
            continue
        resultado.append({"id": aid, "name": attrs.get("name"), "tag": attrs.get("tag")})
    return resultado


def parsear_highscore(data: Any) -> list[dict]:
    """Entradas ordenadas del highscore: id, position, score, ships."""
    resultado = []
    for entrada in elementos(data, "player") or elementos(data, "alliance"):
        attrs = atributos(entrada)
        pid = entero(attrs.get("id"))
        if pid is None:
            continue
        resultado.append({
            "id": pid,
            "position": entero(attrs.get("position")),
            "score": entero(attrs.get("score")),
            "ships": entero(attrs.get("ships")),
        })
    return resultado


def nombre_jugador(detalle: Any) -> Optional[str]:
    return atributos(detalle).get("name")


def parsear_planetas(detalle: Any) -> list[dict]:
    """Planetas de un jugador (playerData.xml): [{'coords': 'G:S:P', 'lunas': n}]."""
    if not isinstance(detalle, dict):
        return []
    planetas = []
    for pl in elementos(detalle.get("planets"), "planet"):
        coords = pl.get("coords") or atributos(pl).get("coords")
        if not coords:
            continue
        planetas.append({"coords": coords, "lunas": len(elementos(pl, "moon"))})
    return planetas


def coordenadas_lunas(detalle: Any) -> list[str]:
    """Coordenadas de cada luna del jugador (una entrada por luna)."""
    return [p["coords"] for p in parsear_planetas(detalle) for _ in range(p["lunas"])]
