#!/usr/bin/env python3
"""Mide el codigo HTTP y el cuerpo EXACTOS que devuelve RTDB para cada forma
de fallar. La pregunta concreta: se puede distinguir un fallo de permisos de
un fallo de validacion mirando solo la respuesta?"""
import base64, json, sys, time, urllib.error, urllib.request

BASE, NS = "http://127.0.0.1:9000", "demo-iot-default-rtdb"
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def b64(o): return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")
def tk(u):
    n = int(time.time())
    return "%s.%s." % (b64({"alg":"none","typ":"JWT"}),
        b64({"iss":"https://securetoken.google.com/demo-iot","aud":"demo-iot","auth_time":n,
             "user_id":u,"sub":u,"iat":n,"exp":n+3600,
             "firebase":{"identities":{},"sign_in_provider":"password"}}))

def escribe(path, uid, body):
    url = "%s/%s.json?ns=%s&auth=%s" % (BASE, path.strip("/"), NS, tk(uid))
    r = urllib.request.Request(url, data=json.dumps(body).encode(), method="PUT",
                               headers={"Content-Type": "application/json"})
    try:
        with op.open(r, timeout=15) as x: return x.status, x.read().decode()[:120]
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:120]
    except urllib.error.URLError as e: sys.exit("sin emulador: %s" % e.reason)

R = str(int(time.time()))
def reg(**k):
    d = {"ts_origen":"2026-08-25T18:00:00.000Z","ts_escritura":"2026-08-25T12:00:00.123-06:00",
         "temperatura_C":25.4,"vibracion_mm_s":12.0,"ciclos_acumulados":100}
    d.update(k); return d

casos = [
 ("dato correcto, UID correcto",      "plantas/planta_01/telemetria/c0_"+R, "UIDING", reg()),
 ("UID equivocado",                   "plantas/planta_01/telemetria/c1_"+R, "UID_MALO", reg()),
 ("visor intenta escribir",           "plantas/planta_01/telemetria/c2_"+R, "UIDVIS", reg()),
 ("temperatura 200 (fuera de rango)", "plantas/planta_01/telemetria/c3_"+R, "UIDING", reg(temperatura_C=200)),
 ("ts_escritura con Z",               "plantas/planta_01/telemetria/c4_"+R, "UIDING", reg(ts_escritura="2026-08-25T18:00:00.000Z")),
 ("campo extra",                      "plantas/planta_01/telemetria/c5_"+R, "UIDING", dict(reg(), extra=1)),
 ("falta un campo",                   "plantas/planta_01/telemetria/c6_"+R, "UIDING", {k:v for k,v in reg().items() if k!="ciclos_acumulados"}),
 ("plantaId mal formado",             "plantas/fantasma/telemetria/c7_"+R,  "UIDING", reg()),
 ("temperatura como texto",           "plantas/planta_01/telemetria/c8_"+R, "UIDING", reg(temperatura_C="25.4")),
]
print("%-36s %-6s %s" % ("CASO", "HTTP", "CUERPO"))
print("-" * 100)
vistos = {}
for desc, path, uid, body in casos:
    codigo, cuerpo = escribe(path, uid, body)
    print("%-36s %-6s %s" % (desc, codigo, cuerpo.strip()))
    vistos.setdefault((codigo, cuerpo.strip()), []).append(desc)
print("\nRESPUESTAS DISTINTAS OBSERVADAS: %d" % len(vistos))
for (c, b), quienes in vistos.items():
    print("  [%s %s] <- %d caso(s): %s" % (c, b, len(quienes), "; ".join(quienes)))
