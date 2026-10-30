"""Consultas sobre la distribución de jugadores por galaxia y distancias entre coordenadas."""

from collections import Counter

from ..geometria import distancia_entre, parsear_coords
from ..normalizacion import parsear_planetas
from .registro import Parametro, Resultado, consulta


@consulta(
    "distribucion_galaxias",
    "Planetas de los jugadores del top agrupados por galaxia",
    (Parametro("limite", "Tamaño del top (highscore de flota) a revisar", int, 50),),
)
def distribucion_galaxias(contexto, limite=50):
    srv = contexto.servidor()
    contador: Counter = Counter()
    top = contexto.highscore(1, 2)[:limite]
    for _, detalle, error in contexto.detalles([e["id"] for e in top]):
        if error or detalle is None:
            continue
        for p in parsear_planetas(detalle):
            contador[parsear_coords(p["coords"])[0]] += 1
    datos = [{"galaxia": g, "planetas": contador.get(g, 0)} for g in range(1, srv["galaxias"] + 1)]
    return Resultado(
        datos=datos,
        titulo=f"Distribución por galaxia (top {limite} de flota)",
        resumen=[f"Planetas contados: {sum(contador.values())}"],
    )


@consulta(
    "distancia",
    "Distancia en galaxias y sistemas entre dos coordenadas (respeta el donut)",
    (
        Parametro("origen", "Coordenadas G:S:P", str, obligatorio=True),
        Parametro("destino", "Coordenadas G:S:P", str, obligatorio=True),
    ),
)
def distancia(contexto, origen, destino):
    srv = contexto.servidor()
    d = distancia_entre(origen, destino, srv)
    return Resultado(
        datos={"origen": origen, "destino": destino, **d},
        titulo=f"Distancia {origen} -> {destino}",
        resumen=[f"Galaxias: {d['galaxias']}", f"Sistemas: {d['sistemas']}"],
    )
