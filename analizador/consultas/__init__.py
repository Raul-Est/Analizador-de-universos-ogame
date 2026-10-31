"""Consultas disponibles. Importar los módulos registra sus consultas con @consulta."""

from . import galaxias, jugadores, lunas, ranking, servidor, vivo, espionaje, mensajes  # noqa: F401,I001
from .registro import CONSULTAS, Consulta, Parametro, Resultado, consulta  # noqa: F401
