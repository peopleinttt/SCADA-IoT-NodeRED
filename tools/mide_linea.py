#!/usr/bin/env python3
"""Geometria de la linea y tiempos de recorrido (paso G de la fase 4). Python 3.9, sin dependencias.

    python3 tools/mide_linea.py datos/corridas/G_2026-11-17 --md docs/corrida_G.md

Definiciones: docs/INSTRUMENTACION_A2.md, seccion 6. Lee la carpeta de la
corrida (eventos del cliente y flancos del registrador), las corridas L1, L2 y
M1 (caja_entra), el archivo de escena (posiciones de los sensores y el
emisor) y config/planta_fio.json. Escribe tablas, sin interpretacion. Para
cada tiempo: n, mediana, p5, p95 y maximo (percentil por rango mas cercano).
"""
import argparse, json, math, pathlib, re, sys
from datetime import datetime

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import limites_planta as lp  # noqa: E402

ESCENA = RAIZ / "docs" / "capturas" / "escena_sorting_by_weight_A2.factoryio"
CORRIDAS_PREVIAS = ["L1_2026-11-11", "L2_2026-11-11", "M1_2026-11-11"]
COMMIT_G = "e575375"
RAMAS = {"left": ("at_left_entry", "at_exit_left"), "forward": ("at_forward_entry", "at_exit_front"),
         "right": ("at_right_entry", "at_exit_right")}
NIVELES = [1.5, 2.5, 3.5, 4.0, 5.0, 7.5, 10.0]
NOMBRE_ESCENA = {"at_scale_entry": "At scale entry", "at_scale": "At scale", "at_scale_exit": "At scale exit",
                 "at_left_entry": "At left entry", "at_forward_entry": "At forward entry", "at_right_entry": "At right entry",
                 "at_exit_left": "At exit left", "at_exit_front": "At exit front", "at_exit_right": "At exit right"}


def t(s):
    m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)$", s)
    frac = (m.group(2) or "0")[:6].ljust(6, "0")
    return datetime.fromisoformat("%s.%s%s" % (m.group(1), frac, "+00:00" if m.group(3) == "Z" else m.group(3))).timestamp()


def jsonl(ruta):
    return [json.loads(l) for l in pathlib.Path(ruta).read_text(encoding="utf-8").splitlines() if l.strip()]


def stats(xs):
    xs = sorted(xs)
    if not xs:
        return {"n": 0}
    rango = lambda p: xs[max(1, math.ceil(p / 100.0 * len(xs))) - 1]
    return {"n": len(xs), "min": xs[0], "mediana": rango(50), "p5": rango(5), "p95": rango(95), "max": xs[-1]}


def nivel(v):
    return next((n for n in NIVELES if isinstance(v, (int, float)) and round(abs(v - n), 6) <= 0.03), None)


def escena():
    txt = ESCENA.read_text(encoding="utf-8-sig")
    pos = {}
    for obj in re.findall(r"<Object .*?</Object>", txt, re.S):
        p = re.search(r'<Proxy PrefabName="([^"]+)"', obj)
        xyz = re.search(r'<Position X="([-\d.]+)" Y="([-\d.]+)" Z="([-\d.]+)"', obj)
        for nombre, en_escena in NOMBRE_ESCENA.items():
            if 'BinaryInput Name="%s"' % en_escena in obj and xyz:
                pos[nombre] = {"prefab": p.group(1), "x": float(xyz.group(1)), "y": float(xyz.group(2)), "z": float(xyz.group(3))}
    em = re.search(r'<Emitter MinTimeToEmit="([\d.]+)" MaxTimeToEmit="([\d.]+)"', txt)
    return pos, (float(em.group(1)), float(em.group(2)))


