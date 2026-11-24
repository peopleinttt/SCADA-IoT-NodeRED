#!/usr/bin/env python3
"""Capa de materiales por un segundo camino (paso M1 de la fase 3). Python 3.9, sin dependencias.

    python3 tools/materiales.py valida [--config config/materiales.json] [--apaga codigo,...]
    python3 tools/materiales.py referencia [--config ...]          (tabla del Anexo B)
    python3 tools/materiales.py recalcula --eventos <jsonl> --desde <ts> --hasta <ts> [--config ...] [--json]

La misma cuenta que node-red/funciones/39_mat_modelo.js, escrita aparte; las
pruebas (pruebas/prueba_materiales.py) comparan los dos caminos. Las
definiciones estan en ese archivo y en docs/PARAMETROS_MATERIALES.md.

recalcula toma los eventos paso_caja del archivo (los de A2-Planta) cuyo
ts_salida cae en [desde, hasta], en el orden de ts_salida, y reporta por
laminado D y los pasos por region. Un paso sin peso numerico se cuenta como
sin_peso y no se evalua.

Codigo de salida: valida -> numero de errores; recalcula -> 0, o 2 si no hay eventos.
"""
import argparse, json, math, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config" / "materiales.json"

CAMPOS = {
    "raiz": ["version", "fuente", "carga", "ajuste_nivel", "n_tope_ciclos", "ciclos_por_paso", "umbrales_D", "galga",
             "laminados"],
    "carga": ["sigma_ref_MPa", "R_ref", "senal_ref_V"],
    "ajuste_nivel": ["niveles_V", "tolerancia_V"],
    "umbrales_D": ["preventiva", "critica", "falla"],
    "galga": ["ruido_sd_ue", "semilla"],
    "laminado": ["id", "pieza", "a_MPa", "b", "sigma_uts_MPa", "E0_GPa", "nivel_min_pct", "nivel_max_pct", "rigidez"],
}
CODIGOS = ["b_no_negativo", "a_no_positivo", "intervalo_invertido", "umbrales_desordenados",
           "rigidez_no_empieza_en_cero", "rigidez_D_no_creciente", "rigidez_d_decreciente",
           "rigidez_D_fuera_de_rango", "campo_desconocido", "campo_faltante", "tipo_invalido", "valor_invalido",
           "version_no_soportada", "senal_plena_escala_obsoleta", "niveles_desordenados", "tolerancia_invalida"]


def carga_config(ruta=None):
    return json.loads(pathlib.Path(ruta or CONFIG).read_text(encoding="utf-8"))


def es_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


