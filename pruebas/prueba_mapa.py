#!/usr/bin/env python3
"""Pruebas del contrato de registros (C1). Compatible con Python 3.9.

    /usr/bin/python3 pruebas/prueba_mapa.py -v

Cada caso de rechazo parte del mapa real, le mete UN defecto y comprueba que
el validador devuelva exactamente el codigo de ese defecto y ningun otro. Cada
rechazo lleva al lado su control: el caso limite que SI debe pasar, para que
una prueba no salga verde por un validador que lo rechaza todo.
"""
import copy, json, pathlib, sys, tempfile, unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import mapa_registros as mr  # noqa: E402

REAL = json.loads(mr.MAPA.read_text(encoding="utf-8"))


def codigos(mapa):
    return sorted(e.split(":", 1)[0] for e in mr.valida(mapa))


def etiqueta(mapa, nombre):
    return next(e for e in mapa["etiquetas"] if e["nombre"] == nombre)


class MapaReal(unittest.TestCase):
    def test_mapa_real_es_valido(self):
        self.assertEqual(mr.valida(REAL), [])
        self.assertEqual(len(mr.carga()["etiquetas"]), 11)

    def test_doc_generada_al_dia(self):
        self.assertEqual(mr.DOC.read_text(encoding="utf-8"), mr.genera_doc(),
                         "docs/MAPA_REGISTROS.md desfasado: python3 tools/mapa_registros.py doc")


class DireccionRepetida(unittest.TestCase):
    def test_rechaza_repetida_en_la_misma_tabla(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "sens_bascula")["direccion"] = 0          # choca con sens_entrada
        self.assertEqual(codigos(m), ["direccion_repetida"])

    def test_control_misma_direccion_en_otra_tabla(self):
        # peso_V, emisor_on y vel_banda_V ya estan todos en la direccion 0 de
        # su tabla; el mapa real lo demuestra, aqui se deja explicito.
        ceros = {e["tabla"] for e in REAL["etiquetas"] if e["direccion"] == 0}
        self.assertEqual(ceros, set(mr.TABLAS))
        self.assertEqual(codigos(REAL), [])


class DireccionFueraDeLimite(unittest.TestCase):
    def caso(self, nombre, direccion):
        m = copy.deepcopy(REAL)
        etiqueta(m, nombre)["direccion"] = direccion
        return codigos(m)

    def test_rechaza_digital_256(self):
        self.assertEqual(self.caso("sens_salida", 256), ["direccion_fuera_de_limite"])

    def test_rechaza_registro_64(self):
        self.assertEqual(self.caso("vel_banda_V", 64), ["direccion_fuera_de_limite"])

    def test_rechaza_negativa(self):
        self.assertEqual(self.caso("luz_alerta", -1), ["direccion_fuera_de_limite"])

    def test_control_ultimas_direcciones_validas(self):
        self.assertEqual(self.caso("sens_salida", 255), [])
        self.assertEqual(self.caso("vel_banda_V", 63), [])


class EscalaDesbordaTipo(unittest.TestCase):
    def caso(self, nombre, rango):
        m = copy.deepcopy(REAL)
        etiqueta(m, nombre)["rango_fisico"] = rango
        return codigos(m)

    def test_rechaza_uint16_sobre_65535(self):
        self.assertEqual(self.caso("peso_V", [0, 700]), ["escala_desborda_tipo"])      # 70000

    def test_rechaza_int16_bajo_menos_32768(self):
        self.assertEqual(self.caso("vel_banda_V", [-400, 10]), ["escala_desborda_tipo"])  # -40000

    def test_rechaza_negativo_en_uint16(self):
        self.assertEqual(self.caso("peso_V", [-1, 10]), ["escala_desborda_tipo"])

    def test_control_justo_en_el_tope(self):
        self.assertEqual(self.caso("peso_V", [0, 655.35]), [])                         # 65535
        self.assertEqual(self.caso("vel_banda_V", [-327.68, 327.67]), [])              # int16 completo

    def test_escala_mayor_desborda_y_ademas_no_es_la_del_driver(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "vel_banda_V")["escala"] = 10000                                  # +-100000
        self.assertEqual(codigos(m), ["escala_desborda_tipo", "escala_distinta_del_driver"])


