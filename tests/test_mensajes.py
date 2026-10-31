import tempfile
import unittest
from pathlib import Path

from analizador import mensajes as m
from analizador.cliente import ErrorApi

EJEMPLO = (
    "- juradin31.10.2026 20:05:42\n"
    "Felicidades, nerd, sal de casa un poco que te gastas toda la paguita en mo           "
    "[Imperio](https://s268-es.ogame.gameforge.com/game/allianceInfo.php?allianceId=500522)juradin"
    "[![](https://gf1.geo.gfsrv.net/cdn3b/ec7d0e284af9927de8c785978b4c77.png)[2:1:12]]"
    "(https://s268-es.ogame.gameforge.com/game/index.php?page=ingame&component=galaxy&galaxy=2&system=1&position=12)\n"
)


class FakeContexto:
    def __init__(self, jugadores, detalles):
        self._jugadores = jugadores
        self._detalles = detalles

    def jugadores(self):
        return self._jugadores

    def detalle_jugador(self, pid):
        if pid not in self._detalles:
            raise ErrorApi(f"sin datos de {pid}")
        return self._detalles[pid]

    def detalles(self, pids):
        for pid in pids:
            try:
                yield pid, self.detalle_jugador(pid), None
            except ErrorApi as exc:
                yield pid, None, str(exc)


def planeta(coords):
    return {"planets": {"planet": [{"coords": coords}]}}


class AnalisisTest(unittest.TestCase):
    def test_analiza_el_ejemplo_y_descarta_los_enlaces(self):
        (mensaje,) = m.analizar_mensajes(EJEMPLO)
        self.assertEqual(mensaje["fecha"], "2026-10-31T20:05:42")
        self.assertEqual(mensaje["remitente"], "juradin")
        self.assertEqual(mensaje["alianza"], "Imperio")
        self.assertEqual(mensaje["coords"], "2:1:12")
        self.assertEqual(
            mensaje["texto"],
            "Felicidades, nerd, sal de casa un poco que te gastas toda la paguita en mo",
        )

    def test_varios_mensajes_y_sin_alianza(self):
        texto = (
            "- ana01.11.2026 10:00:00\nHola ana[![](x.png)[3:3:3]](https://x)\n"
            + EJEMPLO
        )
        primero, segundo = m.analizar_mensajes(texto)
        self.assertEqual(primero["remitente"], "ana")
        self.assertIsNone(primero["alianza"])
        self.assertEqual(primero["texto"], "Hola")
        self.assertEqual(segundo["remitente"], "juradin")

    def test_sin_planeta_falla_con_mensaje_claro(self):
        with self.assertRaisesRegex(ValueError, "planeta"):
            m.analizar_mensajes("- juradin31.10.2026 20:05:42\nSolo texto\n")

    def test_texto_antes_de_la_cabecera_falla(self):
        with self.assertRaises(ValueError):
            m.analizar_mensajes("hola\n" + EJEMPLO)


class IdentificacionTest(unittest.TestCase):
    def test_por_nombre_y_planeta(self):
        ctx = FakeContexto(
            [{"id": 7, "name": "juradin"}, {"id": 9, "name": "otro"}],
            {7: planeta("2:1:12"), 9: planeta("1:1:1")},
        )
        self.assertEqual(m.identificar_jugador(ctx, "juradin", "2:1:12"), 7)

    def test_cambio_de_nombre_se_resuelve_por_planeta(self):
        ctx = FakeContexto(
            [{"id": 5, "name": "juradin"}, {"id": 7, "name": "nuevo"}],
            {5: planeta("1:1:1"), 7: planeta("2:1:12")},
        )
        self.assertEqual(m.identificar_jugador(ctx, "juradin", "2:1:12"), 7)

    def test_sin_coincidencia_devuelve_none(self):
        ctx = FakeContexto([{"id": 7, "name": "x"}], {7: planeta("1:1:1")})
        self.assertIsNone(m.identificar_jugador(ctx, "juradin", "2:1:12"))


class AlmacenTest(unittest.TestCase):
    def test_guardar_sin_duplicar_y_ordenado(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / m.NOMBRE_ARCHIVO
            tarde = m.analizar_mensajes(EJEMPLO)
            temprano = m.analizar_mensajes("- juradin30.10.2026 08:00:00\nAntes[![](x)[2:1:12]](y)\n")
            resolver = lambda nombre, coords: 7
            self.assertEqual(m.guardar_mensajes(archivo, tarde, resolver), (1, 0))
            self.assertEqual(m.guardar_mensajes(archivo, tarde + temprano, resolver), (1, 1))
            guardados = m.buscar(archivo, "juradin")
            self.assertEqual([g["fecha"] for g in guardados], ["2026-10-30T08:00:00", "2026-10-31T20:05:42"])
            self.assertTrue(all(g["jugador_id"] == 7 for g in guardados))

    def test_buscar_por_id_sigue_al_jugador_tras_cambiar_de_nombre(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / m.NOMBRE_ARCHIVO
            m.guardar_mensajes(archivo, m.analizar_mensajes(EJEMPLO), lambda n_, c: 7)
            nuevo = m.analizar_mensajes("- nuevo02.11.2026 09:00:00\nOtro[![](x)[2:1:12]](y)\n")
            m.guardar_mensajes(archivo, nuevo, lambda n_, c: 7)
            por_id = m.buscar(archivo, "7")
            self.assertEqual([r["remitente"] for r in por_id], ["juradin", "nuevo"])
            por_nombre_viejo = m.buscar(archivo, "juradin")
            self.assertEqual(len(por_nombre_viejo), 2)

    def test_mensaje_sin_id_se_busca_por_su_nombre(self):
        with tempfile.TemporaryDirectory() as tmp:
            archivo = Path(tmp) / m.NOMBRE_ARCHIVO
            m.guardar_mensajes(archivo, m.analizar_mensajes(EJEMPLO), lambda n_, c: None)
            self.assertEqual(len(m.buscar(archivo, "jura")), 1)
            self.assertEqual(m.buscar(archivo, "99"), [])


if __name__ == "__main__":
    unittest.main()
