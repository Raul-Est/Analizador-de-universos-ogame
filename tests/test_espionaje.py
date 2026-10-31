"""Pruebas del lector de informes de espionaje y del formulario web (sin abrir navegador)."""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from analizador import informes_guardados as almacen
from analizador import web_espionaje
from analizador.exportar import guardar
from analizador.espionaje import filas_planas, parsear_informe

INFORME_A = """Jugador:
  Ratardilla espacial
(v ph)
Clase:
Descubridor
Clase de alianza:
Combatiente (alianza)
Recursos:
823,854M
Botín: 75%
Posibilidades de contra-espionaje: 0 %
Flotas:
7Mrd
Defensa: 8.7M
Tu espionaje muestra anormalidades en la atmósfera del planeta, lo que indica actividad en los últimos 15 minutos.
Recursos
Metal
158.994.337
Cristal
628.270.336
Flotas
Nave pequeña de carga
182.119
Defensa
Lanzamisiles
3.483
Edificio
Hangar
2
Investigación
Astrofísica
19
Investigación de forma de vida
Crucero 2.0
42
"""

INFORME_B = """Jugador:
  Scipion
(ph)
Clase:
Descubridor
Recursos:
536,762M
Botín: 75%
Flotas:
3Mrd
Tu espionaje muestra anormalidades en la atmósfera del planeta, lo que indica actividad en los últimos 41 minutos.
Recursos
Metal
405.379.308
Campo de escombros
Metal
0
Cristal
9.321
Flotas
Nave grande de carga
96.635
Edificio
Base lunar
7
Investigación
Motor de fusión
2"""


INFORME_WEB = """Informe de espionaje en Luna [![](https://gf3.geo.gfsrv.net/cdn21/a55944240beaebefbf17e51a4712a4.png)L - DI3GO [3:134:9]](https://s268-es.ogame.gameforge.com/game/index.php?page=ingame&component=galaxy&galaxy=3&system=134&position=9)28.10.2026 16:13:38
De: Control del espacio![](https://s268-es.ogame.gameforge.com/cdn/img/icons/basic/not_favorited.png)![](https://s268-es.ogame.gameforge.com/cdn/img/icons/basic/apikey.png)
![](https://s268-es.ogame.gameforge.com/cdn/img/icons/basic/espionage.png)![](https://s268-es.ogame.gameforge.com/cdn/img/icons/basic/refuse.png)

Jugador:  Ratardilla espacial(v ph)
Clase:Descubridor
Clase de alianza:Combatiente (alianza)

Recursos:823,854M
Botín: 75%

Posibilidades de contra-espionaje: 0 %

Flotas:7Mrd

Defensa: 8.7M

Tu espionaje muestra anormalidades en la atmósfera del planeta, lo que indica actividad en los últimos 15 minutos.
RecursosMetal
158.994.337

Cristal
628.270.336

FlotasNave pequeña de carga
182.119

Crucero
101.718

DefensaLanzamisiles
3.483

EdificioSensor Phalanx
11

Base lunar
10

InvestigaciónAstrofísica
19

Investigación de forma de vidaReconversor de calor
78

Crucero 2.0
42
"""


