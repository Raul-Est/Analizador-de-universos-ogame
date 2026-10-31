"""Formulario web local para pegar mensajes del juego (se guardan por jugador). Solo escucha en 127.0.0.1."""

import html
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from . import mensajes as almacen
from .cliente import ErrorApi

MAX_CUERPO = 2_000_000

PAGINA = """<!doctype html><html lang="es"><meta charset="utf-8"><title>Mensajes del juego</title>
<style>body{{font-family:Segoe UI,sans-serif;background:#1d2229;color:#dde;max-width:1000px;margin:20px auto;padding:0 12px}}
textarea{{width:100%;height:260px;background:#12161b;color:#dde;border:1px solid #445;padding:8px;font-family:Consolas,monospace}}
button{{background:#2d6cdf;color:#fff;border:0;padding:8px 16px;cursor:pointer;border-radius:4px}}
table{{border-collapse:collapse;margin:8px 0 18px;width:100%}}td,th{{border:1px solid #445;padding:3px 10px;text-align:left;vertical-align:top}}
td.t{{white-space:pre-wrap}}.err{{color:#ff6b6b}}.ok{{color:#6bff8f}}</style>
<h1>Mensajes del juego</h1>
<form method="post" action="/guardar">
<textarea name="texto" placeholder="Pega aquí los mensajes (con su cabecera '- remitente dd.mm.aaaa hh:mm:ss')">{texto}</textarea><br>
<button>Guardar</button></form>{resultado}"""


def _tabla(mensajes: list[dict]) -> str:
    filas = "".join(
        f"<tr><td>{html.escape(m['fecha'].replace('T', ' '))}</td><td>{html.escape(m['remitente'])}</td>"
        f"<td>{html.escape(m['coords'])}</td><td>{html.escape(m['alianza'] or '')}</td>"
        f"<td class='t'>{html.escape(m['texto'])}</td></tr>"
        for m in mensajes
    )
    return ("<table><tr><th>Fecha</th><th>Remitente</th><th>Coords</th><th>Alianza</th><th>Mensaje</th></tr>"
            f"{filas}</table>")


def _manejador(carpeta: Path, resolver):
    class Manejador(BaseHTTPRequestHandler):
        def _responder(self, cuerpo: bytes, estado=200):
            self.send_response(estado)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _pagina(self, texto="", resultado="", estado=200):
            self._responder(PAGINA.format(texto=html.escape(texto), resultado=resultado).encode("utf-8"), estado)

        def do_GET(self):
            if self.path == "/":
                self._pagina()
            else:
                self._responder(b"No encontrado", 404)

        def do_POST(self):
            largo = int(self.headers.get("Content-Length") or 0)
            if largo > MAX_CUERPO:
                self._responder("Texto demasiado grande".encode(), 413)
                return
            campos = parse_qs(self.rfile.read(largo).decode("utf-8", "replace"))
            texto = (campos.get("texto") or [""])[0]
            if self.path != "/guardar":
                self._responder(b"No encontrado", 404)
                return
            try:
                analizados = almacen.analizar_mensajes(texto)
                if not analizados:
                    raise ValueError("No se encontró ningún mensaje. Pega el texto completo con su cabecera.")
                nuevos, repetidos = almacen.guardar_mensajes(carpeta / almacen.NOMBRE_ARCHIVO, analizados, resolver)
            except (ValueError, OSError, ErrorApi) as exc:
                self._pagina(texto, f"<p class='err'>{html.escape(str(exc))}</p>")
                return
            aviso = f"{nuevos} mensaje(s) guardado(s); {repetidos} ya estaban guardados."
            self._pagina("", f"<p class='ok'>{html.escape(aviso)}</p>{_tabla(analizados)}")

        def log_message(self, *args):
            pass

    return Manejador


def abrir(carpeta: Path, resolver, abrir_navegador: bool = True) -> None:
    """Sirve el formulario hasta Ctrl+C."""
    carpeta.mkdir(parents=True, exist_ok=True)
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _manejador(carpeta, resolver))
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"
    print(f"Formulario en {url}  (Ctrl+C para cerrar)")
    print(f"Los mensajes se guardan en {carpeta / almacen.NOMBRE_ARCHIVO}")
    if abrir_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
