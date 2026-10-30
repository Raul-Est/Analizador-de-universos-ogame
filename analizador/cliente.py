"""Cliente HTTP para la API pública de OGame: pausas entre peticiones y reintentos."""

import time
from typing import Any, Optional

import requests

from .config import Universo

REINTENTOS = 3
ESTADOS_REINTENTABLES = {429, 500, 502, 503, 504}


class ErrorApi(Exception):
    """Error al consultar la API (red, HTTP o respuesta no válida)."""


class ClienteOgame:
    def __init__(
        self,
        universo: Universo,
        pausa_segundos: float = 1.0,
        timeout: float = 15.0,
        sesion: Optional[requests.Session] = None,
    ):
        self.universo = universo
        self.pausa_segundos = pausa_segundos
        self.timeout = timeout
        self._sesion = sesion or requests.Session()
        self._sesion.headers["User-Agent"] = "analizador-universos-ogame/1.0"
        self._ultima_peticion = 0.0

    def get_json(self, ruta: str, **params: Any) -> Any:
        """Consulta `<api del universo>/<ruta>` pidiendo JSON (toJson=1)."""
        return self.get_json_url(f"{self.universo.url_api}/{ruta}", {**params, "toJson": 1})

    def get_json_url(self, url: str, params: Optional[dict] = None) -> Any:
        """Consulta una URL absoluta y devuelve el JSON decodificado."""
        ultimo_error: Optional[ErrorApi] = None
        for intento in range(1, REINTENTOS + 1):
            self._esperar_pausa()
            try:
                resp = self._sesion.get(url, params=params or {}, timeout=self.timeout)
            except requests.RequestException as exc:
                ultimo_error = ErrorApi(f"Error de red en {url}: {exc}")
            else:
                if resp.status_code in ESTADOS_REINTENTABLES:
                    ultimo_error = ErrorApi(f"HTTP {resp.status_code} en {url}")
                elif resp.status_code >= 400:
                    raise ErrorApi(f"HTTP {resp.status_code} en {url}")
                else:
                    return self._decodificar(resp, url)
            if intento < REINTENTOS:
                time.sleep(2 * intento)
        raise ultimo_error

    def _esperar_pausa(self) -> None:
        transcurrido = time.monotonic() - self._ultima_peticion
        if transcurrido < self.pausa_segundos:
            time.sleep(self.pausa_segundos - transcurrido)
        self._ultima_peticion = time.monotonic()

    @staticmethod
    def _decodificar(resp: requests.Response, url: str) -> Any:
        try:
            return resp.json()
        except ValueError as exc:
            raise ErrorApi(
                f"Respuesta no JSON de {url}. Comprueba que el universo existe y está abierto "
                "(si no, la web devuelve HTML)."
            ) from exc
