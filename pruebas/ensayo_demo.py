#!/usr/bin/env python3
"""Ensayo completo de docs/DEMO_A2.md, sin intervenir fuera de lo que dice el documento. Python 3.9.

    /usr/bin/python3 pruebas/ensayo_demo.py          (~5 min, con el sustituto)
    /usr/bin/python3 pruebas/ensayo_demo.py --real   (~6 min, Factory I/O + Firebase real + grafica)
    /usr/bin/python3 pruebas/ensayo_demo.py --real --con-gemini   (paso D de la fase 4: UNA consulta real)
    /usr/bin/python3 pruebas/ensayo_demo.py --real --con-nube     (nube encendida, sin llave ni consulta)

Con --con-gemini (solo con --real): el archivo de variables del ensayo conserva
la llave de Gemini de .env y enciende la nube (A2_NUBE=1, PLANTA_ID=planta_01),
ya que .env sigue con A2_NUBE=0. Lleva A2_DIAG_MAX_DIA=1, para que el tope
diario de A2-Diagnostico impida una segunda consulta (incluida la del disparo
periodico), y DIAG_MAX_DIA=-1, para que la pestana de diagnostico de la
Actividad 1 (que consulta al arrancar y comparte la llave) se detenga en su
tope diario sin consultar: con 0 no sirve, porque 11_arma_prompt.js hace
Number(...) || 200. El paso 7 presiona el boton una vez, espera la respuesta,
y pasados 65 s (el limitador de 1 por minuto descarta lo que llega antes) lo
presiona otra vez para comprobar el tope.

Con --real: la escena de Factory I/O en Parallels, por el relevo de Node
(pruebas/relevo.mjs, que hace de interruptor del paso 8 y deja a la sonda de
Python llegar a la VM), escribiendo en planta_01 de la base real con
A2_NUBE=1 y la grafica con el visor real. Gemini no se consulta (sin llave en
el archivo del ensayo: no gasta cuota).

Corre los pasos del guion en orden, con la planta sustituta (escena del
desviador) y los mismos comandos del documento: demo_a2.sh, proxy_retardo.py
como interruptor, la HMI (por su socket.io, como el navegador), la sonda en
modo vigila. Usa un archivo de variables propio (ENV_ARCHIVO) copiado de .env
con dos cambios para no gastar cuota ni tocar la base real: sin llave de
Gemini y con la base de la Actividad 1 apuntando a una direccion muerta. La
unica llamada real es la revision de sesion de Firebase de demo_a2.sh.
Los pasos que dependen de una PUERTA ARI se reportan como BLOQUEADO, no como OK.
"""
import json, os, pathlib, subprocess, sys, tempfile, time, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
from prueba_hmi import Pagina  # noqa: E402
from proxy_retardo import Proxy  # noqa: E402

verifica = ps.verifica
bloqueados = []


def bloqueado(paso, puerta):
    bloqueados.append((paso, puerta))
    print("  BLOQ  %s (%s)" % (paso, puerta))


