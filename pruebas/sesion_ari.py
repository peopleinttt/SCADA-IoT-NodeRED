#!/usr/bin/env python3
"""Sesion con Ari (paso A de la fase 4): telefono, paro de emergencia con la nube y Start repetido. Python 3.9.

    caffeinate -d /usr/bin/python3 -u pruebas/sesion_ari.py --host 10.211.55.3 --puerto 502

Se apoya en lo mismo que prueba_fio.py tablero: reinicio de la escena por
Modbus, A2-Planta con el cliente de Factory I/O y su propio DATOS_DIR, y un
vigilante (este proceso, separado de Node-RED) que lee el tablero por su propia
conexion Modbus y anota cada cambio con su hora. Diferencias:
  - la nube va encendida (A2_NUBE=1, PLANTA_ID=planta_01) en el archivo de
    variables de la sesion, que vive fuera del repositorio; .env no se toca;
  - no hay llave de Gemini;
  - cada parte dice en pantalla que hacer y espera a verlo; una parte que no
    se completa en su plazo queda como bloqueada y la sesion sigue;
  - al terminar, Node-RED se detiene y el DATOS_DIR se copia a
    datos/corridas/A_<fecha>/ (sin el archivo de variables).
Ninguna credencial se imprime. Las definiciones estan en
docs/INSTRUMENTACION_A2.md, seccion 5; los resultados los arma
tools/analiza_sesion_a.py.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys, tempfile, threading, time
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
from modbus_tcp import Cliente  # noqa: E402

MAPA = RAIZ / "config" / "mapa_registros_fio.json"
E = {e["nombre"]: e for e in json.load(open(str(MAPA)))["etiquetas"]}
BOTONES = ["start_button", "stop_button", "emergency_stop"]
TS_BIN = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"


def iso(t=None):
    return datetime.fromtimestamp(time.time() if t is None else t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def lee_env():
    v = {}
    for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, x = l.split("=", 1)
            v[k.strip()] = x.strip().strip('"').strip("'")
    return v


def archivo_variables():
    """El archivo de variables de la sesion (fuera del repo): nube encendida, sin Gemini."""
    env = lee_env()
    for k in ("FIREBASE_DB_URL", "FIREBASE_API_KEY", "FB_INGESTOR_EMAIL", "FB_INGESTOR_PASS"):
        if not env.get(k):
            sys.exit("falta %s en .env" % k)
    v = {"FIREBASE_DB_URL": env["FIREBASE_DB_URL"], "IDENTITY_BASE_URL": "https://identitytoolkit.googleapis.com",
         "FIREBASE_API_KEY": env["FIREBASE_API_KEY"], "FB_INGESTOR_EMAIL": env["FB_INGESTOR_EMAIL"],
         "FB_INGESTOR_PASS": env["FB_INGESTOR_PASS"], "PLANTA_ID": "planta_01", "A2_NUBE": "1", "GEMINI_API_KEY": ""}
    d = pathlib.Path(tempfile.mkdtemp(prefix="a2_sesion_env_"))
    ruta = d / "sesion.env"
    ruta.write_text("".join("%s=%s\n" % kv for kv in v.items()), encoding="utf-8")
    os.chmod(str(ruta), 0o600)
    return ruta, v


class Vigilante(threading.Thread):
    """Lee el tablero cada ~15 ms por su propia conexion y anota cada cambio."""

    def __init__(self, host, puerto, archivo):
        super().__init__(daemon=True)
        self.c = Cliente(host, puerto, unidad=1)
        self.c.conecta()
        self.f = open(str(archivo), "a", encoding="utf-8")
        self.cambios = []
        self.vivo = True
        self.previo = None

    def run(self):
        while self.vivo:
            try:
                d = self.c.lee_discretas(0, 16)
            except Exception as e:                       # una lectura fallida no detiene la sesion
                self.f.write(json.dumps({"ts": iso(), "error": str(e)}) + "\n")
                self.f.flush()
                time.sleep(0.2)
                try:
                    self.c.cierra()
                    self.c.conecta()
                except Exception:
                    pass
                continue
            t = time.time()
            actual = {b: int(d[E[b]["direccion"]]) for b in BOTONES}
            if self.previo is None:
                self.f.write(json.dumps({"ts": iso(t), "t": t, "reposo": actual}) + "\n")
            else:
                for b in BOTONES:
                    if actual[b] != self.previo[b]:
                        reg = {"ts": iso(t), "t": t, "boton": b, "de": self.previo[b], "a": actual[b]}
                        self.cambios.append(reg)
                        self.f.write(json.dumps(reg) + "\n")
            self.f.flush()
            self.previo = actual
            time.sleep(0.015)

    def pulsaciones(self, boton, desde):
        """Pulsaciones completas de un boton desde t: (t_presiona, t_suelta)."""
        nc = boton != "start_button"
        presiona, suelta = (1, 0) if nc else (0, 1), (0, 1) if nc else (1, 0)
        out, abierta = [], None
        for c in self.cambios:
            if c["boton"] != boton or c["t"] < desde:
                continue
            if (c["de"], c["a"]) == presiona:
                abierta = c["t"]
            elif (c["de"], c["a"]) == suelta and abierta is not None:
                out.append((abierta, c["t"]))
                abierta = None
        return out

    def cierra(self):
        self.vivo = False
        time.sleep(0.1)
        self.c.cierra()


class Conexiones(threading.Thread):
    """Conexiones establecidas al puerto de Node-RED, cada 2 s (A1)."""

    def __init__(self, archivo):
        super().__init__(daemon=True)
        self.f = open(str(archivo), "a", encoding="utf-8")
        self.vivo = True

    def run(self):
        while self.vivo:
            r = subprocess.run(["lsof", "-nP", "-iTCP:%d" % ps.PUERTO_NR, "-sTCP:ESTABLISHED"],
                               capture_output=True, text=True)
            remotos = sorted({l.split("->")[1].split()[0] for l in r.stdout.splitlines() if "->" in l})
            self.f.write(json.dumps({"ts": iso(), "remotos": remotos}) + "\n")
            self.f.flush()
            time.sleep(2)


def eventos(datos):
    ruta = datos / "a2_planta_eventos.jsonl"
    if not ruta.exists():
        return []
    out = []
    for l in ruta.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def desde(evs, t_iso):
    return [e for e in evs if e.get("ts", "") >= t_iso]


def espera(cond, plazo_s, cada=0.5):
    fin = time.time() + plazo_s
    while time.time() < fin:
        r = cond()
        if r:
            return r
        time.sleep(cada)
    return None


def dice(texto):
    print(">>> " + texto, flush=True)


class _SoloA3(Exception):
    pass


def parte_a3(x, vig, datos, parte, pf):
    """Solo Start repetido, con la escena reiniciada antes, como la parte A3."""
    print("    reinicio de la escena por Modbus antes de A3", flush=True)
    ok_r = pf.reinicia(x.host)
    time.sleep(2)
    t0, t0n = iso(), time.time()
    dice("PARTE A3. En el tablero de la escena: Start y despues Stop, veinte veces cada uno, alternados,")
    dice("con clics rapidos como los de la sesion A. Te digo cuantas llevo.")
    visto = [0, 0]
    def listo():
        n_st = len(vig.pulsaciones("start_button", t0n))
        n_sp = len(vig.pulsaciones("stop_button", t0n))
        if (n_st, n_sp) != tuple(visto):
            visto[:] = [n_st, n_sp]
            print("    A3: %d Start y %d Stop vistos" % (n_st, n_sp), flush=True)
        return n_st >= 20 and n_sp >= 20
    r = espera(listo, x.plazo_a3, cada=0.3)
    parte("A3", "hecha" if r else "bloqueada", t0, ("reinicio %s" % ("ok" if ok_r else "FALLO")) +
          ("" if r else "; %d Start y %d Stop vistos en el plazo" % tuple(visto)))


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--host", default="10.211.55.3")
    a.add_argument("--puerto", type=int, default=502)
    a.add_argument("--plazo-a1", type=int, default=480)
    a.add_argument("--plazo-a2", type=int, default=360)
    a.add_argument("--plazo-a3", type=int, default=720)
    a.add_argument("--fecha", default=datetime.now().strftime("%Y-%m-%d"))
    a.add_argument("--solo-a3", action="store_true", help="solo la parte de Start repetido (paso S del cierre de la fase 4)")
    a.add_argument("--sin-nube", action="store_true", help="nube apagada y sin credenciales de Firebase")
    a.add_argument("--prefijo", default="A", help="carpeta datos/corridas/<prefijo>_<fecha>")
    x = a.parse_args()

    if x.sin_nube:
        d_env = pathlib.Path(tempfile.mkdtemp(prefix="a2_sesion_env_"))
        ruta_env, variables = d_env / "sesion.env", {"GEMINI_API_KEY": ""}
        ruta_env.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    else:
        ruta_env, variables = archivo_variables()
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_sesion_A_"))
    ts_ip = subprocess.run([TS_BIN, "ip", "-4"], capture_output=True, text=True).stdout.split()
    ts_ip = ts_ip[0] if ts_ip else None
    partes = open(str(datos / "partes.jsonl"), "a", encoding="utf-8")

    def parte(nombre, estado, t0, detalle=""):
        partes.write(json.dumps({"parte": nombre, "estado": estado, "inicio": t0, "fin": iso(), "detalle": detalle}) + "\n")
        partes.flush()
        print("    %s: %s %s" % (nombre, estado, detalle), flush=True)

    print("=== Sesion %s (datos en %s; variables de la sesion fuera del repo; %s; sin Gemini) ==="
          % (x.prefijo, datos, "nube apagada" if x.sin_nube else "nube encendida en planta_01"), flush=True)
    sys.path.insert(0, str(RAIZ / "pruebas"))
    import prueba_fio as pf
    if not pf.reinicia(x.host):
        sys.exit("no se pudo reiniciar la escena")
    ps.arranca(datos, A2_MAPA=MAPA, A2_PLANTA_CONFIG=RAIZ / "config" / "planta_fio.json", A2_SUSTITUTO=0,
               A2_MODBUS_HOST=x.host, A2_MODBUS_PUERTO=x.puerto, A2_MODBUS_UNIDAD=1, **variables)
    vig = Vigilante(x.host, x.puerto, datos / "vigilante.jsonl")
    con = Conexiones(datos / "conexiones.jsonl")
    try:
        if not pp.espera(lambda: pp.estado()["com"] == "ok", 30):
            sys.exit("A2-Planta no conecta con la escena")
        vig.start()
        con.start()
        print("    A2-Planta conectada (com ok); vigilante y conexiones corriendo; IP de Tailscale de la Mac: %s" % ts_ip, flush=True)

        # ---- A1 -----------------------------------------------------------------------
        t0 = iso()
        if x.solo_a3:
            raise _SoloA3()
        url = "http://%s:%d/dashboard/a2" % (ts_ip, ps.PUERTO_NR)
        dice("PARTE A1. En el telefono, con Tailscale activo, abre %s" % url)
        dice("presiona Start en la pagina, espera a que salgan al menos tres cajas, toma la captura y presiona Stop.")
        def a1_listo():
            ev = desde(eventos(datos), t0)
            m = next((i for i, e in enumerate(ev) if e["ev"] == "comando" and e.get("accion") == "marcha"
                      and e.get("origen") == "hmi"), None)
            if m is None:
                return None
            cajas = 0
            for e in ev[m + 1:]:
                if e["ev"] == "paso_caja":
                    cajas += 1
                if e["ev"] == "comando" and e.get("accion") == "paro" and e.get("origen") == "hmi":
                    return cajas >= 3
            return None
        r = espera(a1_listo, x.plazo_a1)
        parte("A1", "hecha" if r else "bloqueada", t0, "" if r else "no se vio marcha, 3 cajas y paro con origen hmi en el plazo")
        pp.comando(accion="paro")
        time.sleep(2)

        # ---- A2 -----------------------------------------------------------------------
        t0, t0n = iso(), time.time()
        dice("PARTE A2. En el tablero de la escena: Start; espera dos cajas; Emergency stop y sostenlo unos 5 s;")
        dice("suelta Emergency stop; despues Start y Stop.")
        def a2_listo():
            ev = desde(eventos(datos), t0)
            emer = vig.pulsaciones("emergency_stop", t0n)
            if not emer or not any(e["ev"] == "emergencia_liberada" for e in ev):
                return None
            t_suelta = emer[0][1]
            st = [p for p in vig.pulsaciones("start_button", t_suelta)]
            sp = [p for p in vig.pulsaciones("stop_button", t_suelta)]
            return bool(st and sp and sp[-1][0] > st[0][0])
        r = espera(a2_listo, x.plazo_a2)
        time.sleep(3)
        parte("A2", "hecha" if r else "bloqueada", t0, "" if r else "no se vio la secuencia completa en el plazo")
        pp.comando(accion="paro")
        time.sleep(3)

        # ---- A3 -----------------------------------------------------------------------
        print("    reinicio de la escena por Modbus antes de A3", flush=True)
        ok_r = pf.reinicia(x.host)
        time.sleep(2)
        t0, t0n = iso(), time.time()
        dice("PARTE A3. En el tablero de la escena: Start y despues Stop, veinte veces, a tu ritmo normal,")
        dice("dejando al menos 2 s entre una pulsacion y la siguiente. Te digo cuantas llevo.")
        visto = [0]
        def a3_listo():
            n_st = len(vig.pulsaciones("start_button", t0n))
            n_sp = len(vig.pulsaciones("stop_button", t0n))
            if n_st != visto[0]:
                visto[0] = n_st
                print("    A3: %d Start y %d Stop vistos" % (n_st, n_sp), flush=True)
            return n_st >= 20 and n_sp >= 20
        r = espera(a3_listo, x.plazo_a3, cada=0.3)
        parte("A3", "hecha" if r else "bloqueada", t0, ("reinicio %s" % ("ok" if ok_r else "FALLO")) +
              ("" if r else "; %d Start vistos en el plazo" % visto[0]))
        dice("SESION TERMINADA. Gracias; ya puedes irte.")
    except _SoloA3:
        parte_a3(x, vig, datos, parte, pf)
        dice("SESION TERMINADA. Gracias; ya puedes irte.")
    finally:
        try:
            pp.comando(accion="paro")
            time.sleep(4)                                # el ultimo latido (cambio de estado) sale a la nube
        except Exception:
            pass
        con.vivo = False
        try:
            vig.cierra()
        except Exception:
            pass
        ps.detiene()
        destino = RAIZ / "datos" / "corridas" / ("%s_%s" % (x.prefijo, x.fecha))
        destino.mkdir(parents=True, exist_ok=True)
        for f in datos.iterdir():
            if f.is_file():
                shutil.copy(str(f), str(destino / f.name))
        shutil.rmtree(str(ruta_env.parent), ignore_errors=True)
        print("=== Node-RED detenido; datos copiados a %s ===" % destino.relative_to(RAIZ), flush=True)


if __name__ == "__main__":
    main()
