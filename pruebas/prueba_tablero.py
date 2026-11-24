#!/usr/bin/env python3
"""Tablero de la escena y T_ef medido, sin Factory I/O. Python 3.9.

    /usr/bin/python3 pruebas/prueba_tablero.py          (~2 min)

Un servidor Modbus minimo (FC 1-6) con las direcciones de
config/mapa_registros_fio.json hace de escena: la prueba mueve sus entradas
(botones y sensores) y mira lo que A2-Planta escribe en bobinas y registros.
Node-RED corre con config/planta_fio.json (copiada, con el refresco medido
lleno para que el bloque "medido" valga):
  1. limites del cliente = tools/limites_planta.py con la regla medida (T_ef
     sin holgura), y con otro sondeo vuelve a la formula con holgura;
  2. luces segun la linea; Start -> marcha, Stop (NC) -> paro;
  3. Emergency stop (NC) por nivel: todo apagado, marcha rechazada, Stop no lo
     saca; al soltarlo queda detenida; Start vuelve a arrancar;
  4. una caja por destino (pesaje detenido a mano) -> los tres contadores;
  5. E-stop ya presionado al arrancar Node-RED -> emergencia desde el inicio;
  6. otro sondeo: las medidas no valen y vuelve la holgura;
  7. fronteras de clase en volts (paso U de la fase 3): cajas de 4.49, 4.51,
     6.99 y 7.01 V con la configuracion de antes del cambio de unidad (1 kg por
     volt, umbrales 4.5 / 7.0, tomada del commit 266e697) y con la del repo
     (2 kg por volt, 9.0 / 14.0): mismos destinos, masa = V x plena / 10;
  8. una sola lectura (cierre de la fase 4, paso S): un Stop que dura una
     lectura detiene la linea, un Start de una lectura no la arranca y una
     lectura falsa en at_scale no da flanco; con la mutacion (Stop sin
     lecturas_para_cambio propio) el primer caso falla.

    /usr/bin/python3 pruebas/prueba_tablero.py una_lectura  (solo el punto 8, ~1 min)

    /usr/bin/python3 pruebas/prueba_tablero.py fronteras   (solo el punto 7, ~1 min)
"""
import json, pathlib, socket, struct, subprocess, sys, tempfile, threading, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
sys.path.insert(0, str(RAIZ / "tools"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
import limites_planta as lp  # noqa: E402

verifica = ps.verifica
PUERTO = 5098
MAPA = RAIZ / "config" / "mapa_registros_fio.json"
E = {e["nombre"]: e for e in json.load(open(str(MAPA)))["etiquetas"]}


class Escena:
    """Servidor Modbus TCP minimo: 16 entradas, 1 registro de entrada, 11 bobinas, 3 registros."""

    def __init__(self, puerto):
        self.di, self.ir, self.co, self.hr = [False] * 16, [0] * 4, [False] * 16, [0] * 4
        self.escrituras = []
        self.lecturas_di = 0          # peticiones FC2 servidas (para una pulsacion de una sola lectura)
        self.s = socket.socket()
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(("127.0.0.1", puerto))
        self.s.listen(4)
        self.vivo = True
        threading.Thread(target=self._acepta, daemon=True).start()

    def _acepta(self):
        while self.vivo:
            try:
                c, _ = self.s.accept()
            except OSError:
                return
            threading.Thread(target=self._atiende, args=(c,), daemon=True).start()

    def _atiende(self, c):
        buf = b""
        while self.vivo:
            try:
                d = c.recv(4096)
            except OSError:
                return
            if not d:
                return
            buf += d
            while len(buf) >= 7:
                largo = struct.unpack(">H", buf[4:6])[0]
                if len(buf) < 6 + largo:
                    break
                trama, buf = buf[:6 + largo], buf[6 + largo:]
                c.sendall(self._responde(trama))

    def _responde(self, t):
        tid, uid, fc = struct.unpack(">H", t[:2])[0], t[6], t[7]
        dir_, val = struct.unpack(">HH", t[8:12])
        if fc in (1, 2):
            if fc == 2:
                self.lecturas_di += 1
            bits = (self.co if fc == 1 else self.di)[dir_:dir_ + val]
            datos = bytearray((val + 7) // 8)
            for i, b in enumerate(bits):
                if b:
                    datos[i // 8] |= 1 << (i % 8)
            cuerpo = bytes([fc, len(datos)]) + bytes(datos)
        elif fc in (3, 4):
            pal = (self.hr if fc == 3 else self.ir)[dir_:dir_ + val]
            cuerpo = bytes([fc, 2 * len(pal)]) + b"".join(struct.pack(">H", p) for p in pal)
        elif fc == 5:
            self.co[dir_] = val == 0xFF00
            self.escrituras.append((time.time(), "co", dir_, self.co[dir_]))
            cuerpo = t[7:12]
        elif fc == 6:
            self.hr[dir_] = val
            self.escrituras.append((time.time(), "hr", dir_, val))
            cuerpo = t[7:12]
        else:
            cuerpo = bytes([fc | 0x80, 1])
        return struct.pack(">HHHB", tid, 0, len(cuerpo) + 1, uid) + cuerpo

    def pon(self, nombre, valor):
        self.di[E[nombre]["direccion"]] = bool(valor)

    def bobina(self, nombre):
        return self.co[E[nombre]["direccion"]]

    def registro(self, nombre):
        return self.hr[E[nombre]["direccion"]]

    def cierra(self):
        self.vivo = False
        self.s.close()


def config(tmp, refresco_p95=33):
    c = json.load(open(str(RAIZ / "config" / "planta_fio.json")))
    c["medido"]["refresco_p95_ms"] = refresco_p95
    ruta = tmp / "planta_fio_prueba.json"
    ruta.write_text(json.dumps(c, indent=2), encoding="utf-8")
    return ruta, c


def arranca(tmp, cfg_ruta, **extra):
    datos = tmp / ("datos_%d" % int(time.time() * 1000))
    datos.mkdir()
    ps.arranca(datos, A2_MAPA=MAPA, A2_PLANTA_CONFIG=cfg_ruta, A2_SUSTITUTO=0, A2_MODBUS_HOST="127.0.0.1",
               A2_MODBUS_PUERTO=PUERTO, A2_MODBUS_UNIDAD=1, **extra)
    ok = pp.espera(lambda: pp.estado()["com"] == "ok", 30)
    return datos, ok


def eventos(datos):
    ruta = datos / "a2_planta_eventos.jsonl"
    return [json.loads(l) for l in ruta.read_text().splitlines() if l.strip()] if ruta.exists() else []


def pulsa(esc, nombre, nc=False, s=0.3):
    """Presiona y suelta: un boton NO pasa a 1 al presionar, uno NC pasa a 0."""
    esc.pon(nombre, not nc)
    time.sleep(s)
    esc.pon(nombre, nc)
    time.sleep(0.3)


def caja(esc, peso_V, rama):
    """Una caja por la escena falsa: llega a la bascula, se pesa parada, sale por `rama`."""
    esc.ir[E["weight"]["direccion"]] = int(round(peso_V * 100))
    esc.pon("at_scale", True)
    pp.espera(lambda: not esc.bobina("load_scale"), 5, paso=0.05)
    pp.espera(lambda: esc.bobina("load_scale"), 5, paso=0.05)           # el cliente la suelta
    esc.pon("at_scale", False)
    esc.pon("at_scale_exit", True)
    time.sleep(0.4)
    esc.pon("at_scale_exit", False)
    esc.ir[E["weight"]["direccion"]] = 0
    time.sleep(0.3)
    sensor = {"left": "at_left_entry", "forward": "at_forward_entry", "right": "at_right_entry"}[rama]
    esc.pon(sensor, True)
    time.sleep(0.5)
    esc.pon(sensor, False)
    time.sleep(0.4)


COMMIT_ANTES_U = "266e697"          # ultimo commit con 1 kg por volt en config/planta_fio.json
FRONTERAS = ((4.49, "left"), (4.51, "forward"), (6.99, "forward"), (7.01, "right"))


def fronteras(tmp, esc):
    print("=== 7. Fronteras de clase en volts: antes y despues del cambio de unidad (paso U) ===")
    antes = json.loads(subprocess.check_output(["git", "show", COMMIT_ANTES_U + ":config/planta_fio.json"], cwd=str(RAIZ)))
    ahora = json.load(open(str(RAIZ / "config" / "planta_fio.json")))
    destinos = {}
    for nombre, c in (("antes (" + COMMIT_ANTES_U + ")", antes), ("repo", ahora)):
        c["medido"]["refresco_p95_ms"] = 33
        ruta = tmp / ("planta_fio_%s.json" % nombre.split()[0])
        ruta.write_text(json.dumps(c, indent=2), encoding="utf-8")
        plena = c["bascula"]["plena_escala_kg"]
        umbrales = [k["hasta_kg"] for k in c["desviador"]["clases"]]
        try:
            datos, ok = arranca(tmp, ruta)
            verifica("%s: plena escala %g kg, umbrales %s; A2-Planta conecta" % (nombre, plena, umbrales), ok)
            pulsa(esc, "start_button")
            pp.espera(lambda: pp.estado()["linea"] == "en_marcha", 5)
            time.sleep(c["desviador"]["purga_ms"] / 1000.0 + 0.3)
            for peso, rama in FRONTERAS:
                caja(esc, peso, rama)
            pp.comando(accion="paro")
            # Destino que el cliente elige al pesar (caja_pesada), no el sensor que
            # la escena falsa enciende despues (esa siempre es la rama esperada).
            ev = [e for e in eventos(datos) if e["ev"] == "caja_pesada"]
            destinos[nombre] = [e["destino"] for e in ev]
            masas = [e["masa_kg"] for e in ev]
            esperadas = [round(v / 10.0 * plena, 3) for v, _ in FRONTERAS]
            print("    %s: %s" % (nombre, [(e["peso_V"], e["masa_kg"], e["destino"]) for e in ev]))
            verifica("%s: destinos elegidos al pesar %s = %s" % (nombre, destinos[nombre], [r for _, r in FRONTERAS]),
                     destinos[nombre] == [r for _, r in FRONTERAS])
            verifica("%s: masa_kg = V x %g / 10 = %s" % (nombre, plena, esperadas),
                     len(masas) == len(esperadas) and all(abs(m - x) < 1e-9 for m, x in zip(masas, esperadas)), masas)
            st = pp.estado()["contadores"]
            verifica("%s: sin desvios erroneos ni perdidas" % nombre,
                     st["desvios_erroneos"] == 0 and st["perdidas"] == 0, st)
        finally:
            ps.detiene()
    a, b = list(destinos.values())
    verifica("mismos destinos antes y despues del cambio de unidad", a == b and len(a) == len(FRONTERAS), destinos)


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_tablero_"))
    esc = Escena(PUERTO)
    for n in ("stop_button", "emergency_stop", "at_exit_left", "at_exit_front", "at_exit_right", "fio_running"):
        esc.pon(n, True)                                            # NC en reposo y la escena en Play
    cfg_ruta, cfg = config(tmp)
    try:
        print("=== 1. T_ef con lo medido (misma regla en Python y en Node-RED) ===")
        datos, ok = arranca(tmp, cfg_ruta)
        verifica("A2-Planta conecta con la escena falsa", ok)
        st = pp.estado()
        m = cfg["medido"]
        py = lp.calcula(cfg, cfg["sondeo_ms"], cfg["rtt_previsto_ms"], None, cfg["refresco_ms"],
                        lp.medido_vale(cfg, cfg["sondeo_ms"]))
        esperado = max(m["periodo_p95_ms"], (cfg["lecturas_por_ciclo_max"] + cfg["escrituras_por_ciclo_max"]) * m["rtt_p95_ms"],
                       m["refresco_p95_ms"])
        verifica("Python: T_ef = max(p95 periodo, peticiones x p95 rtt, p95 refresco) = %d ms, sin holgura" % esperado,
                 py["t_ef_ms"] == esperado and py["t_ef_origen"] == "medido", py["t_ef_ms"])
        verifica("Node-RED da lo mismo: T_ef %s ms (%s), factible %s" % (st["limites"]["t_ef_ms"], st["limites"].get("t_ef_origen"),
                                                                       st["limites"]["factible"]),
                 (st["limites"]["t_ef_ms"], st["limites"]["factible"], st["limites"].get("t_ef_origen"))
                 == (py["t_ef_ms"], py["factible"], "medido"), (st["limites"], py["t_ef_ms"]))
        verifica("t_min = 3 x T_ef = %.3f s" % (3 * esperado / 1000.0), abs(st["limites"]["t_min_s"] - 3 * esperado / 1000.0) < 0.001)

        print("=== 2. Luces, Start y Stop ===")
        verifica("detenida: stop_light 1, start_light 0, reset_light 0",
                 pp.espera(lambda: esc.bobina("stop_light") and not esc.bobina("start_light") and not esc.bobina("reset_light"), 5))
        verifica("contadores en 0", [esc.registro(n) for n in ("left_count", "forward_count", "right_count")] == [0, 0, 0])
        pulsa(esc, "start_button")
        verifica("Start -> en marcha", pp.espera(lambda: pp.estado()["linea"] == "en_marcha", 5), pp.estado()["linea"])
        verifica("bandas encendidas y start_light 1, stop_light 0",
                 pp.espera(lambda: esc.bobina("entry_conveyor") and esc.bobina("front_conveyor") and esc.bobina("start_light")
                           and not esc.bobina("stop_light"), 5))
        pulsa(esc, "stop_button", nc=True)                          # NC: presionar = 0
        verifica("Stop (NC, baja a 0) -> detenida", pp.espera(lambda: pp.estado()["linea"] == "detenida", 5), pp.estado()["linea"])
        verifica("bandas apagadas y stop_light 1",
                 pp.espera(lambda: not esc.bobina("entry_conveyor") and not esc.bobina("load_scale") and esc.bobina("stop_light"), 5))
        ev = eventos(datos)
        verifica("eventos: boton start y boton stop, comandos con origen tablero",
                 [e["boton"] for e in ev if e["ev"] == "boton"] == ["start", "stop"]
                 and [e.get("origen") for e in ev if e["ev"] == "comando"] == ["tablero", "tablero"],
                 [(e["ev"], e.get("boton"), e.get("origen")) for e in ev if e["ev"] in ("boton", "comando")])

        print("=== 3. Emergency stop ===")
        pulsa(esc, "start_button")
        pp.espera(lambda: pp.estado()["linea"] == "en_marcha", 5)
        esc.pon("emergency_stop", False)                            # presionado y se queda
        verifica("E-stop presionado -> linea en emergencia", pp.espera(lambda: pp.estado()["linea"] == "emergencia", 5),
                 pp.estado()["linea"])
        apagadas = ("entry_conveyor", "load_scale", "left_conveyor", "right_conveyor", "front_conveyor",
                    "send_left", "send_forward", "send_right")
        verifica("todo apagado: bandas y ruedas", pp.espera(lambda: not any(esc.bobina(b) for b in apagadas), 5),
                 {b: esc.bobina(b) for b in apagadas})
        verifica("reset_light 1, stop_light 1, start_light 0",
                 pp.espera(lambda: esc.bobina("reset_light") and esc.bobina("stop_light") and not esc.bobina("start_light"), 5))
        c, r = pp.comando(accion="marcha")
        verifica("marcha por HTTP con el E-stop presionado -> 409 paro_de_emergencia",
                 c == 409 and r.get("motivo") == "paro_de_emergencia", (c, r))
        pulsa(esc, "start_button")
        verifica("Start del tablero tampoco arranca", pp.estado()["linea"] == "emergencia" and not esc.bobina("entry_conveyor"))
        pulsa(esc, "stop_button", nc=True)
        verifica("Stop no saca de la emergencia", pp.estado()["linea"] == "emergencia", pp.estado()["linea"])
        esc.pon("emergency_stop", True)                             # se suelta
        verifica("al soltarlo: detenida, sin arrancar sola", pp.espera(lambda: pp.estado()["linea"] == "detenida", 5)
                 and not esc.bobina("entry_conveyor"), pp.estado()["linea"])
        verifica("reset_light vuelve a 0", pp.espera(lambda: not esc.bobina("reset_light"), 5))
        pulsa(esc, "start_button")
        verifica("Start vuelve a arrancar", pp.espera(lambda: pp.estado()["linea"] == "en_marcha", 5))

        print("=== 4. Contadores por destino ===")
        time.sleep(cfg["desviador"]["purga_ms"] / 1000.0 + 0.3)     # termina la purga del arranque
        for peso, rama in ((3.0, "left"), (5.5, "forward"), (8.0, "right"), (2.0, "left")):
            caja(esc, peso, rama)
        st = pp.estado()
        verifica("el cliente clasifica las 4 cajas sin errores %s" % st["contadores"]["por_destino"],
                 st["contadores"]["por_destino"] == {"left": 2, "forward": 1, "right": 1}
                 and st["contadores"]["desvios_erroneos"] == 0 and st["contadores"]["perdidas"] == 0, st["contadores"])
        cont = lambda: [esc.registro(n) for n in ("left_count", "forward_count", "right_count")]
        verifica("left_count 2, forward_count 1, right_count 1 en los registros", pp.espera(lambda: cont() == [2, 1, 1], 5), cont())
        pp.comando(accion="paro")
    finally:
        ps.detiene()

    print("=== 5. E-stop ya presionado al arrancar ===")
    esc.pon("emergency_stop", False)
    try:
        datos, ok = arranca(tmp, cfg_ruta)
        verifica("con el E-stop presionado desde antes, la linea queda en emergencia",
                 ok and pp.espera(lambda: pp.estado()["linea"] == "emergencia", 5), pp.estado()["linea"])
        c, r = pp.comando(accion="marcha")
        verifica("y marcha -> 409", c == 409, (c, r))
    finally:
        ps.detiene()
        esc.pon("emergency_stop", True)

    print("=== 6. Otro sondeo: las medidas no valen, vuelve la holgura ===")
    try:
        datos, ok = arranca(tmp, cfg_ruta, A2_SONDEO_MS=100)
        st = pp.estado()
        py = lp.calcula(cfg, 100, cfg["rtt_previsto_ms"], None, cfg["refresco_ms"], lp.medido_vale(cfg, 100))
        verifica("sondeo 100: Node-RED %s ms (%s) = Python %d ms (%s)" % (st["limites"]["t_ef_ms"], st["limites"].get("t_ef_origen"),
                                                                        py["t_ef_ms"], py["t_ef_origen"]),
                 ok and (st["limites"]["t_ef_ms"], st["limites"].get("t_ef_origen")) == (py["t_ef_ms"], "holgura")
                 and py["t_ef_origen"] == "holgura")
    finally:
        ps.detiene()
    try:
        fronteras(tmp, esc)
        una_sola_lectura(tmp, esc)
    finally:
        esc.cierra()


def una_lectura(esc, nombre, valor):
    """Pone la entrada en `valor` durante exactamente una lectura FC2 del cliente y la regresa."""
    previo = esc.di[E[nombre]["direccion"]]
    n0 = esc.lecturas_di
    esc.pon(nombre, valor)
    fin = time.time() + 2
    while esc.lecturas_di == n0 and time.time() < fin:
        time.sleep(0.001)
    esc.pon(nombre, previo)
    time.sleep(0.4)


def una_sola_lectura(tmp, esc):
    """Cierre de la fase 4, paso S: Stop actua con una lectura; Start y los sensores siguen con dos."""
    print("=== 8. Una sola lectura: Stop detiene, Start no arranca, un sensor no da flanco ===")
    resultados = {}
    for nombre, quita in (("repo", False), ("mutacion (stop sin lecturas_para_cambio)", True)):
        c = json.load(open(str(RAIZ / "config" / "planta_fio.json")))
        c["medido"]["refresco_p95_ms"] = 33
        if quita:
            c["tablero"]["stop"].pop("lecturas_para_cambio", None)
        ruta = tmp / ("planta_fio_una_%s.json" % ("mut" if quita else "repo"))
        ruta.write_text(json.dumps(c, indent=2), encoding="utf-8")
        try:
            datos, ok = arranca(tmp, ruta)
            pulsa(esc, "start_button")
            pp.espera(lambda: pp.estado()["linea"] == "en_marcha", 5)
            una_lectura(esc, "stop_button", False)                  # NC: presionado = 0, una lectura
            detuvo = bool(pp.espera(lambda: pp.estado()["linea"] == "detenida", 2))
            resultados[nombre] = detuvo
            if not quita:
                verifica("repo: un Stop de una sola lectura detiene la linea", ok and detuvo, pp.estado()["linea"])
                una_lectura(esc, "start_button", True)              # NA: presionado = 1, una lectura
                time.sleep(1)
                verifica("repo: un Start de una sola lectura no arranca la linea (Start sigue con 2 lecturas)",
                         pp.estado()["linea"] == "detenida", pp.estado()["linea"])
                pulsa(esc, "start_button")
                pp.espera(lambda: pp.estado()["linea"] == "en_marcha", 5)
                time.sleep(c["desviador"]["purga_ms"] / 1000.0 + 0.3)
                n_entra = sum(1 for e in eventos(datos) if e["ev"] in ("caja_entra", "caja_fantasma"))
                una_lectura(esc, "at_scale", True)                  # una lectura falsa en un sensor de la linea
                time.sleep(1)
                n_entra2 = sum(1 for e in eventos(datos) if e["ev"] in ("caja_entra", "caja_fantasma"))
                verifica("repo: una sola lectura falsa en at_scale no produce flanco (caja_entra/caja_fantasma %d -> %d)"
                         % (n_entra, n_entra2), n_entra2 == n_entra)
                pp.comando(accion="paro")
        finally:
            ps.detiene()
    verifica("mutacion: sin lecturas_para_cambio propio, el mismo Stop de una lectura NO detiene (el caso falla sin el cambio)",
             resultados.get("repo") is True and resultados.get("mutacion (stop sin lecturas_para_cambio)") is False, resultados)


def solo_una_lectura():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_tablero_"))
    esc = Escena(PUERTO)
    for n in ("stop_button", "emergency_stop", "at_exit_left", "at_exit_front", "at_exit_right", "fio_running"):
        esc.pon(n, True)
    try:
        una_sola_lectura(tmp, esc)
    finally:
        esc.cierra()


def solo_fronteras():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_tablero_"))
    esc = Escena(PUERTO)
    for n in ("stop_button", "emergency_stop", "at_exit_left", "at_exit_front", "at_exit_right", "fio_running"):
        esc.pon(n, True)
    try:
        fronteras(tmp, esc)
    finally:
        esc.cierra()


if __name__ == "__main__":
    if sys.argv[1:] == ["fronteras"]:
        solo_fronteras()
    elif sys.argv[1:] == ["una_lectura"]:
        solo_una_lectura()
    else:
        main()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