# ---- validador ------------------------------------------------------------------------
def valida(cfg, apaga=()):
    off = set(apaga or ())
    errores = []

    def err(codigo, ruta, detalle):
        if codigo not in off:
            errores.append({"codigo": codigo, "ruta": ruta, "detalle": detalle})

    def campos(obj, lista, ruta):
        if not isinstance(obj, dict):
            err("tipo_invalido", ruta, "se esperaba un objeto")
            return False
        for k in obj:
            if k not in lista:
                err("campo_desconocido", ruta + "." + k, "campo no definido")
        for k in lista:
            if k not in obj:
                err("campo_faltante", ruta + "." + k, "falta")
        return True

    def positivo(v, ruta):
        if not es_num(v) or v <= 0:
            err("valor_invalido", ruta, "debe ser un numero > 0: %r" % (v,))

    if not campos(cfg, CAMPOS["raiz"], "cfg"):
        return {"ok": not errores, "errores": errores}
    if cfg.get("version") != 2:
        err("version_no_soportada", "cfg.version", "solo se conoce la version 2: %r" % (cfg.get("version"),))
    if not isinstance(cfg.get("fuente"), str):
        err("tipo_invalido", "cfg.fuente", "texto")
    c = cfg.get("carga")
    if isinstance(c, dict) and "senal_plena_escala_V" in c:
        err("senal_plena_escala_obsoleta", "cfg.carga.senal_plena_escala_V",
            "la version 2 usa senal_ref_V (7.5 V no es la plena escala de la bascula)")
    if campos(c, CAMPOS["carga"], "cfg.carga"):
        positivo(c.get("sigma_ref_MPa"), "cfg.carga.sigma_ref_MPa")
        positivo(c.get("senal_ref_V"), "cfg.carga.senal_ref_V")
        R = c.get("R_ref")
        if not es_num(R) or R < 0 or R >= 1:
            err("valor_invalido", "cfg.carga.R_ref", "debe estar en [0, 1): %r" % (R,))
    A = cfg.get("ajuste_nivel")
    if campos(A, CAMPOS["ajuste_nivel"], "cfg.ajuste_nivel"):
        n, tol = A.get("niveles_V"), A.get("tolerancia_V")
        n_ok = isinstance(n, list) and all(es_num(x) for x in n)
        if not n_ok:
            err("tipo_invalido", "cfg.ajuste_nivel.niveles_V", "lista de numeros (puede estar vacia)")
        elif any(x <= 0 or (k > 0 and not (x > n[k - 1])) for k, x in enumerate(n)):
            err("niveles_desordenados", "cfg.ajuste_nivel.niveles_V", "numeros positivos en orden creciente: %r" % (n,))
        if not es_num(tol) or tol < 0:
            err("tolerancia_invalida", "cfg.ajuste_nivel.tolerancia_V", "debe ser >= 0: %r" % (tol,))
        elif n_ok and len(n) > 1:
            sep = min(b - a for a, b in zip(n, n[1:]))
            if sep > 0 and not (tol < sep / 2.0):
                err("tolerancia_invalida", "cfg.ajuste_nivel.tolerancia_V",
                    "debe ser menor que la mitad de la separacion minima (%r): %r" % (sep, tol))
    positivo(cfg.get("n_tope_ciclos"), "cfg.n_tope_ciclos")
    positivo(cfg.get("ciclos_por_paso"), "cfg.ciclos_por_paso")
    u = cfg.get("umbrales_D")
    if campos(u, CAMPOS["umbrales_D"], "cfg.umbrales_D"):
        vals = [u.get("preventiva"), u.get("critica"), u.get("falla")]
        if not all(es_num(v) for v in vals):
            err("tipo_invalido", "cfg.umbrales_D", "numeros")
        elif not (0 < vals[0] < vals[1] < vals[2]):
            err("umbrales_desordenados", "cfg.umbrales_D", "se requiere 0 < preventiva < critica < falla: %r" % (vals,))
    g = cfg.get("galga")
    if campos(g, CAMPOS["galga"], "cfg.galga"):
        if not es_num(g.get("ruido_sd_ue")) or g.get("ruido_sd_ue") < 0:
            err("valor_invalido", "cfg.galga.ruido_sd_ue", ">= 0")
        s = g.get("semilla")
        if not (isinstance(s, int) and not isinstance(s, bool)):
            err("valor_invalido", "cfg.galga.semilla", "entero")
    lams = cfg.get("laminados")
    if not isinstance(lams, list) or not lams:
        err("tipo_invalido", "cfg.laminados", "lista no vacia")
    else:
        ids = set()
        for i, L in enumerate(lams):
            r = "cfg.laminados[%d]" % i
            if not campos(L, CAMPOS["laminado"], r):
                continue
            if not isinstance(L.get("id"), str) or not L.get("id") or L.get("id") in ids:
                err("valor_invalido", r + ".id", "texto unico")
            ids.add(L.get("id"))
            if not isinstance(L.get("pieza"), str) or not L.get("pieza"):
                err("valor_invalido", r + ".pieza", "texto")
            b = L.get("b")
            if not es_num(b):
                err("tipo_invalido", r + ".b", "numero")
            elif b >= 0:
                err("b_no_negativo", r + ".b", "el exponente debe ser < 0: %r" % (b,))
            a = L.get("a_MPa")
            if not es_num(a):
                err("tipo_invalido", r + ".a_MPa", "numero")
            elif a <= 0:
                err("a_no_positivo", r + ".a_MPa", "debe ser > 0: %r" % (a,))
            positivo(L.get("sigma_uts_MPa"), r + ".sigma_uts_MPa")
            positivo(L.get("E0_GPa"), r + ".E0_GPa")
            lo, hi = L.get("nivel_min_pct"), L.get("nivel_max_pct")
            if not es_num(lo) or not es_num(hi):
                err("tipo_invalido", r + ".nivel_*_pct", "numeros")
            elif lo >= hi:
                err("intervalo_invertido", r, "nivel_min_pct (%r) debe ser menor que nivel_max_pct (%r)" % (lo, hi))
            t = L.get("rigidez")
            if not (isinstance(t, list) and len(t) >= 2 and all(isinstance(p, list) and len(p) == 2
                                                                and all(es_num(x) for x in p) for p in t)):
                err("tipo_invalido", r + ".rigidez", "lista de al menos 2 pares [D, d] numericos")
                continue
            if t[0][0] != 0 or t[0][1] != 0:
                err("rigidez_no_empieza_en_cero", r + ".rigidez[0]", "debe ser [0, 0]: %r" % (t[0],))
            for k in range(len(t)):
                if t[k][0] < 0 or t[k][0] > 1:
                    err("rigidez_D_fuera_de_rango", r + ".rigidez[%d]" % k, "D en [0, 1]: %r" % (t[k][0],))
                if k > 0 and not (t[k][0] > t[k - 1][0]):
                    err("rigidez_D_no_creciente", r + ".rigidez[%d]" % k, "D debe crecer: %r -> %r" % (t[k - 1][0], t[k][0]))
                if k > 0 and t[k][1] < t[k - 1][1]:
                    err("rigidez_d_decreciente", r + ".rigidez[%d]" % k, "d no puede bajar: %r -> %r" % (t[k - 1][1], t[k][1]))
    return {"ok": not errores, "errores": errores}


