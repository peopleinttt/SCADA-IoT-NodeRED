#!/usr/bin/env python3
"""Capa de materiales contra la escena (paso M3 de la fase 3). Python 3.9, sin dependencias.

    python3 tools/corrida_materiales.py --corrida L1=datos/corridas/L1_2026-11-11 \\
        --corrida L2=datos/corridas/L2_2026-11-11 --corrida M1=datos/corridas/M1_2026-11-11 \\
        --md docs/corrida_materiales.md [--verifica-vivo M1]

Por corrida recalcula con tools/materiales.py y config/materiales.json (version
2) sobre los paso_caja de a2_planta_eventos.jsonl y reporta, por laminado: D
final, pasos por region, lecturas ajustadas, linea de tiempo de D cada 50
pasos, paso / caja / instante de cada umbral, relacion entre los D finales,
aporte a D de los pasos con peso_modelo_V de 7.5 V y del resto, pasos con
sigma_max >= sigma_uts y, para las corridas de L, el D de la version 1 tomado
de docs/corrida_L.md. Tablas, sin interpretacion.

--verifica-vivo NOMBRE: para esa corrida (capa encendida en vivo) compara el
archivo de verdad con el recalculo (rel < 1e-9 en cada paso), D no decrece,
los pasos sobre no cambian D, y la HMI (hmi_materiales.jsonl del observador)
mostro cada nivel en el paso que predice el recalculo. Exit = fallas.
"""
import argparse, json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import materiales as mt  # noqa: E402

UMBRALES = [("preventiva", 0.5), ("critica", 0.8), ("falla", 1.0)]
CADA = 50


def rel(a, b):
    return 0.0 if a == b else abs(a - b) / max(abs(a), abs(b))


def eventos(d):
    return mt.pasos_caja(str(pathlib.Path(d) / "a2_planta_eventos.jsonl"), "0", "9")


def recalcula(cfg, evs):
    """Paso a paso: registros por laminado con lo necesario para el reporte."""
    A = mt.Acumulador(cfg)
    filas = []                      # por paso: (evento, [resultado por laminado] o None)
    for e in evs:
        r = A.paso(e.get("peso_V"))
        filas.append((e, r))
    return A, filas


def d_v1(nombre):
    """D final de la version 1 en docs/corrida_L.md (tabla 7 de la seccion de la corrida)."""
    ruta = RAIZ / "docs" / "corrida_L.md"
    if not ruta.exists():
        return {}
    t = ruta.read_text(encoding="utf-8")
    m = re.search(r"\n## %s\n(.*?)(\n## |\Z)" % re.escape(nombre), t, re.S)
    if not m:
        return {}
    sec = m.group(1).split("### 7.", 1)
    if len(sec) < 2:
        return {}
    out = {}
    for l in sec[1].splitlines():
        mm = re.match(r"\| (\S+) \| ([0-9.]+) \| ([0-9.]+) \|", l)
        if mm:
            out[mm.group(1)] = float(mm.group(2))
    return out


def analiza(nombre, d, cfg):
    evs = eventos(d)
    A, filas = recalcula(cfg, evs)
    res = {"nombre": nombre, "dir": str(d), "pasos": A.pasos, "sin_peso": A.sin_peso, "ajustados": A.ajustados,
           "lam": [], "v1": d_v1(nombre)}
    for i, L in enumerate(cfg["laminados"]):
        serie, cruces, aporte75, aporte_resto, uts = [], {}, 0.0, 0.0, 0
        for k, (e, r) in enumerate(filas, 1):
            if r is None:
                continue
            x = r[i]
            if x["peso_modelo_V"] == 7.5:
                aporte75 += x["dD"]
            else:
                aporte_resto += x["dD"]
            if x["sigma_max"] >= L["sigma_uts_MPa"]:
                uts += 1
            for nv, u in UMBRALES:
                if nv not in cruces and x["D"] >= u:
                    cruces[nv] = (k, e.get("caja"), e.get("ts_salida"))
            if k % CADA == 0:
                serie.append((k, x["D"]))
        S = A.lam[i]
        if not serie or serie[-1][0] != A.pasos:
            serie.append((A.pasos, S["D"]))
        res["lam"].append({"id": L["id"], "D": S["D"], "conteos": S["conteos"], "cruces": cruces, "serie": serie,
                           "aporte75": aporte75, "aporte_resto": aporte_resto, "uts": uts,
                           "sigma_uts": L["sigma_uts_MPa"]})
    return res, filas


