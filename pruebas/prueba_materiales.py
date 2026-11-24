#!/usr/bin/env python3
"""Capa de materiales (pasos M1 y M2 de la fase 3). Python 3.9.

    /usr/bin/python3 pruebas/prueba_materiales.py modelo     (M1: sin Node-RED, ~10 s)
    /usr/bin/python3 pruebas/prueba_materiales.py flujo      (M2: Node-RED con el sustituto, ~8 min)
    /usr/bin/python3 pruebas/prueba_materiales.py todo       (las dos)

El modelo en JavaScript es node-red/funciones/39_mat_modelo.js, ejecutado por
pruebas/arnes_materiales.js (el mismo archivo que va en el flujo). El segundo
camino es tools/materiales.py. Desde el paso R (configuracion version 2) los
valores esperados son los del Anexo B de docs/ORDEN_A2_FASE_3_CIERRE.md; no se
ajustan para que la prueba pase.

Codigo de salida = numero de comprobaciones fallidas.
"""
import copy, json, math, os, pathlib, random, subprocess, sys, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import materiales as mt  # noqa: E402

CFG = mt.carga_config()
EVENTOS = RAIZ / "datos" / "a2_planta_eventos.jsonl"
resultado = {"ok": 0, "falla": 0}
NODE_ENV = dict(os.environ, PATH="/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:" + os.environ.get("PATH", ""))


def verifica(desc, condicion, detalle=""):
    if condicion:
        resultado["ok"] += 1
        print("  OK    %s" % desc)
    else:
        resultado["falla"] += 1
        print("  FALLA %s %s" % (desc, detalle))


def js(peticiones):
    r = subprocess.run(["node", str(RAIZ / "pruebas" / "arnes_materiales.js")], input=json.dumps(peticiones),
                       capture_output=True, text=True, env=NODE_ENV, timeout=300)
    if r.returncode != 0:
        raise RuntimeError("arnes: " + r.stderr[-800:])
    out = json.loads(r.stdout)
    if out["avisos"]:
        print("  aviso del nodo:", out["avisos"][:3])
    return out["respuestas"]


def rel(a, b):
    if a == b:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b))


# ---- Anexo B de docs/ORDEN_A2_FASE_3_CIERRE.md (configuracion version 2) -----------------
# peso_V, peso_modelo_V, ajustado, sigma_max, (region, N_ajuste, N_usado, dD) para 0:0 y para 9:1
_B = lambda: ("bajo", None, None, 0)
_S = lambda: ("sobre", None, None, 0)
ANEXO_B = [
    (7.50, 7.50, False, 930.0000, ("dentro", 26737.4818, 26737.4818, 0.01309024), ("dentro", 6739167.3880, 1000000.0, 0.00035000)),
    (7.49, 7.50, True, 930.0000, ("dentro", 26737.4818, 26737.4818, 0.01309024), ("dentro", 6739167.3880, 1000000.0, 0.00035000)),
    (7.47, 7.50, True, 930.0000, ("dentro", 26737.4818, 26737.4818, 0.01309024), ("dentro", 6739167.3880, 1000000.0, 0.00035000)),
    (7.53, 7.50, True, 930.0000, ("dentro", 26737.4818, 26737.4818, 0.01309024), ("dentro", 6739167.3880, 1000000.0, 0.00035000)),
    (7.46, 7.46, False, 925.5360, ("dentro", 33622.2535, 33622.2535, 0.01040977), _B()),
    (7.54, 7.54, False, 934.4640, _S(), ("dentro", 4786978.7674, 1000000.0, 0.00035000)),
    (6.75, 6.75, False, 846.3000, ("dentro", 2385230.7033, 1000000.0, 0.00035000), _B()),
    (6.74, 6.74, False, 845.1840, _B(), _B()),
    (5.00, 5.00, False, 651.0000, _B(), _B()),
    (4.97, 5.00, True, 651.0000, _B(), _B()),
    (5.04, 5.04, False, 655.4640, _B(), _B()),
    (8.36, 8.36, False, 1025.9760, _S(), ("dentro", 6051.6510, 6051.6510, 0.05783546)),
    (8.48, 8.48, False, 1039.3680, _S(), ("dentro", 2396.5040, 2396.5040, 0.14604607)),
    (8.49, 8.49, False, 1040.4840, _S(), _S()),
    (9.27, 9.27, False, 1127.5320, _S(), _S()),
    (9.28, 9.28, False, 1128.6480, _S(), _S()),
    (10.00, 10.00, False, 1209.0000, _S(), _S()),
]
MIXTA = [7.50, 7.49, 7.47, 7.46, 7.53, 7.54, 5.00, 6.75, 6.74, 8.36, 8.48, 8.49, 9.29, 10.00, 7.50]
# Tablas de rigidez sin cambio entre las versiones 1 y 2: d(D) del Anexo B de docs/ORDEN_A2_FASE_3.md
RIGIDEZ = {0: [(0.0935, 0.043235), (0.25, 0.068826), (0.5, 0.084531), (0.8, 0.102426), (0.95, 0.112224),
               (1.0, 0.135100), (1.2, 0.135100)],
           1: [(0.025, 0.014467), (0.25, 0.018743), (0.5, 0.027694), (0.8, 0.036959), (1.0, 0.043900), (1.2, 0.043900)]}
GALGA = [(0, 7.50, 0.0, 10338.439), (0, 7.50, 0.5, 11293.055), (0, 7.50, 0.8, 11518.204), (0, 7.50, 1.0, 11953.334),
         (0, 5.00, 0.0, 6892.292), (0, 10.00, 0.0, 13784.585),
         (1, 7.50, 0.0, 8999.032), (1, 7.50, 0.5, 9255.352), (1, 7.50, 0.8, 9344.392), (1, 7.50, 1.0, 9412.229),
         (1, 10.00, 0.0, 11998.710)]
# Tercera parte: recalculo de L1 y L2 (D, dentro, bajo, sobre, cruces 0.5/0.8/1.0, pasos con sigma >= uts)
CORRIDAS_L = {
    "L1": {"ajustados": 269, "lam": [(1.14730757, (91, 490, 20), (250, 413, 526), 9), (0.09261109, (92, 494, 15), (None, None, None), 0)]},
    "L2": {"ajustados": 265, "lam": [(1.18322756, (93, 496, 12), (248, 405, 499), 4), (0.03262895, (93, 499, 9), (None, None, None), 0)]},
}