def analiza(d):
    d = pathlib.Path(d)
    ev = jsonl(d / "a2_planta_eventos.jsonl")
    fl = [x for x in jsonl(d / "flancos.jsonl") if "senal" in x]
    # La configuracion del commit del paso G (e575375): desde el paso H del cierre de la fase 4
    # linea ya no trae distancias ni velocidad, y este reporte describe los limites de entonces.
    import subprocess
    cfg = json.loads(subprocess.check_output(["git", "show", COMMIT_G + ":config/planta_fio.json"], cwd=str(RAIZ)))
    sube = lambda s: [x["t"] for x in fl if x["senal"] == s and x["valor"] == 1]
    baja = lambda s: [x["t"] for x in fl if x["senal"] == s and x["valor"] == 0]
    sig = lambda xs, t0: next((x for x in xs if x > t0), None)
    prev = lambda xs, t0: next((x for x in reversed(xs) if x < t0), None)
    R = {"carpeta": str(d)}

    # Confirmacion: caja_pesada -> ts_salida del paso_caja de la misma caja
    pesada = {e["caja"]: t(e["ts"]) for e in ev if e["ev"] == "caja_pesada"}
    pasos = [e for e in ev if e["ev"] == "paso_caja"]
    conf = [t(e["ts_salida"]) - pesada[e["caja"]] for e in pasos if e["caja"] in pesada]
    R["confirmacion_s"] = stats(conf)
    # Fisico: at_scale_exit sube -> sensor de rama sube
    fis = {}
    for rama, (ent, sal) in RAMAS.items():
        se = sube("at_scale_exit")
        fis[rama] = stats([x - prev(se, x) for x in sube(ent) if prev(se, x) is not None])
    R["fin_bascula_a_rama_s"] = fis
    # Llegada a fin de bascula: at_scale sube -> entry_conveyor se apaga
    ec_off = baja("entry_conveyor")
    R["at_scale_a_parada_s"] = stats([sig(ec_off, x) - x for x in sube("at_scale") if sig(ec_off, x) is not None
                                      and sig(ec_off, x) - x < 5])
    # Rama: entrada sube -> salida NC baja (banda sin detenerse). En orden FIFO: la k-esima
    # caja que entra a la rama es la k-esima que sale (la escena arranca vacia y la banda no
    # adelanta cajas); la siguiente bajada de la salida puede ser de la caja anterior.
    rama = {}
    for r, (ent, sal) in RAMAS.items():
        s_ent = sube(ent)
        b_sal = [x for x in baja(sal) if s_ent and x > s_ent[0]]
        rama[r] = stats([b - a for a, b in zip(s_ent, b_sal)])
    R["rama_s"] = rama
    # Pulso del sensor de rama por tipo de pieza (nivel del paso_caja que confirma)
    pulso = {}
    for e in pasos:
        ent = RAMAS[e["destino"]][0]
        ts = t(e["ts_salida"])
        s0 = min(sube(ent), key=lambda x: abs(x - ts), default=None)
        if s0 is None or abs(s0 - ts) > 0.3:
            continue
        b = sig(baja(ent), s0)
        if b is None:
            continue
        pulso.setdefault(str(nivel(e["peso_V"])), []).append(b - s0)
    R["pulso_rama_s"] = {k: stats(v) for k, v in sorted(pulso.items())}
    # Intervalo entre caja_entra consecutivos
    def intervalos(evs):
        ts = sorted(t(e["ts"]) for e in evs if e["ev"] == "caja_entra")
        return [b - a for a, b in zip(ts, ts[1:])]
    R["caja_entra_s"] = {"G": stats(intervalos(ev))}
    for c in CORRIDAS_PREVIAS:
        ruta = RAIZ / "datos" / "corridas" / c / "a2_planta_eventos.jsonl"
        if ruta.exists():
            R["caja_entra_s"][c.split("_")[0]] = stats(intervalos(jsonl(ruta)))
    pos, emisor = escena()
    R["posiciones"] = pos
    R["emisor_s"] = {"MinTimeToEmit": emisor[0], "MaxTimeToEmit": emisor[1]}
    dist = lambda a, b: math.hypot(pos[a]["x"] - pos[b]["x"], pos[a]["z"] - pos[b]["z"])
    R["distancias_unidades_escena"] = {
        "at_scale_entry -> at_scale_exit": dist("at_scale_entry", "at_scale_exit"),
        **{"at_scale_exit -> %s" % RAMAS[r][0]: dist("at_scale_exit", RAMAS[r][0]) for r in RAMAS},
        **{"%s -> %s" % RAMAS[r]: dist(*RAMAS[r]) for r in RAMAS}}
    # Limites con la configuracion vigente
    L = cfg["linea"]
    t_ef_ms, origen = lp.t_efectivo(cfg, cfg["sondeo_ms"], cfg["rtt_previsto_ms"], cfg["refresco_ms"],
                                     cfg["medido"] if lp.medido_vale(cfg, cfg["sondeo_ms"]) else None)
    R["t_ef_ms"], R["t_ef_origen"] = t_ef_ms, origen
    lim_conf = 1.5 * L["fin_bascula_a_confirmacion_m"] / L["velocidad_fija_m_s"] + \
        (cfg["lecturas_para_cambio"] + 1) * t_ef_ms / 1000.0 + cfg["rtt_previsto_ms"] / 1000.0
    lim_fin = 1.5 * L["entrada_a_fin_bascula_m"] / L["velocidad_fija_m_s"] + 3 * t_ef_ms / 1000.0
    R["limites"] = [
        {"limite": "timeout_confirmacion_s", "valor_s": lim_conf, "max_observado_s": R["confirmacion_s"].get("max"),
         "tramo": "caja_pesada -> confirmacion de rama"},
        {"limite": "no_llego_a_fin_bascula", "valor_s": lim_fin, "max_observado_s": R["at_scale_a_parada_s"].get("max"),
         "tramo": "at_scale sube -> entry_conveyor se apaga (lo mas que corre ese reloj con pesaje detenido)"}]
    for x in R["limites"]:
        x["margen_s"] = None if x["max_observado_s"] is None else x["valor_s"] - x["max_observado_s"]
        x["cumple"] = x["margen_s"] is not None and x["margen_s"] > 0
    R["linea"] = {k: L[k] for k in ("velocidad_fija_m_s", "intervalo_emision_min_s", "largo_caja_m",
                                     "entrada_a_fin_bascula_m", "fin_bascula_a_confirmacion_m")}
    R["n_paso_caja"] = len(pasos)
    return R


