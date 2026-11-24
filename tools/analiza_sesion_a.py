#!/usr/bin/env python3
"""Resultados de la sesion con Ari (paso A de la fase 4). Python 3.9, sin dependencias.

    python3 tools/analiza_sesion_a.py datos/corridas/A_2026-11-17 [--md docs/sesion_A.md] [--base]

Definiciones: docs/INSTRUMENTACION_A2.md, seccion 5. Lee la carpeta de la
sesion (eventos, CSV de sondeo, CSV de la nube, vigilante, conexiones y
partes) y reporta A1, A2 y los cuatro resultados de A3, en tablas y sin
interpretacion salvo la conclusion que pide la orden.

--base: lee de la base real, con la cuenta del visor de .env, los dos latidos
de A2 por su registro_id (verificacion 3). No imprime credenciales ni tokens.
Sin --base el reporte no depende de la red, asi que dos corridas sobre la
misma carpeta dan el mismo texto.
"""
import argparse, csv, json, pathlib, sys
from datetime import datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TS_MAC = "100.81.236.34"
VENTANA_EVENTO_S = 0.5
# El cliente fecha el flanco con la hora de SU lectura y el vigilante con la de la suya: son
# dos sondeos independientes, asi que la lectura del cliente puede caer hasta un periodo de
# sondeo (~52 ms) antes de que el vigilante vea el cambio. La ventana empieza 0.1 s antes.
ANTES_S = 0.1
EVENTOS_CAJA = ("caja_perdida", "desvio_erroneo", "caja_fantasma", "caja_purgada")
T_PASO = {"vistas": 3, "registradas": 2,
          "fuente": "datos/corridas/T_2026-11-11/prueba_fio.log: Start a los 41.9, 53.6 y 65.5 s; eventos del cliente "
                    "con dos boton start"}


def t(s):
    """ISO 8601 con Z o con desfase (-06:00) y fraccion de segundo opcional -> epoch."""
    import re
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)$", s)
    base, frac, zona = m.group(1), (m.group(2) or "0")[:6].ljust(6, "0"), m.group(3)
    return datetime.fromisoformat("%s.%s%s" % (base, frac, "+00:00" if zona == "Z" else zona)).timestamp()


def jsonl(ruta):
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def en_tailnet(ip):
    p = [int(x) for x in ip.split(".")]
    return p[0] == 100 and 64 <= p[1] <= 127


def pulsaciones(vig, boton, desde, hasta):
    nc = boton != "start_button"
    presiona, suelta = ((1, 0), (0, 1)) if nc else ((0, 1), (1, 0))
    out, abierta = [], None
    for c in vig:
        if c.get("boton") != boton:
            continue
        if (c["de"], c["a"]) == presiona and desde <= c["t"] <= hasta:
            abierta = c["t"]
        elif (c["de"], c["a"]) == suelta and abierta is not None:
            out.append((abierta, c["t"]))
            abierta = None
    return out


def percentil(xs, p):
    xs = sorted(xs)
    import math
    k = max(1, math.ceil(p / 100.0 * len(xs)))
    return xs[k - 1]


def iso(x):
    return datetime.utcfromtimestamp(x).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def lee_base(registros):
    """Lee registros por registro_id con la cuenta del visor (.env). No imprime credenciales."""
    import urllib.request
    env = {}
    for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, v = l.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    cuerpo = json.dumps({"email": env["FB_VISOR_EMAIL"], "password": env["FB_VISOR_PASS"], "returnSecureToken": True}).encode()
    r = urllib.request.Request("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + env["FIREBASE_API_KEY"],
                               data=cuerpo, headers={"Content-Type": "application/json"})
    tok = json.loads(urllib.request.urlopen(r, timeout=15).read())["idToken"]
    out = {}
    for rid in registros:
        url = "%s/plantas/planta_01/proceso/%s.json?auth=%s" % (env["FIREBASE_DB_URL"].rstrip("/"), rid, tok)
        out[rid] = json.loads(urllib.request.urlopen(url, timeout=15).read())
    return out


