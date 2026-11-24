#!/usr/bin/env python3
"""Tramos de recorrido medidos con eventos del cliente (paso H del cierre de la fase 4). Python 3.9.

    python3 tools/mide_tramos.py --md docs/corrida_H.md [--json salida.json]

Definiciones: docs/INSTRUMENTACION_A2.md, seccion 7. Lee a2_planta_eventos.jsonl de
las corridas sin paros intermedios (L1, L2, M1, G, I) y reporta, por corrida y en
conjunto, n, mediana, p95 y maximo de los dos tramos, el tiempo medido (maximo), los
limites con la formula nueva y los de config/planta_fio.json, y el margen. Sin
interpretacion.
"""
import argparse, json, math, pathlib, re, sys
from datetime import datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import limites_planta as lp  # noqa: E402

CORRIDAS = [("L1", "L1_2026-11-11"), ("L2", "L2_2026-11-11"), ("M1", "M1_2026-11-11"), ("G", "G_2026-11-17"),
            ("I", "I_2026-11-17")]


def t(s):
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)$", s)
    frac = (m.group(2) or "0")[:6].ljust(6, "0")
    return datetime.fromisoformat("%s.%s%s" % (m.group(1), frac, "+00:00" if m.group(3) == "Z" else m.group(3))).timestamp()


def stats(xs):
    xs = sorted(xs)
    if not xs:
        return {"n": 0}
    r = lambda p: xs[max(1, math.ceil(p / 100.0 * len(xs))) - 1]
    return {"n": len(xs), "mediana": r(50), "p95": r(95), "max": xs[-1]}


def tramos(ruta):
    pesada, entra, parada, conf, previo = {}, {}, {}, [], []
    for l in open(str(ruta), encoding="utf-8"):
        e = json.loads(l)
        ev = e.get("ev")
        if ev == "caja_pesada":
            pesada[e["caja"]] = t(e["ts"])
        elif ev == "paso_caja" and e.get("caja") in pesada:
            conf.append((e["caja"], t(e["ts_salida"]) - pesada[e["caja"]]))
        elif ev == "caja_entra":
            entra[e["caja"]] = t(e["ts_entrada"])
        elif ev == "escritura" and e.get("etiqueta") == "entry_conveyor" and e.get("valor") is False \
                and e.get("motivo") == "pesaje" and e.get("caja") in entra and e["caja"] not in parada:
            parada[e["caja"]] = t(e["ts"])
            previo.append((e["caja"], parada[e["caja"]] - entra[e["caja"]]))
    return conf, previo


def analiza():
    cfg = json.loads((RAIZ / "config" / "planta_fio.json").read_text(encoding="utf-8"))
    R = {"corridas": {}}
    todo_c, todo_p = [], []
    for nombre, d in CORRIDAS:
        conf, previo = tramos(RAIZ / "datos" / "corridas" / d / "a2_planta_eventos.jsonl")
        R["corridas"][nombre] = {"carpeta": "datos/corridas/" + d, "confirmacion": stats([x for _, x in conf]),
                                 "previo": stats([x for _, x in previo]),
                                 "max_conf_caja": max(conf, key=lambda c: c[1])[0] if conf else None,
                                 "max_prev_caja": max(previo, key=lambda c: c[1])[0] if previo else None}
        todo_c += [(nombre, c, x) for c, x in conf]
        todo_p += [(nombre, c, x) for c, x in previo]
    R["conjunto"] = {"confirmacion": stats([x for *_, x in todo_c]), "previo": stats([x for *_, x in todo_p])}
    mc, mp = max(todo_c, key=lambda z: z[2]), max(todo_p, key=lambda z: z[2])
    R["tiempo_medido"] = {"t_pesada_a_confirmacion_s": round(mc[2], 3), "donde_conf": "%s caja %s" % (mc[0], mc[1]),
                          "t_entrada_a_parada_s": round(mp[2], 3), "donde_prev": "%s caja %s" % (mp[0], mp[1])}
    t_ef, origen = lp.t_efectivo(cfg, cfg["sondeo_ms"], cfg["rtt_previsto_ms"], cfg["refresco_ms"],
                                 lp.medido_vale(cfg, cfg["sondeo_ms"]))
    N, rtt, com = cfg["lecturas_para_cambio"], cfg["rtt_previsto_ms"] / 1000.0, cfg["comunicacion_timeout_ms"] / 1000.0
    tm = R["tiempo_medido"]
    R["t_ef_ms"], R["t_ef_origen"], R["rtt_s"], R["com_s"] = t_ef, origen, rtt, com
    R["limites"] = {"confirmacion": 1.5 * tm["t_pesada_a_confirmacion_s"] + (N + 1) * t_ef / 1000.0 + rtt + com,
                    "previo": 1.5 * tm["t_entrada_a_parada_s"] + 3 * t_ef / 1000.0 + com}
    R["margen"] = {k: R["limites"][k] - R["conjunto"][k]["max"] for k in ("confirmacion", "previo")}
    R["supera"] = {"confirmacion": sum(1 for *_, x in todo_c if x > R["limites"]["confirmacion"]),
                   "previo": sum(1 for *_, x in todo_p if x > R["limites"]["previo"])}
    return R


