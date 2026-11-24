#!/usr/bin/env python3
"""
Suite de verificacion de las reglas contra la base REAL de Firebase.

Misma bateria que prueba_reglas_v2.py, pero autenticandose de verdad: pide un
idToken a Identity Toolkit con las credenciales del .env. Las contrasenas nunca
salen de tu maquina; este script no las imprime ni las manda a ningun lado
salvo al propio endpoint de Google.

Uso:
    cd ~/dev/IoT && source .env
    python3 prueba_reglas_real.py --planta planta_99

Variables que lee del entorno:
    FIREBASE_DB_URL, FIREBASE_API_KEY,
    FB_INGESTOR_EMAIL, FB_INGESTOR_PASS, FB_VISOR_EMAIL, FB_VISOR_PASS

IMPORTANTE - por que --planta planta_99 y no planta_01:
    la suite da de alta ~30 registros y las reglas son append-only, asi que
    NO se pueden borrar desde el flujo (solo desde la consola, que hace bypass).
    Corriendola en planta_99 tu telemetria real de planta_01 queda intacta.
    El script se niega a correr en planta_01 salvo que pases --acepto-ensuciar.

Codigo de salida 0 si los casos coinciden con lo esperado, 1 si no.
El grupo "Holgura restante" PASA a proposito: documenta lo que el esquema
congelado no permite cerrar.
"""
import argparse, json, os, pathlib, ssl, sys, time, urllib.error, urllib.parse, urllib.request


