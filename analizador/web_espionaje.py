"""Formulario web local para pegar informes de espionaje y exportarlos (solo escucha en 127.0.0.1)."""

import html
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from .consultas.registro import Resultado
from .espionaje import filas_planas, parsear_informe
from .exportar import guardar, nombre_seguro
from .informes_guardados import NOMBRE_ARCHIVO, guardar_informe

MAX_CUERPO = 2_000_000
TIPOS = {"json": "application/json", "csv": "text/csv", "md": "text/markdown"}

PAGINA = """<!doctype html><html lang="es"><meta charset="utf-8"><title>Informe de espionaje</title>
<style>body{{font-family:Segoe UI,sans-serif;background:#1d2229;color:#dde;max-width:1000px;margin:20px auto;padding:0 12px}}
textarea{{width:100%;height:220px;background:#12161b;color:#dde;border:1px solid #445;padding:8px;font-family:Consolas,monospace}}
button{{background:#2d6cdf;color:#fff;border:0;padding:8px 16px;margin:6px 6px 6px 0;cursor:pointer;border-radius:4px}}
table{{border-collapse:collapse;margin:8px 0 18px}}td,th{{border:1px solid #445;padding:3px 10px;text-align:left}}
td.n{{text-align:right}}h2{{margin-bottom:2px}}.err{{color:#ff6b6b}}.ok{{color:#6bff8f}}</style>
<h1>Informe de espionaje</h1>
<form method="post" action="/analizar">
<textarea name="texto" placeholder="Pega aquí el informe de espionaje">{texto}</textarea><br>
<button>Analizar</button></form>{resultado}"""


def _numero(valor) -> str:
    return f"{valor:,}".replace(",", ".") if isinstance(valor, int) else html.escape(str(valor))


def _html_informe(informe: dict, texto: str, aviso: str) -> str:
    partes = [f"<p class='ok'>{html.escape(aviso)}</p>" if aviso else "", "<h2>Cabecera</h2><table>"]
    for clave, valor in informe["cabecera"].items():
        partes.append(f"<tr><th>{html.escape(clave)}</th><td>{html.escape(valor)}</td></tr>")
    for mensaje in informe["mensajes"]:
        partes.append(f"<tr><th>Mensaje</th><td>{html.escape(mensaje)}</td></tr>")
    partes.append("</table>")
    for titulo, datos in informe["secciones"].items():
        partes.append(f"<h2>{html.escape(titulo)}</h2><table>")
        partes += [f"<tr><td>{html.escape(c)}</td><td class='n'>{_numero(v)}</td></tr>" for c, v in datos.items()]
        partes.append("</table>")
    oculto = html.escape(texto)
    for formato in TIPOS:
        partes.append(
            f"<form method='post' action='/exportar/{formato}' style='display:inline'>"
            f"<textarea name='texto' hidden>{oculto}</textarea><button>Exportar {formato.upper()}</button></form>"
        )
    return "".join(partes)


def _nombre_archivo(informe: dict) -> str:
    jugador = informe["cabecera"].get("Jugador", "informe")
    return "espionaje_" + nombre_seguro(jugador, "informe")


def exportar_informe(informe: dict, formato: str, carpeta: Path) -> Path:
    jugador = informe["cabecera"].get("Jugador", "?")
    titulo = f"Informe de espionaje de {jugador}"
    datos = informe if formato == "json" else filas_planas(informe)
    return guardar(Resultado(datos=datos, titulo=titulo, resumen=[f"Jugador: {jugador}"]), formato, carpeta, _nombre_archivo(informe))


def _manejador(carpeta: Path):
    class Manejador(BaseHTTPRequestHandler):
        def _responder(self, cuerpo: bytes, tipo="text/html; charset=utf-8", estado=200, extra=None):
            self.send_response(estado)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            for clave, valor in (extra or {}).items():
                self.send_header(clave, valor)
            self.end_headers()
            self.wfile.write(cuerpo)

        def _pagina(self, texto="", resultado="", estado=200):
            contenido = PAGINA.format(texto=html.escape(texto), resultado=resultado)
            self._responder(contenido.encode("utf-8"), estado=estado)

        def do_GET(self):
            if self.path == "/":
                self._pagina()
            else:
                self._responder(b"No encontrado", "text/plain", 404)

        def do_POST(self):
            largo = int(self.headers.get("Content-Length") or 0)
            if largo > MAX_CUERPO:
                self._responder("Texto demasiado grande".encode(), "text/plain; charset=utf-8", 413)
                return
            campos = parse_qs(self.rfile.read(largo).decode("utf-8", "replace"))
            texto = (campos.get("texto") or [""])[0]
            try:
                informe = parsear_informe(texto)
            except ValueError as exc:
                self._pagina(texto, f"<p class='err'>{html.escape(str(exc))}</p>")
                return
            if self.path == "/analizar":
                try:
                    nuevo, total = guardar_informe(carpeta / NOMBRE_ARCHIVO, informe)
                    aviso = (f"Informe guardado ({total} de este jugador)." if nuevo
                             else "Idéntico al último guardado de este jugador; no se duplica.")
                except (ValueError, OSError) as exc:
                    aviso = f"No se pudo guardar: {exc}"
                self._pagina(texto, _html_informe(informe, texto, aviso))
            elif self.path.startswith("/exportar/") and self.path[10:] in TIPOS:
                formato = self.path[10:]
                ruta = exportar_informe(informe, formato, carpeta)
                self._responder(
                    ruta.read_bytes(), TIPOS[formato] + "; charset=utf-8",
                    extra={"Content-Disposition": f'attachment; filename="{ruta.name}"'},
                )
            else:
                self._responder(b"No encontrado", "text/plain", 404)

        def log_message(self, *args):
            pass

    return Manejador


def abrir(carpeta: Path, abrir_navegador: bool = True) -> None:
    """Sirve el formulario hasta Ctrl+C. Los archivos exportados se guardan también en `carpeta`."""
    carpeta.mkdir(parents=True, exist_ok=True)
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _manejador(carpeta))
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"
    print(f"Formulario en {url}  (Ctrl+C para cerrar)")
    print(f"Los archivos exportados se guardan en {carpeta}")
    if abrir_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
