"""Formulario web para pegar informes de espionaje (se guardan) y consulta de la última flota conocida."""

import shutil
from pathlib import Path

from .. import informes_guardados as almacen
from .. import web_espionaje
from ..config import CARPETA_SALIDA
from ..exportar import nombre_seguro
from .registro import Parametro, Resultado, consulta

SUBCARPETA_FLOTAS = "flotas"


def carpeta_flotas(universo) -> Path:
    """output/<universo>/flotas: informes guardados y todas las exportaciones de flotas del universo."""
    carpeta = CARPETA_SALIDA / universo.clave / SUBCARPETA_FLOTAS
    carpeta.mkdir(parents=True, exist_ok=True)
    antiguo = CARPETA_SALIDA / "espionaje" / almacen.NOMBRE_ARCHIVO
    nuevo = carpeta / almacen.NOMBRE_ARCHIVO
    if antiguo.exists() and not nuevo.exists():
        shutil.move(str(antiguo), str(nuevo))
    return carpeta


@consulta(
    "informe_espionaje",
    "INFORMES DE ESPIONAJE: formulario web para pegar informes (se guardan) y exportarlos (json/csv/md)",
)
def informe_espionaje(contexto):
    """Abre el formulario en el navegador y espera hasta Ctrl+C."""
    web_espionaje.abrir(carpeta_flotas(contexto.universo))
    return Resultado(datos=[], titulo="Informes de espionaje", resumen=["Formulario cerrado."])


@consulta(
    "ultima_flota",
    "ÚLTIMA FLOTA conocida de un jugador (de los informes de espionaje guardados)",
    (Parametro("jugador", "Nombre (o parte) del jugador", str, obligatorio=True),),
)
def ultima_flota(contexto, jugador):
    registro = almacen.ultimo_informe(carpeta_flotas(contexto.universo) / almacen.NOMBRE_ARCHIVO, jugador)
    filas = almacen.filas_ultima_flota(registro)
    return Resultado(
        datos=filas,
        titulo=f"Última flota conocida de {registro['jugador']}",
        resumen=[f"Informe guardado el {filas[0]['valor']}"],
        nombre_archivo=f"ultima_flota_{nombre_seguro(registro['jugador'])}",
        subcarpeta=SUBCARPETA_FLOTAS,
    )