def carga_env():
    """Lee ../.env y lo mete en os.environ.

    Hace falta porque 'source .env' solo crea variables de shell: no se
    exportan, asi que el proceso de Python no las ve y el script moriria
    diciendo que faltan. Con esto da igual si el usuario hizo source o no.
    Las variables reales del entorno ganan sobre el archivo.
    """
    ruta = pathlib.Path(__file__).resolve().parent.parent / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def contexto_ssl():
    """CA para HTTPS. El Python de python.org en macOS no trae rutas de
    certificados configuradas y toda llamada HTTPS falla con
    CERTIFICATE_VERIFY_FAILED."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    if ssl.get_default_verify_paths().cafile:
        return ssl.create_default_context()
    raise SystemExit(
        "Python no encuentra los certificados raiz y no puede hablar por HTTPS.\n"
        "Arreglo, cualquiera de los dos:\n"
        "  pip3 install certifi\n"
        '  open "/Applications/Python 3.10/Install Certificates.command"')


carga_env()
CTX = contexto_ssl()

ap = argparse.ArgumentParser()
ap.add_argument("--planta", default="planta_99", help="debe cumplir ^planta_[0-9]{2}$")
ap.add_argument("--acepto-ensuciar", action="store_true",
                help="permite correr sobre planta_01 (deja registros imborrables)")
ap.add_argument("--emulador", metavar="HOST:PUERTO",
                help="corre contra el emulador con JWT sin firmar en vez de la base real")
ap.add_argument("--ns", default="demo-iot-default-rtdb", help="solo con --emulador")
ap.add_argument("--rapido", action="store_true",
                help="solo 3 casos decisivos: dice si las reglas estan publicadas o no")
a = ap.parse_args()

if a.planta == "planta_01" and not a.acepto_ensuciar:
    sys.exit("planta_01 es tu corrida real. Usa --planta planta_99, o --acepto-ensuciar si de verdad quieres.")

# ---------------------------------------------------------------- transporte
op = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                 urllib.request.HTTPSHandler(context=CTX))

def pide(metodo, url, cuerpo=None, cabeceras=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pet = urllib.request.Request(url, data=datos, method=metodo,
                                 headers=cabeceras or {"Content-Type": "application/json"})
    try:
        with op.open(pet, timeout=25) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except urllib.error.URLError as e:
        sys.exit("No se pudo conectar: %s" % e.reason)

# ------------------------------------------------------------------- sesion
if a.emulador:
    import base64
    BASE = "http://" + a.emulador
    SUFIJO = "?ns=" + a.ns + "&auth="
    def _b64(o): return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")
    def token_de(uid):
        n = int(time.time())
        return "%s.%s." % (_b64({"alg": "none", "typ": "JWT"}), _b64({
            "iss": "https://securetoken.google.com/demo-iot", "aud": "demo-iot",
            "auth_time": n, "user_id": uid, "sub": uid, "iat": n, "exp": n + 3600,
            "firebase": {"identities": {}, "sign_in_provider": "password"}}))
    TOK = {"ingestor": token_de("UIDING"), "visor": token_de("UIDVIS"),
           "tercero": token_de("UID_NO_AUTORIZADO"), "anonimo": None}
else:
    DB  = (os.environ.get("FIREBASE_DB_URL") or "").rstrip("/")
    KEY = os.environ.get("FIREBASE_API_KEY") or ""
    if not DB or not KEY:
        sys.exit("Falta FIREBASE_DB_URL o FIREBASE_API_KEY. Corre 'source .env' primero.")
    BASE, SUFIJO = DB, "?auth="

    def entra(etiqueta, var_correo, var_clave):
        correo, clave = os.environ.get(var_correo), os.environ.get(var_clave)
        if not correo or not clave:
            sys.exit("Falta %s o %s en el entorno." % (var_correo, var_clave))
        s, c = pide("POST",
                    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + KEY,
                    {"email": correo, "password": clave, "returnSecureToken": True})
        if s != 200:
            motivo = ""
            try: motivo = json.loads(c)["error"]["message"]
            except Exception: motivo = c[:120]
            sys.exit("No pude autenticar a '%s': %s" % (etiqueta, motivo))
        d = json.loads(c)
        print("  sesion %-9s uid=%s" % (etiqueta, d["localId"]))
        return d["idToken"]

    print("Autenticando contra el proyecto real...")
    TOK = {"ingestor": entra("ingestor", "FB_INGESTOR_EMAIL", "FB_INGESTOR_PASS"),
           "visor":    entra("visor",    "FB_VISOR_EMAIL",    "FB_VISOR_PASS"),
           "anonimo":  None}
    TOK["tercero"] = None   # sin tercera cuenta real: el caso anonimo ya cubre "sesion ajena"

def llama(metodo, ruta, quien, cuerpo=None):
    url = "%s/%s.json%s" % (BASE, ruta.strip("/"), SUFIJO)
    if TOK.get(quien): url += urllib.parse.quote(TOK[quien], safe="")
    elif url.endswith("?auth="):
        url = url[:-len("?auth=")]   # rstrip("?auth=") quitaria CARACTERES sueltos
    s, _ = pide(metodo, url, cuerpo)
    return "PERMITE" if 200 <= s < 300 else "NIEGA"

# -------------------------------------------------------------------- casos
R = str(int(time.time()))
P = a.planta
TEL, DIA = "plantas/%s/telemetria" % P, "plantas/%s/diagnosticos" % P
n  = lambda k: "%s/%s_%s" % (TEL, k, R)
nd = lambda k: "%s/%s_%s" % (DIA, k, R)

def reg(t=25.4, v=12.0, c=100,
        o="2026-08-25T18:00:00.000Z", w="2026-08-25T12:00:00.123-06:00"):
    return {"ts_origen": o, "ts_escritura": w,
            "temperatura_C": t, "vibracion_mm_s": v, "ciclos_acumulados": c}

D = {"ts": "2026-08-25T12:00:05.000-06:00", "resumen_entrada": "temperatura al alza",
     "texto_diagnostico": "desgaste de rodamiento probable",
     "accion_prescrita": "inspeccion en el proximo paro", "modelo": "modelo-x", "latencia_ms": 820}

llama("PUT", n("semilla"), "ingestor", reg())
llama("PUT", nd("semilla"), "ingestor", D)

C = [
 ("Lectura", "anonimo lee telemetria", "NIEGA", ("GET", TEL, "anonimo", None)),
 ("Lectura", "visor lee telemetria", "PERMITE", ("GET", TEL, "visor", None)),
 ("Lectura", "visor lee diagnosticos", "PERMITE", ("GET", DIA, "visor", None)),
 ("Lectura", "ingestor lee telemetria", "PERMITE", ("GET", TEL, "ingestor", None)),
 ("Lectura", "visor lista /plantas", "NIEGA", ("GET", "plantas", "visor", None)),
 ("Lectura", "visor lee materiales", "NIEGA", ("GET", "plantas/%s/materiales" % P, "visor", None)),
 ("Lectura", "visor lee la planta completa", "NIEGA", ("GET", "plantas/%s" % P, "visor", None)),
 ("Lectura", "visor lee la raiz", "NIEGA", ("GET", "/", "visor", None)),

 ("Escritura", "anonimo da de alta", "NIEGA", ("PUT", n("a1"), "anonimo", reg())),
 ("Escritura", "visor da de alta", "NIEGA", ("PUT", n("a2"), "visor", reg())),
 ("Escritura", "ingestor da de alta valida", "PERMITE", ("PUT", n("ok1"), "ingestor", reg())),
 ("Escritura", "ingestor hace push de diagnostico", "PERMITE", ("POST", DIA, "ingestor", D)),

 ("Append-only", "sobrescribe registro existente", "NIEGA", ("PUT", n("semilla"), "ingestor", reg(t=50))),
 ("Append-only", "parcha un campo existente", "NIEGA", ("PATCH", n("semilla"), "ingestor", {"temperatura_C": 50})),
 ("Append-only", "borra un registro", "NIEGA", ("DELETE", n("semilla"), "ingestor", None)),
 ("Append-only", "borra la rama telemetria", "NIEGA", ("DELETE", TEL, "ingestor", None)),
 ("Append-only", "borra la planta entera", "NIEGA", ("DELETE", "plantas/%s" % P, "ingestor", None)),
 ("Append-only", "multi-ruta de puras altas nuevas", "PERMITE", ("PATCH", TEL, "ingestor", {"la_%s" % R: reg(), "lb_%s" % R: reg()})),
 ("Append-only", "multi-ruta que toca historia vieja", "NIEGA", ("PATCH", TEL, "ingestor", {"semilla_%s/temperatura_C" % R: 50})),
 ("Append-only", "multi-ruta mezclando alta nueva e historia", "NIEGA", ("PATCH", TEL, "ingestor", {"lc_%s" % R: reg(), "semilla_%s/temperatura_C" % R: 1})),

 ("Esquema", "campo fuera del esquema", "NIEGA", ("PUT", n("e1"), "ingestor", dict(reg(), extra=1))),
 ("Esquema", "falta campo obligatorio", "NIEGA", ("PUT", n("e2"), "ingestor", {k: v for k, v in reg().items() if k != "ciclos_acumulados"})),
 ("Esquema", "temperatura como texto", "NIEGA", ("PUT", n("e3"), "ingestor", dict(reg(), temperatura_C="25.4"))),
 ("Esquema", "ciclos no entero", "NIEGA", ("PUT", n("e4"), "ingestor", reg(c=3.5))),
 ("Esquema", "ciclos negativo", "NIEGA", ("PUT", n("e5"), "ingestor", reg(c=-1))),
 ("Esquema", "diagnostico con texto vacio", "NIEGA", ("PUT", nd("e6"), "ingestor", dict(D, texto_diagnostico=""))),
 ("Esquema", "diagnostico con latencia negativa", "NIEGA", ("PUT", nd("e7"), "ingestor", dict(D, latencia_ms=-5))),

 ("plantaId", "planta conforme", "PERMITE", ("PUT", n("p1"), "ingestor", reg())),
 ("plantaId", "fantasma (no conforme)", "NIEGA", ("PUT", "plantas/fantasma/telemetria/p2_%s" % R, "ingestor", reg())),
 ("plantaId", "planta_7 (un solo digito)", "NIEGA", ("PUT", "plantas/planta_7/telemetria/p3_%s" % R, "ingestor", reg())),
 ("plantaId", "planta_007 (tres digitos)", "NIEGA", ("PUT", "plantas/planta_007/telemetria/p4_%s" % R, "ingestor", reg())),

 ("Marcas", "ts_origen en UTC con Z", "PERMITE", ("PUT", n("m1"), "ingestor", reg())),
 ("Marcas", "ts_origen con offset local", "NIEGA", ("PUT", n("m2"), "ingestor", reg(o="2026-08-25T12:00:00.000-06:00"))),
 ("Marcas", "ts_escritura con offset -06:00", "PERMITE", ("PUT", n("m3"), "ingestor", reg(w="2026-08-25T12:00:00.000-06:00"))),
 ("Marcas", "ts_escritura con Z (Node-RED en UTC)", "NIEGA", ("PUT", n("m4"), "ingestor", reg(w="2026-08-25T18:00:00.000Z"))),
 ("Marcas", "ts sin milisegundos", "NIEGA", ("PUT", n("m5"), "ingestor", reg(o="2026-08-25T18:00:00Z"))),
 ("Marcas", "diagnostico con ts en Z", "NIEGA", ("PUT", nd("m6"), "ingestor", dict(D, ts="2026-08-25T18:00:05.000Z"))),

 ("Rangos", "temperatura 80.0 (limite)", "PERMITE", ("PUT", n("r1"), "ingestor", reg(t=80.0))),
 ("Rangos", "temperatura 80.1", "NIEGA", ("PUT", n("r2"), "ingestor", reg(t=80.1))),
 ("Rangos", "temperatura -40.0 (limite)", "PERMITE", ("PUT", n("r3"), "ingestor", reg(t=-40.0))),
 ("Rangos", "temperatura 120", "NIEGA", ("PUT", n("r4"), "ingestor", reg(t=120))),
 ("Rangos", "vibracion 100.0 (limite)", "PERMITE", ("PUT", n("r5"), "ingestor", reg(v=100.0))),
 ("Rangos", "vibracion 100.1", "NIEGA", ("PUT", n("r6"), "ingestor", reg(v=100.1))),
 ("Rangos", "vibracion 900", "NIEGA", ("PUT", n("r7"), "ingestor", reg(v=900))),

 ("Holgura restante", "ts_escritura anterior a ts_origen", "PERMITE",
   ("PUT", n("h1"), "ingestor", reg(o="2026-08-25T18:00:00.000Z", w="2020-01-01T00:00:00.000-06:00"))),
 ("Holgura restante", "registro fechado en 1999", "PERMITE",
   ("PUT", n("h2"), "ingestor", reg(o="1999-01-01T00:00:00.000Z"))),
]

if a.rapido:
    # Tres casos que separan "reglas publicadas" de "modo bloqueado de fabrica".
    # En modo bloqueado TODO se niega, asi que basta con ver si lo que deberia
    # permitirse se permite.
    print("\nComprobacion rapida en %s (planta %s)\n" % (BASE, P))
    escribe = llama("PUT", n("rapido"), "ingestor", reg())
    lee     = llama("GET", TEL, "visor", None)
    anonimo = llama("GET", TEL, "anonimo", None)
    print("  el ingestor escribe un dato valido ..... %s   (deberia ser PERMITE)" % escribe)
    print("  el visor lee la telemetria ............. %s   (deberia ser PERMITE)" % lee)
    print("  un anonimo lee la telemetria ........... %s   (deberia ser NIEGA)" % anonimo)
    print()
    if escribe == "PERMITE" and lee == "PERMITE" and anonimo == "NIEGA":
        print("  REGLAS PUBLICADAS Y CORRECTAS. Sigue con ./arranca.sh")
        sys.exit(0)
    if escribe == "NIEGA" and lee == "NIEGA" and anonimo == "NIEGA":
        print("  LAS REGLAS NO ESTAN PUBLICADAS.")
        print("  La base esta negando todo, que es lo que hace el modo bloqueado")
        print("  de fabrica. Publica firebase/database.rules.generado.json en:")
        print("  Consola de Firebase -> Realtime Database -> pestana Reglas -> Publicar")
        sys.exit(1)
    print("  RESULTADO MIXTO: hay reglas publicadas, pero no son las nuestras,")
    print("  o los UID no coinciden. Corre la suite completa (sin --rapido).")
    sys.exit(1)

print("\nReglas evaluadas en %s  (planta %s, sufijo de corrida %s)\n" % (BASE, P, R))
fallos, grupo = [], None
for g, desc, esperado, (metodo, ruta, quien, cuerpo) in C:
    if g != grupo:
        grupo = g
        print("== %s ==" % g)
    real = llama(metodo, ruta, quien, cuerpo)
    if real != esperado:
        fallos.append((g, desc, esperado, real))
    print("  %s %-48s esperado=%-7s real=%s" % ("ok" if real == esperado else "!!", desc, esperado, real))

print("\n%d casos, %d discrepancias" % (len(C), len(fallos)))
for f in fallos:
    print("  DISCREPANCIA: [%s] %s -> esperado %s, real %s" % f)
sys.exit(1 if fallos else 0)
