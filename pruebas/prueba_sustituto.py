#!/usr/bin/env python3
"""Pruebas de la planta sustituta (C2) por Modbus TCP, sin Factory I/O.
Compatible con Python 3.9.

    /usr/bin/python3 pruebas/prueba_sustituto.py funcional          (~2 min)
    /usr/bin/python3 pruebas/prueba_sustituto.py determinismo       (~22 min)
    /usr/bin/python3 pruebas/prueba_sustituto.py determinismo --minutos 1

Levanta Node-RED en el 1881 con el userDir temporal de pruebas/prueba.sh
(donde ./prepara_a2.sh dejo las paletas) y lo mata por puerto al terminar,
igual que prueba.sh: nunca por nombre, para no tocar otra instancia.
Las variables de la Actividad 1 apuntan a 127.0.0.1:9, asi que estas pruebas
no salen a Firebase ni a Gemini aunque la pestana de diagnostico dispare.

Codigo de salida = numero de comprobaciones fallidas.
"""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import mapa_registros as mr  # noqa: E402
from modbus_tcp import Cliente  # noqa: E402

PUERTO_NR = int(os.environ.get("PUERTO", "1881"))
USERDIR = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "actividad1-pruebas" / "userdir"
MAPA = mr.carga()
E = {e["nombre"]: e for e in MAPA["etiquetas"]}
CFG = json.loads((RAIZ / "config" / "sustituto_a2.json").read_text(encoding="utf-8"))

resultado = {"ok": 0, "falla": 0}


def verifica(desc, condicion, detalle=""):
    if condicion:
        resultado["ok"] += 1
        print("  OK    %s" % desc)
    else:
        resultado["falla"] += 1
        print("  FALLA %s %s" % (desc, detalle))


# ---- Node-RED ------------------------------------------------------------------
def puerto_ocupado(p):
    return subprocess.run(["lsof", "-ti", "tcp:%d" % p, "-sTCP:LISTEN"], capture_output=True).returncode == 0


