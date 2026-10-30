"""Consultas sobre jugadores y alianzas."""

from ..normalizacion import nombre_jugador, parsear_planetas
from .registro import Parametro, Resultado, consulta


@consulta("jugadores", "Lista de todos los jugadores del universo")
def jugadores(contexto):
    datos = contexto.jugadores()
    return Resultado(datos=datos, titulo="Jugadores", resumen=[f"Total: {len(datos)}"])


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