def compara_fila(nombre, esp, obt_sigma, obt):
    """esp = (region, N_aj, N_us, dD); obt = dict con region, N_ajuste, N_usado, dD.
    N con diferencia relativa < 1e-9 frente a las 4 decimales del anexo no aplica: el anexo da
    N con 4 decimales, asi que N se compara a 4 decimales y dD a 8."""
    malos = []
    region, n_aj, n_us, dd = esp
    if obt["region"] != region:
        malos.append("region %s != %s" % (obt["region"], region))
    if region == "dentro":
        for k, e in (("N_ajuste", n_aj), ("N_usado", n_us)):
            if round(obt[k], 4) != round(e, 4):
                malos.append("%s %r vs %r" % (k, obt[k], e))
        if round(obt["dD"], 8) != dd:
            malos.append("dD %r vs %r" % (obt["dD"], dd))
    elif obt["dD"] != 0 or obt["N_usado"] is not None:
        malos.append("fuera del intervalo con dD %r" % obt["dD"])
    return malos


def recalcula_corrida(nombre, cfg=None):
    cfg = cfg or CFG
    evs = mt.pasos_caja(str(RAIZ / "datos" / "corridas" / ("%s_2026-11-11" % nombre) / "a2_planta_eventos.jsonl"), "0", "9")
    A = mt.Acumulador(cfg)
    uts = [0] * len(cfg["laminados"])
    cruce_caja = [{} for _ in cfg["laminados"]]
    for e in evs:
        r = A.paso(e.get("peso_V"))
        for i, x in enumerate(r or []):
            if x["sigma_max"] >= cfg["laminados"][i]["sigma_uts_MPa"]:
                uts[i] += 1
        for i, S in enumerate(A.lam):
            for nv, paso in S["cruces"].items():
                cruce_caja[i].setdefault(nv, (paso, e.get("caja"), e.get("ts_salida")))
    return evs, A, uts, cruce_caja