class ParserTest(unittest.TestCase):
    def test_formato_copiado_de_la_web_con_coordenadas(self):
        inf = parsear_informe(INFORME_WEB)
        cab = inf["cabecera"]
        self.assertEqual(list(cab)[:5], ["Jugador", "Estado", "Coordenadas", "Ubicación", "Fecha del informe"])
        self.assertEqual(cab["Jugador"], "Ratardilla espacial")
        self.assertEqual(cab["Estado"], "v ph")
        self.assertEqual(cab["Coordenadas"], "3:134:9")
        self.assertEqual(cab["Ubicación"], "Luna L - DI3GO")
        self.assertEqual(cab["Fecha del informe"], "28.10.2026 16:13:38")
        self.assertEqual(cab["De"], "Control del espacio")
        self.assertEqual(cab["Clase de alianza"], "Combatiente (alianza)")
        self.assertEqual(cab["Defensa"], "8.7M")
        self.assertEqual(cab["Flotas"], "7Mrd")
        self.assertEqual(len(inf["mensajes"]), 1)
        sec = inf["secciones"]
        self.assertEqual(sec["Recursos"]["Metal"], 158994337)
        self.assertEqual(sec["Flotas"], {"Nave pequeña de carga": 182119, "Crucero": 101718})
        self.assertEqual(sec["Defensa"], {"Lanzamisiles": 3483})
        self.assertEqual(sec["Edificio"], {"Sensor Phalanx": 11, "Base lunar": 10})
        self.assertEqual(sec["Investigación"], {"Astrofísica": 19})
        self.assertEqual(sec["Investigación de forma de vida"], {"Reconversor de calor": 78, "Crucero 2.0": 42})

    def test_titulo_sin_informe_de_espionaje_y_fecha_en_otra_linea(self):
        inf = parsear_informe("Luna [5:499:9]\n30.10.2026 18:19:35\nDe: Control del espacio\nJugador:  Scipion(ph)\nFlotas\nCrucero\n5")
        cab = inf["cabecera"]
        self.assertEqual((cab["Coordenadas"], cab["Ubicación"], cab["Fecha del informe"]), ("5:499:9", "Luna", "30.10.2026 18:19:35"))

    def test_repara_cabecera_guardada_con_titulo_mal_leido(self):
        from analizador.espionaje import reparar_cabecera
        cab = reparar_cabecera({"Jugador": "X", "Luna [5": "499:9]", "30.10.2026 18": "19:35", "De": "Y"})
        self.assertEqual(cab, {"Jugador": "X", "Coordenadas": "5:499:9", "Ubicación": "Luna", "Fecha del informe": "30.10.2026 18:19:35", "De": "Y"})

    def test_planeta_sin_imagen_en_el_titulo(self):
        inf = parsear_informe("Informe de espionaje en Planeta Casa [1:2:3]  01.02.2026 10:00:00\nJugador:  Ana(i)\nFlotas\nCrucero\n5")
        self.assertEqual(inf["cabecera"]["Ubicación"], "Planeta Casa")
        self.assertEqual(inf["cabecera"]["Coordenadas"], "1:2:3")
        self.assertEqual(inf["cabecera"]["Estado"], "i")

    def test_informe_completo(self):
        inf = parsear_informe(INFORME_A)
        self.assertEqual(inf["cabecera"]["Jugador"], "Ratardilla espacial")
        self.assertEqual(inf["cabecera"]["Estado"], "v ph")
        self.assertEqual(inf["cabecera"]["Recursos"], "823,854M")
        self.assertEqual(inf["cabecera"]["Defensa"], "8.7M")
        self.assertEqual(inf["cabecera"]["Botín"], "75%")
        self.assertEqual(len(inf["mensajes"]), 1)
        self.assertEqual(inf["secciones"]["Recursos"]["Cristal"], 628270336)
        self.assertEqual(inf["secciones"]["Flotas"]["Nave pequeña de carga"], 182119)
        self.assertEqual(inf["secciones"]["Defensa"], {"Lanzamisiles": 3483})
        self.assertEqual(inf["secciones"]["Investigación de forma de vida"], {"Crucero 2.0": 42})

    def test_informe_con_seccion_nueva_y_sin_defensa(self):
        inf = parsear_informe(INFORME_B)
        self.assertNotIn("Defensa", inf["secciones"])
        self.assertEqual(inf["secciones"]["Campo de escombros"], {"Metal": 0, "Cristal": 9321})
        self.assertEqual(inf["secciones"]["Recursos"], {"Metal": 405379308})
        self.assertEqual(inf["cabecera"]["Estado"], "ph")
        self.assertNotIn("Clase de alianza", inf["cabecera"])

    def test_texto_no_valido(self):
        with self.assertRaises(ValueError):
            parsear_informe("hola mundo")
        with self.assertRaises(ValueError):
            parsear_informe("")

    def test_filas_planas(self):
        filas = filas_planas(parsear_informe(INFORME_B))
        self.assertIn({"seccion": "Campo de escombros", "concepto": "Cristal", "valor": 9321}, filas)
        self.assertIn({"seccion": "Cabecera", "concepto": "Jugador", "valor": "Scipion"}, filas)