def analiza(d, base=False):
    d = pathlib.Path(d)
    ev = jsonl(d / "a2_planta_eventos.jsonl")
    for e in ev:
        e["_t"] = t(e["ts"])
    vig = [c for c in jsonl(d / "vigilante.jsonl") if "boton" in c]
    con = jsonl(d / "conexiones.jsonl")
    partes = {p["parte"]: p for p in jsonl(d / "partes.jsonl")}
    sondeo = list(csv.DictReader(open(str(next(d.glob("a2_sondeo_*.csv"))), encoding="utf-8"), delimiter=";"))
    rn = next(d.glob("a2_nube_*.csv"), None)                       # sin nube (sesion S) no hay CSV
    nube = list(csv.DictReader(open(str(rn), encoding="utf-8"), delimiter=";")) if rn else []
    R = {"partes": partes}
    # Eventos de cajas por parte (cierre de la fase 4): cajas que un Stop alcanzo en el desviador.
    R["eventos_caja"] = {}
    for k, p in partes.items():
        a0, b0 = t(p["inicio"]), t(p["fin"])
        c = {}
        for e in ev:
            if not (a0 <= e["_t"] <= b0):
                continue
            if e["ev"] in EVENTOS_CAJA:
                clave = e["ev"] + (" (%s)" % e["motivo"] if e.get("motivo") else "")
                c[clave] = c.get(clave, 0) + 1
            if e["ev"] == "paso_caja" and e.get("rechazo_fallido"):
                c["paso_caja con rechazo_fallido"] = c.get("paso_caja con rechazo_fallido", 0) + 1
        R["eventos_caja"][k] = c

    # ---- A1 ----
    if "A1" not in partes:
        R["A1"] = R["A2"] = None
        return analiza_a3(R, partes, ev, vig, sondeo)
    p = partes["A1"]
    a, b = t(p["inicio"]), t(p["fin"])
    remotos = sorted({r for c in con if a <= t(c["ts"]) <= b for r in c["remotos"]})
    tail = sorted({r.split(":")[0] for r in remotos if en_tailnet(r.split(":")[0]) and r.split(":")[0] != TS_MAC})
    evp = [e for e in ev if a <= e["_t"] <= b]
    im = next((i for i, e in enumerate(evp) if e["ev"] == "comando" and e.get("accion") == "marcha" and e.get("origen") == "hmi"), None)
    ip_ = next((i for i, e in enumerate(evp) if im is not None and i > im and e["ev"] == "comando"
                and e.get("accion") == "paro" and e.get("origen") == "hmi"), None)
    cajas = sum(1 for e in evp[im + 1:ip_] if e["ev"] == "paso_caja") if im is not None and ip_ is not None else 0
    muestras_tail = sum(1 for c in con if a <= t(c["ts"]) <= b and any(r.split(":")[0] in tail for r in c["remotos"]))
    R["A1"] = {"tailnet": tail, "muestras_con_tailnet": muestras_tail,
               "muestras": sum(1 for c in con if a <= t(c["ts"]) <= b),
               "marcha": evp[im]["ts"] if im is not None else None, "paro": evp[ip_]["ts"] if ip_ is not None else None,
               "cajas": cajas, "ok1": bool(tail), "ok2": im is not None and ip_ is not None and cajas >= 3}

    # ---- A2 ----
    p = partes["A2"]
    a, b = t(p["inicio"]), t(p["fin"])
    emer = pulsaciones(vig, "emergency_stop", a, b)
    pe = next((e for e in ev if e["ev"] == "paro_de_emergencia" and a <= e["_t"] <= b), None)
    el = next((e for e in ev if e["ev"] == "emergencia_liberada" and a <= e["_t"] <= b), None)
    lat = [r for r in nube if r["tipo"] == "latido" and r["http"] == "200" and r["resultado"] == "aceptado"]
    def primero(e):
        if not e:
            return None
        for r in lat:
            dt = t(r["ts_escritura"]) - e["_t"]
            if 0 <= dt <= 2:
                return {"registro_id": r["registro_id"], "ts_escritura": r["ts_escritura"], "retraso_s": round(dt, 3)}
        return None
    l1, l2 = primero(pe), primero(el)
    cajas_nube = sum(1 for r in nube if r["tipo"] == "caja" and r["resultado"] == "aceptado")
    pasos = sum(1 for e in ev if e["ev"] == "paso_caja")
    descartadas = [c for e in ev if e["ev"] == "cajas_descartadas_por_emergencia" for c in e.get("cajas", [])]
    R["A2"] = {"emergencia_vigilante": [(iso(x), iso(y), round(y - x, 3)) for x, y in emer],
               "paro_de_emergencia": pe["ts"] if pe else None, "emergencia_liberada": el["ts"] if el else None,
               "latido_paro": l1, "latido_liberada": l2, "cajas_nube": cajas_nube, "paso_caja": pasos,
               "descartadas": descartadas,
               "ok1": bool(emer) and bool(pe) and bool(el), "ok2": bool(l1) and bool(l2), "ok4": cajas_nube == pasos}
    if base and l1 and l2:
        regs = lee_base([l1["registro_id"], l2["registro_id"]])
        r1, r2 = regs[l1["registro_id"]] or {}, regs[l2["registro_id"]] or {}
        # El esquema de proceso no guarda un campo tipo: A2-Nube distingue el latido porque no
        # trae caja_masa_kg (33_nube_valida.js, tools/exporta_corrida.py). Se informa si el campo existe.
        tipo = lambda r: r.get("tipo") or ("caja" if "caja_masa_kg" in r else "latido")
        R["A2"]["base"] = [{"registro_id": l["registro_id"], "campo_tipo": "tipo" in r, "tipo": tipo(r),
                            "estado_linea": r.get("estado_linea"), "campos": sorted(r)} for l, r in ((l1, r1), (l2, r2))]
        R["A2"]["ok3"] = (tipo(r1), r1.get("estado_linea"), tipo(r2), r2.get("estado_linea")) == \
            ("latido", "emergencia", "latido", "detenida")

    return analiza_a3(R, partes, ev, vig, sondeo)


