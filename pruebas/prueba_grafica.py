#!/usr/bin/env python3
"""Prueba de la grafica de la Actividad 2 (C8). Python 3.9.

    /usr/bin/python3 pruebas/prueba_grafica.py          (~3 min)

Todo en local, sin tocar la base real:
  - emuladores de Realtime Database y Auth (firebase-tools), con las cuentas del
    ingestor y del visor creadas en el emulador de Auth y las REGLAS DEL REPO
    (firebase/database.rules.json) con sus UID;
  - Node-RED con el sustituto (desviador), A2-Planta y A2-Nube escribiendo en el
    emulador durante una corrida;
  - web/proceso.html en Chrome sin cabeza (?emulador=1), mirado por el protocolo
    de DevTools (pruebas/cdp_mira.mjs).
Oraculo: la pagina cuenta mas cajas a medida que el emulador recibe registros,
sin ninguna navegacion despues de la primera carga (no se recargo), y sus
cajas coinciden con las que hay en el emulador.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
import prueba_desviador as pd  # noqa: E402

verifica = ps.verifica
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DB, AUTH, WEB, DEVTOOLS = "http://127.0.0.1:9000", "http://127.0.0.1:9099", 8124, 9333


def pide(metodo, url, cuerpo=None, cabeceras=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    h = {"Content-Type": "application/json"}
    h.update(cabeceras or {})
    r = urllib.request.Request(url, data=datos, method=metodo, headers=h)
    with urllib.request.urlopen(r, timeout=10) as x:
        return json.loads(x.read().decode() or "null")


def emuladores(tmp):
    (tmp / "rules.json").write_text('{"rules": {".read": false, ".write": false}}')
    (tmp / "firebase.json").write_text(json.dumps({"database": {"rules": "rules.json"},
        "emulators": {"database": {"host": "127.0.0.1", "port": 9000}, "auth": {"host": "127.0.0.1", "port": 9099},
                      "ui": {"enabled": False}, "singleProjectMode": True}}))
    p = subprocess.Popen(["firebase", "emulators:start", "--only", "database,auth", "--project", "demo-iot"],
                         cwd=str(tmp), stdout=open(str(tmp / "emu.log"), "w"), stderr=subprocess.STDOUT)
    for _ in range(90):
        try:
            urllib.request.urlopen(AUTH + "/", timeout=1)
            urllib.request.urlopen(DB + "/.json?ns=fake-server", timeout=1)
            return p
        except Exception:
            time.sleep(1)
    sys.exit("los emuladores no arrancaron; ver %s" % (tmp / "emu.log"))


def cuenta(correo, clave):
    r = pide("POST", AUTH + "/identitytoolkit.googleapis.com/v1/accounts:signUp?key=demo",
             {"email": correo, "password": clave, "returnSecureToken": True})
    return r["localId"]


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_grafica_"))
    emu = emuladores(tmp)
    procesos = [emu]
    try:
        uid_ing = cuenta("ingestor@demo.mx", "clave-ingestor")
        uid_vis = cuenta("visor@demo.mx", "clave-visor")
        reglas = (RAIZ / "firebase" / "database.rules.json").read_text()
        reglas = reglas.replace("__UID_INGESTOR__", uid_ing).replace("__UID_VISOR__", uid_vis)
        # Node-RED escribe sin ns y el emulador lo guarda en "fake-server".
        r = urllib.request.Request(DB + "/.settings/rules.json?ns=fake-server", data=reglas.encode(), method="PUT",
                                   headers={"Authorization": "Bearer owner"})
        urllib.request.urlopen(r, timeout=10)
        print("=== Grafica en vivo: emuladores RTDB+Auth con las reglas del repo, ingestor %s, visor %s ===" % (uid_ing[:8], uid_vis[:8]))
        try:
            pide("GET", DB + "/plantas/planta_01/proceso.json?ns=fake-server")
            anon = "PERMITE"
        except urllib.error.HTTPError:
            anon = "NIEGA"
        verifica("con las reglas del repo, un anonimo no lee proceso (%s)" % anon, anon == "NIEGA")
        # Paso U (fase 3): un registro de caja anterior al 11 nov 2026 (1 kg por volt),
        # sembrado como dueno; la pagina debe avisar bajo la grafica de masas.
        viejo = {"tipo": "caja", "ts_origen": "2026-10-25T01:22:49.632Z", "ts_escritura": "2026-10-24T19:22:49.700-06:00",
                 "peso_V": 4.0, "caja_masa_kg": 4.0, "destino": "left", "cajas_acumuladas": 1, "estado_linea": "en_marcha"}
        pide("PUT", DB + "/plantas/planta_01/proceso/-0000viejo_25oct.json?ns=fake-server", viejo,
             cabeceras={"Authorization": "Bearer owner"})

        datos = tmp / "datos"
        datos.mkdir()
        proxy = pd.arranca("local", datos, FIREBASE_DB_URL=DB, IDENTITY_BASE_URL=AUTH + "/identitytoolkit.googleapis.com",
                           FIREBASE_API_KEY="demo", FB_INGESTOR_EMAIL="ingestor@demo.mx", FB_INGESTOR_PASS="clave-ingestor",
                           PLANTA_ID="planta_01", A2_NUBE=1, A2_LATIDO_S=20)
        try:
            web = subprocess.Popen([sys.executable, "-m", "http.server", str(WEB), "--directory", str(RAIZ / "web")],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            procesos.append(web)
            time.sleep(1)
            url = ("http://127.0.0.1:%d/proceso.html?emulador=1&correo=visor@demo.mx&clave=clave-visor&planta=planta_01" % WEB)
            chrome = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                                       "--remote-debugging-port=%d" % DEVTOOLS, "--user-data-dir=%s" % (tmp / "chrome"),
                                       "--window-size=1280,900", url],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            procesos.append(chrome)
            for _ in range(30):
                try:
                    urllib.request.urlopen("http://127.0.0.1:%d/json" % DEVTOOLS, timeout=1)
                    break
                except Exception:
                    time.sleep(0.5)
            pp.comando(accion="marcha")
            pp.comando(accion="emisor", valor=True)
            png = tmp / "grafica.png"
            mira = subprocess.run(["node", str(RAIZ / "pruebas" / "cdp_mira.mjs"), str(DEVTOOLS), "100", "5", str(png)],
                                  capture_output=True, text=True, timeout=200)
            muestras = [json.loads(l) for l in mira.stdout.splitlines() if l.strip()]
            pp.comando(accion="emisor", valor=False)
            # Paso C de la fase 4: antes de la muestra final, la ultima escritura de A2-Nube
            # tiene que estar en el emulador y la pagina tiene que haberla recibido. Primero
            # se vacia la linea y la cola hacia el emulador (la cuenta de cajas del emulador
            # deja de cambiar y es igual a los paso_caja del cliente mas el registro viejo
            # sembrado); despues se muestrea la pagina hasta que tenga esa misma cuenta.
            pp.espera(lambda: not pp.estado()["en_tramo"], 60, paso=0.5)
            pp.comando(accion="paro")
            cuenta_emu = lambda: sum(1 for r in (pide("GET", DB + "/plantas/planta_01/proceso.json?ns=fake-server",
                                                      cabeceras={"Authorization": "Bearer owner"}) or {}).values()
                                     if "caja_masa_kg" in r)
            pasos_cliente = lambda: sum(1 for l in (datos / "a2_planta_eventos.jsonl").read_text().splitlines()
                                        if '"ev":"paso_caja"' in l)
            esperado_emu = None
            fin_espera = time.time() + 60
            while time.time() < fin_espera:
                n_emu, n_pasos = cuenta_emu(), pasos_cliente()
                if n_emu == n_pasos + 1:                    # + el registro viejo sembrado
                    esperado_emu = n_emu
                    break
                time.sleep(1)
            final = []
            fin_espera = time.time() + 30
            while esperado_emu is not None and time.time() < fin_espera:
                m2 = subprocess.run(["node", str(RAIZ / "pruebas" / "cdp_mira.mjs"), str(DEVTOOLS), "1", "1", ""],
                                    capture_output=True, text=True, timeout=30)
                final = [json.loads(l) for l in m2.stdout.splitlines() if l.strip()]
                if final and final[-1]["a2"] and final[-1]["a2"]["cajas"] == esperado_emu:
                    break
                time.sleep(1)
            print("  espera final: emulador %s cajas (paso_caja del cliente %d + 1 sembrada); pagina %s" % (
                esperado_emu, pasos_cliente(), final[-1]["a2"]["cajas"] if final and final[-1]["a2"] else None))
            muestras += final
        finally:
            proxy.detiene()
            ps.detiene()
        en_emu = pide("GET", DB + "/plantas/planta_01/proceso.json?ns=fake-server",
                      cabeceras={"Authorization": "Bearer owner"}) or {}
        cajas_emu = sum(1 for r in en_emu.values() if "caja_masa_kg" in r)
        validas = [m for m in muestras if m["a2"]]
        for m in validas[::4]:
            print("  t+%3.0f s  pagina: %d registros, %d cajas, %d actualizaciones, navegaciones %d"
                  % ((m["t"] - validas[0]["t"]) / 1000, m["a2"]["registros"], m["a2"]["cajas"], m["a2"]["actualizaciones"],
                     m["navegaciones"]))
        if mira.stderr.strip():
            print("  cdp:", mira.stderr.strip()[:300])
        verifica("la pagina inicio sesion como visor y lee sin error",
                 validas and all(m["a2"]["error"] is None for m in validas), validas[-1]["a2"] if validas else None)
        primeras = next((m for m in validas if m["a2"]["cajas"] > 0), None)
        ultima = validas[-1] if validas else None
        verifica("las cajas en la pagina subieron durante la corrida (%s -> %s)"
                 % (primeras and primeras["a2"]["cajas"], ultima and ultima["a2"]["cajas"]),
                 primeras and ultima and ultima["a2"]["cajas"] >= primeras["a2"]["cajas"] + 3)
        verifica("con varias actualizaciones del listener (%s)" % (ultima and ultima["a2"]["actualizaciones"]),
                 ultima and ultima["a2"]["actualizaciones"] >= 5)
        verifica("sin recargar: ninguna navegacion despues de conectarse (%s)" % (ultima and ultima["navegaciones"]),
                 ultima and ultima["navegaciones"] == 0)
        verifica("al final la pagina tiene las mismas cajas que el emulador (%s = %d)" % (ultima and ultima["a2"]["cajas"], cajas_emu),
                 ultima and ultima["a2"]["cajas"] == cajas_emu and cajas_emu > 0)
        verifica("la pagina avisa del registro viejo de 1 kg por volt (%s): %s" % (ultima and ultima["a2"].get("viejas"),
                 ultima and ultima["a2"].get("nota")),
                 ultima and ultima["a2"].get("viejas") == 1 and "1 kg per volt" in (ultima["a2"].get("nota") or ""))
        if png.exists():
            destino = RAIZ / "docs" / "img"
            destino.mkdir(exist_ok=True)
            shutil.copy(str(png), str(destino / "grafica_a2_emulador.png"))
            print("  captura: docs/img/grafica_a2_emulador.png")
    finally:
        for p in procesos:
            p.terminate()
        for puerto in (9000, 9099, 4400, 4500, WEB, DEVTOOLS):
            subprocess.run("lsof -ti tcp:%d -sTCP:LISTEN | xargs kill 2>/dev/null" % puerto, shell=True)


if __name__ == "__main__":
    try:
        main()
    finally:
        ps.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