def verifica_vivo(nombre, d, cfg, filas):
    ok = {"n": 0, "f": 0}
    def chk(desc, cond, det=""):
        ok["n" if cond else "f"] += 1
        print("  %s %s%s" % ("OK   " if cond else "FALLA", desc, "" if cond else "  " + str(det)[:400]))
    d = pathlib.Path(d)
    verdad = [json.loads(l) for l in (d / "a2_materiales_verdad.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    piezas = [L["pieza"] for L in cfg["laminados"]]
    por = {(v["paso"], v["pieza"]): v for v in verdad}
    peor, faltan, campos_mal = 0.0, [], []
    for k, (e, r) in enumerate(filas, 1):
        if r is None:
            continue
        for i, p in enumerate(piezas):
            v = por.get((k, p))
            if v is None:
                faltan.append((k, p))
                continue
            peor = max(peor, rel(v["D"], r[i]["D"]))
            if v["region"] != r[i]["region"] or (v["peso_modelo_V"], v["ajustado"]) != (r[i]["peso_modelo_V"], r[i]["ajustado"]) \
                    or v.get("caja") != e.get("caja"):
                campos_mal.append((k, p, v["region"], r[i]["region"]))
    chk("%s: la verdad coincide con el recalculo paso a paso (%d lineas; peor diferencia relativa de D %.1e < 1e-9; "
        "region, peso_modelo_V, ajustado y caja iguales)" % (nombre, len(verdad), peor),
        not faltan and not campos_mal and peor < 1e-9 and len(verdad) == len(piezas) * sum(1 for _, r in filas if r),
        (faltan[:3], campos_mal[:3]))
    decrece, sobre_cambia = [], []
    for p in piezas:
        filas_p = sorted((v for v in verdad if v["pieza"] == p), key=lambda v: v["paso"])
        previo = 0.0
        for v in filas_p:
            if v["D"] < previo:
                decrece.append((p, v["paso"]))
            if v["region"] == "sobre" and (v["dD"] != 0 or v["D"] != previo):
                sobre_cambia.append((p, v["paso"]))
            previo = v["D"]
    chk("%s: D no decrece en ningun laminado" % nombre, not decrece, decrece[:3])
    n_sobre = sum(1 for v in verdad if v["region"] == "sobre")
    chk("%s: los %d pasos sobre el intervalo no cambian D" % (nombre, n_sobre), not sobre_cambia, sobre_cambia[:3])
    hmi = d / "hmi_materiales.jsonl"
    if not hmi.exists():
        chk("%s: hay registro de la HMI (hmi_materiales.jsonl)" % nombre, False)
        return ok["f"]
    tarjetas = [json.loads(l)["tarjeta"] for l in hmi.read_text(encoding="utf-8").splitlines() if l.strip()]
    A = mt.Acumulador(cfg)
    for e, _ in filas:
        A.paso(e.get("peso_V"))
    etiqueta = {"preventiva": "preventive", "critica": "critical", "falla": "failure"}
    for i, L in enumerate(cfg["laminados"]):
        esperado = [(etiqueta[nv], A.lam[i]["cruces"][nv]) for nv, _ in UMBRALES if nv in A.lam[i]["cruces"]]
        ultima = [t for t in tarjetas if t.get("rods") and len(t["rods"]) > i]
        cambios = [(c["level"], c["step"]) for c in (ultima[-1]["rods"][i]["levelChanges"] if ultima else [])]
        vistos = []
        for t in ultima:
            lab = t["rods"][i]["levelLabel"]
            if not vistos or vistos[-1] != lab:
                vistos.append(lab)
        chk("%s, laminado %s: la HMI mostro %s; cambios de nivel en la tarjeta %s = recalculo %s"
            % (nombre, L["id"], vistos, cambios, esperado),
            cambios == esperado and [v for v in vistos if v != "normal"] == [x[0] for x in esperado], (cambios, esperado, vistos))
    return ok["f"]


def f8(x):
    return "%.8f" % x


def md(res):
    L = ["# Capa de materiales contra la escena (paso M3)", "",
         "Generado con `tools/corrida_materiales.py` con `config/materiales.json` versión 2 (`docs/ORDEN_A2_FASE_3_CIERRE.md`). "
         "L1 y L2 son el recálculo de las corridas del paso L sobre sus `paso_caja`; M1 es la corrida en vivo con la capa encendida. "
         "Sin interpretación.", "", "## Fuentes", "", "| Corrida | Archivos | Pasos | Sin peso | Lecturas que el ajuste cambió |",
         "|---|---|---|---|---|"]
    for r in res:
        L.append("| %s | `%s` | %d | %d | %d |" % (r["nombre"], r["dir"], r["pasos"], r["sin_peso"], r["ajustados"]))
    L += ["", "## 1. D final y pasos por región", "",
          "| Corrida | Laminado | D final | Dentro | Por debajo | Por encima | Lecturas ajustadas |", "|---|---|---|---|---|---|---|"]
    for r in res:
        for l in r["lam"]:
            c = l["conteos"]
            L.append("| %s | %s | %s | %d | %d | %d | %d |" % (r["nombre"], l["id"], f8(l["D"]), c["dentro"], c["bajo"], c["sobre"], r["ajustados"]))
    L += ["", "## 2. Línea de tiempo de D (cada %d pasos)" % CADA, ""]
    for r in res:
        ids = [l["id"] for l in r["lam"]]
        L += ["### %s" % r["nombre"], "", "| Paso | " + " | ".join("D %s" % i for i in ids) + " |", "|---|" + "---|" * len(ids)]
        for k in range(len(r["lam"][0]["serie"])):
            L.append("| %d | %s |" % (r["lam"][0]["serie"][k][0], " | ".join(f8(l["serie"][k][1]) for l in r["lam"])))
        L.append("")
    L += ["## 3. Cruce de umbrales", "", "| Corrida | Laminado | Umbral | Paso | Caja | Instante (ts_salida) |", "|---|---|---|---|---|---|"]
    for r in res:
        for l in r["lam"]:
            for nv, u in UMBRALES:
                c = l["cruces"].get(nv)
                L.append("| %s | %s | %s (D = %.1f) | %s | %s | %s |" % (r["nombre"], l["id"], nv, u, *(c if c else ("no cruza", "–", "–"))))
    L += ["", "## 4. Relación entre los D finales", "", "| Corrida | D 0:0 / D 9:1 |", "|---|---|"]
    for r in res:
        a, b = r["lam"][0]["D"], r["lam"][1]["D"]
        L.append("| %s | %s |" % (r["nombre"], "%.4f" % (a / b) if b else "–"))
    L += ["", "## 5. Aporte a D por peso del modelo", "",
          "| Corrida | Laminado | Pasos con peso_modelo_V = 7.5 V | Resto de los pasos | D final |", "|---|---|---|---|---|"]
    for r in res:
        for l in r["lam"]:
            L.append("| %s | %s | %s | %s | %s |" % (r["nombre"], l["id"], f8(l["aporte75"]), f8(l["aporte_resto"]), f8(l["D"])))
    L += ["", "## 6. Pasos con esfuerzo máximo ≥ resistencia a tensión del laminado", "",
          "| Corrida | Laminado | sigma_uts (MPa) | Pasos con sigma_max ≥ sigma_uts |", "|---|---|---|---|"]
    for r in res:
        for l in r["lam"]:
            L.append("| %s | %s | %.1f | %d |" % (r["nombre"], l["id"], l["sigma_uts"], l["uts"]))
    L += ["", "## 7. D de la configuración versión 1 sobre los mismos pasos (de `docs/corrida_L.md`)", "",
          "| Corrida | Laminado | D versión 1 | D versión 2 |", "|---|---|---|---|"]
    for r in res:
        if not r["v1"]:
            continue
        for l in r["lam"]:
            v = r["v1"].get(l["id"])
            L.append("| %s | %s | %s | %s |" % (r["nombre"], l["id"], f8(v) if v is not None else "–", f8(l["D"])))
    return "\n".join(L) + "\n"


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--corrida", action="append", default=[], help="NOMBRE=DIR")
    a.add_argument("--md")
    a.add_argument("--verifica-vivo", action="append", default=[])
    x = a.parse_args()
    cfg = mt.carga_config()
    v = mt.valida(cfg)
    if not v["ok"]:
        sys.exit("config/materiales.json invalida: %s" % [e["codigo"] for e in v["errores"]])
    res, fallas = [], 0
    for c in x.corrida:
        nombre, d = c.split("=", 1)
        r, filas = analiza(nombre, d, cfg)
        res.append(r)
        if nombre in x.verifica_vivo:
            print("--- %s: verdad en vivo contra el recalculo y la HMI ---" % nombre)
            fallas += verifica_vivo(nombre, d, cfg, filas)
    if x.md:
        pathlib.Path(x.md).write_text(md(res), encoding="utf-8")
        print("escrito", x.md)
    for r in res:
        print("%s: %d pasos, %d ajustados; %s" % (r["nombre"], r["pasos"], r["ajustados"], "; ".join(
            "%s D=%.8f %s cruces %s uts %d" % (l["id"], l["D"], l["conteos"], {k: v[0] for k, v in l["cruces"].items()}, l["uts"])
            for l in r["lam"])))
    if x.verifica_vivo:
        print("=== RESULTADO: %d fallas ===" % fallas)
    sys.exit(fallas)


if __name__ == "__main__":
    main()
