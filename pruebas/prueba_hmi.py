#!/usr/bin/env python3
"""Pruebas de la HMI de Dashboard 2.0 (C6). Python 3.9.

    /usr/bin/python3 pruebas/prueba_hmi.py          (~2 min)

Habla con la pagina por el mismo camino que el navegador (socket.io de
Dashboard 2.0, pruebas/socketio_min.py): recibe lo que la pagina pinta
(msg-input) y aprieta sus botones (widget-action). Oraculos: el registro del
sustituto (los controles lo mueven), las respuestas con su codigo (409/422
visibles) y el reloj (la desconexion se ve en menos de timeout_com_ms + 1 s).
Ademas abre la pagina por la IP de Tailscale de esta Mac; abrirla desde OTRO
equipo de la tailnet es una prueba que hace Ari (ver docs/CICLO_DESARROLLO_A2.md).
"""
import http.client, json, pathlib, socket, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
import prueba_desviador as pd  # noqa: E402
from socketio_min import SocketIO  # noqa: E402

verifica = ps.verifica
WIDGET = "ui_tpl_a2"


class Pagina:
    """La pagina vista desde el socket: ultimo estado y ultima respuesta."""
    def __init__(self):
        self.s = SocketIO("127.0.0.1", ps.PUERTO_NR, "/dashboard/socket.io/").conecta()
        self.estado, self.respuesta = None, None

    def lee(self, segundos):
        for nombre, args in self.s.recibe(segundos):
            if nombre == "msg-input:" + WIDGET and args:
                m = args[0]
                p = m.get("payload") if isinstance(m, dict) else None
                # Igual que la pagina: por la forma del payload, no por topic.
                if isinstance(p, dict) and "ready" in p:
                    self.estado = p
                elif isinstance(p, dict) and "codigo" in p:
                    self.respuesta = p

    def espera(self, cond, segundos):
        fin = time.time() + segundos
        while time.time() < fin:
            self.lee(min(2, max(0.2, fin - time.time())))
            if self.estado is not None and cond(self):
                return True
        return False

    def boton(self, accion, **extra):
        self.respuesta = None
        self.s.emite("widget-action", WIDGET, {"payload": dict({"accion": accion}, **extra)})
        self.espera(lambda p: p.respuesta is not None, 6)
        return self.respuesta


def pide(host, ruta):
    c = http.client.HTTPConnection(host, ps.PUERTO_NR, timeout=5)
    c.request("GET", ruta)
    r = c.getresponse()
    t = r.read().decode(errors="replace")
    c.close()
    return r.status, t


