"""Configuración del universo activo y de la aplicación."""

import json
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_CONFIG = RAIZ / "universo.json"
CARPETA_SALIDA = RAIZ / "output"

DEFAULT_IDIOMA = "es"
DEFAULT_NUMERO = 268
DEFAULT_PAUSA = 0.25


@dataclass(frozen=True)
class Universo:
    idioma: str
    numero: int

    @classmethod
    def desde_texto(cls, texto: str) -> "Universo":
        """Convierte 'es:268' en Universo('es', 268)."""
        partes = texto.strip().lower().split(":")
        if len(partes) != 2 or not partes[0] or not partes[1].isdigit():
            raise ValueError(f"Universo no válido: {texto!r}. Usa el formato idioma:numero, por ejemplo es:268")
        return cls(partes[0], int(partes[1]))

    @property
    def clave(self) -> str:
        return f"{self.idioma}-{self.numero}"

    @property
    def host(self) -> str:
        return f"s{self.numero}-{self.idioma}.ogame.gameforge.com"

    @property
    def url_api(self) -> str:
        return f"https://{self.host}/api"

    def __str__(self) -> str:
        return f"{self.idioma}:{self.numero}"


@dataclass(frozen=True)
class Configuracion:
    universo: Universo
    pausa_segundos: float = DEFAULT_PAUSA
    carpeta_salida: Path = CARPETA_SALIDA


def cargar_configuracion(archivo: Path = ARCHIVO_CONFIG) -> Configuracion:
    """Lee universo.json. Si no existe, usa Mars (es:268)."""
    datos = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    universo = Universo(
        idioma=str(datos.get("idioma", DEFAULT_IDIOMA)).lower(),
        numero=int(datos.get("numero", DEFAULT_NUMERO)),
    )
    return Configuracion(
        universo=universo,
        pausa_segundos=float(datos.get("pausa_segundos", DEFAULT_PAUSA)),
    )
