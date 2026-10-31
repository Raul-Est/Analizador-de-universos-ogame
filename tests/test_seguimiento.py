"""Pruebas del seguimiento en vivo (sin red ni ventana)."""

import json
import tempfile
import unittest
from pathlib import Path

from analizador import seguimiento as s


def captura(ts, destruidos, perdidos):
    return {"universo": "es-268", "version": s.VERSION_CAPTURA, "timestamp": ts, "ts_destruidos": ts, "ts_perdidos": ts, "destruidos": destruidos, "perdidos": perdidos}


class CambiosTest(unittest.TestCase):
    def test_verdes_y_rojos_ordenados_y_limitados(self):
        antes = captura(0, {1: 100, 2: 100, 3: 100, 4: 100}, {1: 50, 2: 50, 3: 50})
        ahora = captura(1, {1: 400, 2: 150, 3: 100, 4: 100, 9: 999}, {1: 50, 2: 60, 3: 5000})
        cambios = s.calcular_cambios(antes, ahora, top=10)
        self.assertEqual([(c["id"], c["puntos"]) for c in cambios], [(1, 300), (2, 50), (3, -4950), (2, -10)])
        limitado = s.calcular_cambios(antes, ahora, top=1)
        self.assertEqual([c["puntos"] for c in limitado], [300, -4950])

    def test_ignora_jugadores_nuevos_y_sin_cambios(self):
        antes = captura(0, {1: 10}, {1: 10})
        ahora = captura(1, {1: 10, 2: 500}, {1: 10, 2: 500})
        self.assertEqual(s.calcular_cambios(antes, ahora), [])

    def test_filtra_antes_de_aplicar_el_limite_top(self):
        antes = captura(0, {1: 0, 2: 0, 3: 0}, {1: 0, 2: 0, 3: 0})
        ahora = captura(1, {1: 1000, 2: 100, 3: 50}, {1: 1000, 2: 100, 3: 50})
        cambios = s.calcular_cambios(antes, ahora, top=1, ids_incluidos={2, 3})
        self.assertEqual([(c["id"], c["puntos"]) for c in cambios], [(2, 100), (2, -100)])

    def test_publica_cambios_de_jugadores_de_cualquier_alianza(self):
        class Contexto:
            def jugadores(self):
                return [
                    {"id": 1, "name": "Fuera", "alliance": 10},
                    {"id": 2, "name": "Dentro", "alliance": 20},
                ]

            def alianzas(self):
                return [{"id": 10, "tag": "OTRA"}, {"id": 20, "tag": "MD/ML"}]

        actualizaciones = []
        seguimiento = s.Seguimiento(Contexto(), 10, actualizaciones.append, lambda _: None)
        previa = captura(0, {1: 0, 2: 0}, {1: 0, 2: 0})
        nueva = captura(1, {1: 1000, 2: 100}, {1: 1000, 2: 100})

        seguimiento._publicar(previa, nueva)

        self.assertEqual(
            [(fila["id"], fila["puntos"]) for fila in actualizaciones[0]["filas"]],
            [(1, 1000), (2, 100), (1, -1000), (2, -100)],
        )


class FormatoYEsperaTest(unittest.TestCase):
    def test_formatear_puntos(self):
        self.assertEqual(s.formatear_puntos(292264), "+292.264")
        self.assertEqual(s.formatear_puntos(-3111), "-3.111")

    def test_espera_hasta_siguiente(self):
        marca = 1000
        self.assertEqual(s.espera_hasta_siguiente(marca, marca + 10), s.SONDEO_ESPERA)
        self.assertEqual(s.espera_hasta_siguiente(marca, marca + 3600 - 100), 103)
        self.assertEqual(s.espera_hasta_siguiente(marca, marca + 3700), s.SONDEO_ACTIVO)


class CapturaTest(unittest.TestCase):
    def test_nueva_solo_si_se_actualizan_ambos_rankings(self):
        previa = {**captura(100, {}, {}), "ts_destruidos": 100, "ts_perdidos": 135}
        a_medias = {**previa, "ts_destruidos": 3700, "ts_perdidos": 135}
        completa = {**previa, "ts_destruidos": 3700, "ts_perdidos": 3735}
        self.assertFalse(s.es_nueva(previa, previa))
        self.assertFalse(s.es_nueva(previa, a_medias))
        self.assertTrue(s.es_nueva(previa, completa))
    def test_guardar_leer_y_descartar_otro_universo(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / "c.json"
            s.guardar_captura(archivo, captura(5, {1: 2}, {3: 4}))
            self.assertEqual(s.leer_captura(archivo, "es-268"), captura(5, {1: 2}, {3: 4}))
            self.assertIsNone(s.leer_captura(archivo, "de-279"))
            antigua = {**captura(5, {1: 2}, {3: 4})}
            del antigua["version"]
            archivo.write_text(json.dumps(antigua), encoding="utf-8")
            self.assertIsNone(s.leer_captura(archivo, "es-268"))
            archivo.write_text("no es json", encoding="utf-8")
            self.assertIsNone(s.leer_captura(archivo, "es-268"))
            self.assertIsNone(s.leer_captura(Path(tmp) / "no_existe.json", "es-268"))

    def test_aplanar_historial(self):
        historial = [{"hora": 1793402679, "desde": 0, "filas": [
            {"puntos": 5, "id": 1, "nombre": "A", "alianza": "X"},
            {"puntos": -3, "id": 2, "nombre": "B", "alianza": None},
        ]}]
        filas = s.aplanar_historial(historial)
        self.assertEqual([(f["jugador"], f["tipo"], f["puntos"]) for f in filas], [("A", "destruidos", 5), ("B", "perdidos", -3)])


if __name__ == "__main__":
    unittest.main()