def ip_tailscale():
    try:
        r = subprocess.run(["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "ip", "-4"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def empujador():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_hmi_"))
    print("=== HMI con el empujador (C4), por proxy (datos en %s) ===" % datos)
    proxy = pp.arranca("local", datos)
    try:
        c, t = pide("127.0.0.1", "/dashboard/a2")
        verifica("GET /dashboard/a2 -> 200", c == 200 and "<html" in t.lower(), (c, t[:60]))
        ip = ip_tailscale()
        if ip:
            c, _ = pide(ip, "/dashboard/a2")
            verifica("la pagina abre por la IP de Tailscale de esta Mac (%s) -> 200" % ip, c == 200, c)
        else:
            print("  --    Tailscale sin IP: se omite la prueba por la tailnet")
        pg = Pagina()
        verifica("la pagina recibe el estado de la planta", pg.espera(lambda p: p.estado.get("ready") and p.estado["comm"] == "ok", 15),
                 pg.estado)
        e = pg.estado
        verifica("en ingles: comm 'Online', line 'Stopped', actuator empujador, limites factibles",
                 (e["commLabel"], e["line"], e["actuator"], e["feasible"]) == ("Online", "Stopped", "empujador", True), e)
        r = pg.boton("marcha")
        verifica("Start con consigna 0 -> la pagina muestra 422 consigna_fuera_de_intervalo",
                 r and r["codigo"] == 422 and r.get("motivo") == "consigna_fuera_de_intervalo", r)
        r = pg.boton("velocidad", vel_V=9)
        verifica("consigna 9 V -> la pagina muestra 422", r and r["codigo"] == 422, r)
        n0 = len(ps.eventos(datos))
        r = pg.boton("velocidad", vel_V=3.0)
        verifica("consigna 3 V -> 200", r and r["codigo"] == 200, r)
        r = pg.boton("marcha")
        verifica("Start -> 200", r and r["codigo"] == 200, r)
        r = pg.boton("emisor", valor=True)
        verifica("Emitter ON -> 200", r and r["codigo"] == 200, r)
        time.sleep(1)
        entradas = {(x["etiqueta"], x["valor"]) for x in ps.eventos(datos)[n0:] if x["ev"] == "entrada"}
        verifica("los botones movieron el sustituto: vel 3 V, alimentacion y emisor en 1",
                 {("vel_banda_V", 3.0), ("alimentacion_on", 1), ("emisor_on", 1)} <= entradas, entradas)
        verifica("la pagina muestra Running y el emisor encendido",
                 pg.espera(lambda p: p.estado["running"] and p.estado["emitter"], 5), pg.estado)
        verifica("y cuenta las cajas que entran",
                 pg.espera(lambda p: p.estado["boxesIn"] >= 1, 30), pg.estado and pg.estado["boxesIn"])
        lim = pp.estado()["limites"]
        t_corte = time.time()
        proxy.detiene()
        visto = pg.espera(lambda p: p.estado["comm"] == "sin_comunicacion", lim["timeout_com_ms"] / 1000 + 5)
        tarda = time.time() - t_corte
        verifica("desconexion forzada: la pagina dice NO COMMUNICATION en %.1f s (< %.1f s)"
                 % (tarda, lim["timeout_com_ms"] / 1000 + 1), visto and tarda < lim["timeout_com_ms"] / 1000 + 1,
                 pg.estado and pg.estado["commLabel"])
        r = pg.boton("marcha")
        verifica("sin comunicacion, Start -> la pagina muestra 409", r and r["codigo"] == 409, r)
        proxy.inicia()
        verifica("al volver la red, la pagina vuelve a Online y Stopped",
                 pg.espera(lambda p: p.estado["comm"] == "ok" and not p.estado["running"], 20), pg.estado)
        r = pg.boton("paro")
        verifica("Stop -> 200", r and r["codigo"] == 200, r)
    finally:
        proxy.detiene()


def desviador():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_hmi_desv_"))
    print("=== HMI con el desviador (R3) (datos en %s) ===" % datos)
    proxy = pd.arranca("local", datos)
    try:
        pg = Pagina()
        verifica("estado con actuador desviador y bandas fijas",
                 pg.espera(lambda p: p.estado.get("ready") and p.estado["actuator"] == "desviador", 15)
                 and pg.estado["variableBelt"] is False, pg.estado)
        verifica("conteos por destino left/forward/right en la pagina",
                 set(pg.estado["byDestination"]) == {"left", "forward", "right"}, pg.estado["byDestination"])
        r = pg.boton("velocidad", vel_V=2)
        verifica("consigna con bandas fijas -> 422 velocidad_no_aplica visible", r and r["codigo"] == 422
                 and r.get("motivo") == "velocidad_no_aplica", r)
        r = pg.boton("marcha")
        verifica("Start -> 200 (sin consigna)", r and r["codigo"] == 200, r)
        pg.boton("emisor", valor=True)
        verifica("una caja sale clasificada y la pagina muestra su masa y destino",
                 pg.espera(lambda p: p.estado["lastBox"] is not None, 60), pg.estado and pg.estado["lastBox"])
        lb = pg.estado["lastBox"]
        verifica("ultima caja: masa en kg y destino de la escena (%s kg -> %s)" % (lb["massKg"], lb["destination"]),
                 isinstance(lb["massKg"], (int, float)) and lb["destination"] in ("left", "forward", "right"))
        verifica("cajas por minuto y conteo por destino en la pagina",
                 pg.estado["perMinute"] >= 1 and sum(pg.estado["byDestination"].values()) >= 1, pg.estado)
        pg.boton("paro")
    finally:
        proxy.detiene()


if __name__ == "__main__":
    try:
        empujador()
        desviador()
    finally:
        ps.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