class EnterosSinEscala(unittest.TestCase):
    def test_entero_con_escala_1_se_acepta(self):
        m = copy.deepcopy(REAL)
        m["etiquetas"].append({"nombre": "cuenta", "tabla": "registro_retencion", "direccion": 5, "tipo": "uint16",
                               "escala": 1, "unidad": "cajas", "rango_fisico": [0, 65535], "sentido": "escritura",
                               "descripcion": "contador entero, Factory I/O no lo escala"})
        self.assertEqual(codigos(m), [])

    def test_entero_con_escala_1_que_desborda(self):
        m = copy.deepcopy(REAL)
        m["etiquetas"].append({"nombre": "cuenta", "tabla": "registro_retencion", "direccion": 5, "tipo": "uint16",
                               "escala": 1, "unidad": "cajas", "rango_fisico": [0, 70000], "sentido": "escritura",
                               "descripcion": "contador"})
        self.assertEqual(codigos(m), ["escala_desborda_tipo"])


class OtrosDefectos(unittest.TestCase):
    def test_junta_todos_los_errores(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "sens_bascula")["direccion"] = 0
        etiqueta(m, "peso_V")["rango_fisico"] = [0, 700]
        etiqueta(m, "emisor_on")["direccion"] = 300
        self.assertEqual(codigos(m), ["direccion_fuera_de_limite", "direccion_repetida",
                                      "escala_desborda_tipo"])

    def test_rechaza_escritura_en_tabla_de_entrada(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "sens_entrada")["sentido"] = "escritura"
        self.assertEqual(codigos(m), ["sentido_incompatible"])

    def test_rechaza_bool_en_registro(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "luz_alerta")["tabla"] = "registro_retencion"
        self.assertEqual(codigos(m), ["tipo_incompatible"])

    def test_mapa_fio_pendiente_se_rechaza_con_mensaje_claro(self):
        if not mr.MAPA_FIO.exists():
            self.skipTest("no hay config/mapa_registros_fio.json")
        fio = json.loads(mr.MAPA_FIO.read_text(encoding="utf-8"))
        errores = mr.valida(fio)
        pendientes = [e["nombre"] for e in fio["etiquetas"] if e["direccion"] is None]
        if not pendientes:
            self.assertEqual(errores, [])            # ya llego la captura (R0)
        else:
            self.assertEqual(codigos(fio), ["direccion_pendiente"] * len(pendientes))

    def test_rechaza_direccion_pendiente(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "sens_salida")["direccion"] = None
        self.assertEqual(codigos(m), ["direccion_pendiente"])
        self.assertIn("PUERTA ARI R0", mr.valida(m)[0])

    def test_rechaza_direccion_booleana(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "emp_extender")["direccion"] = True       # True == 1 en Python
        self.assertEqual(codigos(m), ["direccion_invalida"])

    def test_rechaza_nombre_repetido_y_campo_extra(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "luz_alerta")["nombre"] = "emisor_on"
        etiqueta(m, "peso_V")["offset"] = 3
        self.assertEqual(codigos(m), ["campo_no_esperado", "nombre_repetido"])

    def test_carga_lanza_con_la_lista(self):
        m = copy.deepcopy(REAL)
        etiqueta(m, "sens_bascula")["direccion"] = 0
        with tempfile.TemporaryDirectory() as d:
            destino = pathlib.Path(d) / "mapa.json"
            destino.write_text(json.dumps(m), encoding="utf-8")
            with self.assertRaises(mr.MapaInvalido) as ctx:
                mr.carga(destino)
        self.assertEqual(len(ctx.exception.errores), 1)


class Conversion(unittest.TestCase):
    def test_vel_negativa_en_complemento_a_dos(self):
        e = etiqueta(REAL, "vel_banda_V")
        self.assertEqual(mr.a_registro(e, -10), 64536)        # -1000 & 0xFFFF
        self.assertEqual(mr.a_registro(e, -0.01), 65535)
        self.assertEqual(mr.de_registro(e, 64536), -10.0)
        self.assertEqual(mr.de_registro(e, 1000), 10.0)

    def test_peso(self):
        e = etiqueta(REAL, "peso_V")
        self.assertEqual(mr.a_registro(e, 10), 1000)
        self.assertEqual(mr.de_registro(e, 437), 4.37)

    def test_fuera_de_rango_fisico(self):
        with self.assertRaises(ValueError):
            mr.a_registro(etiqueta(REAL, "vel_banda_V"), 10.5)


if __name__ == "__main__":
    unittest.main()
