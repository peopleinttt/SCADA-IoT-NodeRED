#!/usr/bin/env python3
"""Pruebas de A2-Nube (C5) contra el simulador de Firebase. Python 3.9.

    /usr/bin/python3 pruebas/prueba_nube.py          (~2.5 min)

Levanta pruebas/simulador.py (Firebase, Identity Toolkit) en el 8099 y Node-RED
con el sustituto, A2-Planta y A2-Nube. No toca la base real ni Gemini.
El oraculo es lo que el SIMULADOR recibio, contra los paso_caja del cliente.
"""
import json, pathlib, re, statistics, subprocess, sys, tempfile, time, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402

SIM = "http://127.0.0.1:8099"
verifica = ps.verifica
LATIDO_S = 5
CAMPOS = {"ts_origen", "ts_escritura", "vel_banda_V", "peso_V", "caja_masa_kg", "cajas_acumuladas", "estado_linea",
          "destino"}
OBLIGATORIOS = CAMPOS - {"caja_masa_kg", "destino"}


def sim(ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    r = urllib.request.Request(SIM + ruta, data=datos, method="POST" if datos else "GET",
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=5))


def proceso():
    return [v for _, v in sorted(sim("/__estado")["proceso"].items())]


def csv(datos):
    filas = []
    for ruta in sorted(datos.glob("a2_nube_*.csv")):
        for l in ruta.read_text(encoding="utf-8").splitlines():
            if l and not l.startswith("tipo;"):
                filas.append(dict(zip(["tipo", "caja", "registro_id", "ts_origen", "ts_escritura", "latencia_ms",
                                       "rtt_ms", "http", "codigo", "resultado"], l.split(";"))))
    return filas


def esquema_ok(r):
    return (set(r) <= CAMPOS and OBLIGATORIOS <= set(r)
            and re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", r["ts_origen"])
            and re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}$", r["ts_escritura"])
            and -10 <= r["vel_banda_V"] <= 10 and 0 <= r["peso_V"] <= 10
            and ("caja_masa_kg" not in r or 0 <= r["caja_masa_kg"] <= 20)
            and isinstance(r["cajas_acumuladas"], int) and r["cajas_acumuladas"] >= 0
            and r["estado_linea"] in ("en_marcha", "detenida", "sin_comunicacion", "reconectando", "iniciando",
                                      "emergencia")
            and r.get("destino", "salida") in ("salida", "rechazo", "left", "right", "forward"))


def arranca(datos, **extra):
    env = dict(FIREBASE_DB_URL=SIM, IDENTITY_BASE_URL=SIM, FIREBASE_API_KEY="llave-simulada",
               FB_INGESTOR_EMAIL="ingestor@ejemplo.mx", FB_INGESTOR_PASS="secreta", PLANTA_ID="planta_01",
               A2_PLANTA_CONFIG=RAIZ / "config" / "planta_a2.json", A2_LATIDO_S=LATIDO_S)
    env.update(extra)
    ps.arranca(datos, **env)


def tsw(r):
    """ts_escritura de un registro, en segundos epoch (reloj de la Mac, igual que time.time())."""
    import datetime
    return datetime.datetime.fromisoformat(r["ts_escritura"]).timestamp()


def reposo():
    """E2 (fase 3): latido cada A2_LATIDO_S en marcha, cada A2_LATIDO_REPOSO_S detenida
    y uno inmediato (< 2 s) en cada cambio de estado. Periodos cortos: 5 y 12 s."""
    print("=== 5. Latido en reposo (E2): marcha %d s, reposo 12 s ===" % LATIDO_S)
    REPOSO_S = 12
    sim("/__reinicia")
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_nube_reposo_"))
    try:
        arranca(datos, A2_NUBE=1, A2_LATIDO_REPOSO_S=REPOSO_S)
        verifica("A2-Planta en ok", pp.espera(lambda: pp.estado()["com"] == "ok", 30))
        lat = lambda: [r for r in proceso() if "caja_masa_kg" not in r]
        pp.espera(lambda: any(r["estado_linea"] == "detenida" for r in lat()), 15, paso=0.5)
        time.sleep(3 * REPOSO_S + 2)
        pp.comando(accion="velocidad", vel_V=4.0)
        t1 = time.time()
        c, _ = pp.comando(accion="marcha")
        time.sleep(5 * LATIDO_S + 2)
        t2 = time.time()
        pp.comando(accion="paro")
        time.sleep(3 * REPOSO_S + 2)
        L = sorted(lat(), key=tsw)
        print("  latidos (estado, s desde el primero): %s" %
              [(r["estado_linea"][:8], round(tsw(r) - tsw(L[0]), 1)) for r in L])
        det1 = [tsw(r) for r in L if r["estado_linea"] == "detenida" and tsw(r) < t1]
        mar = [tsw(r) for r in L if r["estado_linea"] == "en_marcha"]
        det2 = [tsw(r) for r in L if r["estado_linea"] == "detenida" and tsw(r) > t2]
        g = lambda xs: [round(b - a, 1) for a, b in zip(xs, xs[1:])]
        verifica("detenida antes de marcha: latidos cada %d s (%s)" % (REPOSO_S, g(det1)),
                 len(det1) >= 3 and all(abs(x - REPOSO_S) <= 1.5 for x in g(det1)))
        verifica("marcha (%d): el primer latido en marcha llega %.2f s despues del cambio (< 2 s)" %
                 (c, (mar[0] - t1) if mar else -1), c == 200 and mar and 0 <= mar[0] - t1 < 2)
        verifica("en marcha: latidos cada %d s (%s)" % (LATIDO_S, g(mar)),
                 len(mar) >= 4 and all(abs(x - LATIDO_S) <= 1.5 for x in g(mar)))
        verifica("paro: el primer latido detenida llega %.2f s despues del cambio (< 2 s)" %
                 ((det2[0] - t2) if det2 else -1), det2 and 0 <= det2[0] - t2 < 2)
        verifica("detenida despues del paro: latidos cada %d s (%s)" % (REPOSO_S, g(det2)),
                 len(det2) >= 3 and all(abs(x - REPOSO_S) <= 1.5 for x in g(det2)))
        filas = csv(datos)
        verifica("CSV: todos aceptados con 201 (%d)" % len(filas),
                 filas and all(f["codigo"] == "201" for f in filas))
    finally:
        ps.detiene()


