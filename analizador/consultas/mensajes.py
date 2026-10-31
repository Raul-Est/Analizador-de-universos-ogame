"""Mensajes del juego: formulario para pegarlos (se guardan por jugador) y consulta por nombre o id."""

from datetime import datetime
from pathlib import Path

from .. import mensajes as almacen
from .. import web_mensajes
from ..config import CARPETA_SALIDA
from ..exportar import nombre_seguro
from .registro import Parametro, Resultado, consulta

SUBCARPETA_MENSAJES = "mensajes"


def carpeta_mensajes(universo) -> Path:
    """output/<universo>/mensajes: mensajes guardados y exportaciones del universo."""
    carpeta = CARPETA_SALIDA / universo.clave / SUBCARPETA_MENSAJES
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


@consulta(
    "mensajes_formulario",
    "MENSAJES DEL JUEGO: formulario web para pegar mensajes (se guardan por jugador)",
)
def mensajes_formulario(contexto):
    """Abre el formulario en el navegador y espera hasta Ctrl+C."""
    web_mensajes.abrir(carpeta_mensajes(contexto.universo), almacen.crear_resolutor(contexto))
    return Resultado(datos=[], titulo="Mensajes del juego", resumen=["Formulario cerrado."])


@consulta(
    "mensajes_jugador",
    "MENSAJES DE UN JUGADOR (por nombre o id), ordenados por fecha de recepción",
    (Parametro("jugador", "Nombre (o parte) o id del jugador", str, obligatorio=True),),
)
def mensajes_jugador(contexto, jugador):
    ids = set()
    texto = jugador.strip()
    if not texto.isdigit():
        buscado = texto.lower()
        ids = {j["id"] for j in contexto.jugadores() if buscado in (j.get("name") or "").lower()}
    registros = almacen.buscar(carpeta_mensajes(contexto.universo) / almacen.NOMBRE_ARCHIVO, texto, ids)
    filas = [
        {
            "fecha": datetime.fromisoformat(r["fecha"]).strftime("%d/%m/%Y %H:%M:%S"),
            "remitente": r["remitente"],
            "destinatario": r.get("destinatario") or "",
            "id": "" if r.get("jugador_id") is None else r["jugador_id"],
            "alianza": r.get("alianza") or "",
            "coords": r["coords"],
            "mensaje": r["texto"],
        }
        for r in registros
    ]
    resumen = [f"{len(filas)} mensaje(s)."] if filas else ["No hay mensajes guardados de ese jugador."]
    return Resultado(
        datos=filas,
        titulo=f"Mensajes de {texto}",
        resumen=resumen,
        nombre_archivo=f"mensajes_{nombre_seguro(texto, 'jugador')}",
        subcarpeta=SUBCARPETA_MENSAJES,
    )
