"""Registro de consultas. Para añadir una consulta basta con decorar una función con @consulta."""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class Parametro:
    nombre: str
    descripcion: str
    tipo: type = str
    defecto: Any = None
    obligatorio: bool = False
    opciones: Optional[tuple] = None


@dataclass
class Resultado:
    datos: Any
    titulo: str
    resumen: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Consulta:
    id: str
    descripcion: str
    parametros: tuple[Parametro, ...]
    funcion: Callable[..., Resultado]


CONSULTAS: dict[str, Consulta] = {}


def consulta(id: str, descripcion: str, parametros: tuple[Parametro, ...] = ()):
    """Registra la función como consulta. Debe recibir (contexto, **parametros) y devolver Resultado."""
    def decorador(funcion: Callable[..., Resultado]) -> Callable[..., Resultado]:
        if id in CONSULTAS:
            raise ValueError(f"Consulta duplicada: {id}")
        CONSULTAS[id] = Consulta(id, descripcion, tuple(parametros), funcion)
        return funcion
    return decorador


def convertir_parametro(parametro: Parametro, valor: Any) -> Any:
    if parametro.tipo is bool:
        if isinstance(valor, bool):
            return valor
        return str(valor).lower() in ("1", "si", "sí", "true", "s", "y", "yes")
    convertido = parametro.tipo(valor)
    if parametro.opciones is not None and convertido not in parametro.opciones:
        raise ValueError(f"'{parametro.nombre}' debe ser uno de {parametro.opciones}")
    return convertido


def obtener_parametros(consulta_: Consulta, crudos: dict[str, Any]) -> dict[str, Any]:
    """Combina los valores recibidos con los valores por defecto y valida los obligatorios."""
    conocidos = {p.nombre for p in consulta_.parametros}
    desconocidos = set(crudos) - conocidos
    if desconocidos:
        raise ValueError(f"Parámetros desconocidos para {consulta_.id}: {', '.join(sorted(desconocidos))}")
    valores = {}
    for p in consulta_.parametros:
        if p.nombre in crudos and crudos[p.nombre] not in (None, ""):
            valores[p.nombre] = convertir_parametro(p, crudos[p.nombre])
        elif p.obligatorio:
            raise ValueError(f"Falta el parámetro obligatorio '{p.nombre}'")
        else:
            valores[p.nombre] = p.defecto
    return valores