def emergencia():
    """E1 (fase 3): con el paro de emergencia presionado la linea queda en
    'emergencia'; el latido lleva ese estado y la validacion local no debe
    descartarlo. Escena Modbus falsa de prueba_tablero.py con el mapa real."""
    import prueba_tablero as pt
    print("=== 4. Paro de emergencia con la nube simulada (E1) ===")
    sim("/__reinicia")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_nube_emerg_"))
    esc = pt.Escena(pt.PUERTO)
    for n in ("stop_button", "at_exit_left", "at_exit_front", "at_exit_right", "fio_running"):
        esc.pon(n, True)
    esc.pon("emergency_stop", False)                     # NC: presionado
    cfg_ruta, _ = pt.config(tmp)
    datos = tmp / "datos"
    datos.mkdir()
    try:
        arranca(datos, A2_NUBE=1, A2_LATIDO_REPOSO_S=LATIDO_S, A2_MAPA=pt.MAPA, A2_PLANTA_CONFIG=cfg_ruta, A2_SUSTITUTO=0,
                A2_MODBUS_HOST="127.0.0.1", A2_MODBUS_PUERTO=pt.PUERTO, A2_MODBUS_UNIDAD=1)
        verifica("A2-Planta en ok y la linea en emergencia",
                 pp.espera(lambda: pp.estado()["com"] == "ok" and pp.estado()["linea"] == "emergencia", 30),
                 pp.estado().get("linea"))
        pp.espera(lambda: len(csv(datos)) >= 2, LATIDO_S * 3 + 5, paso=0.5)
        recs = proceso()
        filas = csv(datos)
        latidos = [r for r in recs if "caja_masa_kg" not in r]
        print("  el simulador recibio %d latidos: %s; CSV: %s" % (len(latidos), [r["estado_linea"] for r in latidos],
                                                                  [(f["codigo"], f["resultado"]) for f in filas]))
        verifica("los latidos con estado_linea = emergencia llegan a la base simulada",
                 len(latidos) >= 2 and all(r["estado_linea"] == "emergencia" for r in latidos))
        verifica("y cumplen el esquema de las reglas", latidos and all(esquema_ok(r) for r in latidos))
        verifica("el CSV de A2-Nube no registra rechazos (%d filas, todas 201)" % len(filas),
                 len(filas) >= 2 and all(f["codigo"] == "201" and f["resultado"] == "aceptado" for f in filas),
                 [f for f in filas if f["codigo"] != "201"][:2])
        log = (datos / "nodered.log").read_text(encoding="utf-8", errors="replace")
        verifica("Node-RED no avisa de registros rechazados", "registro de proceso rechazado" not in log)
    finally:
        ps.detiene()
        esc.cierra()


