#!/usr/bin/env python3
"""Distribucion de masas de las corridas largas (paso L de la fase 3). Python 3.9, sin dependencias.

Definiciones: docs/INSTRUMENTACION_A2.md, seccion 4. Solo reporta: tablas, sin
interpretacion.

    # verificacion: datos del 25 oct y valores p conocidos (exit 0 si todo coincide)
    python3 tools/analiza_masas.py --verifica

    # corridas: cada directorio con a2_planta_eventos.jsonl y oraculo.json
    python3 tools/analiza_masas.py --corrida L1=datos/corridas/L1_2026-11-11 \\
        --corrida L2=datos/corridas/L2_2026-11-11 --md docs/corrida_L.md

    # un archivo de eventos con ventana (sin oraculo)
    python3 tools/analiza_masas.py --eventos datos/a2_planta_eventos.jsonl \\
        --desde 2026-10-25T01:00:00Z --hasta 2026-10-25T03:00:00Z --nombre 25oct
"""
import argparse, datetime, json, math, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import materiales as mat  # noqa: E402

NIVELES = [1.5, 2.5, 3.5, 4.0, 5.0, 7.5, 10.0]
TOL_V = 0.03
VENTANA_S = 600
OBJETIVOS_D = [0.5, 0.8, 1.0]


# ---- funcion de supervivencia de la ji cuadrada (implementacion propia) ----------------
def _gamma_inc_reg_superior(a, x):
    """Q(a, x) = Gamma(a, x) / Gamma(a): serie para x < a + 1, fraccion continua si no."""
    if x <= 0:
        return 1.0
    lg = math.lgamma(a)
    if x < a + 1:
        suma, term, n = 1.0 / a, 1.0 / a, 0
        while True:
            n += 1
            term *= x / (a + n)
            suma += term
            if abs(term) < abs(suma) * 1e-15 or n > 10000:
                break
        return 1.0 - suma * math.exp(-x + a * math.log(x) - lg)
    # Lentz modificado
    tiny = 1e-300
    b = x + 1 - a
    c, d = 1.0 / tiny, 1.0 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - lg) * h


def p_ji2(x, gl):
    return _gamma_inc_reg_superior(gl / 2.0, x / 2.0)


def homogeneidad(tabla):
    """tabla: lista de filas (conteos por categoria). Quita filas y columnas en cero."""
    filas = [f for f in tabla if sum(f) > 0]
    if not filas:
        return None
    cols = [j for j in range(len(filas[0])) if sum(f[j] for f in filas) > 0]
    filas = [[f[j] for j in cols] for f in filas]
    R, C = len(filas), len(cols)
    if R < 2 or C < 2:
        return {"x2": None, "gl": 0, "p": None, "filas": R, "columnas": C, "e_menor_5": 0}
    tf = [sum(f) for f in filas]
    tc = [sum(f[j] for f in filas) for j in range(C)]
    n = sum(tf)
    x2, chicas = 0.0, 0
    for i in range(R):
        for j in range(C):
            e = tf[i] * tc[j] / n
            chicas += e < 5
            x2 += (filas[i][j] - e) ** 2 / e
    gl = (R - 1) * (C - 1)
    return {"x2": x2, "gl": gl, "p": p_ji2(x2, gl), "filas": R, "columnas": C, "e_menor_5": chicas,
            "celdas": R * C}


# ---- lectura --------------------------------------------------------------------------
def ts(s):
    return datetime.datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S.%f%z" if "." in s
                                      else "%Y-%m-%dT%H:%M:%S%z").timestamp()


def pasos(ruta, desde=None, hasta=None):
    out = []
    for l in open(str(ruta), encoding="utf-8"):
        if '"paso_caja"' not in l:
            continue
        e = json.loads(l)
        if e.get("ev") != "paso_caja":
            continue
        if desde and e["ts_salida"] < desde:
            continue
        if hasta and e["ts_salida"] >= hasta:
            continue
        out.append(e)
    out.sort(key=lambda e: e["ts_salida"])
    return out


