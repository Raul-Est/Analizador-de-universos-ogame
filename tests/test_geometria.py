"""Pruebas de coordenadas y distancias con donut."""

import unittest

from analizador.geometria import distancia_circular, distancia_entre, parsear_coords


class GeometriaTest(unittest.TestCase):
    def test_parsear_coords(self):
        self.assertEqual(parsear_coords("1:387:12"), (1, 387, 12))
        with self.assertRaises(ValueError):
            parsear_coords("1-2-3")

    def test_distancia_sin_donut(self):
        self.assertEqual(distancia_circular(1, 5, 6, False), 4)

    def test_distancia_con_donut_toma_camino_corto(self):
        self.assertEqual(distancia_circular(1, 6, 6, True), 1)
        self.assertEqual(distancia_circular(1, 4, 6, True), 3)

    def test_distancia_entre_xolotlan(self):
        servidor = {"galaxias": 6, "sistemas": 499, "donut_galaxia": True, "donut_sistema": True}
        d = distancia_entre("1:1:1", "6:499:1", servidor)
        self.assertEqual(d, {"galaxias": 1, "sistemas": 1})


if __name__ == "__main__":
    unittest.main()
