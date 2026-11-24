#!/usr/bin/env python3
"""Reglas de la rama proceso (Actividad 2, C5): emulador o base real. Python 3.9.

    # emulador (pruebas/emulador/README.md para levantarlo)
    python3 pruebas/prueba_reglas_proceso.py --emulador 127.0.0.1:9000
    # base real, despues de publicar firebase/database.rules.generado.json
    python3 pruebas/prueba_reglas_proceso.py --planta planta_99

Las mismas cuatro propiedades de la Actividad 1, ahora sobre
/plantas/{plantaId}/proceso/{registroId}:
  1. sin escritura anonima,  2. solo el ingestor y solo en planta_NN,
  3. solo adicion (append-only),  4. esquema validado en el servidor.

Contra la base real da de alta ~12 registros que NO se pueden borrar desde la
aplicacion (append-only); por eso corre sobre planta_99 y se niega a correr
sobre planta_01 sin --acepto-ensuciar. Lee ../.env solo.
Codigo de salida 0 si todos los casos dan lo esperado.
"""
import argparse, base64, json, os, pathlib, ssl, sys, time, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("--planta", default="planta_99", help="debe cumplir ^planta_[0-9]{2}$")
ap.add_argument("--acepto-ensuciar", action="store_true")
ap.add_argument("--emulador", metavar="HOST:PUERTO")
ap.add_argument("--ns", default="demo-iot-default-rtdb")
a = ap.parse_args()
if a.planta == "planta_01" and not a.acepto_ensuciar:
    sys.exit("planta_01 es la corrida real. Usa --planta planta_99.")


def carga_env():
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def contexto_ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


op = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=contexto_ssl()))


