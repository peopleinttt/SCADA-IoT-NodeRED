#!/usr/bin/env python3
"""Pruebas de A2-Planta con el DESVIADOR (R3) contra el sustituto. Python 3.9.

    /usr/bin/python3 pruebas/prueba_desviador.py                       (seguro + control + factibilidad, ~5 min)
    /usr/bin/python3 pruebas/prueba_desviador.py corrida --cajas 200   (~20 min)
    /usr/bin/python3 pruebas/prueba_desviador.py corrida --escenario local_1fps --cajas 30

Las de C4 adaptadas a la escena Sorting by Weight: tres salidas por clase de
peso, cada una confirmada con el sensor de entrada de su salida, bandas de
velocidad fija. Configuracion: config/planta_desviador.json (cliente),
config/sustituto_desviador.json y config/mapa_registros_desviador.json
(sustituto). El cliente va por proxy_retardo.py, como en C4.

Oraculo: el registro del sustituto (caja_emitida con su masa, caja_desviada
con la rama por la que salio de verdad).
"""
import argparse, json, pathlib, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
sys.path.insert(0, str(RAIZ / "tools"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
import limites_planta as lp  # noqa: E402
from proxy_retardo import Proxy, escrituras  # noqa: E402
from modbus_tcp import Cliente  # noqa: E402

verifica = ps.verifica
CFG = json.loads((RAIZ / "config" / "planta_desviador.json").read_text(encoding="utf-8"))
MAPA = {e["nombre"]: e for e in json.loads((RAIZ / "config" / "mapa_registros_desviador.json").read_text(encoding="utf-8"))["etiquetas"]}
ESC = {e["nombre"]: e for e in CFG["escenarios"]}
TOL_MASA = pp.TOL_MASA


def arranca(escenario, datos, **extra):
    e = ESC[escenario]
    proxy = Proxy(pp.PUERTO_PROXY, ("127.0.0.1", 5020), 0 if e["rtt_ms"] <= 5 else e["rtt_ms"]).inicia()
    env = dict(A2_MAPA=RAIZ / "config" / "mapa_registros_desviador.json",
               A2_SUST_CONFIG=RAIZ / "config" / "sustituto_desviador.json",
               A2_PLANTA_CONFIG=RAIZ / "config" / "planta_desviador.json",
               A2_MODBUS_HOST="127.0.0.1", A2_MODBUS_PUERTO=pp.PUERTO_PROXY,
               A2_SONDEO_MS=e["sondeo_ms"], A2_RTT_PREVISTO_MS=e["rtt_ms"], A2_REFRESCO_MS=e.get("refresco_ms", 0))
    if e.get("lecturas_para_cambio"):
        env["A2_LECTURAS_PARA_CAMBIO"] = e["lecturas_para_cambio"]
    env.update(extra)
    ps.arranca(datos, **env)
    ok = pp.espera(lambda: pp.estado()["com"] == "ok", 30)
    verifica("el cliente con desviador conecta (%s) y queda en ok" % escenario, ok)
    return proxy


def reales(datos):
    real = {}
    for x in ps.eventos(datos):
        if x["ev"] == "caja_emitida":
            real[x["caja"]] = {"masa": x["masa_kg"], "rama": None, "fuera": False}
        elif x["ev"] == "caja_desviada":
            real[x["caja"]]["rama"] = x["rama"]
        elif x["ev"] == "caja_sale":
            real[x["caja"]]["fuera"] = True
    return [real[k] for k in sorted(real)]


def clase_de(masa):
    return next(k for k in CFG["desviador"]["clases"] if k["hasta_kg"] is None or masa <= k["hasta_kg"])


# ---- corrida -------------------------------------------------------------------------
def corrida(escenario, n):
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_desv_corrida_"))
    e = ESC[escenario]
    print("=== %d cajas con desviador, escenario %s: sondeo %d ms, rtt %d ms, refresco %d ms (datos en %s) ==="
          % (n, escenario, e["sondeo_ms"], e["rtt_ms"], e.get("refresco_ms", 0), datos))
    sust = dict(json.loads((RAIZ / "config" / "sustituto_desviador.json").read_text()))
    if e.get("refresco_ms"):
        # El sustituto publica un cuadro cada refresco_ms, como Factory I/O a 1 FPS.
        sust["refresco_s"] = e["refresco_ms"] / 1000
        ruta = datos / "sustituto_refresco.json"
        ruta.write_text(json.dumps(sust))
        proxy = arranca(escenario, datos, A2_SUST_CONFIG=ruta)
    else:
        proxy = arranca(escenario, datos)
    try:
        st = pp.estado()
        py = lp.calcula(CFG, e["sondeo_ms"], e["rtt_ms"], None, e.get("refresco_ms", 0))
        verifica("limites del cliente = tools/limites_planta.py (factible %s, T_ef %d ms)" % (py["factible"], py["t_ef_ms"]),
                 (st["limites"]["factible"], st["limites"]["t_ef_ms"]) == (py["factible"], py["t_ef_ms"]), (st["limites"], py))
        c, r = pp.comando(accion="velocidad", vel_V=2)
        verifica("con bandas fijas, velocidad -> 422 velocidad_no_aplica", c == 422 and r.get("motivo") == "velocidad_no_aplica", (c, r))
        if not py["factible"]:
            c, r = pp.comando(accion="marcha")
            verifica("no factible: marcha -> 409, la corrida no se hace", c == 409, (c, r))
            return
        pp.comando(accion="marcha")
        pp.comando(accion="emisor", valor=True)
        t0 = time.time()
        pp.espera(lambda: sum(1 for x in ps.eventos(datos) if x["ev"] == "caja_emitida") >= n, n * 8 + 60, paso=0.5)
        pp.comando(accion="emisor", valor=False)
        pp.espera(lambda: all(r["fuera"] for r in reales(datos)) and not pp.estado()["en_tramo"], 120, paso=1)
        pp.comando(accion="paro")
        dur = time.time() - t0
        st = pp.estado()
        k = st["contadores"]
        R = reales(datos)
        pasos = sorted((x for x in pp.eventos(datos, "a2_planta_eventos.jsonl") if x["ev"] == "paso_caja"), key=lambda x: x["caja"])
        print("  %.0f s; sustituto %d cajas %s; cliente: entran %d, salen %d, por destino %s, perdidas %d, fantasmas %d+%d, "
              "desvios erroneos %d" % (dur, len(R), {r: sum(1 for x in R if x["rama"] == r) for r in ("left", "forward", "right")},
                                       k["entradas"], k["salidas"], k["por_destino"], k["perdidas"], k["fantasmas"],
                                       k["fantasmas_bascula"], k["desvios_erroneos"]))
        print("  periodo efectivo (ms): %s" % st["periodo_efectivo_ms"])
        print("  lecturas minimas por pulso: %s" % st["min_lecturas_por_pulso"])
        verifica("el sustituto emitio %d cajas y todas salieron" % n, len(R) >= n and all(r["fuera"] for r in R), len(R))
        ids = [p["caja"] for p in pasos]
        verifica("un paso_caja por caja, sin duplicados (%d de %d)" % (len(pasos), len(R)),
                 len(pasos) == len(R) and len(set(ids)) == len(ids))
        verifica("sin perdidas, fantasmas ni desvios erroneos",
                 k["perdidas"] == k["fantasmas"] == k["fantasmas_bascula"] == k["desvios_erroneos"] == 0, k)
        verifica("balance: entradas = salidas = cajas del sustituto", k["entradas"] == k["salidas"] == len(R))
        err = [abs(p["masa_kg"] - r["masa"]) for p, r in zip(pasos, R) if p["masa_kg"] is not None]
        verifica("masa medida = real, caja por caja, +-%.2f kg (peor %.3f)" % (TOL_MASA, max(err or [9])),
                 len(err) == len(R) and max(err) <= TOL_MASA)
        verifica("destino del cliente = rama real, caja por caja", [p["destino"] for p in pasos] == [r["rama"] for r in R])
        lim = [k_["hasta_kg"] for k_ in CFG["desviador"]["clases"] if k_["hasta_kg"] is not None]
        claras = [(p, r) for p, r in zip(pasos, R) if all(abs(r["masa"] - u) > TOL_MASA for u in lim)]
        verifica("cada caja sale por la clase de su masa real (%d cajas; %d a menos de %.2f kg de un umbral se excluyen)"
                 % (len(claras), len(R) - len(claras), TOL_MASA),
                 all(r["rama"] == clase_de(r["masa"])["destino"] for _, r in claras))
        m = st["min_lecturas_por_pulso"]
        verifica("cada pulso de sensor se vio en al menos %d lecturas" % CFG["periodos_minimos"],
                 all(v >= CFG["periodos_minimos"] for v in m.values()) and len(m) >= 4, m)
        verifica("conteos por destino = ramas del sustituto",
                 k["por_destino"] == {r: sum(1 for x in R if x["rama"] == r) for r in k["por_destino"]})
    finally:
        proxy.detiene()


# ---- estado seguro ---------------------------------------------------------------------
def seguro():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_desv_seguro_"))
    print("=== Estado seguro con desviador (datos en %s) ===" % datos)
    proxy = arranca("local", datos)
    R = CFG["roles"]
    SEGURA = [(5, MAPA[R["emisor"]]["direccion"], 0)] + [(5, MAPA[a]["direccion"], 0) for a in R["alimentacion"]]
    try:
        cable = [(f, d, v) for _, f, d, v in escrituras(proxy.del_cliente)]
        verifica("al arrancar, en el cable: emitter=0, entry_conveyor=0, load_scale=0, en ese orden",
                 cable[:3] == SEGURA, cable[:4])
        pp.comando(accion="marcha")
        pp.comando(accion="emisor", valor=True)
        verifica("con la linea en marcha entran cajas", pp.espera(lambda: pp.estado()["contadores"]["entradas"] >= 2, 40))
        en_tramo = len(pp.estado()["en_tramo"])
        t_corte = time.time()
        proxy.detiene()
        sin = pp.espera(lambda: pp.estado()["com"] == "sin_comunicacion", 10, paso=0.1)
        tarda = time.time() - t_corte
        lim = pp.estado()["limites"]
        verifica("al cortar, sin comunicacion en %.1f s (< timeout %d ms + 1 s)" % (tarda, lim["timeout_com_ms"]),
                 sin and tarda < lim["timeout_com_ms"] / 1000 + 1)
        c, r = pp.comando(accion="marcha")
        verifica("sin comunicacion, marcha -> 409", c == 409, (c, r))
        time.sleep(2)
        proxy.inicia()
        verifica("al volver la red queda en ok", pp.espera(lambda: pp.estado()["com"] == "ok", 20, paso=0.1))
        st = pp.estado()
        verifica("y la linea queda detenida", st["linea"] == "detenida", st["linea"])
        cable = [(f, d, v) for _, f, d, v in escrituras(proxy.del_cliente, t_corte)]
        verifica("tras reconectar, en el cable: emitter=0, entry_conveyor=0, load_scale=0, en ese orden",
                 cable[:3] == SEGURA, cable[:5])
        verifica("las %d cajas del tramo se marcan como perdidas por la desconexion" % en_tramo,
                 st["contadores"]["perdidas_desconexion"] >= en_tramo, st["contadores"])
        c, r = pp.comando(accion="marcha")
        verifica("despues, marcha vuelve a funcionar", c == 200, (c, r))
    finally:
        proxy.detiene()


# ---- control: desvio forzado por fuera del cliente ------------------------------------------------
def control():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_desv_control_"))
    print("=== Control: ruedas forzadas a la izquierda por fuera del cliente (datos en %s) ===" % datos)
    proxy = arranca("local", datos)
    try:
        pp.comando(accion="marcha")
        pp.comando(accion="emisor", valor=True)
        with Cliente("127.0.0.1", 5020) as c:
            fin = time.time() + 120
            while time.time() < fin and sum(1 for x in ps.eventos(datos) if x["ev"] == "caja_emitida") < 6:
                # Se pisa la orden del cliente: siempre izquierda.
                c.escribe_bobina(MAPA["send_right"]["direccion"], False)
                c.escribe_bobina(MAPA["send_forward"]["direccion"], False)
                c.escribe_bobina(MAPA["send_left"]["direccion"], True)
                time.sleep(0.05)
            pp.comando(accion="emisor", valor=False)
            fin = time.time() + 90
            while time.time() < fin and not all(r["fuera"] for r in reales(datos)):
                c.escribe_bobina(MAPA["send_right"]["direccion"], False)
                c.escribe_bobina(MAPA["send_forward"]["direccion"], False)
                c.escribe_bobina(MAPA["send_left"]["direccion"], True)
                time.sleep(0.05)
        pp.espera(lambda: not pp.estado()["en_tramo"], 30, paso=1)
        st = pp.estado()
        k = st["contadores"]
        R = reales(datos)
        mal = sum(1 for r in R if clase_de(r["masa"])["destino"] != "left")
        print("  sustituto: %d cajas, %d por la izquierda, %d de ellas no eran de esa clase; cliente: entran %d, salen %d, "
              "desvios erroneos %d, perdidas %d, por destino %s"
              % (len(R), sum(1 for r in R if r["rama"] == "left"), mal, k["entradas"], k["salidas"], k["desvios_erroneos"],
                 k["perdidas"], k["por_destino"]))
        verifica("todas salieron por la izquierda (el forzado funciono)", all(r["rama"] == "left" for r in R), [r["rama"] for r in R])
        verifica("el cliente marca un desvio erroneo por cada caja que no era de esa clase (%d)" % mal,
                 k["desvios_erroneos"] == mal and mal >= 1)
        verifica("balance completo: entradas = salidas = cajas del sustituto, ninguna sin contar",
                 k["entradas"] == k["salidas"] == len(R) and not st["en_tramo"])
        verifica("y por destino cuenta donde fueron de verdad (left = %d)" % len(R), k["por_destino"].get("left") == len(R))
    finally:
        proxy.detiene()


def factibilidad():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_desv_factible_"))
    print("=== Escenario medido el 24 oct (500 ms, rtt 1890 ms, 1 FPS): no factible ===")
    proxy = arranca("azure_medido_24oct", datos, A2_MODBUS_PUERTO=5020)  # sin el retardo: solo se mira el calculo
    try:
        st = pp.estado()
        verifica("factible false, con los problemas en el estado (T_ef %d ms)" % st["limites"]["t_ef_ms"],
                 st["limites"]["factible"] is False and len(st["limites"]["problemas"]) >= 1, st["limites"])
        n0 = st["contadores"]["sondeos"]
        time.sleep(3)
        verifica("el cliente sigue corriendo (sondea y queda en ok)",
                 pp.estado()["contadores"]["sondeos"] > n0 and pp.estado()["com"] == "ok")
        c, r = pp.comando(accion="marcha")
        verifica("y marcha -> 409 limites_no_factibles", c == 409 and r.get("motivo") == "limites_no_factibles", (c, r))
    finally:
        proxy.detiene()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("modo", nargs="?", default="rapidas", choices=["rapidas", "corrida", "seguro", "control", "factibilidad"])
    p.add_argument("--escenario", choices=sorted(ESC), default="local")
    p.add_argument("--cajas", type=int, default=200)
    a = p.parse_args()
    try:
        if a.modo == "corrida":
            corrida(a.escenario, a.cajas)
        elif a.modo == "rapidas":
            seguro(); control(); factibilidad()
        else:
            {"seguro": seguro, "control": control, "factibilidad": factibilidad}[a.modo]()
    finally:
        ps.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
