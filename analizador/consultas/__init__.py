"""Consultas disponibles. Importar los módulos registra sus consultas con @consulta."""

from . import galaxias, jugadores, lunas, ranking, servidor, vivo  # noqa: F401
from .registro import CONSULTAS, Consulta, Parametro, Resultado, consulta  # noqa: F401
