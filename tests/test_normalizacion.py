"""Pruebas unitarias de la lógica sin red."""

import unittest

from analizador import normalizacion as n
from analizador.config import Universo


class NormalizacionTest(unittest.TestCase):
    def test_elementos_lista_objeto_y_vacio(self):
        self.assertEqual(n.elementos({"player": [{"a": 1}, {"a": 2}]}, "player"), [{"a": 1}, {"a": 2}])
        self.assertEqual(n.elementos({"player": {"a": 1}}, "player"), [{"a": 1}])
        self.assertEqual(n.elementos({"player": ""}, "player"), [])
        self.assertEqual(n.elementos(None, "player"), [])

    def test_parsear_jugadores_con_attributes(self):
        data = {"player": [{"@attributes": {"id": "7", "name": "Ana", "status": "", "alliance": "3"}}]}
        self.assertEqual(
            n.parsear_jugadores(data),
            [{"id": 7, "name": "Ana", "status": "", "alliance": 3}],
        )

    def test_parsear_highscore_jugador_unico(self):
        data = {"player": {"@attributes": {"id": "5", "position": "1", "score": "100", "ships": "9"}}}
        self.assertEqual(n.parsear_highscore(data), [{"id": 5, "position": 1, "score": 100, "ships": 9}])

    def test_parsear_servidor_donut(self):
        info = n.parsear_servidor({
            "language": "es", "number": "268", "name": "Mars", "galaxies": "5", "systems": "499",
            "donutGalaxy": "0", "donutSystem": "0", "speed": "8",
        })
        self.assertEqual(info["galaxias"], 5)
        self.assertFalse(info["donut_galaxia"])
        self.assertTrue(n.parsear_servidor({"donutGalaxy": "1"})["donut_galaxia"])

    def test_parsear_planetas_y_lunas(self):
        detalle = {"planets": {"planet": [
            {"coords": "1:2:3", "moon": {"name": "Luna"}},
            {"coords": "1:2:4"},
            {"coords": "2:2:5", "moon": [{"name": "a"}, {"name": "b"}]},
        ]}}
        self.assertEqual(n.coordenadas_lunas(detalle), ["1:2:3", "2:2:5", "2:2:5"])


class UniversoTest(unittest.TestCase):
    def test_desde_texto_y_host(self):
        u = Universo.desde_texto("ES:279")
        self.assertEqual((u.idioma, u.numero, u.clave), ("es", 279, "es-279"))
        self.assertEqual(u.url_api, "https://s279-es.ogame.gameforge.com/api")

    def test_texto_invalido(self):
        with self.assertRaises(ValueError):
            Universo.desde_texto("es-268")


if __name__ == "__main__":
    unittest.main()
