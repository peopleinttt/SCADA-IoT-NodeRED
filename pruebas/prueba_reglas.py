#!/usr/bin/env python3
"""
Suite de verificacion de database.rules.json (v2) contra el emulador de Realtime Database.

Ejecuta escrituras y lecturas reales para comprobar las cuatro propiedades declaradas
mas los cambios de la v2: rangos ajustados a la instrumentacion, regex de marca de
tiempo separadas (ts_origen en UTC / ts_escritura y ts con offset local) y $plantaId
acotado a planta_NN.

Uso:
  1) sustituye __UID_INGESTOR__ y __UID_VISOR__ en database.rules.json por los UID
     que le pases a este script
  2) firebase emulators:start --only database --project demo-iot
  3) python3 prueba_reglas_v2.py --uid-ingestor UIDING --uid-visor UIDVIS --port 9000

Codigo de salida 0 si los 50 casos coinciden con lo esperado, 1 si alguno no.
Los casos del grupo "Holgura restante" PASAN a proposito: documentan lo que el
esquema congelado no permite cerrar, no son fallos.
"""
import argparse, base64, json, sys, time, urllib.error, urllib.request

_p = argparse.ArgumentParser()
_p.add_argument("--uid-ingestor", default="UIDING")
_p.add_argument("--uid-visor",    default="UIDVIS")
_p.add_argument("--host",     default="127.0.0.1")
_p.add_argument("--port",     default="9000")
_p.add_argument("--ns",       default="demo-iot-default-rtdb")
_p.add_argument("--planta",   default="planta_07", help="debe cumplir ^planta_[0-9]{2}$")
_a = _p.parse_args()

NS   = _a.ns
BASE = "http://%s:%s" % (_a.host, _a.port)
R    = str(int(time.time()))
P    = _a.planta
op   = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def b64(o): return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")
def tk(u):
    n=int(time.time())
    return "%s.%s."%(b64({"alg":"none","typ":"JWT"}),b64({"iss":"https://securetoken.google.com/demo-iot",
      "aud":"demo-iot","auth_time":n,"user_id":u,"sub":u,"iat":n,"exp":n+3600,
      "firebase":{"identities":{},"sign_in_provider":"password"}}))
T={"anonimo":None,"ingestor":tk(_a.uid_ingestor),"visor":tk(_a.uid_visor),"tercero":tk("UID_NO_AUTORIZADO")}
def call(m,path,who,body=None):
    url="%s/%s.json?ns=%s"%(BASE,path.strip("/"),NS)
    if T.get(who): url+="&auth="+T[who]
    d=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(url,data=d,method=m,headers={"Content-Type":"application/json"})
    try:
        with op.open(r,timeout=15) as x: return "PERMITE" if 200<=x.status<300 else "NIEGA"
    except urllib.error.HTTPError: return "NIEGA"
    except urllib.error.URLError as e: sys.exit("No hay emulador escuchando en %s (%s)." % (BASE, e.reason))
def reg(t=25.4,v=12.0,c=100,o="2026-08-25T18:00:00.000Z",w="2026-08-25T12:00:00.123-06:00"):
    return {"ts_origen":o,"ts_escritura":w,"temperatura_C":t,"vibracion_mm_s":v,"ciclos_acumulados":c}
D={"ts":"2026-08-25T12:00:05.000-06:00","resumen_entrada":"temp al alza","texto_diagnostico":"rodamiento",
   "accion_prescrita":"inspeccion","modelo":"m1","latencia_ms":820}
TEL="plantas/%s/telemetria"%P; DIA="plantas/%s/diagnosticos"%P
def n(k): return "%s/%s_%s"%(TEL,k,R)
def nd(k): return "%s/%s_%s"%(DIA,k,R)
call("PUT",n("semilla"),"ingestor",reg()); call("PUT",nd("semilla"),"ingestor",D)