def analiza_a3(R, partes, ev, vig, sondeo):
    # ---- A3 ----
    p = partes["A3"]
    a, b = t(p["inicio"]), t(p["fin"])
    botones_ev = [e for e in ev if e["ev"] == "boton"]
    inicios = [(int(r["t_inicio_ms"]) / 1000.0, int(r["duracion_ms"]), r["com"]) for r in sondeo]
    filas = []
    for boton, nombre in (("start_button", "start"), ("stop_button", "stop")):
        for x, y in pulsaciones(vig, boton, a, b):
            reg = any(e["boton"] == nombre and x - ANTES_S <= e["_t"] <= x + VENTANA_EVENTO_S for e in botones_ev)
            dentro = sum(1 for c in inicios if x <= c[0] <= y)
            completos = sum(1 for c in inicios if x <= c[0] and c[0] + c[1] / 1000.0 <= y)
            filas.append({"presiona": x, "suelta": y, "boton": nombre, "duracion_ms": round((y - x) * 1000), "registrada": reg,
                          "ciclos_dentro": dentro, "ciclos_completos": completos})
    filas.sort(key=lambda f: f["presiona"])
    sin = []
    for f in filas:
        if f["registrada"]:
            continue
        ciclos = [c for c in inicios if f["presiona"] - 1 <= c[0] <= f["suelta"] + 1]
        cubre = None
        for c0, c1 in zip(inicios, inicios[1:]):
            if c0[0] <= f["presiona"] and c1[0] >= f["suelta"] and (c1[0] - c0[0]) >= (f["suelta"] - f["presiona"]):
                cubre = round((c1[0] - c0[0]) * 1000)
                break
        sin.append({"fila": f, "ciclos": ciclos, "hueco_ms": cubre})
    periodos = [round((c1[0] - c0[0]) * 1000) for c0, c1 in zip(inicios, inicios[1:])]
    st = [f for f in filas if f["boton"] == "start"]
    R["A3"] = {"filas": filas, "sin_evento": sin,
               "start_vistas": len(st), "start_registradas": sum(1 for f in st if f["registrada"]),
               "stop_vistas": sum(1 for f in filas if f["boton"] == "stop"),
               "stop_registradas": sum(1 for f in filas if f["boton"] == "stop" and f["registrada"]),
               "por_ciclos": sorted({(f["ciclos_dentro"], f["registrada"]): 0 for f in filas}.keys()),
               "periodo": {"n": len(periodos), "mediana": percentil(periodos, 50), "p95": percentil(periodos, 95),
                           "max": max(periodos), "ge300": sum(1 for x in periodos if x >= 300)}}
    sin_hueco = [s for s in sin if s["hueco_ms"] is None]
    if not sin:
        R["A3"]["conclusion"] = "no reproducida: todas las pulsaciones de la sesion se registraron"
    elif sin_hueco:
        R["A3"]["conclusion"] = "DEFECTO DEL CLIENTE posible: %d pulsacion(es) sin evento y sin hueco de sondeo que la cubra" % len(sin_hueco)
    else:
        R["A3"]["conclusion"] = "hueco de sondeo: cada pulsacion sin evento cae dentro de un hueco (%s ms)" % \
            ", ".join(str(s["hueco_ms"]) for s in sin)
    return R