# ---- generador con semilla (el de 39_mat_modelo.js, en aritmetica de 32 bits) ------------
M32 = 0xFFFFFFFF


def _i32(x):
    x &= M32
    return x - (1 << 32) if x & 0x80000000 else x


def _imul(a, b):
    return _i32((a & M32) * (b & M32))


def _ushr(x, n):
    return (x & M32) >> n


def mezcla(x):
    x = _imul(x ^ _ushr(x, 16), 0x85ebca6b)
    x = _imul(x ^ _ushr(x, 13), 0xc2b2ae35)
    return _i32(x ^ _ushr(x, 16))


def semilla_laminado(semilla, i):
    return mezcla(_i32(semilla + _imul(i, 0x9E3779B9)))


class Generador:
    """mulberry32 + Box-Muller, igual que 24_sust_emulador.js y 39_mat_modelo.js."""

    def __init__(self, s):
        self.s = _i32(s)

    def azar(self):
        a = self.s = _i32(self.s + 0x6D2B79F5)
        t = _imul(a ^ _ushr(a, 15), 1 | a)
        t = _i32(_i32(t + _imul(t ^ _ushr(t, 7), 61 | t)) ^ t)
        return _ushr(t ^ _ushr(t, 14), 0) / 4294967296.0

    def normal(self):
        u1 = 1 - self.azar()
        u2 = self.azar()
        return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


# ---- cuentas ----------------------------------------------------------------------------
def rigidez(L, D):
    t = L["rigidez"]
    if D <= t[0][0]:
        return t[0][1]
    if D >= t[-1][0]:
        return t[-1][1]
    for k in range(1, len(t)):
        if D <= t[k][0]:
            (D0, d0), (D1, d1) = t[k - 1], t[k]
            return d0 + (d1 - d0) * (D - D0) / (D1 - D0)
    return t[-1][1]


def nivel(cfg, D):
    u = cfg["umbrales_D"]
    if D >= u["falla"]:
        return "falla"
    if D >= u["critica"]:
        return "critica"
    if D >= u["preventiva"]:
        return "preventiva"
    return "normal"