def modelo():
    print("=== Modelo de la capa de materiales, configuracion version 2 (paso R) ===")
    print("--- 0. Configuracion ---")
    v_py = mt.valida(CFG)
    v_js = js([{"accion": "valida", "cfg": CFG}])[0]["payload"]
    verifica("config/materiales.json es valida en Python y en JavaScript", v_py["ok"] and v_js["ok"], (v_py, v_js))
    anexo_a = (RAIZ / "docs" / "ORDEN_A2_FASE_3_CIERRE.md").read_text(encoding="utf-8").split("## Anexo A")[1]
    anexo_a = json.loads(anexo_a.split("```json", 1)[1].split("```", 1)[0])
    verifica("config/materiales.json es exactamente el Anexo A de la orden de cierre (version %s)" % CFG.get("version"),
             anexo_a == CFG)
    v1 = json.loads(subprocess.run(["git", "show", "a946ecf:config/materiales.json"], cwd=str(RAIZ), capture_output=True,
                                   text=True).stdout)
    r_py, r_js = mt.valida(v1), js([{"accion": "valida", "cfg": v1}])[0]["payload"]
    cods = lambda r: sorted({e["codigo"] for e in r["errores"]})
    verifica("la configuracion del commit a946ecf (version 1) se rechaza y lo dice: %s" % cods(r_py),
             not r_py["ok"] and not r_js["ok"] and cods(r_py) == cods(r_js)
             and {"version_no_soportada", "senal_plena_escala_obsoleta"} <= set(cods(r_py)), (cods(r_py), cods(r_js)))
    for desc, cambio, codigo in (("tolerancia_V de 0.3", lambda c: c["ajuste_nivel"].__setitem__("tolerancia_V", 0.3), "tolerancia_invalida"),
                                 ("niveles en desorden", lambda c: c["ajuste_nivel"].__setitem__("niveles_V", [1.5, 3.5, 2.5, 4.0, 5.0, 7.5]),
                                  "niveles_desordenados")):
        c = copy.deepcopy(CFG)
        cambio(c)
        r_py, r_js = mt.valida(c), js([{"accion": "valida", "cfg": c}])[0]["payload"]
        verifica("una configuracion con %s se rechaza con %s (py y js)" % (desc, codigo),
                 cods(r_py) == cods(r_js) == [codigo], (cods(r_py), cods(r_js)))

    print("--- 1. Tabla del Anexo B (JavaScript y Python) ---")
    pet = [{"accion": "punto", "cfg": CFG, "laminado": i, "peso_V": v, "D": 0} for v, *_ in ANEXO_B for i in (0, 1)]
    r_js = [r["payload"] for r in js(pet)]
    malos = []
    for k, (v, pm, aj, sigma, e00, e91) in enumerate(ANEXO_B):
        for i, esp in ((0, e00), (1, e91)):
            p_js = r_js[2 * k + i]
            p_py = mt.punto(CFG, CFG["laminados"][i], v)
            for camino, p in (("js", p_js), ("py", p_py)):
                if p["peso_modelo_V"] != pm or p["ajustado"] != aj:
                    malos.append("%s %.2f V peso_modelo %r ajustado %r" % (camino, v, p["peso_modelo_V"], p["ajustado"]))
                if rel(p["sigma_max"], sigma) >= 1e-9 or abs(p["sigma_min"] - 93.0) > 1e-9:
                    malos.append("%s %.2f V sigma %r vs %r" % (camino, v, p["sigma_max"], sigma))
                malos += ["%s %.2f V %s: %s" % (camino, v, CFG["laminados"][i]["id"], m)
                          for m in compara_fila(camino, esp, p["sigma_max"], p)]
            for clave in ("sigma_max", "N_ajuste", "N_usado", "dD"):
                a, b = p_js[clave], p_py[clave]
                if (a is None) != (b is None) or (a is not None and rel(a, b) >= 1e-9):
                    malos.append("js vs py %.2f V %s: %r vs %r" % (v, clave, a, b))
    verifica("17 pesos x 2 laminados: peso_modelo_V y ajustado exactos, sigma_max (rel < 1e-9), N a 4 decimales y "
             "JS = Python (rel < 1e-9), dD a 8 decimales, region exacta", not malos, malos[:5])

    print("--- 2. Carga constante y secuencia mixta ---")
    sec_js = js([{"accion": "secuencia", "cfg": CFG, "pesos": [7.5] * 77},
                 {"accion": "secuencia", "cfg": CFG, "pesos": MIXTA}])
    for nombre, pesos, sj, esp, cruces, n_aj in (
            ("77 pasos de 7.50 V", [7.5] * 77, sec_js[0], [(1.00794833, None), (0.02695000, None)],
             {"preventiva": 39, "critica": 62, "falla": 77}, 0),
            ("secuencia mixta de 15 pasos", MIXTA, sec_js[1], [(0.07621096, (7, 2, 6)), (0.20598153, (8, 4, 3))], None, 3)):
        A = mt.Acumulador(CFG)
        for v in pesos:
            A.paso(v)
        aj_js = sum(1 for r in sj["resultados"] if r and r[0]["ajustado"])
        for i, (D_esp, cont) in enumerate(esp):
            L = sj["estado"]["laminados"][i]
            S = A.lam[i]
            ok = round(L["D"], 8) == D_esp and round(S["D"], 8) == D_esp and rel(L["D"], S["D"]) < 1e-12
            c_js = (L["conteos"]["dentro"], L["conteos"]["bajo"], L["conteos"]["sobre"])
            c_py = (S["conteos"]["dentro"], S["conteos"]["bajo"], S["conteos"]["sobre"])
            if cont:
                ok = ok and c_js == cont and c_py == cont
            serie = [r[i]["D"] for r in sj["resultados"]]
            ok = ok and all(b >= a for a, b in zip([0.0] + serie, serie))
            extra = ""
            if cruces and i == 0:
                cr_js = {}
                for k, r in enumerate(sj["resultados"]):
                    if r[0]["cambio_nivel"]:
                        cr_js[r[0]["nivel"]] = k + 1
                ok = ok and S["cruces"] == cruces and cr_js == cruces
                extra = ", cruces %s" % S["cruces"]
            if i == 0:
                ok = ok and A.ajustados == n_aj and aj_js == n_aj
                extra += ", %d ajustadas" % A.ajustados
            verifica("%s, laminado %s: D = %.8f (js %.8f, py %.8f)%s%s, D no decrece" %
                     (nombre, CFG["laminados"][i]["id"], D_esp, L["D"], S["D"],
                      ", dentro/bajo/sobre %s" % (cont,) if cont else "", extra), ok, (c_js, c_py, A.ajustados, aj_js))

    print("--- 3. Fronteras ---")
    fr = [(0, 6.74, "bajo"), (0, 6.75, "dentro"), (0, 7.53, "dentro"), (0, 7.54, "sobre"),
          (1, 7.46, "bajo"), (1, 7.47, "dentro"), (1, 8.48, "dentro"), (1, 8.49, "sobre")]
    r = [x["payload"] for x in js([{"accion": "punto", "cfg": CFG, "laminado": i, "peso_V": v} for i, v, _ in fr])]
    malos = [(i, v, e, r[k]["region"], mt.punto(CFG, CFG["laminados"][i], v)["region"])
             for k, (i, v, e) in enumerate(fr) if r[k]["region"] != e or mt.punto(CFG, CFG["laminados"][i], v)["region"] != e]
    verifica("0:0: 6.74 V bajo, 6.75 V dentro (con el tope), 7.53 V dentro (ajustado a 7.50), 7.54 V sobre; "
             "9:1: 7.46 V bajo, 7.47 V dentro (ajustado), 8.48 V dentro, 8.49 V sobre", not malos, malos)
    verifica("a 6.75 V el laminado 0:0 usa el tope de 10^6 ciclos", r[1]["N_usado"] == 1000000 and r[1]["N_ajuste"] > 1e6)

    print("--- 4. Rigidez interpolada y galga sin ruido ---")
    pet = [{"accion": "rigidez", "cfg": CFG, "laminado": i, "D": D} for i in (0, 1) for D, _ in RIGIDEZ[i]]
    r = [x["payload"] for x in js(pet)]
    esp = [(i, D, d) for i in (0, 1) for D, d in RIGIDEZ[i]]
    malos = [(i, D, d, r[k], mt.rigidez(CFG["laminados"][i], D)) for k, (i, D, d) in enumerate(esp)
             if abs(r[k] - d) >= 5e-7 or abs(mt.rigidez(CFG["laminados"][i], D) - d) >= 5e-7]
    verifica("d(D) en 0:0 (7 valores) y 9:1 (6 valores), a 6 decimales, en JS y Python (tablas sin cambio)", not malos, malos)
    r = [x["payload"]["galga_sin_ruido"] for x in
         js([{"accion": "punto", "cfg": CFG, "laminado": i, "peso_V": v, "D": D} for i, v, D, _ in GALGA])]
    malos = [(i, v, D, g, r[k], mt.punto(CFG, CFG["laminados"][i], v, D)["galga_sin_ruido"])
             for k, (i, v, D, g) in enumerate(GALGA)
             if abs(r[k] - g) >= 0.001 or abs(mt.punto(CFG, CFG["laminados"][i], v, D)["galga_sin_ruido"] - g) >= 0.001]
    verifica("galga sin ruido del Anexo B (11 casos) con diferencia < 0.001 ue en JS y Python", not malos, malos)

    print("--- 5. Ruido de la galga ---")
    n = 10000
    sec = js([{"accion": "secuencia", "cfg": CFG, "pesos": [5.0] * n}, {"accion": "secuencia", "cfg": CFG, "pesos": [5.0] * n}])
    g0 = [mt.punto(CFG, L, 5.0, 0.0)["galga_sin_ruido"] for L in CFG["laminados"]]
    for i in (0, 1):
        r1 = [p[i]["deformacion_ue"] - g0[i] for p in sec[0]["resultados"]]
        r2 = [p[i]["deformacion_ue"] - g0[i] for p in sec[1]["resultados"]]
        A = mt.Acumulador(CFG)
        r3 = [A.paso(5.0)[i]["deformacion_ue"] - g0[i] for _ in range(n)]
        media = sum(r1) / n
        sd = math.sqrt(sum((x - media) ** 2 for x in r1) / (n - 1))
        verifica("laminado %s: la misma semilla da la misma secuencia (dos corridas JS identicas; JS vs Python "
                 "max %.2e ue)" % (CFG["laminados"][i]["id"], max(abs(a - b) for a, b in zip(r1, r3))),
                 r1 == r2 and max(abs(a - b) for a, b in zip(r1, r3)) < 1e-6)
        verifica("laminado %s: %d muestras, media %.3f ue (|media| < 1) y desviacion %.3f ue (|sd - 25| < 1)"
                 % (CFG["laminados"][i]["id"], n, media, sd), abs(media) < 1 and abs(sd - 25) < 1)
    s0 = sec[0]["resultados"][0]
    verifica("los dos laminados usan generadores distintos (primer ruido distinto)",
             s0[0]["deformacion_ue"] - g0[0] != s0[1]["deformacion_ue"] - g0[1])

    print("--- 6. D de JavaScript y Python sobre 10000 pesos con semilla ---")
    rnd = random.Random(20261110)
    # mitad cerca de los intervalos ensayados (6.5 a 8.6 V), mitad en toda la escala
    pesos = [round(rnd.uniform(6.5, 8.6) if rnd.random() < 0.5 else rnd.uniform(0.0, 10.0), 2) for _ in range(n)]
    pesos[100] = None                                    # un paso sin peso
    cfg_lenta = copy.deepcopy(CFG)
    cfg_lenta["ciclos_por_paso"] = 1                     # para que D no se dispare y tenga cifras que comparar
    for nombre, cfg in (("config del repo", CFG), ("ciclos_por_paso = 1", cfg_lenta)):
        sj = js([{"accion": "secuencia", "cfg": cfg, "pesos": pesos}])[0]
        A = mt.Acumulador(cfg)
        serie_py = []
        for v in pesos:
            r = A.paso(v)
            serie_py.append(None if r is None else [x["D"] for x in r])
        malos = []
        for i in (0, 1):
            Dj, Dp = sj["estado"]["laminados"][i]["D"], A.lam[i]["D"]
            if rel(Dj, Dp) >= 1e-9:
                malos.append((i, Dj, Dp))
            if sj["estado"]["laminados"][i]["conteos"] != A.lam[i]["conteos"]:
                malos.append((i, sj["estado"]["laminados"][i]["conteos"], A.lam[i]["conteos"]))
        peor = max(rel(a[i], b[i]) for a, b in zip([r and [x["D"] for x in r] for r in sj["resultados"]], serie_py)
                   if a is not None for i in (0, 1))
        verifica("%s: D final igual (rel < 1e-9; peor paso %.1e), mismos conteos, sin_peso %d/%d: %s" %
                 (nombre, peor, sj["estado"]["sin_peso"], A.sin_peso,
                  ", ".join("%s D=%.6g" % (L["id"], L["D"]) for L in sj["estado"]["laminados"])),
                 not malos and peor < 1e-9 and sj["estado"]["sin_peso"] == A.sin_peso == 1, malos)

    print("--- 7. Validador: cada rechazo con su control y prueba de mutacion ---")
    casos = valida_casos()
    for caso in casos:
        codigo, mutar = caso[0], caso[1]
        otros = list(caso[2]) if len(caso) > 2 else []     # codigos que la misma mutacion tambien dispara
        cfg = copy.deepcopy(CFG)
        mutar(cfg)
        r_py = mt.valida(cfg)
        r_js = js([{"accion": "valida", "cfg": cfg}])[0]["payload"]
        cods_py = {e["codigo"] for e in r_py["errores"]}
        cods_js = {e["codigo"] for e in r_js["errores"]}
        sin_py = mt.valida(cfg, apaga=[codigo] + otros)
        sin_js = js([{"accion": "valida", "cfg": cfg, "apaga": [codigo] + otros}])[0]["payload"]
        solo_otros = mt.valida(cfg, apaga=otros) if otros else {"ok": False}
        verifica("%-27s rechaza (py y js) y con la regla apagada deja de rechazar%s" % (codigo, " (apagando tambien %s)" % otros if otros else ""),
                 codigo in cods_py and codigo in cods_js and cods_py == cods_js and sin_py["ok"] and sin_js["ok"]
                 and not solo_otros["ok"],
                 (sorted(cods_py), sorted(cods_js), sin_py["errores"][:2], sin_js["errores"][:2]))
    r = subprocess.run([sys.executable, str(RAIZ / "tools" / "materiales.py"), "valida"], capture_output=True, text=True)
    verifica("control: tools/materiales.py valida acepta el Anexo A (exit %d)" % r.returncode, r.returncode == 0)

    print("--- 8. recalcula L1 y L2 (tercera parte del Anexo B) ---")
    for nombre, esp in CORRIDAS_L.items():
        evs, A, uts, cr = recalcula_corrida(nombre)
        malos = []
        if A.ajustados != esp["ajustados"]:
            malos.append("ajustados %d" % A.ajustados)
        for i, (D, cont, cruces, n_uts) in enumerate(esp["lam"]):
            S = A.lam[i]
            c = (S["conteos"]["dentro"], S["conteos"]["bajo"], S["conteos"]["sobre"])
            cz = tuple(S["cruces"].get(k) for k in ("preventiva", "critica", "falla"))
            if round(S["D"], 8) != D or c != cont or cz != cruces or uts[i] != n_uts:
                malos.append((S["id"], round(S["D"], 8), c, cz, uts[i]))
            for nv, (paso, caja, _) in cr[i].items():
                if paso != caja:
                    malos.append("%s %s paso %d caja %s" % (S["id"], nv, paso, caja))
        verifica("%s: %d pasos, %d ajustados; %s" % (nombre, len(evs), A.ajustados, "; ".join(
            "%s D=%.8f %s cruces %s uts %d" % (S["id"], S["D"], S["conteos"], S["cruces"], uts[i]) for i, S in enumerate(A.lam))),
            not malos and len(evs) == 601, malos)
    r = subprocess.run([sys.executable, str(RAIZ / "tools" / "materiales.py"), "recalcula", "--eventos",
                        str(RAIZ / "datos" / "corridas" / "L1_2026-11-11" / "a2_planta_eventos.jsonl"),
                        "--desde", "2026-11-11T00:00:00Z", "--hasta", "2026-11-12T00:00:00Z", "--json"],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    verifica("tools/materiales.py recalcula da lo mismo por linea de comandos en L1 (0:0 D=%.8f)" % d["laminados"][0]["D"],
             r.returncode == 0 and round(d["laminados"][0]["D"], 8) == 1.14730757 and d["ajustados"] == 269)


def valida_casos():
    def pon(ruta, valor):
        def f(c):
            o = c
            for k in ruta[:-1]:
                o = o[k]
            o[ruta[-1]] = valor
        return f
    return [
        ("b_no_negativo", pon(["laminados", 0, "b"], 0.021)),
        ("a_no_positivo", pon(["laminados", 1, "a_MPa"], 0.0)),
        ("intervalo_invertido", pon(["laminados", 0, "nivel_min_pct"], 85.0)),
        ("umbrales_desordenados", pon(["umbrales_D", "critica"], 0.4)),
        ("rigidez_no_empieza_en_cero", pon(["laminados", 0, "rigidez", 0], [0.0, 0.01])),
        ("rigidez_D_no_creciente", pon(["laminados", 1, "rigidez", 3], [0.00004, 0.0075])),
        ("rigidez_d_decreciente", pon(["laminados", 0, "rigidez", 5], [0.06859, 0.0200])),
        ("rigidez_D_fuera_de_rango", lambda c: c["laminados"][1]["rigidez"].append([1.2, 0.05])),
        ("campo_desconocido", pon(["laminados", 0, "color"], "negro")),
        ("campo_desconocido", pon(["galga", "ganancia"], 2.0)),
        ("campo_desconocido", pon(["extra"], 1)),
        ("version_no_soportada", pon(["version"], 1)),
        ("senal_plena_escala_obsoleta", pon(["carga", "senal_plena_escala_V"], 10.0), ["campo_desconocido"]),
        ("niveles_desordenados", pon(["ajuste_nivel", "niveles_V"], [1.5, 2.5, 2.5, 4.0, 5.0, 7.5])),
        ("niveles_desordenados", pon(["ajuste_nivel", "niveles_V"], [0.0, 2.5, 3.5, 4.0, 5.0, 7.5])),
        ("tolerancia_invalida", pon(["ajuste_nivel", "tolerancia_V"], 0.25)),
        ("tolerancia_invalida", pon(["ajuste_nivel", "tolerancia_V"], -0.01)),
    ]


# =====================================================================================
# M2. Pestana A2 · Materiales contra el sustituto del desviador
# =====================================================================================
def _ps():
    sys.path.insert(0, str(RAIZ / "pruebas"))
    import prueba_sustituto as ps
    ps.verifica = verifica           # antes de importar los demas: un solo contador para todo el archivo
    import prueba_planta as pp
    import prueba_desviador as pd
    import admin_desechable as ad
    from socketio_min import SocketIO
    return ps, pp, pd, ad, SocketIO


VERDAD_CAMPOS = {"region", "N_usado", "N_ajuste", "dD", "D", "d", "nivel", "conteos", "cambio_nivel", "alerta",
                 "peso_modelo_V", "ajustado"}
MEDIDO_CAMPOS = {"ts_salida", "caja", "pieza", "peso_V", "peso_estable", "f", "sigma_max_MPa", "delta_sigma_MPa",
                 "deformacion_ue", "paso"}


def lee_jsonl(ruta):
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def sust_config(datos, nombre, masa):
    c = json.loads((RAIZ / "config" / "sustituto_desviador.json").read_text(encoding="utf-8"))
    c["masa_kg"] = masa
    c["emision_s"] = {"min": 3.5, "max": 4.0}
    ruta = datos.parent / ("sust_%s.json" % nombre)
    ruta.write_text(json.dumps(c, indent=2), encoding="utf-8")
    return ruta


def mat_config(datos, nombre, **cambios):
    c = copy.deepcopy(CFG)
    for k, v in cambios.items():
        if k == "sigma_ref_MPa":
            c["carga"]["sigma_ref_MPa"] = v
        else:
            c[k] = v
    ruta = datos.parent / ("mat_%s.json" % nombre)
    ruta.write_text(json.dumps(c, indent=2), encoding="utf-8")
    return ruta, c


class Tarjeta:
    """Lo que la pagina recibe para la tarjeta Materials layer (socket.io de Dashboard 2.0)."""
    def __init__(self, SocketIO, ps):
        self._abre = lambda: SocketIO("127.0.0.1", ps.PUERTO_NR, "/dashboard/socket.io/").conecta()
        self.s = self._abre()
        self.mat, self.vistos, self.estado = None, [], None

    def lee(self, segundos):
        try:
            eventos = self.s.recibe(segundos)
        except ConnectionError:
            # Sin sondear un rato, el servidor cierra la sesion (400): se abre
            # otra, como al recargar la pagina. La tarjeta se reenvia cada 2 s.
            self.s = self._abre()
            eventos = self.s.recibe(segundos)
        for nombre, args in eventos:
            if nombre == "msg-input:ui_tpl_a2" and args and isinstance(args[0], dict):
                p = args[0].get("payload")
                if isinstance(p, dict) and p.get("materials") is True:
                    self.mat = p
                    self.vistos.append(p)
                elif isinstance(p, dict) and "ready" in p:
                    self.estado = p

    def espera(self, cond, segundos):
        fin = time.time() + segundos
        while time.time() < fin:
            self.lee(min(2, max(0.2, fin - time.time())))
            if cond(self):
                return True
        return False


def corre_cajas(pp, datos, n, limite_s=None):
    """Marcha y emisor hasta n paso_caja nuevos; despues paro."""
    pasos = lambda: [x for x in pp.eventos(datos, "a2_planta_eventos.jsonl") if x["ev"] == "paso_caja"]
    n0 = len(pasos())
    pp.comando(accion="marcha")
    pp.comando(accion="emisor", valor=True)
    pp.espera(lambda: len(pasos()) >= n0 + n, limite_s or n * 8 + 60, paso=0.5)
    pp.comando(accion="emisor", valor=False)
    pp.espera(lambda: not pp.estado()["en_tramo"], 60, paso=0.5)
    time.sleep(1.0)                                     # el ultimo paso termina de guardarse
    pp.comando(accion="paro")
    return pasos()


def recalcula_eventos(cfg, datos):
    evs = sorted((x for x in pp_eventos(datos) if x["ev"] == "paso_caja"), key=lambda x: x["ts_salida"])
    return mt.recalcula(cfg, evs), evs


def pp_eventos(datos):
    return lee_jsonl(datos / "a2_planta_eventos.jsonl")


def compara_verdad(cfg, datos, etiqueta):
    """El archivo de verdad contra tools/materiales.py sobre los paso_caja del cliente."""
    verdad = lee_jsonl(datos / "a2_materiales_verdad.jsonl")
    r, evs = recalcula_eventos(cfg, datos)
    piezas = [L["pieza"] for L in cfg["laminados"]]
    malos = []
    for i, pieza in enumerate(piezas):
        filas = [v for v in verdad if v["pieza"] == pieza]
        if not filas:
            malos.append("%s sin filas" % pieza)
            continue
        D_v = filas[-1]["D"]
        D_py = r["laminados"][i]["D"]
        if rel(D_v, D_py) >= 1e-9:
            malos.append("%s D %r vs recalcula %r" % (pieza, D_v, D_py))
        # Paso R: la verdad guarda peso_V, peso_modelo_V y ajustado, iguales al ajuste de tools/materiales.py
        mal_aj = [v for v in filas if (v.get("peso_modelo_V"), v.get("ajustado")) != mt.peso_modelo(cfg, v.get("peso_V"))]
        if mal_aj:
            malos.append("%s ajuste distinto en %d pasos: %s" % (pieza, len(mal_aj), mal_aj[:1]))
        cont = {k: sum(1 for v in filas if v["region"] == k) for k in ("dentro", "bajo", "sobre")}
        if cont != r["laminados"][i]["conteos"]:
            malos.append("%s conteos %s vs %s" % (pieza, cont, r["laminados"][i]["conteos"]))
        serie = [v["D"] for v in filas]
        if any(b < a for a, b in zip(serie, serie[1:])):
            malos.append("%s D decrece" % pieza)
    print("    %s: %d paso_caja; %s" % (etiqueta, len(evs), "; ".join(
        "%s D=%.8f %s" % (L["id"], L["D"], L["conteos"]) for L in r["laminados"])))
    return malos, r, verdad, evs


def flujo():
    ps, pp, pd, ad, SocketIO = _ps()
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_materiales_"))
    print("=== M2. Pestana A2 · Materiales contra el sustituto del desviador (en %s) ===" % tmp)
    # Masas de prueba (no son del Anexo). Con la version 2 (7.5 V = 15 kg es la
    # referencia) el 0:0 esta dentro entre 13.5 y 15.0 kg y el 9:1 entre 15.0 y
    # 17.0 kg: la mezcla deja pasos bajo, dentro y sobre en los dos laminados.
    mezcla = {"distribucion": "normal", "media": 15.0, "sd": 3.0, "min": 2.0, "max": 25.0}
    # Umbrales: todas dentro del 0:0 (14.0 a 15.0 kg). La configuracion de esa
    # corrida usa ciclos_por_paso = 2500 (valor de prueba) para cruzar los tres
    # umbrales en ~12 pasos en lugar de ~77.
    pesada = {"distribucion": "normal", "media": 14.8, "sd": 0.3, "min": 14.0, "max": 15.0}

    # ---- 1. sin la bandera ---------------------------------------------------------
    print("--- 1. Sin A2_MATERIALES ---")
    datos = tmp / "sin_bandera"
    datos.mkdir()
    proxy = pd.arranca("local", datos, A2_SUST_CONFIG=sust_config(datos, "mezcla", mezcla),
                       A2_MAT_CONFIG=RAIZ / "config" / "materiales.json")
    try:
        tj = Tarjeta(SocketIO, ps)
        corre_cajas(pp, datos, 3)
        tj.lee(3)
        archivos = sorted(x.name for x in datos.glob("a2_materiales*"))
        verifica("sin la bandera, la pestana no crea archivos (%s)" % archivos, not archivos)
        verifica("y la HMI no recibe la tarjeta (estado de la planta si: %s)" % bool(tj.estado),
                 tj.estado is not None and not tj.vistos)
    finally:
        ps.detiene()
        proxy.detiene()

    # ---- 2, 3, 4 y 7: corrida con persistencia --------------------------------------
    print("--- 2. Corrida contra el sustituto, con un reinicio de Node-RED a media corrida ---")
    datos = tmp / "corrida"
    datos.mkdir()
    sust = sust_config(datos, "mezcla", mezcla)
    env_adm, clave = ad.genera()
    extra = dict(A2_SUST_CONFIG=sust, A2_MATERIALES=1, A2_MAT_CONFIG=RAIZ / "config" / "materiales.json", **env_adm)
    proxy = pd.arranca("local", datos, **extra)
    try:
        corre_cajas(pp, datos, 15)
        verdad_a = lee_jsonl(datos / "a2_materiales_verdad.jsonl")
        estado_a = json.loads((datos / "a2_materiales_estado.json").read_text())
    finally:
        ps.detiene()
        proxy.detiene()
    print("    primera parte: %d pasos; Node-RED detenido" % estado_a["pasos"])
    proxy = pd.arranca("local", datos, **extra)
    try:
        tj = Tarjeta(SocketIO, ps)
        corre_cajas(pp, datos, 15)
        tok = ad.token(env_adm["NODE_RED_ADMIN_USER"], clave)
        c_g, t_g = ad.pide("GET", "/context/global", tok)
        c_m, t_m = ad.pide("GET", "/context/global/a2_mat_medido", tok)
        tj.lee(3)
    finally:
        ps.detiene()
        proxy.detiene()
    malos, r, verdad, evs = compara_verdad(CFG, datos, "corrida completa")
    verifica("la verdad coincide con tools/materiales.py recalcula: D por laminado (rel < 1e-9), conteos exactos, "
             "D no decrece", not malos, malos)
    regiones = {(v["pieza"], v["region"]) for v in verdad}
    verifica("la configuracion de prueba deja pasos dentro y bajo en los dos laminados (%s)" % sorted(regiones),
             {("varilla_00", "dentro"), ("varilla_00", "bajo"), ("varilla_91", "dentro"), ("varilla_91", "bajo")} <= regiones)

    print("--- 4. Persistencia ---")
    pasos_a = estado_a["pasos"]
    primera_b = [v for v in verdad if v["paso"] == pasos_a + 1]
    ultimo_a = {v["pieza"]: v for v in verdad_a if v["paso"] == pasos_a}
    ok = bool(primera_b) and all(abs(v["D"] - v["dD"] - ultimo_a[v["pieza"]]["D"]) <= 1e-12 * max(1, v["D"])
                                 for v in primera_b)
    verifica("al volver, D continua desde el ultimo valor del archivo de verdad (paso %d -> %d)" % (pasos_a, pasos_a + 1),
             ok, (ultimo_a, primera_b))
    verifica("los pasos siguen numerandose sin saltos ni repeticiones (%d pasos)" % len({v["paso"] for v in verdad}),
             sorted({v["paso"] for v in verdad}) == list(range(1, len(evs) + 1)))

    print("--- 3. Separacion entre lo medido y la verdad ---")
    medido = lee_jsonl(datos / "a2_materiales_medido.jsonl")
    campos = set().union(*[set(m) for m in medido]) if medido else set()
    verifica("el archivo de lo medido trae solo sus campos (%s), ninguno de la verdad" % sorted(campos),
             campos == MEDIDO_CAMPOS and not (campos & VERDAD_CAMPOS))
    verifica("una linea de lo medido y una de la verdad por paso y laminado (%d y %d)" % (len(medido), len(verdad)),
             len(medido) == len(verdad) == 2 * len(evs))
    try:
        glob_ = json.loads(t_g)
    except ValueError:
        glob_ = {}
    claves = set()
    for almacen in glob_.values() if isinstance(glob_, dict) else []:
        if isinstance(almacen, dict):
            claves |= set(almacen)
    texto = t_g + t_m
    fugas = [k for k in ("\"D\"", "\"dD\"", "N_usado", "\"region\"", "\"nivel\"", "\"d\"", "dentro", "preventiva",
                         "mat_estado", "mat_hmi", "deformacion_ue\\\":null") if k in texto]
    verifica("contexto global leido con el token desechable (%d, %d): claves %s; sin claves ni valores de la verdad"
             % (c_g, c_m, sorted(k for k in claves if k.startswith("a2_mat"))),
             c_g == 200 and c_m == 200 and "a2_mat_medido" in claves and not fugas, fugas)
    try:
        m_val = json.loads(json.loads(t_m)["memory"]["msg"]) if "memory" in json.loads(t_m) else json.loads(json.loads(t_m)["msg"])
    except (ValueError, KeyError, TypeError):
        m_val = None
    ok = isinstance(m_val, dict) and all(len(v) <= 30 for v in m_val.get("laminados", {}).values()) \
        and all(set(x) <= MEDIDO_CAMPOS for v in m_val.get("laminados", {}).values() for x in v)
    verifica("global.a2_mat_medido: ultimos 30 pasos por laminado, solo campos medidos, y conteos de pasos (%s)"
             % (sorted(m_val) if isinstance(m_val, dict) else m_val), ok and "pasos" in m_val, t_m[:200])
    flujos = json.loads((RAIZ / "node-red" / "flows.json").read_text(encoding="utf-8"))
    por_id = {n["id"]: n for n in flujos}
    mat = {n["id"] for n in flujos if n.get("z") == "a2_materiales"}
    hacia_diag = [(n["id"], d) for n in flujos if n["id"] in mat for ws in n.get("wires", []) for d in ws
                  if por_id.get(d, {}).get("z") == "a2_diagnostico"]
    hacia_diag += [(n["id"], d) for n in flujos if n["id"] in mat and n["type"] == "link out" for d in n.get("links", [])
                   if por_id.get(d, {}).get("z") == "a2_diagnostico"]
    verifica("en flows.json no hay cable ni enlace de la pestana de materiales hacia la de diagnostico", not hacia_diag, hacia_diag)
    salen = [(n["id"], d, por_id[d]["z"]) for n in flujos if n["id"] in mat and n["type"] == "link out"
             for d in n.get("links", [])]
    verifica("el unico enlace que sale de la pestana va a la HMI (%s)" % salen,
             salen == [("link_mat_hmi", "link_hmi_mat", "a2_hmi")])
    tipos = {por_id[i]["type"] for i in mat}
    verifica("la pestana no tiene nodos Modbus ni http request: no escribe en la planta, en Firebase ni en Gemini (%s)"
             % sorted(tipos), not any(t.startswith("modbus") or t == "http request" for t in tipos))
    r_git = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "node-red/funciones/37_diag_arma.js",
                            "node-red/funciones/38_diag_valida.js"], cwd=str(RAIZ))
    r_ini = subprocess.run(["git", "diff", "--quiet", "b23428b", "--", "node-red/funciones/37_diag_arma.js",
                            "node-red/funciones/38_diag_valida.js"], cwd=str(RAIZ))
    verifica("37_diag_arma.js y 38_diag_valida.js identicos a HEAD y al inicio de la fase",
             r_git.returncode == 0 and r_ini.returncode == 0)

    print("--- 7. Galga ---")
    gens = [mt.Generador(mt.semilla_laminado(CFG["galga"]["semilla"], i)) for i in range(len(CFG["laminados"]))]
    D_antes = {L["pieza"]: 0.0 for L in CFG["laminados"]}
    peor = 0.0
    v_por = {(v["paso"], v["pieza"]): v for v in verdad}
    for m in sorted(medido, key=lambda x: (x["paso"], [L["pieza"] for L in CFG["laminados"]].index(x["pieza"]))):
        i = [L["pieza"] for L in CFG["laminados"]].index(m["pieza"])
        L = CFG["laminados"][i]
        g = mt.punto(CFG, L, m["peso_V"], D_antes[m["pieza"]])["galga_sin_ruido"] + CFG["galga"]["ruido_sd_ue"] * gens[i].normal()
        peor = max(peor, abs(g - m["deformacion_ue"]))
        D_antes[m["pieza"]] = v_por[(m["paso"], m["pieza"])]["D"]
    verifica("la deformacion medida = la recalculada con la secuencia de D de la verdad y la misma semilla "
             "(peor diferencia %.2e ue < 0.1)" % peor, medido and peor < 0.1)

    print("--- 4b. Archivo de estado danado ---")
    (datos / "a2_materiales_estado.json").write_text("{esto no es json", encoding="utf-8")
    n_v, n_m = len(verdad), len(medido)
    proxy = pd.arranca("local", datos, **extra)
    try:
        tj = Tarjeta(SocketIO, ps)
        corre_cajas(pp, datos, 3)
        tj.espera(lambda t: t.mat is not None, 6)
        log = (datos / "nodered.log").read_text(encoding="utf-8", errors="replace")
    finally:
        ps.detiene()
        proxy.detiene()
    verifica("con el estado danado la pestana no acumula: verdad %d -> %d lineas, medido %d -> %d"
             % (n_v, len(lee_jsonl(datos / "a2_materiales_verdad.jsonl")), n_m, len(lee_jsonl(datos / "a2_materiales_medido.jsonl"))),
             len(lee_jsonl(datos / "a2_materiales_verdad.jsonl")) == n_v and len(lee_jsonl(datos / "a2_materiales_medido.jsonl")) == n_m)
    verifica("no reinicia en silencio: el archivo danado sigue igual",
             (datos / "a2_materiales_estado.json").read_text() == "{esto no es json")
    verifica("y lo reporta: HMI '%s', registro de Node-RED" % (tj.mat or {}).get("error"),
             tj.mat is not None and "NOT accumulating" in (tj.mat.get("error") or "")
             and "state file unreadable" in tj.mat["error"] and "no acumula (archivo de estado ilegible" in log)

    print("--- 4c. Estado de otra version de configuracion (cfg_version 1) ---")
    viejo = copy.deepcopy(estado_a)
    viejo["cfg_version"] = 1
    (datos / "a2_materiales_estado.json").write_text(json.dumps(viejo), encoding="utf-8")
    n_v, n_m = len(lee_jsonl(datos / "a2_materiales_verdad.jsonl")), len(lee_jsonl(datos / "a2_materiales_medido.jsonl"))
    proxy = pd.arranca("local", datos, **extra)
    try:
        tj = Tarjeta(SocketIO, ps)
        corre_cajas(pp, datos, 3)
        tj.espera(lambda t: t.mat is not None, 6)
        log = (datos / "nodered.log").read_text(encoding="utf-8", errors="replace")
    finally:
        ps.detiene()
        proxy.detiene()
    verifica("con un estado de cfg_version 1 la pestana no acumula: verdad %d -> %d, medido %d -> %d"
             % (n_v, len(lee_jsonl(datos / "a2_materiales_verdad.jsonl")), n_m, len(lee_jsonl(datos / "a2_materiales_medido.jsonl"))),
             len(lee_jsonl(datos / "a2_materiales_verdad.jsonl")) == n_v and len(lee_jsonl(datos / "a2_materiales_medido.jsonl")) == n_m)
    verifica("el estado viejo sigue igual (no se reescribe)",
             json.loads((datos / "a2_materiales_estado.json").read_text()) == viejo)
    verifica("y lo reporta: HMI '%s', registro de Node-RED" % (tj.mat or {}).get("error"),
             tj.mat is not None and "NOT accumulating" in (tj.mat.get("error") or "")
             and "another configuration version" in tj.mat["error"]
             and "otra version de configuracion: estado 1, configuracion 2" in log)

    # ---- 5. umbrales --------------------------------------------------------------------
    print("--- 5. Umbrales: la HMI pasa por normal, preventive, critical y failure ---")
    datos = tmp / "umbrales"
    datos.mkdir()
    ruta_u, cfg_u = mat_config(datos, "umbrales", ciclos_por_paso=2500)
    proxy = pd.arranca("local", datos, A2_SUST_CONFIG=sust_config(datos, "pesada", pesada), A2_MATERIALES=1,
                       A2_MAT_CONFIG=ruta_u)
    try:
        tj = Tarjeta(SocketIO, ps)
        tj.espera(lambda t: t.mat is not None and t.mat["rods"], 10)
        pasos = lambda: [x for x in pp.eventos(datos, "a2_planta_eventos.jsonl") if x["ev"] == "paso_caja"]
        pp.comando(accion="marcha")
        pp.comando(accion="emisor", valor=True)
        tj.espera(lambda t: t.mat and t.mat["rods"] and t.mat["rods"][0]["level"] == "falla"
                  and t.mat["steps"] >= len(pasos()) - 1, 150)
        pp.comando(accion="emisor", valor=False)
        pp.espera(lambda: not pp.estado()["en_tramo"], 60, paso=0.5)
        time.sleep(1)
        pp.comando(accion="paro")
        tj.lee(3)
    finally:
        ps.detiene()
        proxy.detiene()
    malos, r, verdad, evs = compara_verdad(cfg_u, datos, "umbrales")
    vistos_0 = []
    for p in tj.vistos:
        if p["rods"]:
            lab = p["rods"][0]["levelLabel"]
            if not vistos_0 or vistos_0[-1][0] != lab:
                vistos_0.append((lab, p["steps"]))
    cruces = r["laminados"][0]["cruces"]
    esperado = [("normal", None), ("preventive", cruces.get("preventiva")), ("critical", cruces.get("critica")),
                ("failure", cruces.get("falla"))]
    cambios = (tj.mat or {}).get("rods", [{}])[0].get("levelChanges", [])
    print("    HMI vio (nivel, paso): %s; recalcula: %s; cambios en la tarjeta: %s" % (vistos_0, cruces, cambios))
    verifica("la verdad coincide con el recalculo (D sobre 1 en el laminado 0:0: %.4f)" % r["laminados"][0]["D"],
             not malos and r["laminados"][0]["D"] > 1, malos)
    verifica("la HMI paso por normal, preventive, critical y failure en ese orden",
             [x[0] for x in vistos_0] == ["normal", "preventive", "critical", "failure"], vistos_0)
    verifica("cada cambio de nivel en el paso que predice el recalculo",
             [(c["level"], c["step"]) for c in cambios] == [(e, s) for e, s in esperado[1:]], (cambios, esperado))

    # ---- 6. region sobre ------------------------------------------------------------------
    print("--- 6. Region sobre (masas de mas de 15 kg en el 0:0, configuracion del repo) ---")
    datos = tmp / "sobre"
    datos.mkdir()
    ruta, cfg_s = mat_config(datos, "sobre")
    proxy = pd.arranca("local", datos, A2_SUST_CONFIG=sust_config(datos, "mezcla6", mezcla), A2_MATERIALES=1,
                       A2_MAT_CONFIG=ruta)
    try:
        tj = Tarjeta(SocketIO, ps)
        corre_cajas(pp, datos, 10)
        tj.mat = None
        tj.espera(lambda t: t.mat is not None and t.mat["rods"], 10)
    finally:
        ps.detiene()
        proxy.detiene()
    malos, r, verdad, evs = compara_verdad(cfg_s, datos, "sobre")
    sobre = [v for v in verdad if v["region"] == "sobre"]
    previo = {}
    cambian = []
    for v in sorted(verdad, key=lambda x: x["paso"]):
        if v["region"] == "sobre" and (v["dD"] != 0 or v["D"] != previo.get(v["pieza"], 0.0)):
            cambian.append(v)
        previo[v["pieza"]] = v["D"]
    alerta = [x["alert"] for x in (tj.mat or {}).get("rods", []) if x.get("alert")]
    verifica("la verdad coincide con el recalculo con la configuracion de prueba", not malos, malos)
    verifica("%d pasos sobre el intervalo, contados (%s)" % (len(sobre), [L["conteos"] for L in r["laminados"]]),
             len(sobre) > 0 and sum(L["conteos"]["sobre"] for L in r["laminados"]) == len(sobre))
    verifica("los pasos sobre no cambian D", not cambian, cambian[:2])
    verifica("y levantan la alerta en la HMI (%s; tarjeta recibida: %s)" % (alerta, tj.mat is not None), alerta and all(a["code"] == "carga_fuera_del_intervalo" for a in alerta)
             and sum(a["count"] for a in alerta) == len(sobre))

    # ---- 8. regresion: nodos de la Actividad 1 -------------------------------------------
    print("--- 8. Nodos de la Actividad 1 ---")
    ini = json.loads(subprocess.run(["git", "show", "b23428b:node-red/flows.json"], cwd=str(RAIZ), capture_output=True,
                                    text=True).stdout)
    a1 = lambda fl: sorted((json.dumps(n, sort_keys=True) for n in fl
                            if n.get("z") in ("a1_ingesta", "a1_diagnostico") or n["id"] in ("a1_ingesta", "a1_diagnostico")))
    verifica("los %d nodos de la Actividad 1 son identicos a los del inicio de la fase" % len(a1(ini)), a1(ini) == a1(flujos))


if __name__ == "__main__":
    modos = {"modelo": modelo, "flujo": flujo, "todo": lambda: (modelo(), flujo())}
    m = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if m not in modos:
        sys.exit(__doc__)
    try:
        modos[m]()
    finally:
        if m != "modelo":
            sys.path.insert(0, str(RAIZ / "pruebas"))
            import prueba_sustituto as _ps_fin
            _ps_fin.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (resultado["ok"], resultado["falla"]))
    sys.exit(resultado["falla"])