def nivel_de(v):
    if not isinstance(v, (int, float)):
        return None
    for n in NIVELES:
        if round(abs(v - n), 6) <= TOL_V:
            return n
    return None


def superior(v):
    """Nivel inmediato superior de una lectura fuera de nivel (igual si pasa de 10.0)."""
    return next((n for n in NIVELES if n > v), v)


# ---- analisis de una corrida ------------------------------------------------------------
def analiza(nombre, ev, oraculo=None):
    pesos = [e["peso_V"] for e in ev]
    num = [v for v in pesos if isinstance(v, (int, float))]
    r = {"nombre": nombre, "cajas": len(ev), "sin_peso": len(pesos) - len(num),
         "primera": ev[0]["ts_salida"] if ev else None, "ultima": ev[-1]["ts_salida"] if ev else None, "fuente": None}
    # 1. histograma y niveles
    hist = {}
    for v in num:
        b = min(int(v / 0.5), 20)
        hist[b] = hist.get(b, 0) + 1
    r["histograma"] = [("[%.1f, %.1f)" % (b * 0.5, b * 0.5 + 0.5), hist.get(b, 0)) for b in range(21)]
    r["por_nivel"] = {n: sum(1 for v in num if nivel_de(v) == n) for n in NIVELES}
    r["fuera"] = sum(1 for v in num if nivel_de(v) is None)
    # 2-4. con el oraculo emparejado por orden
    esp = (oraculo or {}).get("esperado") or []
    def detalle(i):
        e = ev[i]
        o = esp[i] if i < len(esp) else None
        return {"i": i, "caja": e.get("caja"), "ts": e["ts_salida"], "peso_V": e["peso_V"],
                "oraculo_V": o[0] if o else None, "var_03s": o[2] if o else None,
                "crudo_max": (o[3] if o and len(o) > 3 else None)}
    r["con_oraculo"] = bool(esp)
    r["fuera_detalle"] = [detalle(i) for i, v in enumerate(pesos) if isinstance(v, (int, float)) and nivel_de(v) is None]
    altas = [detalle(i) for i, v in enumerate(pesos) if isinstance(v, (int, float)) and v >= 8.0]
    r["altas"] = altas
    r["altas_bajo_995"] = sum(1 for a in altas if a["peso_V"] < 9.95)
    r["sat"] = [detalle(i) for i, v in enumerate(pesos) if isinstance(v, (int, float)) and v >= 9.0]
    # 5-6. ventanas y cadencia
    if ev:
        t0, t1 = ts(ev[0]["ts_salida"]), ts(ev[-1]["ts_salida"])
        r["duracion_min"] = (t1 - t0) / 60.0
        r["cadencia"] = len(ev) / r["duracion_min"] if r["duracion_min"] > 0 else None
        nv = int((t1 - t0) // VENTANA_S) + 1
        filas = [[0] * (len(NIVELES) + 1) for _ in range(nv)]
        for e in ev:
            v = e["peso_V"]
            if not isinstance(v, (int, float)):
                continue
            k = int((ts(e["ts_salida"]) - t0) // VENTANA_S)
            n = nivel_de(v)
            filas[k][NIVELES.index(n) if n is not None else len(NIVELES)] += 1
        r["ventanas"] = filas
        r["ultima_parcial_s"] = (t1 - t0) - (nv - 1) * VENTANA_S
        r["homog"] = homogeneidad(filas)
    # 7. materiales
    cfg = mat.carga_config()
    crudo = mat.recalcula(cfg, [{"peso_V": v} for v in pesos])
    subido = mat.recalcula(cfg, [{"peso_V": (superior(v) if isinstance(v, (int, float)) and nivel_de(v) is None else v)}
                                 for v in pesos])
    r["mat"] = []
    for a, b in zip(crudo["laminados"], subido["laminados"]):
        fila = {"id": a["id"], "D_crudo": a["D"], "D_superior": b["D"], "conteos_crudo": a["conteos"],
                "conteos_superior": b["conteos"]}
        for etiqueta, D in (("crudo", a["D"]), ("superior", b["D"])):
            fila["t_" + etiqueta] = {o: (o / (D / r["duracion_min"]) if D > 0 and r.get("duracion_min") else None)
                                     for o in OBJETIVOS_D}
        r["mat"].append(fila)
    return r


# ---- salida -----------------------------------------------------------------------------
def f(x, d=2):
    return "–" if x is None else ("%." + str(d) + "f") % x


def t_texto(minutos):
    if minutos is None:
        return "–"
    return "%.0f min (%.1f h)" % (minutos, minutos / 60.0)


def md(res, entre=None, titulo="Corridas L: distribución de masas"):
    L = ["# " + titulo, "",
         "Generado con `tools/analiza_masas.py`. Definiciones: `docs/INSTRUMENTACION_A2.md`, sección 4. Sin interpretación.", ""]
    L += ["## Fuentes", "", "| Corrida | Archivos | Primera caja (ts_salida) | Última caja (ts_salida) |", "|---|---|---|---|"]
    for r in res:
        L.append("| %s | `%s` | %s | %s |" % (r["nombre"], r["fuente"], r["primera"], r["ultima"]))
    L += ["", "## Resumen", "", "| Corrida | Cajas | Sin peso | Duración (min) | Cadencia (cajas/min) | Fuera de nivel | ≥ 8.0 V | ≥ 8.0 V y < 9.95 V |",
          "|---|---|---|---|---|---|---|---|"]
    for r in res:
        L.append("| %s | %d | %d | %s | %s | %d | %d | %d (%s) |" % (
            r["nombre"], r["cajas"], r["sin_peso"], f(r.get("duracion_min"), 1), f(r.get("cadencia")), r["fuera"],
            len(r["altas"]), r["altas_bajo_995"], f(r["altas_bajo_995"] / len(r["altas"]), 3) if r["altas"] else "–"))
    L += ["", "## 1. Pesos por nivel (|peso − nivel| ≤ 0.03 V)", "",
          "| Corrida | " + " | ".join("%.1f V" % n for n in NIVELES) + " | Fuera de nivel |",
          "|---|" + "---|" * (len(NIVELES) + 1)]
    for r in res:
        L.append("| %s | %s | %d |" % (r["nombre"], " | ".join(str(r["por_nivel"][n]) for n in NIVELES), r["fuera"]))
    L += ["", "### Histograma (intervalos de 0.5 V)", "", "| Intervalo (V) | " + " | ".join(r["nombre"] for r in res) + " |",
          "|---|" + "---|" * len(res)]
    for k in range(21):
        L.append("| %s | %s |" % (res[0]["histograma"][k][0], " | ".join(str(r["histograma"][k][1]) for r in res)))
    for r in res:
        L += ["", "## %s" % r["nombre"], ""]
        cab = "| # | Caja | ts_salida | Peso cliente (V) | Oráculo al soltar (V) | Variación 0.3 s (V) |"
        L += ["### 2. Lecturas fuera de nivel (%d)" % len(r["fuera_detalle"]), "", cab, "|---|---|---|---|---|---|"]
        for d in r["fuera_detalle"]:
            L.append("| %d | %s | %s | %s | %s | %s |" % (d["i"], d["caja"], d["ts"], f(d["peso_V"]), f(d["oraculo_V"]), f(d["var_03s"])))
        L += ["", "### 3. Lecturas de 8.0 V o más (%d; %d por debajo de 9.95 V)" % (len(r["altas"]), r["altas_bajo_995"]), "",
              cab, "|---|---|---|---|---|---|"]
        for d in r["altas"]:
            L.append("| %d | %s | %s | %s | %s | %s |" % (d["i"], d["caja"], d["ts"], f(d["peso_V"]), f(d["oraculo_V"]), f(d["var_03s"])))
        sat = r["sat"]
        con = [d for d in sat if d["crudo_max"] is not None]
        L += ["", "### 4. Máximo crudo del registro durante el pesaje, cajas de 9.0 V o más (%d)" % len(sat), "",
              "Llegan a 1000: %d. Rebasan 1000: %d. Sin máximo del oráculo: %d." % (
                  sum(1 for d in con if d["crudo_max"] >= 1000), sum(1 for d in con if d["crudo_max"] > 1000), len(sat) - len(con)), "",
              "| # | Caja | Peso cliente (V) | Máximo crudo |", "|---|---|---|---|"]
        for d in sat:
            L.append("| %d | %s | %s | %s |" % (d["i"], d["caja"], f(d["peso_V"]), "–" if d["crudo_max"] is None else d["crudo_max"]))
        if "ventanas" in r:
            L += ["", "### 5 y 6. Reparto por nivel en ventanas de 10 min y cadencia", "",
                  "| Ventana | " + " | ".join("%.1f V" % n for n in NIVELES) + " | Fuera | Cajas | Cajas/min |",
                  "|---|" + "---|" * (len(NIVELES) + 3)]
            for k, fila in enumerate(r["ventanas"]):
                ult = k == len(r["ventanas"]) - 1
                dur = (r["ultima_parcial_s"] if ult else VENTANA_S) / 60.0
                L.append("| %d%s | %s | %d | %s |" % (k + 1, " (parcial, %.1f min)" % dur if ult and r["ultima_parcial_s"] < VENTANA_S else "",
                                                      " | ".join(str(x) for x in fila), sum(fila), f(sum(fila) / dur if dur > 0 else None)))
            h = r["homog"]
            L += ["", "Homogeneidad entre ventanas: X² = %s, %d grados de libertad, p = %s (%d filas × %d columnas con total distinto de cero; %s celdas con E < 5)."
                  % (f(h["x2"], 3), h["gl"], f(h["p"], 4), h["filas"], h["columnas"], "%d de %d" % (h["e_menor_5"], h.get("celdas", 0)))]
        L += ["", "### 7. Capa de materiales (`tools/materiales.py`, `config/materiales.json` versión %s)" % mat.carga_config().get("version"), "",
              "| Laminado | D con pesos crudos | D con fuera de nivel al nivel superior | Pasos dentro / bajo / sobre (crudo) | Pasos dentro / bajo / sobre (superior) |",
              "|---|---|---|---|---|"]
        for m in r["mat"]:
            c, s = m["conteos_crudo"], m["conteos_superior"]
            L.append("| %s | %.8f | %.8f | %d / %d / %d | %d / %d / %d |" % (
                m["id"], m["D_crudo"], m["D_superior"], c.get("dentro", 0), c.get("bajo", 0), c.get("sobre", 0),
                s.get("dentro", 0), s.get("bajo", 0), s.get("sobre", 0)))
        L += ["", "Tiempo esperado para llegar a D (extrapolación lineal al ritmo medio de la corrida):", "",
              "| Laminado | Cálculo | " + " | ".join("D = %.1f" % o for o in OBJETIVOS_D) + " |", "|---|---|" + "---|" * len(OBJETIVOS_D)]
        for m in r["mat"]:
            for etiqueta, nombre in (("crudo", "crudo"), ("superior", "fuera de nivel al superior")):
                L.append("| %s | %s | %s |" % (m["id"], nombre, " | ".join(t_texto(m["t_" + etiqueta][o]) for o in OBJETIVOS_D)))
    if entre:
        L += ["", "## 5. Homogeneidad entre corridas", "",
              "Corridas completas como filas: X² = %s, %d grados de libertad, p = %s (%d filas × %d columnas; %d de %d celdas con E < 5)."
              % (f(entre["x2"], 3), entre["gl"], f(entre["p"], 4), entre["filas"], entre["columnas"], entre["e_menor_5"], entre.get("celdas", 0))]
    return "\n".join(L) + "\n"


def fila_total(r):
    return [r["por_nivel"][n] for n in NIVELES] + [r["fuera"]]


# ---- verificacion -----------------------------------------------------------------------
def verifica():
    ok = True
    def chk(desc, cond, det=""):
        nonlocal ok
        ok = ok and cond
        print("  %s %s%s" % ("OK   " if cond else "FALLA", desc, "" if cond else "  " + str(det)))
    print("--- valor p de la ji cuadrada (implementacion propia) ---")
    for x, gl, esp in ((11.24, 2, 0.0036), (3.841, 1, 0.050), (9.488, 4, 0.050)):
        p = p_ji2(x, gl)
        chk("X2 = %g con %d grados -> p = %.4f (esperado %.4f)" % (x, gl, p, esp), round(p, 4 if esp < 0.01 else 3) == esp, p)
    print("--- datos del 25 oct, 01:00 a 03:00 UTC ---")
    ev = pasos(RAIZ / "datos" / "a2_planta_eventos.jsonl", "2026-10-25T01:00:00Z", "2026-10-25T03:00:00Z")
    r = analiza("25oct", ev)
    chk("429 cajas (%d)" % r["cajas"], r["cajas"] == 429)
    esperado = [68, 63, 66, 63, 74, 44, 5]
    chk("por nivel %s = %s" % ([r["por_nivel"][n] for n in NIVELES], esperado), [r["por_nivel"][n] for n in NIVELES] == esperado)
    chk("46 fuera de nivel (%d)" % r["fuera"], r["fuera"] == 46)
    altas = sorted(d["peso_V"] for d in r["altas"])
    chk("lecturas >= 8.0 V: %s" % altas, altas == [8.36, 8.37, 8.72, 9.4, 9.4, 9.53, 9.67, 9.77, 10, 10, 10, 10, 10])
    # Con la configuracion version 1 esto daba 0.54952814 (docs/corrida_L.md). Desde el paso R
    # (version 2) se comprueba contra tools/materiales.py con la configuracion vigente.
    cfg = mat.carga_config()
    ref = mat.recalcula(cfg, ev)["laminados"][0]["D"]
    chk("D crudo del 0:0 igual que tools/materiales.py recalcula con config/materiales.json version %s (%.8f = %.8f)"
        % (cfg.get("version"), r["mat"][0]["D_crudo"], ref), r["mat"][0]["D_crudo"] == ref)
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verifica", action="store_true")
    ap.add_argument("--corrida", action="append", default=[], help="NOMBRE=DIR (con a2_planta_eventos.jsonl y oraculo.json)")
    ap.add_argument("--eventos")
    ap.add_argument("--desde")
    ap.add_argument("--hasta")
    ap.add_argument("--nombre", default="eventos")
    ap.add_argument("--md")
    ap.add_argument("--json")
    a = ap.parse_args()
    if a.verifica:
        ok = verifica()
        print("=== RESULTADO: %s ===" % ("coincide" if ok else "NO coincide"))
        sys.exit(0 if ok else 1)
    res = []
    for c in a.corrida:
        nombre, d = c.split("=", 1)
        d = pathlib.Path(d)
        o = json.load(open(str(d / "oraculo.json"))) if (d / "oraculo.json").exists() else None
        res.append(analiza(nombre, pasos(d / "a2_planta_eventos.jsonl"), o))
        res[-1]["fuente"] = str(d)
    if a.eventos:
        res.append(analiza(a.nombre, pasos(a.eventos, a.desde, a.hasta)))
        res[-1]["fuente"] = "%s [%s, %s)" % (a.eventos, a.desde, a.hasta)
    if not res:
        ap.error("nada que analizar")
    entre = homogeneidad([fila_total(r) for r in res]) if len(res) > 1 else None
    texto = md(res, entre)
    if a.md:
        pathlib.Path(a.md).write_text(texto, encoding="utf-8")
        print("escrito", a.md)
    else:
        print(texto)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"corridas": res, "entre": entre}, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
