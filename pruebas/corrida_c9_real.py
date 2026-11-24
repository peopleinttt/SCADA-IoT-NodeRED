#!/usr/bin/env python3
"""C9 contra Factory I/O escribiendo en la base REAL (planta_01) y C8 con datos reales. Python 3.9.

    node pruebas/relevo.mjs 5031 10.211.55.3 502 &     # el oraculo de la planta lee por aqui
    /usr/bin/python3 pruebas/corrida_c9_real.py         (~14 min)

Escribe en /plantas/planta_01/proceso de la base real (autorizado para C9) con
las credenciales del .env, que no se imprimen. Gemini no se consulta.
  1. reinicia la escena por Modbus (tools/reinicia_escena.mjs);
  2. Node-RED con el mapa y el cliente de Factory I/O, A2_NUBE=1, PLANTA_ID=planta_01;
  3. web/proceso.html en Chrome sin cabeza, con el visor real, mirado por
     DevTools (pruebas/cdp_mira.mjs) durante toda la corrida (C8);
  4. marcha, 10 minutos, paro; espera a que la cola hacia Firebase se vacie;
  5. exporta la ventana con tools/exporta_corrida.py --rama proceso y la
     analiza con tools/analiza_corrida.py --a2 (docs/INSTRUMENTACION_A2.md),
     reporte en docs/corrida_a2.md.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402

verifica = ps.verifica
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WEB, DEVTOOLS = 8125, 9334
MINUTOS = float(os.environ.get("C9_MINUTOS", "10"))
# Paso I de la fase 4: el reporte, la captura y los datos van a otro lado para no
# sobrescribir los del 25 oct. C9_DATOS: directorio de datos propio de la corrida
# (fuera del repo); C9_COPIA: carpeta del repo donde se copian sus archivos al final.
REPORTE = os.environ.get("C9_REPORTE", "docs/corrida_a2.md")
IMAGEN = os.environ.get("C9_IMAGEN", "docs/img/grafica_a2_real.png")
DATOS_PROPIOS = os.environ.get("C9_DATOS")
COPIA = os.environ.get("C9_COPIA")


def lee_env():
    v = {}
    for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, x = l.split("=", 1)
            v[k.strip()] = x.strip().strip('"').strip("'")
    return v


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def main():
    env = lee_env()
    for k in ("FIREBASE_DB_URL", "FIREBASE_API_KEY", "FB_INGESTOR_EMAIL", "FB_INGESTOR_PASS", "FB_VISOR_EMAIL", "FB_VISOR_PASS"):
        if not env.get(k):
            sys.exit("falta %s en .env" % k)
    datos = pathlib.Path(DATOS_PROPIOS or env.get("DATOS_DIR") or (RAIZ / "datos"))
    datos.mkdir(parents=True, exist_ok=True)
    host = env.get("A2_MODBUS_HOST", "10.211.55.3")
    print("=== C9 contra Factory I/O (%s) escribiendo en planta_01 de la base real; C8 con la grafica ===" % host)
    r = subprocess.run(["node", str(RAIZ / "tools" / "reinicia_escena.mjs"), host, "502"], capture_output=True, text=True, timeout=60)
    print("\n".join("    " + l for l in r.stdout.strip().splitlines()))
    verifica("escena reiniciada por Modbus (codigo %d)" % r.returncode, r.returncode == 0, r.stderr)
    if r.returncode:
        return
    procesos = []
    t_ini = t_fin = None
    try:
        ps.arranca(datos, A2_MAPA=RAIZ / "config" / "mapa_registros_fio.json",
                   A2_PLANTA_CONFIG=RAIZ / "config" / "planta_fio.json", A2_SUSTITUTO=0,
                   A2_MODBUS_HOST=host, A2_MODBUS_PUERTO=502, A2_MODBUS_UNIDAD=1,
                   FIREBASE_DB_URL=env["FIREBASE_DB_URL"], IDENTITY_BASE_URL="https://identitytoolkit.googleapis.com",
                   FIREBASE_API_KEY=env["FIREBASE_API_KEY"], FB_INGESTOR_EMAIL=env["FB_INGESTOR_EMAIL"],
                   FB_INGESTOR_PASS=env["FB_INGESTOR_PASS"], PLANTA_ID="planta_01", A2_NUBE=1)
        verifica("A2-Planta conecta con la escena", pp.espera(lambda: pp.estado()["com"] == "ok", 30))
        st = pp.estado()
        verifica("limites factibles, T_ef de lo medido (%s ms)" % st["limites"]["t_ef_ms"],
                 st["limites"]["factible"] and st["limites"].get("t_ef_origen") == "medido", st["limites"])

        web = subprocess.Popen([sys.executable, "-m", "http.server", str(WEB), "--directory", str(RAIZ / "web")],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procesos.append(web)
        time.sleep(1)
        url = "http://127.0.0.1:%d/proceso.html?%s" % (WEB, urllib.parse.urlencode(
            {"correo": env["FB_VISOR_EMAIL"], "clave": env["FB_VISOR_PASS"], "planta": "planta_01"}))
        perfil = pathlib.Path(tempfile.mkdtemp(prefix="a2_c9_chrome_"))   # fuera del repo
        chrome = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                                   "--remote-debugging-port=%d" % DEVTOOLS, "--user-data-dir=%s" % perfil,
                                   "--window-size=1280,900", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procesos.append(chrome)
        # Chrome sin ventana puede tardar mas de 4 s en abrir DevTools (paso I de la fase 4:
        # el primer intento fallo con ECONNREFUSED en cdp_mira.mjs). Se espera a que /json
        # liste la pagina, hasta 30 s, como en prueba_grafica.py.
        for _ in range(60):
            try:
                lista = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % DEVTOOLS, timeout=1))
                if any(x.get("type") == "page" for x in lista):
                    break
            except Exception:
                pass
            time.sleep(0.5)
        time.sleep(2)
        png = perfil / "grafica_c9.png"
        mira = subprocess.Popen(["node", str(RAIZ / "pruebas" / "cdp_mira.mjs"), str(DEVTOOLS),
                                 str(int(MINUTOS * 60 + 150)), "5", str(png)], stdout=subprocess.PIPE, text=True)
        procesos.append(mira)

        t_ini = time.time()
        c, rr = pp.comando(accion="marcha")
        verifica("marcha -> 200", c == 200, (c, rr))
        while time.time() - t_ini < MINUTOS * 60:
            time.sleep(30)
            k = pp.estado()["contadores"]
            if time.time() - t_ini > 60 and k["entradas"] == 0:
                # Factory I/O contesta Modbus aunque su simulacion no avance (ventana
                # minimizada o en pausa en la VM): sin cajas en 60 s no hay corrida.
                verifica("entran cajas en el primer minuto (la escena avanza)", False, "0 cajas en 60 s")
                break
            print("    %4.1f min  cajas %d  por destino %s" % ((time.time() - t_ini) / 60, k["salidas"], k["por_destino"]), flush=True)
        pp.comando(accion="paro")
        t_fin = time.time()
        # Lo ya confirmado sigue su camino hacia Firebase: se espera a que A2-Nube termine.
        time.sleep(20)
        st = pp.estado()
        salida_mira, _ = mira.communicate(timeout=200)
    finally:
        ps.detiene()
        for p in procesos:
            if p.poll() is None:
                p.terminate()
        for puerto in (WEB, DEVTOOLS):
            subprocess.run("lsof -ti tcp:%d -sTCP:LISTEN | xargs kill 2>/dev/null" % puerto, shell=True)
    if t_ini is None or t_fin is None:
        return
    k = st["contadores"]
    verifica("0 desvios erroneos, 0 perdidas, 0 fantasmas (%d / %d / %d)" % (k["desvios_erroneos"], k["perdidas"],
             k["fantasmas"] + k["fantasmas_bascula"]),
             k["desvios_erroneos"] == 0 and k["perdidas"] == 0 and k["fantasmas"] + k["fantasmas_bascula"] == 0, k)

    desde, hasta = iso(t_ini - 1), iso(t_fin + 1)
    dia = datetime.now().strftime("%Y-%m-%d")
    csv = datos / "proceso_c9.csv"
    r = subprocess.run([sys.executable, str(RAIZ / "tools" / "exporta_corrida.py"), "--rama", "proceso", "--desde", desde,
                        "--hasta", hasta, "--salida", str(csv)], capture_output=True, text=True, timeout=120)
    print("    " + (r.stdout.strip().splitlines() or [""])[-1])
    verifica("exporta_corrida --rama proceso (codigo %d)" % r.returncode, r.returncode == 0, r.stderr[-300:])
    sondeo = sorted(datos.glob("a2_sondeo_*.csv"))[-1]
    r = subprocess.run([sys.executable, str(RAIZ / "tools" / "analiza_corrida.py"), "--a2", str(csv), "--sondeo", str(sondeo),
                        "--eventos", str(datos / "a2_planta_eventos.jsonl"), "--desde", desde, "--hasta", hasta,
                        "--md", str(RAIZ / REPORTE)], capture_output=True, text=True, timeout=120)
    print("\n".join("    " + l for l in r.stdout.strip().splitlines()))
    verifica("analiza_corrida --a2 (codigo %d) -> %s" % (r.returncode, REPORTE), r.returncode == 0, r.stderr[-300:])
    filas = [l for l in csv.read_text().splitlines()[1:] if l.strip()] if csv.exists() else []
    cab = csv.read_text().splitlines()[0].split(";") if csv.exists() else []
    i_tipo = cab.index("tipo") if "tipo" in cab else None
    cajas_fb = sum(1 for f in filas if i_tipo is not None and f.split(";")[i_tipo] == "caja")
    verifica("completitud: %d cajas en Firebase = %d confirmadas por A2-Planta" % (cajas_fb, k["salidas"]),
             cajas_fb == k["salidas"] and cajas_fb > 0, (cajas_fb, k["salidas"]))

    print("--- C8: grafica con datos reales ---")
    muestras = [json.loads(l) for l in salida_mira.splitlines() if l.strip()]
    validas = [m for m in muestras if m["a2"]]
    ult = validas[-1] if validas else None
    prim = next((m for m in validas if m["a2"]["cajas"] > 0), None)
    verifica("la pagina inicio sesion como visor real y lee sin error",
             validas and all(m["a2"]["error"] is None for m in validas), ult and ult["a2"])
    verifica("las cajas subieron durante la corrida sin recargar (%s -> %s, %s navegaciones)"
             % (prim and prim["a2"]["cajas"], ult and ult["a2"]["cajas"], ult and ult["navegaciones"]),
             prim and ult and ult["a2"]["cajas"] >= prim["a2"]["cajas"] + 10 and ult["navegaciones"] == 0)
    verifica("al final la pagina tiene las cajas de la corrida que estan en Firebase (%s >= %d)" % (ult and ult["a2"]["cajas"], cajas_fb),
             ult and ult["a2"]["cajas"] >= cajas_fb, ult and ult["a2"])
    if png.exists():
        (RAIZ / IMAGEN).parent.mkdir(exist_ok=True)
        shutil.copy(str(png), str(RAIZ / IMAGEN))
        print("    captura: %s" % IMAGEN)
    print("    ventana: %s a %s" % (desde, hasta))
    print("    registros escritos en la ventana: %d caja, %d latido" % (cajas_fb, sum(
        1 for f in filas if i_tipo is not None and f.split(";")[i_tipo] == "latido")))
    if COPIA:
        destino = RAIZ / COPIA
        destino.mkdir(parents=True, exist_ok=True)
        for f in datos.iterdir():
            if f.is_file():
                shutil.copy(str(f), str(destino / f.name))
        print("    datos copiados a %s" % COPIA)


if __name__ == "__main__":
    try:
        main()
    finally:
        ps.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