def demo(*args, env=None):
    r = subprocess.run([str(RAIZ / "demo_a2.sh")] + list(args), capture_output=True, text=True, env=env, timeout=240)
    return r.returncode, r.stdout + r.stderr


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_ensayo_"))
    datos = tmp / "datos"
    datos.mkdir()
    lineas = [l for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines()
              if not l.split("=", 1)[0].strip() in ("GEMINI_API_KEY", "FIREBASE_DB_URL", "DATOS_DIR", "A2_NUBE",
                                                    # el hash del editor de Ari no se copia a un archivo temporal;
                                                    # en el ensayo el editor queda deshabilitado (paso S2)
                                                    "NODE_RED_ADMIN_USER", "NODE_RED_ADMIN_HASH")
              and not l.startswith("A2_")]
    lineas += ["GEMINI_API_KEY=", "FIREBASE_DB_URL=http://127.0.0.1:9", 'DATOS_DIR="%s"' % datos, "A2_NUBE=",
               # Entre comillas: la ruta del repo lleva un espacio ("dev aws") y
               # demo_a2.sh carga este archivo con "." de bash.
               'A2_MAPA="%s"' % (RAIZ / "config" / "mapa_registros_desviador.json"),
               'A2_SUST_CONFIG="%s"' % (RAIZ / "config" / "sustituto_desviador.json"),
               'A2_PLANTA_CONFIG="%s"' % (RAIZ / "config" / "planta_desviador.json"),
               "A2_MODBUS_HOST=127.0.0.1", "A2_MODBUS_PUERTO=5030"]
    archivo = tmp / "env.ensayo"
    archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    env = dict(os.environ, ENV_ARCHIVO=str(archivo))
    proxy = None
    try:
        print("=== 0. Antes de grabar ===")
        proxy = Proxy(5030, ("127.0.0.1", 5020), 0).inicia()          # el interruptor del paso 8
        c, out = demo("--revisa", env=env)
        print("\n".join("    " + l for l in out.strip().splitlines()[-8:]))
        verifica("./demo_a2.sh --revisa: limites factibles y sesion de Firebase", c == 0 and "limites factibles" in out
                 and "Firebase da sesion" in out, c)

        print("=== 1. Arquitectura: ./demo_a2.sh ===")
        c, out = demo(env=env)
        print("\n".join("    " + l for l in out.strip().splitlines()[-12:]))
        verifica("demo_a2.sh arranca todo y no reporta fallas (Modbus del sustituto incluido)", c == 0, c)
        verifica("imprime las URL de la HMI y de la grafica", "/dashboard/a2" in out and "/proceso.html" in out)
        # Paso S2: GET /flows es de la API de administracion y con el .env real
        # pediria la contrasena de Ari. Las pestanas salen del archivo de flujos
        # que arranca.sh copia al runtime y con el que arranca Node-RED.
        flujos = json.loads((RAIZ / "node-red" / "runtime" / "flows.json").read_text(encoding="utf-8"))
        tabs = [n["label"] for n in flujos if n["type"] == "tab"]
        verifica("el editor muestra las pestanas A2 junto a las de la A1 (%d)" % len(tabs),
                 {"A1 · Ingesta", "A2 · Planta (cliente Modbus)", "A2 · Nube (rama proceso)", "A2 · HMI (Dashboard 2.0)",
                  "A2 · Diagnostico (Gemini)", "A2 · Sustituto (planta simulada)"} <= set(tabs), tabs)

        print("=== 2. Factory I/O corriendo ===")
        bloqueado("Factory I/O real con Sorting by Weight", "PUERTA ARI R0 (mapa) y R1 (VM offline)")

        print("=== 3. HMI: marcha y paro ===")
        pg = Pagina()
        verifica("la HMI abre y dice Online / Stopped", pg.espera(lambda p: p.estado.get("ready") and p.estado["comm"] == "ok", 20)
                 and pg.estado["line"] == "Stopped", pg.estado)
        r = pg.boton("marcha")
        verifica("Start -> 200", r and r["codigo"] == 200, r)
        r = pg.boton("emisor", valor=True)
        verifica("Emitter ON -> 200", r and r["codigo"] == 200, r)
        r = pg.boton("velocidad", vel_V=3)
        verifica("comando rechazado visible: consigna con bandas fijas -> 422 velocidad_no_aplica",
                 r and r["codigo"] == 422 and r.get("motivo") == "velocidad_no_aplica", r)

        print("=== 4. Cajas clasificadas (y vigila del paso 2 contra el sustituto) ===")
        v = subprocess.run([sys.executable, str(RAIZ / "tools" / "sonda_modbus.py"), "--mapa",
                            str(RAIZ / "config" / "mapa_registros_desviador.json"), "--host", "127.0.0.1", "--puerto", "5030",
                            "vigila", "-s", "20"],     # --host: sin el, la sonda toma A2_MODBUS_HOST de .env (la VM)
                           capture_output=True, text=True, timeout=60)
        print("\n".join("    " + l for l in v.stdout.strip().splitlines()[:6]))
        verifica("sonda vigila ve cambiar sensores con la linea en marcha", v.returncode == 0 and "pulsos en 1" in v.stdout)
        verifica("en un minuto la HMI cuenta cajas clasificadas por destino y 0 perdidas",
                 pg.espera(lambda p: p.estado["boxesOut"] >= 5, 90) and pg.estado["lost"] == 0, pg.estado and
                 {k: pg.estado[k] for k in ("boxesOut", "perMinute", "byDestination", "lost", "lastBox")})
        print("    HMI: %s" % {k: pg.estado[k] for k in ("boxesOut", "perMinute", "byDestination", "lastBox")})

        print("=== 5. Registros llegando a Firebase ===")
        verifica("la HMI dice que la escritura en la nube esta apagada (A2_NUBE)", pg.estado["firebaseOn"] is False)
        bloqueado("registros en la consola de Firebase", "PUERTA ARI P1 (publicar reglas) y A2_NUBE=1")

        print("=== 6. Grafica en vivo ===")
        c = urllib.request.urlopen("http://127.0.0.1:8123/proceso.html", timeout=5).status
        verifica("http://localhost:8123/proceso.html se sirve (200)", c == 200, c)
        bloqueado("grafica con datos reales", "PUERTA ARI P1; probada contra el emulador en C8 (6/7)")

        print("=== 7. Diagnostico ===")
        pg.s.emite("widget-action", "ui_tpl_a2", {"payload": {"accion": "diagnostico"}})
        pg.lee(3)
        verifica("sin llave en el ensayo, el boton no consulta y la HMI no muestra nada invalido",
                 pg.estado.get("diagnosis") is None, pg.estado.get("diagnosis"))
        print("  --    (en el ensayo no se gasta cuota; la consulta real se probo en C7)")

        print("=== 8. Estado seguro: desconexion y recuperacion ===")
        n_ev = sum(1 for _ in (datos / "a2_planta_eventos.jsonl").open())
        t0 = time.time()
        proxy.detiene()                                                # "stop the proxy (Ctrl+C)"
        visto = pg.espera(lambda p: p.estado["comm"] == "sin_comunicacion", 8)
        tarda = time.time() - t0
        verifica("la HMI dice NO COMMUNICATION en %.1f s (< timeout_com_ms + 1 s)" % tarda, visto and tarda < 3.0)
        r = pg.boton("marcha")
        verifica("Start -> 409 sin_comunicacion en pantalla", r and r["codigo"] == 409, r)
        proxy.inicia()                                                 # "start the proxy again"
        verifica("al volver: Online y Stopped, sin reanudar sola",
                 pg.espera(lambda p: p.estado["comm"] == "ok" and not p.estado["running"], 20), pg.estado)
        ev = [json.loads(l) for l in (datos / "a2_planta_eventos.jsonl").read_text().splitlines()[n_ev:]]
        seguros = [e["etiqueta"] for e in ev if e.get("ev") == "escritura" and e.get("motivo") == "seguro"]
        nombres = [e["ev"] for e in ev]
        verifica("eventos: reconexion_inicia, escrituras seguras emitter, entry_conveyor, load_scale, reconexion_completa",
                 "reconexion_inicia" in nombres and "reconexion_completa" in nombres
                 and seguros[:3] == ["emitter", "entry_conveyor", "load_scale"], (nombres[:8], seguros))
        r = pg.boton("marcha")
        verifica("Start vuelve a funcionar", r and r["codigo"] == 200, r)
        pg.boton("paro")

        print("=== 9. Cierre ===")
        c, out = demo("--apaga", env=env)
        time.sleep(1)
        libres = all(subprocess.run(["lsof", "-ti", "tcp:%d" % p, "-sTCP:LISTEN"], capture_output=True).returncode != 0
                     for p in (1881, 8123))
        verifica("./demo_a2.sh --apaga deja libres el 1881 y el 8123", c == 0 and libres, out)
    finally:
        if proxy:
            proxy.detiene()
        for p in (1881, 8123):
            subprocess.run("lsof -ti tcp:%d -sTCP:LISTEN | xargs kill 2>/dev/null" % p, shell=True)
    print("\nBloqueados por puertas de Ari: %d" % len(bloqueados))
    for paso, puerta in bloqueados:
        print("  - %s: %s" % (paso, puerta))