def md(R, d):
    A1, A2, A3 = R["A1"], R["A2"], R["A3"]
    titulo = ("Sesión con Ari (paso S del cierre de la fase 4: Stop con una lectura)"
              if pathlib.Path(str(d)).name.startswith("S_") else "Sesión con Ari (paso A de la fase 4)")
    L = ["# " + titulo, "",
         "Generado con `tools/analiza_sesion_a.py %s`. Definiciones: `docs/INSTRUMENTACION_A2.md`, sección 5. Sin interpretación, "
         "salvo la conclusión de A3 que pide la orden." % d, "",
         "| Parte | Estado | Inicio | Fin |", "|---|---|---|---|"]
    for k in [x for x in ("A1", "A2", "A3") if x in R["partes"]]:
        p = R["partes"][k]
        L.append("| %s | %s | %s | %s |" % (k, p["estado"], p["inicio"], p["fin"]))
    L += eventos_caja_md(R)
    if A1 is not None:
        L += a1_a2_md(A1, A2)
    return a3_md(L, A3)


def a1_a2_md(A1, A2):
    L = []
    L += ["", "## A1. HMI desde el teléfono", "",
          "| Comprobación | Resultado |", "|---|---|",
          "| Conexiones establecidas al puerto de Node-RED desde la tailnet, distintas de %s | %s (en %d de %d muestras) |"
          % (TS_MAC, ", ".join(A1["tailnet"]) or "ninguna", A1["muestras_con_tailnet"], A1["muestras"]),
          "| `comando` marcha con origen `hmi` | %s |" % A1["marcha"],
          "| `comando` paro con origen `hmi` | %s |" % A1["paro"],
          "| `paso_caja` entre ambos | %d |" % A1["cajas"],
          "| Verificación 1 / 2 | %s / %s |" % ("pasa" if A1["ok1"] else "NO pasa", "pasa" if A1["ok2"] else "NO pasa")]
    L += ["", "## A2. Paro de emergencia con la nube", "",
          "| Comprobación | Resultado |", "|---|---|",
          "| Emergency stop visto por el vigilante (baja, sube, duración s) | %s |" % "; ".join("%s → %s (%.3f)" % x for x in A2["emergencia_vigilante"]),
          "| `paro_de_emergencia` / `emergencia_liberada` del cliente | %s / %s |" % (A2["paro_de_emergencia"], A2["emergencia_liberada"]),
          "| Latido aceptado (HTTP 200) tras el paro: registro, escritura, retraso | %s |" % (
              "%s, %s, %.3f s" % (A2["latido_paro"]["registro_id"], A2["latido_paro"]["ts_escritura"], A2["latido_paro"]["retraso_s"]) if A2["latido_paro"] else "ninguno en 2 s"),
          "| Latido aceptado tras la liberación: registro, escritura, retraso | %s |" % (
              "%s, %s, %.3f s" % (A2["latido_liberada"]["registro_id"], A2["latido_liberada"]["ts_escritura"], A2["latido_liberada"]["retraso_s"]) if A2["latido_liberada"] else "ninguno en 2 s"),
          "| Registros `caja` aceptados en la sesión / `paso_caja` | %d / %d (cajas descartadas por la emergencia: %s) |" % (A2["cajas_nube"], A2["paso_caja"], A2["descartadas"] or "ninguna"),
          "| Verificación 1 / 2 / 4 | %s / %s / %s |" % tuple("pasa" if A2[k] else "NO pasa" for k in ("ok1", "ok2", "ok4"))]
    if "base" in A2:
        for r in A2["base"]:
            L.append("| Base real, registro %s | %s (sin `caja_masa_kg`; %s), estado_linea `%s`; campos %s |" % (
                r["registro_id"], r["tipo"], "con campo `tipo`" if r["campo_tipo"] else "el registro no tiene campo `tipo`",
                r["estado_linea"], ", ".join(r["campos"])))
        L.append("| Verificación 3 | %s |" % ("pasa" if A2["ok3"] else "NO pasa"))
    return L


