"""Contexto de ejecución: universo activo, cliente HTTP y caché de los datos ya descargados."""

import json
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from . import normalizacion as n
from .cliente import ClienteOgame, ErrorApi
from .config import Universo

TTL_CACHE_SEGUNDOS = 6 * 3600


def _coincidencias(lista: list[dict], texto: str) -> list[dict]:
    buscado = texto.lower()
    return [e for e in lista if e.get("name") and buscado in e["name"].lower()]


def _unica(items: list[dict], tipo: str, texto: str) -> dict:
    if not items:
        raise ValueError(f"No se encontró ningún {tipo} que coincida con '{texto}'")
    if len(items) > 1:
        lista = "; ".join(f"{e['id']}: {e.get('name')}" for e in items[:20])
        raise ValueError(f"Varias coincidencias para '{texto}' ({tipo}). Usa el id exacto: {lista}")
    return items[0]


def _o_menos_uno(valor: Optional[int]) -> int:
    return -1 if valor is None else valor


class Contexto:
    """Estado de una sesión sobre un universo concreto. Al cambiar de universo se crea un Contexto nuevo."""

    def __init__(self, universo: Universo, cliente: ClienteOgame, carpeta_cache: Optional[Path] = None):
        self.universo = universo
        self.cliente = cliente
        self.carpeta_cache = carpeta_cache
        self._cache: dict[Any, Any] = {}

    def _memo(self, clave: Any, obtener: Callable[[], Any]) -> Any:
        if clave not in self._cache:
            self._cache[clave] = obtener()
        return self._cache[clave]

    def servidor(self) -> dict:
        def obtener() -> dict:
            info = n.parsear_servidor(self.cliente.get_json("serverData.xml"))
            if info["numero"] != self.universo.numero or info["idioma"] != self.universo.idioma:
                raise ErrorApi(
                    f"La API de {self.universo.host} responde con el universo "
                    f"{info['idioma']}:{info['numero']} ({info['nombre']}), no con {self.universo}"
                )
            return info
        return self._memo("servidor", obtener)

    def jugadores(self) -> list[dict]:
        return self._memo("jugadores", lambda: n.parsear_jugadores(self.cliente.get_json("players.xml")))

    def alianzas(self) -> list[dict]:
        return self._memo("alianzas", lambda: n.parsear_alianzas(self.cliente.get_json("alliances.xml")))

    def highscore(self, categoria: int = 1, tipo: int = 3) -> list[dict]:
        """Highscore completo (ordenado por posición). categoria: 1 jugadores, 2 alianzas."""
        return self._memo(
            ("highscore", categoria, tipo),
            lambda: n.parsear_highscore(self.cliente.get_json("highscore.xml", category=categoria, type=tipo)),
        )

    def nombres_ranking(self, categoria: int) -> dict[int, Optional[str]]:
        origen = self.jugadores() if categoria == 1 else self.alianzas()
        return {e["id"]: e.get("name") for e in origen}

    def detalle_jugador(self, pid: int) -> dict:
        return self._memo(("jugador", pid), lambda: self._detalle_con_disco(pid))

    def _detalle_con_disco(self, pid: int) -> dict:
        """playerData.xml cambia poco: se reutiliza el fichero descargado durante `TTL_CACHE_SEGUNDOS`."""
        ruta = self.carpeta_cache / f"jugador_{pid}.json" if self.carpeta_cache else None
        if ruta and ruta.exists() and time.time() - ruta.stat().st_mtime < TTL_CACHE_SEGUNDOS:
            try:
                return json.loads(ruta.read_text(encoding="utf-8"))
            except ValueError:
                pass
        detalle = self.cliente.get_json("playerData.xml", id=pid)
        if ruta:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps(detalle, ensure_ascii=False), encoding="utf-8")
        return detalle

    def detalles(self, pids: list[int]) -> Iterator[tuple[int, Optional[dict], Optional[str]]]:
        """Descarga el detalle de cada jugador. Devuelve (id, detalle, error) sin detener el proceso por fallos individuales."""
        for pid in pids:
            try:
                yield pid, self.detalle_jugador(pid), None
            except ErrorApi as exc:
                yield pid, None, str(exc)

    def miembros_alianza(self, alianza_id: int) -> list[dict]:
        """Jugadores de una alianza con puntos militares y naves, ordenados por naves y luego por puntos."""
        hs = {e["id"]: e for e in self.highscore(1, 3)}
        filas = []
        for j in self.jugadores():
            if j["alliance"] != alianza_id:
                continue
            entrada = hs.get(j["id"], {})
            filas.append({
                "id": j["id"],
                "nombre": j["name"],
                "estado": j["status"],
                "puntos_militares": entrada.get("score"),
                "naves": entrada.get("ships"),
            })
        filas.sort(key=lambda f: (_o_menos_uno(f["naves"]), _o_menos_uno(f["puntos_militares"])), reverse=True)
        return filas

    def resolver_jugador(self, texto: str) -> int:
        """Acepta un id numérico o un nombre (parcial, sin distinguir mayúsculas)."""
        texto = texto.strip()
        if texto.isdigit():
            return int(texto)
        return _unica(_coincidencias(self.jugadores(), texto), "jugador", texto)["id"]

    def resolver_alianza(self, texto: str) -> dict:
        texto = texto.strip()
        alianzas = self.alianzas()
        if texto.isdigit():
            return _unica([a for a in alianzas if a["id"] == int(texto)], "alianza", texto)
        return _unica(_coincidencias(alianzas, texto), "alianza", texto)
