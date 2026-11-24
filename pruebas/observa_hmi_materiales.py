#!/usr/bin/env python3
"""Observa la tarjeta Materials layer de la HMI durante una corrida (paso M3). Python 3.9.

    /usr/bin/python3 -u pruebas/observa_hmi_materiales.py --salida DIR [--captura docs/img/hmi_materiales.png]

Solo lee: se conecta a la HMI (Dashboard 2.0, socket.io en el puerto de
Node-RED de las pruebas) por el mismo camino que el navegador y guarda cada
tarjeta que recibe en DIR/hmi_materiales.jsonl (una linea por tarjeta, con la
hora local de llegada). Espera a que Node-RED arranque y termina cuando
Node-RED deja de contestar despues de haber recibido tarjetas.

--captura: cuando la varilla 0:0 cruza D = 0.5 (segun la propia tarjeta), abre
Chrome sin ventana en /dashboard/a2, espera a que la pagina pinte y guarda una
captura (pruebas/cdp_mira.mjs). Solo una vez.
"""
import argparse, json, pathlib, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
from socketio_min import SocketIO  # noqa: E402

PUERTO = 1881
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEVTOOLS = 9334


def vivo():
    import http.client
    try:
        c = http.client.HTTPConnection("127.0.0.1", PUERTO, timeout=3)
        c.request("GET", "/a2/planta/estado")
        c.getresponse().read()
        return True
    except OSError:
        return False


def captura(ruta):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_hmi_captura_"))
    chrome = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                               "--remote-debugging-port=%d" % DEVTOOLS, "--user-data-dir=%s" % (tmp / "chrome"),
                               "--window-size=1280,2400", "http://127.0.0.1:%d/dashboard/a2" % PUERTO],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request
        for _ in range(40):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/json" % DEVTOOLS, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        png = tmp / "hmi.png"
        r = subprocess.run(["node", str(RAIZ / "pruebas" / "cdp_mira.mjs"), str(DEVTOOLS), "10", "5", str(png)],
                           capture_output=True, text=True, timeout=120)
        if png.exists():
            pathlib.Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(ruta).write_bytes(png.read_bytes())
            return True, r.stderr.strip()[:200]
        return False, r.stderr.strip()[:300]
    finally:
        chrome.terminate()


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--salida", required=True)
    a.add_argument("--captura")
    a.add_argument("--espera-max", type=int, default=600, help="segundos a esperar a que Node-RED arranque")
    x = a.parse_args()
    salida = pathlib.Path(x.salida)
    salida.mkdir(parents=True, exist_ok=True)
    archivo = open(str(salida / "hmi_materiales.jsonl"), "a", encoding="utf-8")
    fin = time.time() + x.espera_max
    while not vivo():
        if time.time() > fin:
            sys.exit("Node-RED no arranco en %d s" % x.espera_max)
        time.sleep(1)
    print("Node-RED arriba; observando la tarjeta", flush=True)
    s, n, capturada, caidas = None, 0, False, 0
    while True:
        try:
            if s is None:
                s = SocketIO("127.0.0.1", PUERTO, "/dashboard/socket.io/").conecta()
            eventos = s.recibe(2)
            caidas = 0
        except (ConnectionError, OSError):
            s = None
            if not vivo():
                caidas += 1
                if caidas >= 5 and n > 0:
                    break
            time.sleep(1)
            continue
        for nombre, args in eventos:
            if nombre != "msg-input:ui_tpl_a2" or not args or not isinstance(args[0], dict):
                continue
            p = args[0].get("payload")
            if not (isinstance(p, dict) and p.get("materials") is True):
                continue
            n += 1
            archivo.write(json.dumps({"llegada": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tarjeta": p}) + "\n")
            archivo.flush()
            rods = p.get("rods") or []
            if x.captura and not capturada and rods and rods[0].get("D", 0) >= 0.5:
                capturada = True
                time.sleep(3)
                ok, det = captura(x.captura)
                print("captura %s en el paso %s (D 0:0 = %.4f): %s %s" % (x.captura, p.get("steps"), rods[0]["D"],
                                                                          "guardada" if ok else "FALLO", det), flush=True)
    print("Node-RED se detuvo; %d tarjetas guardadas" % n, flush=True)


if __name__ == "__main__":
    main()
