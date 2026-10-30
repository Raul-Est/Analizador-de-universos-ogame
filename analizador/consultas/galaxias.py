"""Consultas sobre la distribución de jugadores por galaxia y distancias entre coordenadas."""

from collections import Counter

from itertools import combinations

from ..geometria import distancia_circular, parsear_coords
from ..normalizacion import nombre_jugador, parsear_planetas
from .registro import Parametro, Resultado, consulta


@consulta(
    "distribucion_galaxias",
    "Planetas de los N mejores del ranking militar por galaxia",
    (Parametro("limite", "Tamaño del top (ranking militar = flota) a revisar", int, 50),),
)
def distribucion_galaxias(contexto, limite=50):
    srv = contexto.servidor()
    contador: Counter = Counter()
    top = contexto.highscore(1, 3)[:limite]
    for _, detalle, error in contexto.detalles([e["id"] for e in top]):
        if error or detalle is None:
            continue
        for p in parsear_planetas(detalle):
            contador[parsear_coords(p["coords"])[0]] += 1
    datos = [{"galaxia": g, "planetas": contador.get(g, 0)} for g in range(1, srv["galaxias"] + 1)]
    return Resultado(
        datos=datos,
        titulo=f"Distribución por galaxia (top {limite} de flota)",
        resumen=[
            f"Planetas contados: {sum(contador.values())}",
            f"Naves del top {len(top)}: {sum(e.get('ships') or 0 for e in top):,}".replace(",", "."),
        ],
    )


def _unidades(sistemas: int, planetas: int) -> int:
    """Distancia de vuelo de OGame dentro de una galaxia."""
    if sistemas:
        return 2700 + 95 * sistemas
    if planetas:
        return 1000 + 5 * planetas
    return 5


@consulta(
    "distancia",
    "Distancia entre los planetas de un jugador por galaxia (respeta el donut)",
    (Parametro("jugador", "Id o nombre (parcial) del jugador", str, obligatorio=True),),
)
def distancia(contexto, jugador):
    srv = contexto.servidor()
    pid = contexto.resolver_jugador(jugador)
    detalle = contexto.detalle_jugador(pid)
    por_galaxia: dict[int, list[tuple[str, int, int]]] = {}
    for p in parsear_planetas(detalle):
        g, s, pl = parsear_coords(p["coords"])
        por_galaxia.setdefault(g, []).append((p["coords"], s, pl))
    datos = []
    for g in sorted(por_galaxia):
        planetas = sorted(por_galaxia[g], key=lambda t: (t[1], t[2]))
        for (c1, s1, p1), (c2, s2, p2) in combinations(planetas, 2):
            sistemas = distancia_circular(s1, s2, srv["sistemas"], srv["donut_sistema"])
            datos.append(
                {
                    "galaxia": g,
                    "planeta_a": c1,
                    "planeta_b": c2,
                    "sistemas": sistemas,
                    "unidades": _unidades(sistemas, abs(p1 - p2)),
                }
            )
    nombre = nombre_jugador(detalle)
    return Resultado(
        datos=datos,
        titulo=f"Distancias entre planetas de {nombre} ({pid}) por galaxia",
        resumen=[
            f"Planetas: {sum(len(v) for v in por_galaxia.values())}",
            f"Galaxias con planetas: {len(por_galaxia)}",
            f"Pares medidos: {len(datos)}",
        ],
    )
