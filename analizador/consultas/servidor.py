"""Información del universo y lista de universos del lobby."""

from ..cliente import ClienteOgame
from ..normalizacion import entero
from .registro import Parametro, Resultado, consulta

LOBBY_URL = "https://lobby.ogame.gameforge.com/api/servers"


@consulta("servidor", "Configuración del universo activo (galaxias, sistemas, donut)")
def servidor(contexto):
    info = contexto.servidor()
    forma = "circular" if info["donut_galaxia"] and info["donut_sistema"] else "no circular"
    return Resultado(
        datos=info,
        titulo=f"Universo {contexto.universo} - {info['nombre']}",
        resumen=[
            f"Galaxias: {info['galaxias']}",
            f"Sistemas por galaxia: {info['sistemas']}",
            f"Donut galaxias: {info['donut_galaxia']} | donut sistemas: {info['donut_sistema']} ({forma})",
            f"Velocidad economía: {info['velocidad_economia']}",
        ],
    )


@consulta(
    "universos_lobby",
    "Lista de universos del lobby de Gameforge (filtrable por idioma)",
    (Parametro("idioma", "Código de idioma (es, de, fr, it, en...). Vacío = todos", str, ""),),
)
def universos_lobby(contexto, idioma=""):
    respuesta = ClienteOgame(contexto.universo, pausa_segundos=0).get_json_url(LOBBY_URL)
    filtro = (idioma or "").lower()
    filas = []
    for s in respuesta:
        if filtro and str(s.get("language", "")).lower() != filtro:
            continue
        filas.append({
            "idioma": s.get("language"),
            "numero": entero(s.get("number")),
            "nombre": s.get("name"),
            "jugadores": s.get("playerCount"),
            "online": s.get("playersOnline"),
            "abierto": s.get("opened"),
            "cerrado": s.get("serverClosed"),
        })
    filas.sort(key=lambda f: (f["idioma"] or "", f["numero"] or 0))
    return Resultado(datos=filas, titulo=f"Universos del lobby ({idioma or 'todos'})", resumen=[f"Total: {len(filas)}"])