def f3(x):
    return "–" if x is None else "%.3f" % x


def md(R):
    L = ["# Tramos de recorrido con eventos del cliente (paso H)", "",
         "Generado con `tools/mide_tramos.py`. Definiciones: `docs/INSTRUMENTACION_A2.md`, sección 7. Sin interpretación.", ""]
    for tramo, titulo in (("confirmacion", "Tramo de confirmación: `caja_pesada` → `ts_salida` del `paso_caja`"),
                          ("previo", "Tramo previo al pesaje: `ts_entrada` de `caja_entra` → escritura que apaga `entry_conveyor` por pesaje")):
        L += ["## " + titulo, "", "| Corrida | n | Mediana (s) | p95 (s) | Máximo (s) |", "|---|---|---|---|---|"]
        for k, c in R["corridas"].items():
            s = c[tramo]
            L.append("| %s | %d | %s | %s | %s |" % (k, s["n"], f3(s.get("mediana")), f3(s.get("p95")), f3(s.get("max"))))
        s = R["conjunto"][tramo]
        L.append("| **conjunto** | %d | %s | %s | %s |" % (s["n"], f3(s["mediana"]), f3(s["p95"]), f3(s["max"])))
        L.append("")
    tm = R["tiempo_medido"]
    L += ["## Tiempos medidos y límites", "",
          "| Tramo | Tiempo medido (máximo, s) | Dónde | Límite nuevo (s) | Margen sobre el máximo (s) | Cajas por encima del límite |",
          "|---|---|---|---|---|---|",
          "| confirmación | %s | %s | %s | %s | %d |" % (f3(tm["t_pesada_a_confirmacion_s"]), tm["donde_conf"], f3(R["limites"]["confirmacion"]),
                                                     f3(R["margen"]["confirmacion"]), R["supera"]["confirmacion"]),
          "| previo al pesaje | %s | %s | %s | %s | %d |" % (f3(tm["t_entrada_a_parada_s"]), tm["donde_prev"], f3(R["limites"]["previo"]),
                                                         f3(R["margen"]["previo"]), R["supera"]["previo"]),
          "", "T_ef %s ms (%s), rtt %.3f s, comunicacion_timeout %.3f s." % (R["t_ef_ms"], R["t_ef_origen"], R["rtt_s"], R["com_s"])]
    return "\n".join(L) + "\n"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--md")
    a.add_argument("--json")
    x = a.parse_args()
    R = analiza()
    texto = md(R)
    if x.md:
        pathlib.Path(x.md).write_text(texto, encoding="utf-8")
        print("escrito", x.md)
    else:
        print(texto)
    if x.json:
        pathlib.Path(x.json).write_text(json.dumps(R, indent=1), encoding="utf-8")
    sys.exit(0 if R["supera"]["confirmacion"] == 0 and R["supera"]["previo"] == 0 else 1)


if __name__ == "__main__":
    main()