def cent(x):
    """Centesimas de volt enteras, floor(x * 100 + 0.5), igual que en JS."""
    return math.floor(x * 100 + 0.5)


def peso_modelo(cfg, peso_V):
    A = cfg["ajuste_nivel"]
    c, t = cent(peso_V), cent(A["tolerancia_V"])
    for n in A["niveles_V"]:
        if abs(c - cent(n)) <= t:
            return n, n != peso_V
    return peso_V, False


def punto(cfg, L, peso_V, D_antes=0.0):
    c = cfg["carga"]
    pm, ajustado = peso_modelo(cfg, peso_V)
    f = pm / c["senal_ref_V"]
    smax = c["sigma_ref_MPa"] * (c["R_ref"] + (1 - c["R_ref"]) * f)
    smin = c["sigma_ref_MPa"] * c["R_ref"]
    lo = L["nivel_min_pct"] / 100.0 * L["sigma_uts_MPa"]
    hi = L["nivel_max_pct"] / 100.0 * L["sigma_uts_MPa"]
    region = "bajo" if smax < lo else ("sobre" if smax > hi else "dentro")
    N_aj = N_us = None
    dD = 0.0
    if region == "dentro":
        N_aj = (smax / L["a_MPa"]) ** (1.0 / L["b"])
        N_us = min(N_aj, cfg["n_tope_ciclos"])
        dD = cfg["ciclos_por_paso"] / N_us
    d_antes = rigidez(L, D_antes)
    galga = (smax - smin) / (L["E0_GPa"] * 1000.0 * (1 - d_antes)) * 1e6
    return {"peso_V": peso_V, "peso_modelo_V": pm, "ajustado": ajustado, "f": f, "sigma_max": smax, "sigma_min": smin, "delta_sigma": smax - smin, "region": region,
            "N_ajuste": N_aj, "N_usado": N_us, "dD": dD, "d_antes": d_antes, "galga_sin_ruido": galga,
            "intervalo_MPa": [lo, hi]}