C=[
("Lectura","anonimo lee telemetria","NIEGA",("GET",TEL,"anonimo",None)),
("Lectura","tercero autenticado lee telemetria","NIEGA",("GET",TEL,"tercero",None)),
("Lectura","visor lee telemetria","PERMITE",("GET",TEL,"visor",None)),
("Lectura","visor lee diagnosticos","PERMITE",("GET",DIA,"visor",None)),
("Lectura","visor lista /plantas","NIEGA",("GET","plantas","visor",None)),
("Lectura","visor lee materiales","NIEGA",("GET","plantas/%s/materiales"%P,"visor",None)),

("Escritura","anonimo da de alta","NIEGA",("PUT",n("a1"),"anonimo",reg())),
("Escritura","visor da de alta","NIEGA",("PUT",n("a2"),"visor",reg())),
("Escritura","tercero da de alta","NIEGA",("PUT",n("a3"),"tercero",reg())),
("Escritura","ingestor da de alta valida","PERMITE",("PUT",n("ok1"),"ingestor",reg())),
("Escritura","ingestor hace push de diagnostico","PERMITE",("POST",DIA,"ingestor",D)),

("Append-only","sobrescribe registro existente","NIEGA",("PUT",n("semilla"),"ingestor",reg(t=50))),
("Append-only","parcha un campo existente","NIEGA",("PATCH",n("semilla"),"ingestor",{"temperatura_C":50})),
("Append-only","borra un registro","NIEGA",("DELETE",n("semilla"),"ingestor",None)),
("Append-only","borra la rama telemetria","NIEGA",("DELETE",TEL,"ingestor",None)),
("Append-only","borra la planta entera","NIEGA",("DELETE","plantas/%s"%P,"ingestor",None)),
("Append-only","multi-ruta de puras altas nuevas","PERMITE",("PATCH",TEL,"ingestor",{"la_%s"%R:reg(),"lb_%s"%R:reg()})),
("Append-only","multi-ruta que toca historia vieja","NIEGA",("PATCH",TEL,"ingestor",{"semilla_%s/temperatura_C"%R:50})),
("Append-only","multi-ruta mezclando alta nueva e historia","NIEGA",("PATCH",TEL,"ingestor",{"lc_%s"%R:reg(),"semilla_%s/temperatura_C"%R:1})),

("Esquema","campo fuera del esquema","NIEGA",("PUT",n("e1"),"ingestor",dict(reg(),extra=1))),
("Esquema","falta campo obligatorio","NIEGA",("PUT",n("e2"),"ingestor",{k:v for k,v in reg().items() if k!="ciclos_acumulados"})),
("Esquema","temperatura como texto","NIEGA",("PUT",n("e3"),"ingestor",dict(reg(),temperatura_C="25.4"))),
("Esquema","ciclos no entero","NIEGA",("PUT",n("e4"),"ingestor",reg(c=3.5))),
("Esquema","ciclos negativo","NIEGA",("PUT",n("e5"),"ingestor",reg(c=-1))),
("Esquema","diagnostico con texto vacio","NIEGA",("PUT",nd("e6"),"ingestor",dict(D,texto_diagnostico=""))),
("Esquema","diagnostico con latencia negativa","NIEGA",("PUT",nd("e7"),"ingestor",dict(D,latencia_ms=-5))),

("plantaId","planta_07 (conforme)","PERMITE",("PUT",n("p1"),"ingestor",reg())),
("plantaId","planta_99 (otra conforme)","PERMITE",("PUT","plantas/planta_99/telemetria/p2_%s"%R,"ingestor",reg())),
("plantaId","fantasma (no conforme)","NIEGA",("PUT","plantas/fantasma/telemetria/p3_%s"%R,"ingestor",reg())),
("plantaId","planta_7 (un solo digito)","NIEGA",("PUT","plantas/planta_7/telemetria/p4_%s"%R,"ingestor",reg())),
("plantaId","planta_007 (tres digitos)","NIEGA",("PUT","plantas/planta_007/telemetria/p5_%s"%R,"ingestor",reg())),
("plantaId","diagnostico en planta no conforme","NIEGA",("PUT","plantas/fantasma/diagnosticos/p6_%s"%R,"ingestor",D)),

("Marcas","ts_origen en UTC con Z","PERMITE",("PUT",n("m1"),"ingestor",reg())),
("Marcas","ts_origen con offset local","NIEGA",("PUT",n("m2"),"ingestor",reg(o="2026-08-25T12:00:00.000-06:00"))),
("Marcas","ts_escritura con offset -06:00","PERMITE",("PUT",n("m3"),"ingestor",reg(w="2026-08-25T12:00:00.000-06:00"))),
("Marcas","ts_escritura con Z (Node-RED en UTC)","NIEGA",("PUT",n("m4"),"ingestor",reg(w="2026-08-25T18:00:00.000Z"))),
("Marcas","ts_escritura con +00:00","PERMITE",("PUT",n("m5"),"ingestor",reg(w="2026-08-25T18:00:00.000+00:00"))),
("Marcas","ts sin milisegundos","NIEGA",("PUT",n("m6"),"ingestor",reg(o="2026-08-25T18:00:00Z"))),
("Marcas","diagnostico con ts en Z","NIEGA",("PUT",nd("m7"),"ingestor",dict(D,ts="2026-08-25T18:00:05.000Z"))),

("Rangos","temperatura 80.0 (limite)","PERMITE",("PUT",n("r1"),"ingestor",reg(t=80.0))),
("Rangos","temperatura 80.1","NIEGA",("PUT",n("r2"),"ingestor",reg(t=80.1))),
("Rangos","temperatura -40.0 (limite)","PERMITE",("PUT",n("r3"),"ingestor",reg(t=-40.0))),
("Rangos","temperatura -40.1","NIEGA",("PUT",n("r4"),"ingestor",reg(t=-40.1))),
("Rangos","temperatura 120 (antes pasaba)","NIEGA",("PUT",n("r5"),"ingestor",reg(t=120))),
("Rangos","vibracion 100.0 (limite)","PERMITE",("PUT",n("r6"),"ingestor",reg(v=100.0))),
("Rangos","vibracion 100.1","NIEGA",("PUT",n("r7"),"ingestor",reg(v=100.1))),
("Rangos","vibracion 900 (antes pasaba)","NIEGA",("PUT",n("r8"),"ingestor",reg(v=900))),
("Rangos","vibracion 60 (sobre la escala 0-50 del sensor)","PERMITE",("PUT",n("r9"),"ingestor",reg(v=60))),

("Holgura restante","ts_escritura anterior a ts_origen","PERMITE",("PUT",n("h1"),"ingestor",reg(o="2026-08-25T18:00:00.000Z",w="2020-01-01T00:00:00.000-06:00"))),
("Holgura restante","registro fechado en 1999","PERMITE",("PUT",n("h2"),"ingestor",reg(o="1999-01-01T00:00:00.000Z"))),
]
fallos=[]; g0=None
for g,desc,esp,(m,p_,w,b) in C:
    if g!=g0: g0=g; print("\n== %s =="%g)
    real=call(m,p_,w,b)
    if real!=esp: fallos.append((g,desc,esp,real))
    print("  %s %-50s esperado=%-7s real=%s"%("ok" if real==esp else "!!",desc,esp,real))
print("\n%d casos, %d discrepancias"%(len(C),len(fallos)))
for f in fallos: print("  DISCREPANCIA: [%s] %s -> esperado %s, real %s"%f)

sys.exit(1 if fallos else 0)
