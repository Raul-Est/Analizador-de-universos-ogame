"""Seguimiento en vivo de puntos militares destruidos y perdidos."""

from .. import ventana
from .registro import Parametro, Resultado, consulta


@consulta(
    "seguimiento_vivo",
    "SEGUIMIENTO EN VIVO: puntos destruidos (verde) y perdidos (rojo), se actualiza cada hora",
    (Parametro("top", "Jugadores a mostrar por actualización en cada lado (ganan / pierden)", int, 10),),
)
def seguimiento_vivo(contexto, top=10):
    """Abre una ventana que se actualiza sola hasta que se cierra; devuelve los cambios recibidos."""
    datos = ventana.abrir(contexto, top)
    return Resultado(
        datos=datos,
        titulo="Seguimiento en vivo de puntos destruidos y perdidos",
        resumen=[f"Cambios registrados durante la sesión: {len(datos)}"],
    )