def a3_md(L, A3):
    L += ["", "## A3. Start repetido", "", "### Resultado 1. Pulsaciones vistas por el vigilante", "",
          "| # | Presiona (UTC) | Botón | Duración (ms) | Inicios de ciclo de sondeo durante la pulsación | Evento `boton` en 0.5 s |",
          "|---|---|---|---|---|---|"]
    for i, f in enumerate(A3["filas"], 1):
        L.append("| %d | %s | %s | %d | %d | %s |" % (i, iso(f["presiona"]), f["boton"], f["duracion_ms"], f["ciclos_dentro"],
                                                    "sí" if f["registrada"] else "**no**"))
    from collections import Counter
    stop = [f for f in A3["filas"] if f["boton"] == "stop"]
    con = [f for f in stop if f["ciclos_completos"] >= 1]
    sin = [f for f in stop if f["ciclos_completos"] == 0]
    L += ["", "Stop con al menos un ciclo de sondeo completo dentro de la pulsación (inicio y fin del ciclo entre presionar y "
          "soltar): %d, de ellas %d con evento `boton`. Stop sin ningún ciclo completo dentro: %d (%d con evento)."
          % (len(con), sum(1 for f in con if f["registrada"]), len(sin), sum(1 for f in sin if f["registrada"]))]
    for boton in ("start", "stop"):
        cb = Counter((f["ciclos_dentro"], f["registrada"]) for f in A3["filas"] if f["boton"] == boton)
        L += ["", "%s por número de inicios de ciclo dentro de la pulsación:" % boton.capitalize(), "",
              "| Inicios de ciclo dentro | Vistas | Registradas |", "|---|---|---|"]
        for n in sorted({k[0] for k in cb}):
            L.append("| %d | %d | %d |" % (n, cb[(n, True)] + cb[(n, False)], cb[(n, True)]))
    cuenta = Counter((f["ciclos_dentro"], f["registrada"]) for f in A3["filas"])
    L += ["", "Pulsaciones por número de inicios de ciclo dentro de ellas:", "",
          "| Inicios de ciclo dentro | Registradas | Sin evento |", "|---|---|---|"]
    for n in sorted({k[0] for k in cuenta}):
        L.append("| %d | %d | %d |" % (n, cuenta[(n, True)], cuenta[(n, False)]))
    tot_v, tot_r = A3["start_vistas"] + T_PASO["vistas"], A3["start_registradas"] + T_PASO["registradas"]
    L += ["", "### Resultado 2. Conteo", "", "| | Vistas | Registradas |", "|---|---|---|",
          "| Start, esta sesión | %d | %d |" % (A3["start_vistas"], A3["start_registradas"]),
          "| Stop, esta sesión | %d | %d |" % (A3["stop_vistas"], A3["stop_registradas"]),
          "| Start, paso T (11 nov) | %d | %d |" % (T_PASO["vistas"], T_PASO["registradas"]),
          "| Start, total | %d | %d |" % (tot_v, tot_r), "", "Fuente del paso T: %s." % T_PASO["fuente"],
          "", "### Resultado 3. Pulsaciones sin evento y ciclos de sondeo", ""]
    if not A3["sin_evento"]:
        L.append("Ninguna pulsación sin evento en esta sesión.")
    for s in A3["sin_evento"]:
        f = s["fila"]
        L += ["%s presionado %s, %d ms. Hueco que la cubre: %s." % (f["boton"], iso(f["presiona"]), f["duracion_ms"],
                                                                   "%d ms" % s["hueco_ms"] if s["hueco_ms"] else "ninguno"), "",
              "| Inicio del ciclo | Duración (ms) | Comunicación |", "|---|---|---|"]
        L += ["| %s | %d | %s |" % (iso(c[0]), c[1], c[2]) for c in s["ciclos"]]
        L.append("")
    P = A3["periodo"]
    L += ["", "### Resultado 4. Periodo de sondeo de toda la sesión", "",
          "| n | Mediana (ms) | p95 (ms) | Máximo (ms) | Periodos ≥ 300 ms |", "|---|---|---|---|---|",
          "| %d | %d | %d | %d | %d |" % (P["n"], P["mediana"], P["p95"], P["max"], P["ge300"]),
          "", "### Conclusión", "", A3["conclusion"] + "."]
    return "\n".join(L) + "\n"


def eventos_caja_md(R):
    L = ["", "## Eventos de cajas por parte", "",
         "Cuenta, dentro de cada parte, los eventos `caja_perdida`, `desvio_erroneo`, `caja_fantasma` y `caja_purgada` del "
         "cliente y los `paso_caja` con `rechazo_fallido` (cajas que un Stop alcanzó en el desviador). Solo se registran.", "",
         "| Parte | Eventos |", "|---|---|"]
    for k in sorted(R["eventos_caja"]):
        c = R["eventos_caja"][k]
        L.append("| %s | %s |" % (k, ", ".join("%s: %d" % kv for kv in sorted(c.items())) or "ninguno"))
    return L


def main():
    a = argparse.ArgumentParser()
    a.add_argument("carpeta")
    a.add_argument("--md")
    a.add_argument("--base", action="store_true")
    a.add_argument("--json")
    x = a.parse_args()
    R = analiza(x.carpeta, x.base)
    texto = md(R, x.carpeta)
    if x.md:
        pathlib.Path(x.md).write_text(texto, encoding="utf-8")
        print("escrito", x.md)
    else:
        print(texto)
    if x.json:
        pathlib.Path(x.json).write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    ok = R["A1"] is None or (R["A1"]["ok1"] and R["A1"]["ok2"] and R["A2"]["ok1"] and R["A2"]["ok2"] and R["A2"]["ok4"]
                             and R["A2"].get("ok3", True))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
