"""Consultas sobre el highscore (ranking) de jugadores o alianzas."""

from .registro import Parametro, Resultado, consulta

CATEGORIAS = {1: "jugadores", 2: "alianzas"}
TIPOS = {0: "economía", 1: "investigación", 2: "flota", 3: "militar", 4: "militar construido",
         5: "militar destruido", 6: "honor", 7: "pérdidas"}


@consulta(
    "ranking",
    "Ranking del highscore por categoría y tipo",
    (
        Parametro("categoria", "1 = jugadores, 2 = alianzas", int, 1, opciones=(1, 2)),
        Parametro("tipo", "0 economía, 1 investigación, 2 flota, 3 militar, 4-7 otros", int, 3,
                  opciones=tuple(TIPOS)),
        Parametro("limite", "Número de posiciones a mostrar", int, 200),
    ),
)
def ranking(contexto, categoria=1, tipo=3, limite=200):
    nombres = contexto.nombres_ranking(categoria)
    entradas = contexto.highscore(categoria, tipo)[:limite]
    datos = [
        {
            "posicion": e["position"],
            "id": e["id"],
            "nombre": nombres.get(e["id"]),
            "puntuacion": e["score"],
            "naves": e["ships"],
        }
        for e in entradas
    ]
    return Resultado(
        datos=datos,
        titulo=f"Ranking de {CATEGORIAS[categoria]} - {TIPOS[tipo]}",
        resumen=[f"Posiciones: {len(datos)}"],
    )
