#!/usr/bin/env python3
"""Pruebas de A2-Planta (C4) contra el sustituto, con latencia simulada. Python 3.9.

    /usr/bin/python3 pruebas/prueba_planta.py seguro                    (~1.5 min)
    /usr/bin/python3 pruebas/prueba_planta.py corrida --escenario local (~20 min, 200 cajas, sondeo 250 ms)
    /usr/bin/python3 pruebas/prueba_planta.py corrida --escenario azure (~20 min, 200 cajas, 500 ms + 200 ms)
    /usr/bin/python3 pruebas/prueba_planta.py control                   (~3 min)

El cliente nunca habla directo con el sustituto: va por pruebas/proxy_retardo.py
(127.0.0.1:5030 -> 5020), que agrega el tiempo de ida y vuelta del escenario
sin tocar el sustituto, y que sirve tambien para cortar la conexion a la mala.

Oraculo: el registro de eventos del SUSTITUTO (que caja se emitio, con que
masa, si salio o la empujaron). Lo que reporta el cliente se compara contra
eso caja por caja.
"""
import argparse, json, os, pathlib, sys, tempfile, time, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
sys.path.insert(0, str(RAIZ / "tools"))
import prueba_sustituto as ps  # noqa: E402
import limites_planta as lp  # noqa: E402
from proxy_retardo import Proxy, escrituras  # noqa: E402
from modbus_tcp import Cliente  # noqa: E402

verifica = ps.verifica
CFG = json.loads((RAIZ / "config" / "planta_a2.json").read_text(encoding="utf-8"))
ESC = {e["nombre"]: e for e in CFG["escenarios"]}
URL = "http://127.0.0.1:%d/a2/planta" % ps.PUERTO_NR
PUERTO_PROXY = 5030
# Exactitud exigida a la masa. Con 500 ms entre lecturas y tau = 0.3 s la
# ultima lectura valida puede caer ~1.5 s dentro de la bascula: 0.6 % de
# residuo, 0.11 kg en una caja de 18 kg. Las cajas a menos de esto del limite
# de tolerancia no cuentan para la prueba de clasificacion.
TOL_MASA = 0.15


def estado():
    return json.load(urllib.request.urlopen(URL + "/estado", timeout=5))


def comando(**c):
    r = urllib.request.Request(URL + "/comando", data=json.dumps(c).encode(),
                               headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=5) as x:
            return x.status, json.load(x)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def espera(cond, limite_s, paso=0.25):
    fin = time.time() + limite_s
    while time.time() < fin:
        try:
            v = cond()
            if v:
                return v
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(paso)
    return None


def eventos(datos, nombre):
    ruta = datos / nombre
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def arranca(escenario, datos, **extra):
    e = ESC[escenario]
    rtt_proxy = 0 if escenario == "local" else e["rtt_ms"]
    proxy = Proxy(PUERTO_PROXY, ("127.0.0.1", 5020), rtt_proxy).inicia()
    env = dict(A2_PLANTA_CONFIG=RAIZ / "config" / "planta_a2.json",
               A2_MODBUS_HOST="127.0.0.1", A2_MODBUS_PUERTO=PUERTO_PROXY,
               A2_SONDEO_MS=e["sondeo_ms"], A2_RTT_PREVISTO_MS=e["rtt_ms"])
    env.update(extra)
    ps.arranca(datos, **env)
    ok = espera(lambda: estado()["com"] == "ok", 30)
    verifica("el cliente conecta por el proxy (%s, %d ms de ida y vuelta) y queda en ok" % (escenario, rtt_proxy), ok)
    return proxy