class AlmacenTest(unittest.TestCase):
    def test_guardar_y_recuperar_ultima_flota(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "informes.json"
            viejo = parsear_informe(INFORME_B)
            nuevo = parsear_informe(INFORME_B.replace("96.635", "100.000"))
            self.assertEqual(almacen.guardar_informe(archivo, viejo, datetime(2026, 10, 30, 10, 0)), (True, 1))
            self.assertEqual(almacen.guardar_informe(archivo, viejo), (False, 1))
            self.assertEqual(almacen.guardar_informe(archivo, nuevo, datetime(2026, 10, 31, 3, 40)), (True, 2))
            self.assertEqual(almacen.guardar_informe(archivo, parsear_informe(INFORME_A)), (True, 1))
            registro = almacen.ultimo_informe(archivo, "scip")
            self.assertEqual(registro["guardado"], "2026-10-31T03:40:00")
            filas = almacen.filas_ultima_flota(registro)
            self.assertEqual(filas[0], {"concepto": "Guardado", "valor": "31/10/2026 03:40"})
            self.assertIn({"concepto": "Jugador", "valor": "Scipion"}, filas)
            self.assertIn({"concepto": "Nave grande de carga", "valor": 100000}, filas)
            self.assertIn({"concepto": "Metal", "valor": 405379308}, filas)

    def test_ultima_flota_por_fecha_del_informe_y_con_coordenadas(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "informes.json"
            reciente = parsear_informe(INFORME_WEB)
            antiguo = parsear_informe(INFORME_WEB.replace("28.10.2026 16:13:38", "20.10.2026 08:00:00").replace("182.119", "1"))
            almacen.guardar_informe(archivo, reciente, datetime(2026, 10, 31, 1, 0))
            almacen.guardar_informe(archivo, antiguo, datetime(2026, 10, 31, 2, 0))
            fechas = [r["informe"]["cabecera"]["Fecha del informe"] for r in json.loads(archivo.read_text(encoding="utf-8"))]
            self.assertEqual(fechas, ["20.10.2026 08:00:00", "28.10.2026 16:13:38"])
            registro = almacen.ultimo_informe(archivo, "ratardilla")
            filas = almacen.filas_ultima_flota(registro)
            self.assertIn({"concepto": "Nave pequeña de carga", "valor": 182119}, filas)
            self.assertIn({"concepto": "Coordenadas", "valor": "3:134:9"}, filas)
            self.assertIn({"concepto": "Ubicación", "valor": "Luna L - DI3GO"}, filas)

    def test_nombre_de_archivo_incluye_jugador(self):
        with tempfile.TemporaryDirectory() as tmp:
            import analizador.consultas.espionaje as consulta_esp
            from analizador.config import Universo
            self.enterContext(mock.patch.object(consulta_esp, "CARPETA_SALIDA", Path(tmp)))
            universo = Universo.desde_texto("es:268")
            carpeta = consulta_esp.carpeta_flotas(universo)
            self.assertEqual(carpeta, Path(tmp) / "es-268" / "flotas")
            almacen.guardar_informe(carpeta / "informes.json", parsear_informe(INFORME_B))
            resultado = consulta_esp.ultima_flota(SimpleNamespace(universo=universo), "scip")
            self.assertEqual(resultado.nombre_archivo, "ultima_flota_Scipion")
            self.assertEqual(resultado.subcarpeta, "flotas")
            ruta = guardar(resultado, "csv", carpeta, resultado.nombre_archivo, date(2026, 10, 31))
            self.assertEqual(ruta.name, "ultima_flota_Scipion_31-10-2026.csv")

    def test_migra_informes_de_la_carpeta_antigua(self):
        with tempfile.TemporaryDirectory() as tmp:
            import analizador.consultas.espionaje as consulta_esp
            from analizador.config import Universo
            self.enterContext(mock.patch.object(consulta_esp, "CARPETA_SALIDA", Path(tmp)))
            almacen.guardar_informe(Path(tmp) / "espionaje" / "informes.json", parsear_informe(INFORME_B))
            carpeta = consulta_esp.carpeta_flotas(Universo.desde_texto("es:268"))
            self.assertTrue((carpeta / "informes.json").exists())
            self.assertFalse((Path(tmp) / "espionaje" / "informes.json").exists())

    def test_errores(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "informes.json"
            with self.assertRaises(ValueError):
                almacen.ultimo_informe(archivo, "x")
            almacen.guardar_informe(archivo, parsear_informe(INFORME_B))
            almacen.guardar_informe(archivo, parsear_informe(INFORME_A))
            with self.assertRaises(ValueError):
                almacen.ultimo_informe(archivo, "zzz")
            with self.assertRaises(ValueError):
                almacen.ultimo_informe(archivo, "i")
            archivo.write_text("roto", encoding="utf-8")
            with self.assertRaises(ValueError):
                almacen.ultimo_informe(archivo, "scipion")


class WebTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.carpeta = Path(self.tmp.name)
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), web_espionaje._manejador(self.carpeta))
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.servidor.server_address[1]}"

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.tmp.cleanup()

    def _post(self, ruta, texto):
        datos = urllib.parse.urlencode({"texto": texto}).encode()
        return urllib.request.urlopen(urllib.request.Request(self.base + ruta, datos))

    def test_analizar_y_exportar(self):
        pagina = self._post("/analizar", INFORME_B).read().decode()
        self.assertIn("Campo de escombros", pagina)
        self.assertIn("405.379.308", pagina)
        for formato in ("json", "csv", "md"):
            resp = self._post(f"/exportar/{formato}", INFORME_B)
            self.assertIn("espionaje_Scipion_", resp.headers["Content-Disposition"])
            cuerpo = resp.read().decode("utf-8-sig")
            self.assertIn("Scipion", cuerpo)
            if formato == "json":
                self.assertEqual(json.loads(cuerpo)["secciones"]["Flotas"]["Nave grande de carga"], 96635)
        self.assertEqual(len(list(self.carpeta.iterdir())), 4)
        registros = json.loads((self.carpeta / "informes.json").read_text(encoding="utf-8"))
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["jugador"], "Scipion")

    def test_no_duplica_informe_identico(self):
        self._post("/analizar", INFORME_B)
        pagina = self._post("/analizar", INFORME_B).read().decode()
        self.assertIn("no se duplica", pagina)
        self.assertEqual(len(json.loads((self.carpeta / "informes.json").read_text(encoding="utf-8"))), 1)

    def test_error_si_no_es_informe(self):
        pagina = self._post("/analizar", "nada").read().decode()
        self.assertIn("No se reconoce", pagina)

    def test_html_escapado(self):
        pagina = self._post("/analizar", "Jugador:\n<script>x</script>\nRecursos\nMetal\n1").read().decode()
        self.assertNotIn("<script>x", pagina)

    def test_ruta_desconocida(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post("/otra", INFORME_B)
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