class Relevo:
    """Interruptor del paso 8 con Factory I/O: el relevo TCP de Node."""

    def __init__(self, local, host, puerto):
        self.args, self.p = ["node", str(RAIZ / "pruebas" / "relevo.mjs"), str(local), host, str(puerto)], None
        self.local = local

    def inicia(self):
        self.p = subprocess.Popen(self.args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        return self

    def detiene(self):
        if self.p and self.p.poll() is None:
            self.p.terminate()
            self.p.wait(5)


def real():
    import urllib.parse
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_ensayo_real_"))
    datos = tmp / "datos"
    datos.mkdir()
    base = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines()
                if "=" in l and not l.lstrip().startswith("#"))
    escena = base.get("A2_MODBUS_HOST", "10.211.55.3").strip('"')
    gemini = "--con-gemini" in sys.argv
    # --con-nube: la nube encendida como con --con-gemini, pero sin llave (sin consulta).
    solo_nube = "--con-nube" in sys.argv and not gemini
    quita = ("GEMINI_API_KEY", "DATOS_DIR", "A2_MODBUS_HOST", "A2_MODBUS_PUERTO")
    if gemini or solo_nube:
        quita += ("A2_NUBE", "PLANTA_ID", "A2_DIAG_MAX_DIA", "DIAG_MAX_DIA")
    lineas = [l for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines()
              if l.split("=", 1)[0].strip() not in quita]
    lineas += ['DATOS_DIR="%s"' % datos, "A2_MODBUS_HOST=127.0.0.1", "A2_MODBUS_PUERTO=5030"]
    if gemini:
        clave = [l for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines() if l.split("=", 1)[0].strip() == "GEMINI_API_KEY"]
        if not clave or not clave[0].split("=", 1)[1].strip().strip('"'):
            sys.exit("--con-gemini: falta GEMINI_API_KEY en .env")
        lineas += clave + ["A2_NUBE=1", "PLANTA_ID=planta_01", "A2_DIAG_MAX_DIA=1", "DIAG_MAX_DIA=-1"]
    else:
        lineas += ["GEMINI_API_KEY="]
        if solo_nube:
            lineas += ["A2_NUBE=1", "PLANTA_ID=planta_01"]
    archivo = tmp / "env.ensayo"
    archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.chmod(str(archivo), 0o600)
    env = dict(os.environ, ENV_ARCHIVO=str(archivo))
    nube = gemini or solo_nube or base.get("A2_NUBE", "").strip('"') == "1"
    relevo = Relevo(5030, escena, 502).inicia()
    try:
        print("=== 0. Antes de grabar (Factory I/O en %s por el relevo 127.0.0.1:5030) ===" % escena)
        c, out = demo("--revisa", env=env)
        print("\n".join("    " + l for l in out.strip().splitlines()[-8:]))
        verifica("./demo_a2.sh --revisa: limites factibles, Modbus contesta, sesion de Firebase",
                 c == 0 and "limites factibles" in out and "contesta" in out and "Firebase da sesion" in out, c)

        print("=== 1. Arquitectura: ./demo_a2.sh (reinicia la escena por Modbus) ===")
        c, out = demo(env=env)
        print("\n".join("    " + l for l in out.strip().splitlines()[-12:]))
        verifica("demo_a2.sh arranca todo sin fallas y reinicia la escena", c == 0 and "escena reiniciada" in out, c)
        verifica("imprime las URL de la HMI y de la grafica", "/dashboard/a2" in out and "/proceso.html" in out)

        print("=== 2. Factory I/O corriendo ===")
        st = json.load(urllib.request.urlopen("http://127.0.0.1:1881/a2/planta/estado", timeout=5))
        verifica("A2-Planta: com ok, desviador, factible con T_ef medido (%s ms)" % st["limites"]["t_ef_ms"],
                 st["com"] == "ok" and st["actuador"] == "desviador" and st["limites"]["factible"]
                 and st["limites"].get("t_ef_origen") == "medido", st["limites"])

        print("=== 3. HMI: marcha y paro ===")
        pg = Pagina()
        verifica("la HMI abre y dice Online / Stopped", pg.espera(lambda p: p.estado.get("ready") and p.estado["comm"] == "ok", 20)
                 and pg.estado["line"] == "Stopped", pg.estado)
        r = pg.boton("marcha")
        verifica("Start -> 200", r and r["codigo"] == 200, r)
        r = pg.boton("emisor", valor=True)
        verifica("Emitter ON -> 422 sin_emisor (la escena emite sola)", r and r["codigo"] == 422 and r.get("motivo") == "sin_emisor", r)
        r = pg.boton("velocidad", vel_V=3)
        verifica("comando rechazado visible: consigna con bandas fijas -> 422 velocidad_no_aplica",
                 r and r["codigo"] == 422 and r.get("motivo") == "velocidad_no_aplica", r)

        print("=== 4. Cajas clasificadas (y vigila del paso 2) ===")
        v = subprocess.run([sys.executable, str(RAIZ / "tools" / "sonda_modbus.py"), "--mapa",
                            str(RAIZ / "config" / "mapa_registros_fio.json"), "--host", "127.0.0.1", "--puerto", "5030",
                            "vigila", "-s", "20"], capture_output=True, text=True, timeout=60)
        print("\n".join("    " + l for l in v.stdout.strip().splitlines()[:6]))
        verifica("sonda vigila ve cambiar sensores con la linea en marcha", v.returncode == 0 and "pulsos en 1" in v.stdout)
        verifica("la HMI cuenta cajas clasificadas por destino y 0 perdidas",
                 pg.espera(lambda p: p.estado["boxesOut"] >= 8, 120) and pg.estado["lost"] == 0,
                 {k: pg.estado.get(k) for k in ("boxesOut", "perMinute", "byDestination", "lost", "lastBox")})
        print("    HMI: %s" % {k: pg.estado.get(k) for k in ("boxesOut", "perMinute", "byDestination", "lastBox")})

        print("=== 5. Registros llegando a Firebase ===")
        if nube:
            verifica("la HMI dice que la nube esta encendida y muestra el ultimo registro aceptado",
                     pg.espera(lambda p: p.estado.get("firebaseOn") and p.estado.get("firebase"), 30),
                     {k: pg.estado.get(k) for k in ("firebaseOn", "firebase", "firebaseLast")})
            print("    ultimo aceptado: %s" % pg.estado.get("firebase"))
        else:
            bloqueado("registros en Firebase", "A2_NUBE no es 1 en .env")

        print("=== 6. Grafica en vivo (visor real, sin recargar) ===")
        c = urllib.request.urlopen("http://127.0.0.1:8123/proceso.html", timeout=5).status
        verifica("http://localhost:8123/proceso.html se sirve (200)", c == 200, c)
        if nube:
            url = "http://127.0.0.1:8123/proceso.html?" + urllib.parse.urlencode(
                {"correo": base["FB_VISOR_EMAIL"].strip('"'), "clave": base["FB_VISOR_PASS"].strip('"'), "planta": "planta_01"})
            chrome = subprocess.Popen(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new",
                                       "--disable-gpu", "--no-first-run", "--remote-debugging-port=9335",
                                       "--user-data-dir=%s" % (tmp / "chrome"), "--window-size=1280,900", url],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                # Chrome sin ventana puede tardar mas de 4 s en abrir DevTools (paso D de la
                # fase 4: con la espera fija de 4 s el paso no tuvo ni una muestra). Se espera
                # a que /json liste la pagina, hasta 30 s, como en prueba_grafica.py.
                for _ in range(60):
                    try:
                        if any(x.get("type") == "page" for x in json.load(urllib.request.urlopen(
                                "http://127.0.0.1:9335/json", timeout=1))):
                            break
                    except Exception:
                        pass
                    time.sleep(0.5)
                time.sleep(2)
                mira = subprocess.run(["node", str(RAIZ / "pruebas" / "cdp_mira.mjs"), "9335", "60", "5",
                                       str(tmp / "grafica.png")], capture_output=True, text=True, timeout=120)
            finally:
                chrome.terminate()
            if mira.stderr.strip():
                print("    cdp_mira: %s" % mira.stderr.strip().splitlines()[-1][:200])
            m = [json.loads(l) for l in mira.stdout.splitlines() if l.strip()]
            m = [x for x in m if x["a2"]]
            verifica("la grafica lee como visor real y sube sin recargar (%s -> %s cajas, %s navegaciones)"
                     % (m and m[0]["a2"]["cajas"], m and m[-1]["a2"]["cajas"], m and m[-1]["navegaciones"]),
                     len(m) >= 2 and all(x["a2"]["error"] is None for x in m) and m[-1]["a2"]["cajas"] > m[0]["a2"]["cajas"]
                     and m[-1]["navegaciones"] == 0, m[-1]["a2"] if m else None)
        else:
            bloqueado("grafica con datos reales", "A2_NUBE no es 1 en .env")

        print("=== 7. Diagnostico ===")
        # La sesion socket.io de la HMI no se sondeo durante el minuto de la
        # grafica y el servidor la cerro: se abre otra, como al recargar la pagina.
        pg = Pagina()
        verifica("la HMI vuelve a abrir (Online)", pg.espera(lambda p: p.estado.get("ready") and p.estado["comm"] == "ok", 20))
        if not gemini:
            pg.s.emite("widget-action", "ui_tpl_a2", {"payload": {"accion": "diagnostico"}})
            pg.lee(3)
            verifica("sin llave en el ensayo, el boton no consulta y la HMI no muestra nada invalido",
                     pg.estado.get("diagnosis") is None, pg.estado.get("diagnosis"))
            print("  --    (no se gasta cuota de Gemini en el ensayo; la consulta real se probo en C7)")
        else:
            diag_csv = lambda: sorted(datos.glob("a2_diagnosticos_*.csv"))
            filas = lambda: [l for f in diag_csv() for l in f.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
            t_boton = time.time()
            pg.s.emite("widget-action", "ui_tpl_a2", {"payload": {"accion": "diagnostico"}})
            pg.espera(lambda p: p.estado.get("diagnosis") is not None or bool(filas()), 90)
            pg.lee(2)
            D = pg.estado.get("diagnosis")
            f1 = filas()
            print("    a2_diagnosticos: %s" % f1)
            if D:
                print("    modelo %s, latencia %s ms, nivel %s, accion %s" % (D.get("modelo"), D.get("latencia_ms"),
                                                                           D.get("nivel_estimado"), D.get("accion_codigo")))
                print("    texto: %s" % D.get("texto_diagnostico"))
                print("    justificacion: %s" % D.get("justificacion"))
            verifica("una consulta real: una sola fila con respuesta del modelo, valida, y la HMI la muestra",
                     len(f1) == 1 and f1[0].split(";")[4] == "valido" and D is not None, (f1, D))
            t_diag = time.time()
            espera = max(0.0, 65 - (time.time() - t_boton))
            print("    espera %.0f s para que el limitador de 1 por minuto no descarte la segunda pulsacion" % espera)
            time.sleep(espera)
            pg = Pagina()
            pg.espera(lambda p: p.estado.get("ready"), 20)
            pg.s.emite("widget-action", "ui_tpl_a2", {"payload": {"accion": "diagnostico"}})
            pg.lee(10)
            D2 = pg.estado.get("diagnosis")
            verifica("la segunda pulsacion se detiene en el tope diario: sigue habiendo una sola fila (ninguna salida a la red) "
                     "y la HMI muestra el mismo diagnostico valido", filas() == f1 and D2 is not None and D is not None
                     and D2.get("ts") == D.get("ts"), (filas(), D2))
            ev = [json.loads(l) for l in (datos / "a2_planta_eventos.jsonl").read_text().splitlines() if l.strip()]
            from datetime import datetime as _dt
            t_ev = lambda e: _dt.fromisoformat(e["ts"].replace("Z", "+00:00")).timestamp()
            cmds = [e for e in ev if e.get("ev") == "comando" and t_diag - 1 <= t_ev(e) <= t_diag + 30]
            verifica("en los 30 s siguientes al diagnostico no hay ningun comando (%d)" % len(cmds), not cmds, cmds)
            a1 = sorted(datos.glob("diagnosticos_*.csv"))
            verifica("la pestana de diagnostico de la Actividad 1 no consulto (sin diagnosticos_*.csv: %s)" % [x.name for x in a1], not a1)

        print("=== 8. Estado seguro: desconexion y recuperacion ===")
        n_ev = sum(1 for _ in (datos / "a2_planta_eventos.jsonl").open())
        t0 = time.time()
        relevo.detiene()                                               # "stop the relay (Ctrl+C)"
        visto = pg.espera(lambda p: p.estado["comm"] == "sin_comunicacion", 8)
        tarda = time.time() - t0
        verifica("la HMI dice NO COMMUNICATION en %.1f s (< timeout_com_ms + 1 s)" % tarda, visto and tarda < 3.0)
        r = pg.boton("marcha")
        verifica("Start -> 409 sin_comunicacion en pantalla", r and r["codigo"] == 409, r)
        relevo.inicia()                                                # "start the relay again"
        verifica("al volver: Online y Stopped, sin reanudar sola",
                 pg.espera(lambda p: p.estado["comm"] == "ok" and not p.estado["running"], 20), pg.estado)
        ev = [json.loads(l) for l in (datos / "a2_planta_eventos.jsonl").read_text().splitlines()[n_ev:]]
        seguros = [e["etiqueta"] for e in ev if e.get("ev") == "escritura" and e.get("motivo") == "seguro"]
        esperado = ["entry_conveyor", "load_scale", "left_conveyor", "right_conveyor", "front_conveyor",
                    "send_left", "send_forward", "send_right"]
        verifica("eventos: reconexion_inicia, 8 escrituras seguras (bandas y ruedas) en orden, reconexion_completa",
                 "reconexion_inicia" in [e["ev"] for e in ev] and "reconexion_completa" in [e["ev"] for e in ev]
                 and seguros[:8] == esperado, seguros)
        r = pg.boton("marcha")
        verifica("Start vuelve a funcionar", r and r["codigo"] == 200, r)
        time.sleep(5)
        pg.boton("paro")

        print("=== 9. Cierre ===")
        c, out = demo("--apaga", env=env)
        time.sleep(1)
        libres = all(subprocess.run(["lsof", "-ti", "tcp:%d" % p, "-sTCP:LISTEN"], capture_output=True).returncode != 0
                     for p in (1881, 8123))
        verifica("./demo_a2.sh --apaga deja libres el 1881 y el 8123", c == 0 and libres, out)
    finally:
        relevo.detiene()
        for p in (1881, 8123):
            subprocess.run("lsof -ti tcp:%d -sTCP:LISTEN | xargs kill 2>/dev/null" % p, shell=True)
    print("\nBloqueados: %d" % len(bloqueados))
    for paso, puerta in bloqueados:
        print("  - %s: %s" % (paso, puerta))


if __name__ == "__main__":
    real() if "--real" in sys.argv else main()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