# ---- estado seguro -----------------------------------------------------------------
def seguro():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_seguro_"))
    print("=== Estado seguro tras una desconexion forzada (datos en %s) ===" % datos)
    proxy = arranca("local", datos)
    try:
        ini = eventos(datos, "a2_planta_eventos.jsonl")
        orden = [x["ev"] if x["ev"] != "escritura" else "escritura:%s=%s" % (x["etiqueta"], x["valor"]) for x in ini][:5]
        verifica("al arrancar: vel_banda_V=0, emisor_on=0 y alimentacion_on=0, en ese orden, antes de quedar en ok",
                 orden == ["reconexion_inicia", "escritura:vel_banda_V=0", "escritura:emisor_on=False",
                           "escritura:alimentacion_on=False", "reconexion_completa"], orden)
        vel, emi, ali = (ps.E[k]["direccion"] for k in ("vel_banda_V", "emisor_on", "alimentacion_on"))
        SEGURA = [(6, vel, 0), (5, emi, 0), (5, ali, 0)]
        cable = [(f, d, v) for _, f, d, v in escrituras(proxy.del_cliente)]
        verifica("y en el cable son las tres primeras escrituras, en ese orden", cable[:3] == SEGURA, cable[:4])

        print("--- consignas ---")
        lim = estado()["limites"]
        c, r = comando(accion="marcha")
        verifica("marcha con consigna 0 -> 422 consigna_fuera_de_intervalo",
                 c == 422 and r.get("motivo") == "consigna_fuera_de_intervalo", (c, r))
        bajo = round(lim["vel_min_V"] - 0.01, 2)
        c, r = comando(accion="velocidad", vel_V=bajo)
        verifica("consigna %.2f V, 0.01 debajo del minimo -> 422" % bajo,
                 c == 422 and r.get("motivo") == "velocidad_fuera_de_limite", (c, r))
        c, r = comando(accion="velocidad", vel_V=round(lim["vel_max_V"] + 0.01, 2))
        verifica("consigna 0.01 V arriba del maximo -> 422", c == 422, (c, r))
        c, r = comando(accion="velocidad", vel_V=0)
        verifica("consigna 0 (paro) se acepta", c == 200, (c, r))
        c, r = comando(accion="velocidad", vel_V=lim["vel_min_V"])
        verifica("consigna justo en el minimo (%.2f V) se acepta" % lim["vel_min_V"], c == 200, (c, r))
        n_cable = len(escrituras(proxy.del_cliente))
        verifica("los comandos rechazados no escribieron nada en el cable", n_cable == 3, n_cable)

        print("--- desconexion forzada ---")
        comando(accion="velocidad", vel_V=3.0)
        comando(accion="marcha")
        comando(accion="emisor", valor=True)
        verifica("con la linea en marcha entran cajas", espera(lambda: estado()["contadores"]["entradas"] >= 2, 40))
        en_tramo = len(estado()["en_tramo"])
        n_sust = len(ps.eventos(datos))
        t_corte = time.time()
        proxy.detiene()
        sin = espera(lambda: estado()["com"] == "sin_comunicacion", 10, paso=0.1)
        tarda = time.time() - t_corte
        verifica("al cortar, la linea queda sin comunicacion en menos de %.1f s (tardo %.1f s)"
                 % (CFG["comunicacion_timeout_ms"] / 1000 + 1, tarda),
                 sin and tarda < CFG["comunicacion_timeout_ms"] / 1000 + 1)
        c, r = comando(accion="marcha")
        verifica("sin comunicacion, un comando se rechaza con 409", c == 409, (c, r))
        time.sleep(3)
        escrito_en_corte = [x for x in ps.eventos(datos)[n_sust:] if x["ev"] == "entrada"]
        verifica("durante el corte la planta no recibio ninguna escritura", not escrito_en_corte, escrito_en_corte)
        n_sust = len(ps.eventos(datos))
        n_pl = len(eventos(datos, "a2_planta_eventos.jsonl"))
        proxy.inicia()
        ok = espera(lambda: estado()["com"] == "ok", 20, paso=0.1)
        verifica("al volver la red, el cliente reconecta y queda en ok", ok)
        st = estado()
        verifica("y la linea queda detenida, sin reanudar sola", st["linea"] == "detenida", st["linea"])
        # Orden en el cable, no en el sustituto: el sustituto mira sus entradas cada
        # 100 ms y dos escrituras a 3 ms de distancia le caen en el mismo tick.
        cable = [(f, d, v) for _, f, d, v in escrituras(proxy.del_cliente, t_corte)]
        verifica("en el cable, tras reconectar: FC6 vel_banda_V=0, FC5 emisor_on=0, FC5 alimentacion_on=0, en ese orden",
                 cable[:3] == SEGURA, cable[:5])
        pl = [x["ev"] for x in eventos(datos, "a2_planta_eventos.jsonl")[n_pl:]]
        verifica("el cliente registro reconexion_inicia -> reconexion_completa",
                 "reconexion_inicia" in pl and "reconexion_completa" in pl
                 and pl.index("reconexion_inicia") < pl.index("reconexion_completa"), pl)
        desc = [x for x in eventos(datos, "a2_planta_eventos.jsonl") if x["ev"] == "cajas_descartadas_por_desconexion"]
        verifica("las %d cajas que estaban en el tramo se marcan como perdidas por la desconexion" % en_tramo,
                 st["contadores"]["perdidas_desconexion"] >= en_tramo and len(desc) == 1, st["contadores"])
        c, r = comando(accion="marcha")
        verifica("despues, marcha vuelve a funcionar", c == 200, (c, r))
        time.sleep(1)
        cable = [(f, d, v) for _, f, d, v in escrituras(proxy.del_cliente, t_corte)]
        verifica("y la consigna de 3 V llega a la planta despues de la secuencia segura",
                 (6, vel, 300) in cable[3:], cable)
        # El sustituto ya estaba en 3 V antes del corte y el 0 intermedio le duro
        # menos de un tick, asi que no registra cambio: se lee el registro directo.
        with Cliente("127.0.0.1", 5020) as c:
            palabra = c.lee_retencion(vel, 1)[0]
        verifica("y el registro del sustituto queda en 3 V (palabra 300)", palabra == 300, palabra)
    finally:
        proxy.detiene()

    print("--- limites no factibles (sondeo de 3000 ms) ---")
    proxy = arranca("local", datos, A2_SONDEO_MS=3000)
    try:
        lim = estado()["limites"]
        verifica("con sondeo de 3000 ms los limites salen no factibles", lim["factible"] is False, lim)
        c, r = comando(accion="marcha")
        verifica("y marcha -> 409 limites_no_factibles", c == 409 and r.get("motivo") == "limites_no_factibles", (c, r))
        time.sleep(10)
        st = estado()
        verifica("con 3000 ms entre lecturas la comunicacion no oscila (timeout %d ms, 0 desconexiones en 10 s)"
                 % lim["timeout_com_ms"], st["com"] == "ok" and st["contadores"]["desconexiones"] == 0,
                 (st["com"], st["contadores"]["desconexiones"]))
    finally:
        proxy.detiene()


