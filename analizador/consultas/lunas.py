"""Consultas sobre lunas de los jugadores con más puntos militares."""

from ..normalizacion import coordenadas_lunas, nombre_jugador
from .registro import Parametro, Resultado, consulta


@consulta(
    "top_lunas",
    "Jugadores del top con una o más lunas, con sus coordenadas",
    (
        Parametro("limite", "Tamaño del top (highscore militar) a revisar", int, 200),
        Parametro("lunas_min", "Mínimo de lunas por jugador", int, 1),
        Parametro("lunas_max", "Máximo de lunas por jugador (0 = sin límite)", int, 0),
    ),
)
def top_lunas(contexto, limite=200, lunas_min=1, lunas_max=0):
    filas = []
    top = contexto.highscore(1, 3)[:limite]
    for pid, detalle, error in contexto.detalles([e["id"] for e in top]):
        if error or detalle is None:
            continue
        coords = coordenadas_lunas(detalle)
        n = len(coords)
        if n < lunas_min or (lunas_max and n > lunas_max):
            continue
        filas.append({"id": pid, "nombre": nombre_jugador(detalle), "lunas": n, "coordenadas": coords})
    filas.sort(key=lambda f: f["lunas"], reverse=True)
    return Resultado(
        datos=filas,
        titulo=f"Top {limite} con lunas ({lunas_min}" + (f"-{lunas_max}" if lunas_max else "+") + ")",
        resumen=[f"Jugadores encontrados: {len(filas)}"],
    )


@consulta(
    "alianza_top_lunas",
    "Coordenadas de lunas de los miembros de una alianza",
    (
        Parametro("alianza", "Id o nombre (parcial) de la alianza", str, obligatorio=True),
        Parametro("top", "Número de miembros a revisar (por naves y puntos)", int, 100),
    ),
)
def alianza_top_lunas(contexto, alianza, top=100):
    al = contexto.resolver_alianza(alianza)
    miembros = contexto.miembros_alianza(al["id"])[:top]
    filas, coords_unicas = [], set()
    for m in miembros:
        coords = coordenadas_lunas(contexto.detalle_jugador(m["id"]))
        if not coords:
            continue
        coords_unicas.update(coords)
        filas.append({"id": m["id"], "nombre": m["nombre"], "lunas": len(coords), "coordenadas": coords})
    filas.sort(key=lambda f: f["lunas"], reverse=True)
    return Resultado(
        datos=filas,
        titulo=f"Lunas de {al.get('name')} [{al.get('tag')}]",
        resumen=[f"Miembros con lunas: {len(filas)}", f"Coordenadas de luna únicas: {len(coords_unicas)}"],
    )