def pide(metodo, url, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pet = urllib.request.Request(url, data=datos, method=metodo, headers={"Content-Type": "application/json"})
    try:
        with op.open(pet, timeout=25) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except urllib.error.URLError as e:
        sys.exit("No se pudo conectar: %s" % e.reason)


if a.emulador:
    BASE, SUFIJO = "http://" + a.emulador, "?ns=" + a.ns + "&auth="

    def _b64(o):
        return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")

    def token_de(uid):
        n = int(time.time())
        return "%s.%s." % (_b64({"alg": "none", "typ": "JWT"}), _b64({
            "iss": "https://securetoken.google.com/demo-iot", "aud": "demo-iot", "auth_time": n,
            "user_id": uid, "sub": uid, "iat": n, "exp": n + 3600,
            "firebase": {"identities": {}, "sign_in_provider": "password"}}))
    TOK = {"ingestor": token_de("UIDING"), "visor": token_de("UIDVIS"),
           "tercero": token_de("UID_NO_AUTORIZADO"), "anonimo": None}
else:
    carga_env()
    BASE = (os.environ.get("FIREBASE_DB_URL") or "").rstrip("/")
    KEY = os.environ.get("FIREBASE_API_KEY") or ""
    if not BASE or not KEY:
        sys.exit("Falta FIREBASE_DB_URL o FIREBASE_API_KEY en .env")
    SUFIJO = "?auth="

    def entra(var_correo, var_clave):
        s, c = pide("POST", "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + KEY,
                    {"email": os.environ.get(var_correo), "password": os.environ.get(var_clave),
                     "returnSecureToken": True})
        if s != 200:
            sys.exit("No pude autenticar %s: %s" % (var_correo, c[:160]))
        return json.loads(c)["idToken"]
    print("Autenticando contra el proyecto real...")
    TOK = {"ingestor": entra("FB_INGESTOR_EMAIL", "FB_INGESTOR_PASS"),
           "visor": entra("FB_VISOR_EMAIL", "FB_VISOR_PASS"), "tercero": None, "anonimo": None}


def llama(metodo, ruta, quien, cuerpo=None):
    url = "%s/%s.json" % (BASE, ruta.strip("/"))
    tok = TOK.get(quien)
    if a.emulador:
        url += SUFIJO + (tok or "")
        if not tok:
            url = url.replace("&auth=", "")
    elif tok:
        url += SUFIJO + tok
    s, _ = pide(metodo, url, cuerpo)
    return "PERMITE" if 200 <= s < 300 else "NIEGA"


R = str(int(time.time()))
P = a.planta
PRO = "plantas/%s/proceso" % P


def n(k):
    return "%s/%s_%s" % (PRO, k, R)


def reg(**cambios):
    d = {"ts_origen": "2026-10-24T18:00:00.123Z", "ts_escritura": "2026-10-24T12:00:00.456-06:00",
         "vel_banda_V": 2.05, "peso_V": 5.12, "caja_masa_kg": 10.24, "cajas_acumuladas": 7,
         "estado_linea": "en_marcha"}
    d.update(cambios)
    return {k: v for k, v in d.items() if v is not None}


latido = reg(caja_masa_kg=None, estado_linea="detenida")
llama("PUT", n("semilla"), "ingestor", reg())

C = [
    ("Lectura", "anonimo lee proceso", "NIEGA", ("GET", PRO, "anonimo", None)),
    ("Lectura", "visor lee proceso", "PERMITE", ("GET", PRO, "visor", None)),
    ("Lectura", "ingestor lee proceso", "PERMITE", ("GET", PRO, "ingestor", None)),

    ("Escritura", "anonimo da de alta", "NIEGA", ("PUT", n("a1"), "anonimo", reg())),
    ("Escritura", "visor da de alta", "NIEGA", ("PUT", n("a2"), "visor", reg())),
    ("Escritura", "ingestor: registro de caja", "PERMITE", ("PUT", n("ok1"), "ingestor", reg())),
    ("Escritura", "ingestor: latido sin caja_masa_kg", "PERMITE", ("PUT", n("ok2"), "ingestor", latido)),
    ("Escritura", "ingestor: POST (clave push), como Node-RED", "PERMITE", ("POST", PRO, "ingestor", reg())),

    ("Append-only", "sobrescribe un registro", "NIEGA", ("PUT", n("semilla"), "ingestor", reg(peso_V=1))),
    ("Append-only", "parcha un campo", "NIEGA", ("PATCH", n("semilla"), "ingestor", {"peso_V": 1})),
    ("Append-only", "borra un registro", "NIEGA", ("DELETE", n("semilla"), "ingestor", None)),
    ("Append-only", "borra la rama proceso", "NIEGA", ("DELETE", PRO, "ingestor", None)),

    ("Esquema", "campo fuera del esquema", "NIEGA", ("PUT", n("e1"), "ingestor", dict(reg(), origen="x"))),
    ("Esquema", "falta estado_linea", "NIEGA", ("PUT", n("e2"), "ingestor", reg(estado_linea=None))),
    ("Esquema", "falta cajas_acumuladas", "NIEGA", ("PUT", n("e3"), "ingestor", reg(cajas_acumuladas=None))),
    ("Esquema", "vel_banda_V como texto", "NIEGA", ("PUT", n("e4"), "ingestor", reg(vel_banda_V="2.05"))),
    ("Esquema", "vel_banda_V 10.01", "NIEGA", ("PUT", n("e5"), "ingestor", reg(vel_banda_V=10.01))),
    ("Esquema", "vel_banda_V -10 (limite)", "PERMITE", ("PUT", n("e6"), "ingestor", reg(vel_banda_V=-10))),
    ("Esquema", "peso_V negativo", "NIEGA", ("PUT", n("e7"), "ingestor", reg(peso_V=-0.01))),
    ("Esquema", "caja_masa_kg 20.01", "NIEGA", ("PUT", n("e8"), "ingestor", reg(caja_masa_kg=20.01))),
    ("Esquema", "cajas_acumuladas no entero", "NIEGA", ("PUT", n("e9"), "ingestor", reg(cajas_acumuladas=7.5))),
    ("Esquema", "estado_linea inventado", "NIEGA", ("PUT", n("e10"), "ingestor", reg(estado_linea="pausa"))),
    ("Esquema", "latido con estado_linea emergencia (E1)", "PERMITE",
     ("PUT", n("e13"), "ingestor", reg(caja_masa_kg=None, estado_linea="emergencia"))),
    ("Esquema", "ts_origen con offset local", "NIEGA", ("PUT", n("e11"), "ingestor", reg(ts_origen="2026-10-24T12:00:00.123-06:00"))),
    ("Esquema", "ts_escritura con Z", "NIEGA", ("PUT", n("e12"), "ingestor", reg(ts_escritura="2026-10-24T18:00:00.456Z"))),

    ("Esquema", "destino left (desviador)", "PERMITE", ("PUT", n("d1"), "ingestor", reg(destino="left"))),
    ("Esquema", "destino rechazo (empujador)", "PERMITE", ("PUT", n("d2"), "ingestor", reg(destino="rechazo"))),
    ("Esquema", "destino inventado", "NIEGA", ("PUT", n("d3"), "ingestor", reg(destino="arriba"))),
    ("Esquema", "destino numerico", "NIEGA", ("PUT", n("d4"), "ingestor", reg(destino=1))),

    ("plantaId", "planta fantasma", "NIEGA", ("PUT", "plantas/fantasma/proceso/p1_%s" % R, "ingestor", reg())),
    ("plantaId", "planta_7", "NIEGA", ("PUT", "plantas/planta_7/proceso/p2_%s" % R, "ingestor", reg())),
]
if a.emulador:
    C.insert(1, ("Lectura", "tercero autenticado lee proceso", "NIEGA", ("GET", PRO, "tercero", None)))
    C.insert(5, ("Escritura", "tercero autenticado da de alta", "NIEGA", ("PUT", n("a3"), "tercero", reg())))

fallos, g0 = [], None
for g, desc, esp, (m, ruta, quien, cuerpo) in C:
    if g != g0:
        g0 = g
        print("\n== %s ==" % g)
    real = llama(m, ruta, quien, cuerpo)
    if real != esp:
        fallos.append((g, desc, esp, real))
    print("  %s %-48s esperado=%-7s real=%s" % ("ok" if real == esp else "!!", desc, esp, real))
print("\n%d casos, %d discrepancias (%s)" % (len(C), len(fallos), "emulador" if a.emulador else "base real, " + P))
for f in fallos:
    print("  DISCREPANCIA: [%s] %s -> esperado %s, real %s" % f)
sys.exit(1 if fallos else 0)