# ---- corrida de N cajas ---------------------------------------------------------------
def corrida(escenario, n):
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_corrida_%s_" % escenario))
    e = ESC[escenario]
    print("=== %d cajas, escenario %s: sondeo %d ms, %d ms de ida y vuelta (datos en %s) ==="
          % (n, escenario, e["sondeo_ms"], e["rtt_ms"], datos))
    proxy = arranca(escenario, datos)
    try:
        lim = estado()["limites"]
        py = lp.calcula(CFG, e["sondeo_ms"], e["rtt_ms"], lp.tope_del_mapa())
        verifica("limites del cliente = tools/limites_planta.py (%s .. %s V)" % (py["vel_min_V"], py["vel_max_V"]),
                 (lim["vel_min_V"], lim["vel_max_V"], lim["t_ef_ms"]) == (py["vel_min_V"], py["vel_max_V"], py["t_ef_ms"]),
                 (lim, py))
        vel = lim["vel_max_V"]
        c, _ = comando(accion="velocidad", vel_V=vel + 0.01)
        verifica("una consigna 0.01 V arriba del limite se rechaza", c == 422)
        for cmd in ({"accion": "velocidad", "vel_V": vel}, {"accion": "marcha"}, {"accion": "emisor", "valor": True}):
            comando(**cmd)
        t0 = time.time()
        # Se apaga el emisor en cuanto el sustituto emitio n cajas.
        espera(lambda: sum(1 for x in ps.eventos(datos) if x["ev"] == "caja_emitida") >= n, n * 8 + 60, paso=0.5)
        comando(accion="emisor", valor=False)
        def todas_fuera():
            ev = ps.eventos(datos)
            emit = sum(1 for x in ev if x["ev"] == "caja_emitida")
            fuera = sum(1 for x in ev if x["ev"] in ("caja_sale", "caja_rechazada"))
            return emit == fuera and not estado()["en_tramo"]
        espera(todas_fuera, 120, paso=1)
        comando(accion="paro")
        dur = time.time() - t0
        st = estado()
        sust = ps.eventos(datos)
        real = {}
        for x in sust:
            if x["ev"] == "caja_emitida":
                real[x["caja"]] = {"masa": x["masa_kg"], "destino": None}
            elif x["ev"] in ("caja_sale", "caja_rechazada"):
                real[x["caja"]]["destino"] = "salida" if x["ev"] == "caja_sale" else "rechazo"
        reales = [real[k] for k in sorted(real)]
        pasos = sorted((x for x in eventos(datos, "a2_planta_eventos.jsonl") if x["ev"] == "paso_caja"),
                       key=lambda x: x["caja"])
        k = st["contadores"]
        print("  %.0f s de corrida a %.2f V; sustituto: %d cajas; cliente: entran %d, salen %d, rechazo %d, "
              "perdidas %d, fantasmas %d+%d, rechazos fallidos %d, lecturas fallidas %d"
              % (dur, vel, len(reales), k["entradas"], k["salidas"], k["rechazos"], k["perdidas"],
                 k["fantasmas"], k["fantasmas_bascula"], k["rechazos_fallidos"], k["lecturas_fallidas"]))
        print("  periodo efectivo (ms): %s" % st["periodo_efectivo_ms"])
        print("  ida y vuelta medida (ms): %s" % st["rtt_medido_ms"])
        print("  lecturas minimas por pulso: %s" % st["min_lecturas_por_pulso"])
        ids = [x["caja"] for x in pasos]
        verifica("el sustituto emitio %d cajas y todas salieron de la linea" % n,
                 len(reales) >= n and all(r["destino"] for r in reales), len(reales))
        verifica("el cliente reporta un paso_caja por caja: %d de %d, sin duplicados"
                 % (len(pasos), len(reales)), len(pasos) == len(reales) and len(set(ids)) == len(ids))
        verifica("sin perdidas, sin fantasmas, sin rechazos fallidos ni fallas del empujador",
                 k["perdidas"] == k["fantasmas"] == k["fantasmas_bascula"] == k["rechazos_fallidos"]
                 == k["fallos_empujador"] == 0, k)
        verifica("balance: entradas = salidas + rechazos", k["entradas"] == k["salidas"] + k["rechazos"] == len(reales))
        errores = [abs(p["masa_kg"] - r["masa"]) for p, r in zip(pasos, reales) if p["masa_kg"] is not None]
        verifica("masa medida = masa real, caja por caja, +-%.2f kg (peor %.3f kg)" % (TOL_MASA, max(errores or [9])),
                 len(errores) == len(reales) and max(errores) <= TOL_MASA)
        verifica("destino del cliente = destino real, caja por caja",
                 [p["destino"] for p in pasos] == [r["destino"] for r in reales])
        nom, tol = CFG["clasificacion"]["masa_nominal_kg"], CFG["clasificacion"]["tolerancia_kg"]
        dudosas = [r for r in reales if abs(abs(r["masa"] - nom) - tol) <= TOL_MASA]
        claras = [(p, r) for p, r in zip(pasos, reales) if r not in dudosas]
        esperado = ["rechazo" if abs(r["masa"] - nom) > tol else "salida" for _, r in claras]
        verifica("rechazos = tolerancia de %.1f +- %.1f kg (%d rechazadas; %d a menos de %.2f kg del limite se excluyen)"
                 % (nom, tol, sum(1 for r in reales if r["destino"] == "rechazo"), len(dudosas), TOL_MASA),
                 [r["destino"] for _, r in claras] == esperado
                 and [p["destino"] for p, _ in claras] == esperado)
        m = st["min_lecturas_por_pulso"]
        verifica("cada pulso de sensor se vio en al menos %d lecturas" % CFG["periodos_minimos"],
                 all(m.get(s, 0) >= CFG["periodos_minimos"] for s in ("sens_entrada", "sens_bascula", "sens_salida")), m)
        return datos
    finally:
        proxy.detiene()