class Acumulador:
    """D, conteos y generador por laminado a lo largo de una secuencia de pasos."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.pasos = 0
        self.sin_peso = 0
        self.ajustados = 0
        self.lam = [{"id": L["id"], "D": 0.0, "nivel": "normal", "conteos": {"dentro": 0, "bajo": 0, "sobre": 0},
                     "gen": Generador(semilla_laminado(cfg["galga"]["semilla"], i)), "cruces": {}}
                    for i, L in enumerate(cfg["laminados"])]

    def paso(self, peso_V):
        self.pasos += 1
        if not es_num(peso_V):
            self.sin_peso += 1
            return None
        if peso_modelo(self.cfg, peso_V)[1]:
            self.ajustados += 1
        res = []
        for L, S in zip(self.cfg["laminados"], self.lam):
            p = punto(self.cfg, L, peso_V, S["D"])
            ruido = self.cfg["galga"]["ruido_sd_ue"] * S["gen"].normal()
            S["conteos"][p["region"]] += 1
            S["D"] += p["dD"]
            nuevo = nivel(self.cfg, S["D"])
            if nuevo != S["nivel"]:
                S["cruces"][nuevo] = self.pasos
            S["nivel"] = nuevo
            res.append(dict(p, id=L["id"], D=S["D"], d=rigidez(L, S["D"]), nivel=nuevo,
                            deformacion_ue=p["galga_sin_ruido"] + ruido))
        return res


def pasos_caja(ruta, desde, hasta):
    """Eventos paso_caja con ts_salida en [desde, hasta], ordenados por ts_salida.
    Las marcas son ISO 8601 en UTC con Z; se comparan como texto de ancho fijo."""
    evs = []
    for l in pathlib.Path(ruta).read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        e = json.loads(l)
        if e.get("ev") != "paso_caja":
            continue
        ts = e.get("ts_salida") or e.get("ts")
        if desde <= ts <= hasta:
            evs.append(e)
    evs.sort(key=lambda e: e.get("ts_salida") or e.get("ts"))
    return evs


def recalcula(cfg, eventos):
    A = Acumulador(cfg)
    for e in eventos:
        A.paso(e.get("peso_V"))
    return {"cajas": len(eventos), "pasos": A.pasos, "sin_peso": A.sin_peso, "ajustados": A.ajustados,
            "laminados": [{"id": S["id"], "D": S["D"], "nivel": S["nivel"], "conteos": dict(S["conteos"]),
                           "cruces": dict(S["cruces"])} for S in A.lam]}


# ---- referencia (Anexo B) ---------------------------------------------------------------
PESOS_REF = [7.50, 7.49, 7.47, 7.53, 7.46, 7.54, 6.75, 6.74, 5.00, 4.97, 5.04, 8.36, 8.48, 8.49, 9.27, 9.28, 10.00]


def referencia(cfg):
    filas = []
    for v in PESOS_REF:
        fila = {"peso_V": v}
        for L in cfg["laminados"]:
            p = punto(cfg, L, v)
            fila["sigma_max"] = p["sigma_max"]
            fila[L["id"]] = p
        filas.append(fila)
    return filas


def _fmt(x, dec):
    return "" if x is None else ("%." + str(dec) + "f") % x


def imprime_referencia(cfg):
    ids = [L["id"] for L in cfg["laminados"]]
    cab = ["peso_V", "peso_modelo_V", "ajustado", "sigma_max (MPa)"]
    for i in ids:
        cab += ["%s region" % i, "%s N del ajuste" % i, "%s N usado" % i, "%s dD" % i]
    print("| " + " | ".join(cab) + " |")
    print("|" + "---|" * len(cab))
    for f in referencia(cfg):
        p0 = f[ids[0]]
        celdas = ["%.2f" % f["peso_V"], "%.2f" % p0["peso_modelo_V"], "si" if p0["ajustado"] else "no", "%.4f" % f["sigma_max"]]
        for i in ids:
            p = f[i]
            celdas += [p["region"], _fmt(p["N_ajuste"], 4), _fmt(p["N_usado"], 4),
                       "%.8f" % p["dD"] if p["dD"] else "0"]
        print("| " + " | ".join(celdas) + " |")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=["valida", "referencia", "recalcula"])
    ap.add_argument("--config", default=str(CONFIG))
    ap.add_argument("--apaga", default="", help="valida: codigos de regla a apagar (prueba de mutacion)")
    ap.add_argument("--eventos")
    ap.add_argument("--desde")
    ap.add_argument("--hasta")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    cfg = carga_config(a.config)
    if a.modo == "valida":
        r = valida(cfg, [x for x in a.apaga.split(",") if x])
        if a.json:
            print(json.dumps(r, ensure_ascii=False))
        else:
            print("%s: %s" % (a.config, "valida" if r["ok"] else "%d errores" % len(r["errores"])))
            for e in r["errores"]:
                print("  %-28s %-34s %s" % (e["codigo"], e["ruta"], e["detalle"]))
        sys.exit(len(r["errores"]))
    v = valida(cfg)
    if not v["ok"]:
        sys.exit("configuracion invalida: %s" % ", ".join(e["codigo"] for e in v["errores"]))
    if a.modo == "referencia":
        imprime_referencia(cfg)
        return
    if not (a.eventos and a.desde and a.hasta):
        ap.error("recalcula necesita --eventos, --desde y --hasta")
    evs = pasos_caja(a.eventos, a.desde, a.hasta)
    r = recalcula(cfg, evs)
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        print("eventos %s, de %s a %s (ts_salida)" % (a.eventos, a.desde, a.hasta))
        print("cajas %d, pasos sin peso %d" % (r["cajas"], r["sin_peso"]))
        for L in r["laminados"]:
            c = L["conteos"]
            print("  laminado %-4s D = %.8f  nivel %-10s dentro %d, bajo %d, sobre %d" %
                  (L["id"], L["D"], L["nivel"], c["dentro"], c["bajo"], c["sobre"]))
    sys.exit(0 if evs else 2)


if __name__ == "__main__":
    main()