def f3(x):
    return "–" if x is None else "%.3f" % x


def fila(nombre, s):
    if not s.get("n"):
        return "| %s | 0 | – | – | – | – |" % nombre
    return "| %s | %d | %s | %s | %s | %s |" % (nombre, s["n"], f3(s["mediana"]), f3(s["p5"]), f3(s["p95"]), f3(s["max"]))


def md(R):
    cab = ["| Tiempo (s) | n | Mediana | p5 | p95 | Máximo |", "|---|---|---|---|---|---|"]
    L = ["# Corrida G: geometría de la línea y tiempos de recorrido", "",
         "Generado con `tools/mide_linea.py %s`. Definiciones: `docs/INSTRUMENTACION_A2.md`, sección 6. Sin interpretación." % R["carpeta"],
         "", "Cajas (`paso_caja`) en la corrida: %d." % R["n_paso_caja"], "",
         "## 1. Tramos de los límites del cliente", ""] + cab
    L.append(fila("`caja_pesada` → confirmación de rama (límite `timeout_confirmacion_s`)", R["confirmacion_s"]))
    L.append(fila("`at_scale` sube → `entry_conveyor` se apaga (límite `no_llego_a_fin_bascula`)", R["at_scale_a_parada_s"]))
    L += ["", "| Límite | Valor con `linea` (s) | Máximo observado (s) | Margen (s) | Mayor que el máximo |", "|---|---|---|---|---|"]
    for x in R["limites"]:
        L.append("| `%s` | %s | %s | %s | %s |" % (x["limite"], f3(x["valor_s"]), f3(x["max_observado_s"]), f3(x["margen_s"]),
                                                  "sí" if x["cumple"] else "**no**"))
    L.append("")
    L.append("T_ef usado: %s ms (%s)." % (R["t_ef_ms"], R["t_ef_origen"]))
    L += ["", "## 2. Recorridos sin detenerse", ""] + cab
    for r, s in R["fin_bascula_a_rama_s"].items():
        L.append(fila("`at_scale_exit` sube → `%s` sube" % RAMAS[r][0], s))
    for r, s in R["rama_s"].items():
        L.append(fila("`%s` sube → `%s` baja (banda de la rama)" % RAMAS[r], s))
    L += ["", "## 3. Pulso del sensor de rama por tipo de pieza (nivel de peso del `paso_caja`)", ""] + cab
    for k, s in R["pulso_rama_s"].items():
        L.append(fila("nivel %s V" % k if k != "None" else "fuera de nivel", s))
    L += ["", "## 4. Intervalo entre `caja_entra` consecutivos", "",
          "| Tiempo (s) | n | Mínimo | Mediana | p5 | p95 | Máximo |", "|---|---|---|---|---|---|---|"]
    for k, s in R["caja_entra_s"].items():
        L.append("| corrida %s | %d | %s | %s | %s | %s | %s |" % (k, s["n"], f3(s["min"]), f3(s["mediana"]), f3(s["p5"]),
                                                              f3(s["p95"]), f3(s["max"])))
    L += ["", "Emisor en el archivo de escena: `MinTimeToEmit` = %s s, `MaxTimeToEmit` = %s s." %
          (R["emisor_s"]["MinTimeToEmit"], R["emisor_s"]["MaxTimeToEmit"]),
          "", "## 5. Posiciones de los sensores en el archivo de escena (unidades de la escena)", "",
          "| Sensor | Pieza | X | Y | Z |", "|---|---|---|---|---|"]
    for n, p in R["posiciones"].items():
        L.append("| `%s` | %s | %g | %g | %g |" % (n, p["prefab"], p["x"], p["y"], p["z"]))
    L += ["", "| Par de sensores | Distancia en el plano X-Z (unidades de la escena) |", "|---|---|"]
    for k, v in R["distancias_unidades_escena"].items():
        L.append("| %s | %.1f |" % (k, v))
    L += ["", "## 6. Valores de `linea` en `config/planta_fio.json` al generar este reporte", "",
          "| Clave | Valor |", "|---|---|"]
    for k, v in R["linea"].items():
        L.append("| `%s` | %s |" % (k, v))
    return "\n".join(L) + "\n"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("carpeta")
    a.add_argument("--md")
    a.add_argument("--json")
    x = a.parse_args()
    R = analiza(x.carpeta)
    texto = md(R)
    if x.md:
        pathlib.Path(x.md).write_text(texto, encoding="utf-8")
        print("escrito", x.md)
    else:
        print(texto)
    if x.json:
        pathlib.Path(x.json).write_text(json.dumps(R, indent=1), encoding="utf-8")
    sys.exit(0 if all(l["cumple"] for l in R["limites"]) else 1)


if __name__ == "__main__":
    main()