# ---- control: el verificador ve las perdidas ------------------------------------------------
def control():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_control_"))
    print("=== Control: banda a 8 V por fuera del cliente, escenario azure (datos en %s) ===" % datos)
    proxy = arranca("azure", datos)
    try:
        lim = estado()["limites"]
        vel = lim["vel_max_V"]
        for cmd in ({"accion": "velocidad", "vel_V": vel}, {"accion": "marcha"}, {"accion": "emisor", "valor": True}):
            comando(**cmd)
        espera(lambda: estado()["contadores"]["entradas"] >= 1, 30)
        # Directo al sustituto, saltandose al cliente: a 8 V la caja tapa la
        # salida 0.5 s, menos que dos lecturas de 650 ms. Se reescribe cada 2 s
        # porque el cliente vuelve a mandar su consigna.
        with Cliente("127.0.0.1", 5020) as c:
            c.escribe_registro(ps.E["vel_banda_V"]["direccion"], ps.palabra("vel_banda_V", 8.0))
            espera(lambda: sum(1 for x in ps.eventos(datos) if x["ev"] == "caja_emitida") >= 6, 90, paso=0.5)
            comando(accion="emisor", valor=False)
            # Todas las cajas fuera de la linea en el sustituto...
            def fuera_todas():
                c.escribe_registro(ps.E["vel_banda_V"]["direccion"], ps.palabra("vel_banda_V", 8.0))
                ev = ps.eventos(datos)
                return (sum(1 for x in ev if x["ev"] == "caja_emitida") ==
                        sum(1 for x in ev if x["ev"] in ("caja_sale", "caja_rechazada")))
            espera(fuera_todas, 120, paso=1)
        # ...y despues el transito maximo que el cliente se da antes de declarar
        # perdida una caja (misma cuenta que 28_planta_lectura.js), mas margen.
        L = CFG["linea"]
        esperado = L["entrada_a_fin_bascula_m"] / L["alimentacion_m_s"] + L["bascula_a_salida_m"] / (L["k_banda_m_s_por_V"] * vel)
        limite_s = 1.5 * esperado + 3 * lim["t_ef_ms"] / 1000
        print("  esperando el transito maximo del cliente: %.0f s" % (limite_s + 5))
        espera(lambda: not estado()["en_tramo"], limite_s + 5, paso=1)
        st = estado()
        k = st["contadores"]
        ev = ps.eventos(datos)
        emitidas = sum(1 for x in ev if x["ev"] == "caja_emitida")
        fuera = sum(1 for x in ev if x["ev"] in ("caja_sale", "caja_rechazada"))
        print("  sustituto: %d emitidas, %d fuera de la linea; cliente: entran %d, salen %d, rechazo %d, perdidas %d, "
              "fantasmas %d, en tramo %d, lecturas minimas por pulso %s"
              % (emitidas, fuera, k["entradas"], k["salidas"], k["rechazos"], k["perdidas"], k["fantasmas"],
                 len(st["en_tramo"]), st["min_lecturas_por_pulso"]))
        verifica("con la banda mas rapida de lo calculado, el cliente marca cajas perdidas", k["perdidas"] >= 1, k)
        verifica("el cliente vio entrar todas las cajas que emitio el sustituto (%d)" % emitidas, k["entradas"] == emitidas)
        verifica("no queda ninguna caja sin contar en el cliente", not st["en_tramo"], st["en_tramo"])
        verifica("balance completo: salidas + rechazos + perdidas = cajas que salieron de la linea (%d + %d + %d = %d)"
                 % (k["salidas"], k["rechazos"], k["perdidas"], fuera),
                 k["salidas"] + k["rechazos"] + k["perdidas"] == fuera == emitidas)
    finally:
        proxy.detiene()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("modo", choices=["seguro", "corrida", "control"])
    p.add_argument("--escenario", choices=sorted(ESC), default="local")
    p.add_argument("--cajas", type=int, default=200)
    a = p.parse_args()
    try:
        {"seguro": seguro, "control": control}.get(a.modo, lambda: corrida(a.escenario, a.cajas))()
    finally:
        ps.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
