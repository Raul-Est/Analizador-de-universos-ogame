"""Pruebas del registro de consultas y de la exportación."""

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from analizador.consultas.registro import CONSULTAS, Parametro, Resultado, consulta, obtener_parametros
from analizador.exportar import formatos_para, guardar


class RegistroTest(unittest.TestCase):
    def test_consultas_registradas(self):
        for id_ in ("servidor", "ranking", "top_lunas", "alianza_top_lunas", "distribucion_galaxias", "distancia"):
            self.assertIn(id_, CONSULTAS)

    def test_duplicada_falla(self):
        with self.assertRaises(ValueError):
            consulta("servidor", "dup")(lambda c: None)

    def test_obtener_parametros_defecto_y_validacion(self):
        c = CONSULTAS["ranking"]
        self.assertEqual(obtener_parametros(c, {})["limite"], 200)
        self.assertEqual(obtener_parametros(c, {"limite": "5"})["limite"], 5)
        with self.assertRaises(ValueError):
            obtener_parametros(c, {"categoria": "3"})
        with self.assertRaises(ValueError):
            obtener_parametros(c, {"inventado": "1"})
        with self.assertRaises(ValueError):
            obtener_parametros(CONSULTAS["distancia"], {})


class ExportarTest(unittest.TestCase):
    def test_formatos(self):
        self.assertEqual(formatos_para([{"a": 1}]), ("json", "csv", "md"))
        self.assertEqual(formatos_para({"a": 1}), ("json",))

    def test_guardar_csv_y_md(self):
        filas = [{"nombre": "A|B", "lunas": 2, "coordenadas": ["1:2:3", "4:5:6"]}]
        res = Resultado(datos=filas, titulo="Prueba", resumen=["Total: 1"])
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            csv_ruta = guardar(res, "csv", carpeta, "t", fecha=date(2026, 10, 30))
            self.assertEqual(csv_ruta.name, "t_30-10-2026.csv")
            with csv_ruta.open(encoding="utf-8-sig") as fh:
                fila = next(csv.DictReader(fh))
            self.assertEqual(fila["coordenadas"], "1:2:3;4:5:6")
            md_ruta = guardar(res, "md", carpeta, "t", fecha=date(2026, 10, 30))
            texto_md = md_ruta.read_text(encoding="utf-8")
            self.assertIn("A\\|B", texto_md)
            self.assertIn("# Prueba (30/10/2026)", texto_md)
            json_ruta = guardar(res, "json", carpeta, "t")
            self.assertEqual(json.loads(json_ruta.read_text(encoding="utf-8")), filas)


if __name__ == "__main__":
    unittest.main()