def main():
    simulador = subprocess.Popen([sys.executable, str(RAIZ / "pruebas" / "simulador.py"), "8099"])
    try:
        time.sleep(1)
        sim("/__reinicia")
        datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_nube_"))
        print("=== 1. Corrida contra el simulador (latido cada %d s, datos en %s) ===" % (LATIDO_S, datos))
        # Reposo = marcha: las secciones 1 y 2 necesitan latidos con la linea
        # detenida al ritmo de LATIDO_S (el reposo largo lo prueba la seccion 5).
        arranca(datos, A2_NUBE=1, A2_LATIDO_REPOSO_S=LATIDO_S)
        verifica("A2-Planta en ok", pp.espera(lambda: pp.estado()["com"] == "ok", 30))
        for c in ({"accion": "velocidad", "vel_V": 4.0}, {"accion": "marcha"}, {"accion": "emisor", "valor": True}):
            pp.comando(**c)
        t0 = time.time()
        pasos = lambda: [x for x in pp.eventos(datos, "a2_planta_eventos.jsonl") if x["ev"] == "paso_caja"]
        pp.espera(lambda: len(pasos()) >= 8, 150, paso=1)
        pp.comando(accion="emisor", valor=False)
        pp.espera(lambda: not pp.estado()["en_tramo"], 60, paso=1)
        pp.comando(accion="paro")
        time.sleep(LATIDO_S + 2)
        dur = time.time() - t0
        recs = proceso()
        cajas = [r for r in recs if "caja_masa_kg" in r]
        latidos = [r for r in recs if "caja_masa_kg" not in r]
        p = pasos()
        filas = csv(datos)
        print("  %.0f s: %d paso_caja en el cliente; el simulador recibio %d registros (%d de caja, %d latidos)"
              % (dur, len(p), len(recs), len(cajas), len(latidos)))
        verifica("un registro de caja por paso_caja (%d)" % len(p), len(cajas) == len(p))
        verifica("con la masa de cada caja, en orden",
                 [r["caja_masa_kg"] for r in cajas] == [round(x["masa_kg"], 3) for x in p])
        verifica("cada registro de caja trae su destino, igual al del paso_caja",
                 [r.get("destino") for r in cajas] == [x["destino"] for x in p])
        verifica("los latidos no traen destino", all("destino" not in r for r in latidos))
        verifica("cajas_acumuladas sube de uno en uno (%s)" % [r["cajas_acumuladas"] for r in cajas],
                 [r["cajas_acumuladas"] for r in cajas] == list(range(1, len(cajas) + 1)))
        # E2 (fase 3): con la linea en marcha el periodo es A2_LATIDO_S; los
        # cambios de estado agregan latidos inmediatos, asi que se mide el
        # periodo entre latidos consecutivos en marcha, no el total.
        t_m = [tsw(r) for r in latidos if r["estado_linea"] == "en_marcha"]
        gaps = [b - a for a, b in zip(t_m, t_m[1:])]
        verifica("latidos en marcha: %d, periodo mediano %.1f s (esperado %d s)" %
                 (len(t_m), statistics.median(gaps) if gaps else -1, LATIDO_S),
                 len(gaps) >= 3 and abs(statistics.median(gaps) - LATIDO_S) <= 1.0, gaps)
        verifica("todos los registros cumplen el esquema de las reglas", all(esquema_ok(r) for r in recs),
                 [r for r in recs if not esquema_ok(r)][:2])
        verifica("el ultimo latido dice detenida", latidos and latidos[-1]["estado_linea"] == "detenida",
                 latidos[-1] if latidos else None)
        verifica("registros de caja con la linea en marcha", all(r["estado_linea"] == "en_marcha" for r in cajas))
        verifica("CSV: una fila por registro, todas con codigo 201 aceptado (%d)" % len(filas),
                 len(filas) == len(recs) and all(f["codigo"] == "201" and f["resultado"] == "aceptado" for f in filas),
                 [f for f in filas if f["codigo"] != "201"][:2])
        lat = [int(f["latencia_ms"]) for f in filas if f["tipo"] == "caja"]
        print("  latencia lectura -> escritura de las cajas (ms): mediana %.0f, max %d" % (statistics.median(lat), max(lat)))
        verifica("la escritura de una caja sale a menos de 1 s de su lectura", max(lat) < 1000, lat)

        print("=== 2. Reglas que rechazan: 401 y renovacion de sesion ===")
        sim("/__modo", {"modo": "permiso"})
        antes = len(csv(datos))
        pp.espera(lambda: len(csv(datos)) > antes, LATIDO_S * 3, paso=0.5)
        f = csv(datos)[antes:]
        verifica("con permiso negado el latido se anota http 401, codigo 502 (no 201)",
                 f and f[0]["http"] == "401" and f[0]["codigo"] == "502", f[:1])
        sim("/__modo", {"modo": "ok"})
        antes = len(csv(datos))
        pp.espera(lambda: any(x["codigo"] == "201" for x in csv(datos)[antes:]), LATIDO_S * 3, paso=0.5)
        verifica("al volver las reglas, el siguiente latido entra con 201 (sesion renovada)",
                 any(x["codigo"] == "201" for x in csv(datos)[antes:]), csv(datos)[antes:])
        ps.detiene()

        print("=== 3. Sin A2_NUBE=1 no se escribe nada ===")
        n0 = len(proceso())
        arranca(datos)
        verifica("A2-Planta en ok", pp.espera(lambda: pp.estado()["com"] == "ok", 30))
        time.sleep(LATIDO_S * 2 + 2)
        verifica("en %d s, 0 registros nuevos en proceso" % (LATIDO_S * 2 + 2), len(proceso()) == n0, len(proceso()) - n0)
        ps.detiene()

        emergencia()
        reposo()
    finally:
        ps.detiene()
        simulador.terminate()


if __name__ == "__main__":
    if sys.argv[1:] in (["emergencia"], ["reposo"]):
        simulador = subprocess.Popen([sys.executable, str(RAIZ / "pruebas" / "simulador.py"), "8099"])
        try:
            time.sleep(1)
            {"emergencia": emergencia, "reposo": reposo}[sys.argv[1]]()
        finally:
            simulador.terminate()
    else:
        main()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