def detiene():
    # Solo el proceso que ESCUCHA: sin -sTCP:LISTEN, lsof tambien da los clientes
    # conectados, y una prueba con un socket abierto al 1881 se mataba a si misma.
    pids = subprocess.run(["lsof", "-ti", "tcp:%d" % PUERTO_NR, "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
    for pid in pids:
        subprocess.run(["kill", pid])
    for _ in range(60):
        if not puerto_ocupado(PUERTO_NR):
            return
        time.sleep(0.5)
    sys.exit("Node-RED no solto el puerto %d" % PUERTO_NR)


def arranca(datos, **extra):
    """Levanta Node-RED con la pestana nueva; regresa cuando el emulador ya avanza."""
    detiene()
    if not (USERDIR / "node_modules" / "node-red-contrib-modbus").exists():
        sys.exit("faltan las paletas en %s: corre ./prepara_a2.sh" % USERDIR)
    shutil.copy(RAIZ / "node-red" / "flows.json", USERDIR / "flows.json")
    env = dict(os.environ)
    env.update({
        "FIREBASE_DB_URL": "http://127.0.0.1:9", "IDENTITY_BASE_URL": "http://127.0.0.1:9",
        "GEMINI_BASE_URL": "http://127.0.0.1:9", "GEMINI_API_KEY": "", "FIREBASE_API_KEY": "",
        "PLANTA_ID": "planta_01", "TZ_REPORTE": "America/Mexico_City", "DATOS_DIR": str(datos),
        "A2_MAPA": str(RAIZ / "config" / "mapa_registros_a2.json"),
        "A2_SUST_CONFIG": str(RAIZ / "config" / "sustituto_a2.json"),
    })
    # Las credenciales del editor nunca se heredan del entorno: sin ellas el
    # editor y la API de administracion quedan deshabilitados (paso S2). La
    # prueba que necesite la API pasa unas desechables (admin_desechable.py).
    for k in ("A2_SUSTITUTO", "A2_SUST_PUERTO", "A2_SUST_HOST", "A2_SUST_SEMILLA",
              "NODE_RED_ADMIN_USER", "NODE_RED_ADMIN_HASH"):
        env.pop(k, None)
    env.update({k: str(v) for k, v in extra.items()})
    log = open(str(datos / "nodered.log"), "a")
    subprocess.Popen(["node-red", "--userDir", str(USERDIR), "--settings", str(RAIZ / "node-red" / "settings.js"),
                      "--port", str(PUERTO_NR)],
                     stdout=log, stderr=subprocess.STDOUT, env=env)
    if not espera_nodered(60):
        sys.exit("Node-RED no arranco; revisa %s" % (datos / "nodered.log"))


RUTA_LISTO = "/a2/planta/estado"


def espera_nodered(limite_s=60, puerto=None):
    """Espera a que los flujos esten corriendo, sin la API de administracion.

    Antes se esperaba GET /settings, que es de la API de administracion: con
    adminAuth contesta 401 y sin credenciales no existe (paso S2). Ahora se
    pregunta por una ruta de un nodo http in de A2-Planta: mientras los flujos
    no arrancan, Node-RED contesta 404; en cuanto corren, la ruta existe y
    contesta lo que sea (200, o 503 sin configuracion de planta)."""
    fin = time.time() + limite_s
    while time.time() < fin:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d%s" % (puerto or PUERTO_NR, RUTA_LISTO), timeout=1)
            return True
        except urllib.error.HTTPError as e:
            if e.code != 404:
                return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def espera_emulador(puerto=5020, limite_s=20):
    """El emulador avanza cuando escribe emp_lim_trasero=1 (empujador retraido)."""
    fin = time.time() + limite_s
    while time.time() < fin:
        try:
            with Cliente("127.0.0.1", puerto, espera_s=1) as c:
                if c.lee_discretas(E["emp_lim_trasero"]["direccion"], 1)[0]:
                    return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def eventos(datos):
    ruta = datos / "a2_sustituto_eventos.jsonl"
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def palabra(nombre, valor):
    return mr.a_registro(E[nombre], valor)


def enciende_linea(c, vel_V):
    # Orden a proposito: velocidad y alimentacion antes que el emisor. El
    # emisor marca t = 0, asi que todo lo que lo determina ya esta puesto.
    c.escribe_registro(E["vel_banda_V"]["direccion"], palabra("vel_banda_V", vel_V))
    c.escribe_bobina(E["alimentacion_on"]["direccion"], True)
    c.escribe_bobina(E["emisor_on"]["direccion"], True)


# ---- pruebas funcionales ----------------------------------------------------------
def funcional():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_sust_"))
    print("=== 1. Arranque y estado inicial (datos en %s) ===" % datos)
    arranca(datos)
    verifica("el emulador avanza en 127.0.0.1:5020", espera_emulador())
    d = {k: E[k]["direccion"] for k in E}
    c = Cliente("127.0.0.1", 5020)
    disc = c.lee_discretas(0, 5)
    verifica("sensores apagados y empujador retraido", disc == [False, False, False, False, True], disc)
    verifica("peso 0 sin caja", c.lee_entrada(d["peso_V"], 1) == [0])

    print("=== 2. vel_banda_V negativa ===")
    c.escribe_registro(d["vel_banda_V"], palabra("vel_banda_V", -2.0))
    leida = c.lee_retencion(d["vel_banda_V"], 1)[0]
    verifica("-2 V se escribe como 65336 y se lee igual", leida == 65336, leida)
    verifica("y se decodifica como -2.0", mr.de_registro(E["vel_banda_V"], leida) == -2.0)
    time.sleep(0.5)
    vistos = [e["valor"] for e in eventos(datos) if e["ev"] == "entrada" and e["etiqueta"] == "vel_banda_V"]
    verifica("el emulador leyo -2.0 V", -2.0 in vistos, vistos)
    c.escribe_registro(d["vel_banda_V"], 2000)                 # 20 V, fuera del mapa
    time.sleep(0.5)
    fuera = [e for e in eventos(datos) if e["ev"] == "entrada_fuera_de_rango"]
    verifica("2000 (20 V) se avisa como fuera de rango", len(fuera) == 1 and fuera[0]["valor"] == 20.0, fuera)

    print("=== 3. Cajas: orden de sensores y peso ===")
    enciende_linea(c, 5.0)
    muestras = []                      # (t, [discretas], peso)
    t0 = time.time()
    while time.time() - t0 < 30:
        muestras.append((time.time() - t0, c.lee_discretas(0, 5), c.lee_entrada(d["peso_V"], 1)[0]))
        time.sleep(0.02)
    ev = eventos(datos)
    emitidas = {e["caja"]: e["masa_kg"] for e in ev if e["ev"] == "caja_emitida"}
    salieron = [e["caja"] for e in ev if e["ev"] == "caja_sale"]
    verifica("salen cajas del tramo", len(salieron) >= 3, salieron)
    orden_ok = []
    for caja in salieron:
        on = [e["etiqueta"] for e in ev if e["ev"] == "sensor_on" and e.get("caja") == caja
              and e["etiqueta"].startswith("sens_")]
        orden_ok.append(on == ["sens_entrada", "sens_bascula", "sens_salida"])
    verifica("cada caja que sale activo entrada, bascula y salida, en ese orden", all(orden_ok), orden_ok)

    # Lo mismo visto desde el cable: primer flanco de cada sensor en el sondeo.
    def primer_flanco(i):
        return next((t for t, disc, _ in muestras if disc[i]), None)
    fl = [primer_flanco(d[k]) for k in ("sens_entrada", "sens_bascula", "sens_salida")]
    verifica("por Modbus, la primera caja pasa entrada < bascula < salida",
             None not in fl and fl[0] < fl[1] < fl[2], fl)

    # Peso: mediana del ULTIMO CUARTO de cada paso por la bascula, contra la masa.
    # La bascula tiene un retraso de primer orden (tau_s) a proposito, para que
    # el cliente tenga que esperar a que el valor se asiente: a la mitad del paso
    # aun le faltan ~3 cuentas (primera corrida: -2, -3, -4), al ultimo cuarto
    # menos de 1.5. El primer valor sobre la bascula queda lejos de la masa.
    tramos, actual = [], []
    for t, disc, p in muestras:
        if disc[d["sens_bascula"]]:
            actual.append(p)
        elif actual:
            tramos.append(actual)
            actual = []
    errores, primeros = [], []
    for i, tramo in enumerate(tramos[:3]):
        cola = sorted(tramo[3 * len(tramo) // 4:])
        esperado = round(emitidas[i + 1] / CFG["bascula"]["plena_escala_kg"] * 10 * E["peso_V"]["escala"])
        errores.append(cola[len(cola) // 2] - esperado)
        primeros.append(round(tramo[0] / esperado, 2))
    verifica("peso asentado = masa/plena escala x 10 V, +-3 cuentas (3 cajas)",
             len(errores) == 3 and all(abs(e) <= 3 for e in errores), errores)
    verifica("el primer valor en la bascula aun no se asienta (< 50 %)",
             len(primeros) == 3 and all(p < 0.5 for p in primeros), primeros)

    print("=== 4. Empujador y rechazo ===")
    c.escribe_bobina(d["emp_extender"], True)
    t0, t_tras, t_front = time.time(), None, None
    while time.time() - t0 < 2:
        disc = c.lee_discretas(0, 5)
        if t_tras is None and not disc[d["emp_lim_trasero"]]:
            t_tras = time.time() - t0
        if t_front is None and disc[d["emp_lim_frontal"]]:
            t_front = time.time() - t0
        time.sleep(0.01)
    carrera = CFG["empujador"]["carrera_s"]
    verifica("al extender, el limite trasero se suelta en menos de 0.3 s", t_tras is not None and t_tras < 0.3, t_tras)
    verifica("y el frontal llega en carrera_s (%.1f s) +-0.25 s" % carrera,
             t_front is not None and abs(t_front - carrera) <= 0.25, t_front)
    fin = time.time() + 20
    while time.time() < fin and not [e for e in eventos(datos) if e["ev"] == "caja_rechazada"]:
        time.sleep(0.2)
    c.escribe_bobina(d["emp_extender"], False)
    t0, t_tras = time.time(), None
    while time.time() - t0 < 2 and t_tras is None:
        if c.lee_discretas(d["emp_lim_trasero"], 1)[0]:
            t_tras = time.time() - t0
        time.sleep(0.01)
    verifica("al retraer, el trasero vuelve en carrera_s +-0.25 s",
             t_tras is not None and abs(t_tras - carrera) <= 0.25, t_tras)
    time.sleep(8)
    ev = eventos(datos)
    rech = [e["caja"] for e in ev if e["ev"] == "caja_rechazada"]
    verifica("una caja que pasa con el empujador extendido sale rechazada", len(rech) >= 1, rech)
    llegaron = [e.get("caja") for e in ev if e["ev"] == "sensor_on" and e["etiqueta"] == "sens_salida"]
    verifica("y nunca llega a sens_salida", not set(rech) & set(llegaron))
    c.cierra()

    print("=== 5. Puerto configurable y bandera de apagado ===")
    arranca(datos, A2_SUST_PUERTO=5021)
    verifica("con A2_SUST_PUERTO=5021 contesta en 5021", espera_emulador(5021))
    verifica("y no en 5020", not espera_emulador(5020, limite_s=2))
    arranca(datos, A2_SUSTITUTO=0)
    time.sleep(3)
    verifica("con A2_SUSTITUTO=0 nadie contesta en 5020", not espera_emulador(5020, limite_s=3))
    detiene()


# ---- determinismo ------------------------------------------------------------------
def corrida(semilla, minutos, etiqueta):
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_det_%s_" % etiqueta))
    arranca(datos, A2_SUST_SEMILLA=semilla)
    if not espera_emulador():
        sys.exit("el emulador no arranco (%s)" % datos)
    with Cliente("127.0.0.1", 5020) as c:
        enciende_linea(c, 5.0)
    objetivo = minutos * 60
    t_inicio = time.time()
    limite = t_inicio + objetivo * 1.5 + 60
    while time.time() < limite:
        if any(e["ev"] == "marca" and e["t"] >= objetivo for e in eventos(datos)):
            break
        time.sleep(5)
    pared = time.time() - t_inicio
    detiene()
    ev = eventos(datos)
    # Lo que produce la planta, desde t = 0. Las entradas las pone esta prueba.
    seq = [(e["t"], e["ev"], e.get("etiqueta"), e.get("caja"), e.get("masa_kg"))
           for e in ev if e["t"] is not None and e["ev"] != "entrada" and e["t"] <= objetivo]
    marcas = [e for e in ev if e["ev"] == "marca"]
    print("  %-9s semilla %d: %d eventos hasta t=%ds, %d cajas emitidas, %d salen, "
          "%.0f s de pared, pedidos sin respuesta %s, datos en %s"
          % (etiqueta, semilla, len(seq), objetivo,
             sum(1 for s in seq if s[1] == "caja_emitida"), sum(1 for s in seq if s[1] == "caja_sale"),
             pared, marcas[-1]["pedidos_sin_respuesta"] if marcas else "?", datos))
    return seq


def huella(seq):
    return hashlib.sha256(json.dumps(seq).encode()).hexdigest()[:16]


def determinismo(minutos):
    semilla = CFG["semilla"]
    print("=== Determinismo: dos corridas de %d min con la semilla %d ===" % (minutos, semilla))
    a = corrida(semilla, minutos, "corrida1")
    b = corrida(semilla, minutos, "corrida2")
    verifica("llego a la marca de t=%d s en las dos" % (minutos * 60),
             a and b and a[-1][1] == "marca" and b[-1][1] == "marca" and a[-1][0] == b[-1][0] == minutos * 60)
    print("  huellas: %s / %s" % (huella(a), huella(b)))
    if a != b:
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        print("  primera diferencia en el evento %d: %s vs %s"
              % (i, a[i] if i < len(a) else None, b[i] if i < len(b) else None))
    verifica("misma secuencia de eventos, evento por evento", a == b)
    print("=== Control: otra semilla, 1 min ===")
    c = corrida(semilla + 1, 1, "control")
    a1 = [s for s in a if s[0] <= 60]
    verifica("con otra semilla la secuencia del primer minuto cambia", c != a1,
             "(si no cambia, la semilla no esta entrando)")
    masas_a = [s[4] for s in a1 if s[1] == "caja_emitida"]
    masas_c = [s[4] for s in c if s[1] == "caja_emitida"]
    print("  masas del primer minuto: semilla %d %s | semilla %d %s" % (semilla, masas_a, semilla + 1, masas_c))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("modo", choices=["funcional", "determinismo"])
    p.add_argument("--minutos", type=int, default=10)
    a = p.parse_args()
    try:
        funcional() if a.modo == "funcional" else determinismo(a.minutos)
    finally:
        detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (resultado["ok"], resultado["falla"]))
    sys.exit(resultado["falla"])
