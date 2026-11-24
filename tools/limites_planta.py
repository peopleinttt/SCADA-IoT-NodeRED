#!/usr/bin/env python3
"""Velocidad de banda con la que cada sensor se ve al menos N periodos de sondeo.

Compatible con Python 3.9. Lee config/planta_a2.json y calcula, para cada
escenario (periodo de sondeo y tiempo de ida y vuelta), el intervalo de
vel_banda_V en el que A2-Planta puede seguir las cajas sin depender de una
sola lectura. A2-Planta hace la misma cuenta en Node-RED (26_planta_config.js)
y las pruebas comparan las dos.

    python3 tools/limites_planta.py                    -> tabla de los escenarios
    python3 tools/limites_planta.py --sondeo 500 --rtt 200
    python3 tools/limites_planta.py --escribe          -> guarda el resultado en la configuracion

Modelo (las definiciones van en docs/CICLO_DESARROLLO_A2.md, C4):
  T_ef  = max(sondeo, (lecturas + escrituras por ciclo) x rtt, refresco) + holgura
          el peor espacio entre dos lecturas DISTINTAS: si el ciclo de
          peticiones no cabe en el periodo, manda el ciclo; si la escena
          refresca mas lento que el sondeo (Factory I/O a 1 FPS en la VM),
          manda el refresco, porque leer dos veces el mismo cuadro no suma.
  Con lo MEDIDO (bloque "medido" de la configuracion, tomado con el mismo
  sondeo que se usa), la holgura fija se reemplaza por las medidas:
  T_ef  = max(p95 del periodo efectivo del sondeo,
              (lecturas + escrituras por ciclo) x p95 de la ida y vuelta,
              p95 del refresco de la escena)
          Si el sondeo en uso no es el medido (o el rtt o el refresco vienen
          dados a mano), las medidas no valen y se usa la formula de arriba.
  t_min = periodos_minimos x T_ef
  Un sensor necesita estar ENCENDIDO al menos t_min (si no, la caja pasa en
  menos de N lecturas) y APAGADO al menos t_min entre dos cajas (si no, dos
  cajas se funden en una sola lectura larga y se pierde una). Con L el largo
  que tapa el sensor y dt el intervalo minimo entre cajas:
      encendido  L / v       >= t_min   ->  v <= L / t_min
      apagado    dt - L / v  >= t_min   ->  v >= L / (dt - t_min)
  Los sensores sobre una banda de velocidad fija (banda "alimentacion", o
  "fija" con su v_m_s) no dependen de vel_banda_V: solo se comprueba si
  cumplen. Si NINGUN sensor esta en la banda variable (escena de bandas
  fijas, como Sorting by Weight), no hay intervalo de velocidad que calcular:
  vel_min_V y vel_max_V quedan en None y factible depende solo de esas
  comprobaciones.
"""
import argparse, json, math, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config" / "planta_a2.json"
sys.path.insert(0, str(RAIZ / "tools"))
import mapa_registros as mr  # noqa: E402


def medido_vale(cfg, sondeo_ms):
    """El bloque "medido" vale solo si se midio con este mismo periodo de sondeo y trae los tres p95."""
    m = cfg.get("medido")
    numeros = m and all(isinstance(m.get(k), (int, float)) and not isinstance(m.get(k), bool)
                        for k in ("periodo_p95_ms", "rtt_p95_ms", "refresco_p95_ms"))
    return m if numeros and m.get("sondeo_ms") == sondeo_ms else None


def t_efectivo(cfg, sondeo_ms, rtt_ms, refresco_ms, medido=None):
    """(T_ef en ms, origen). Misma regla que 26_planta_config.js."""
    peticiones = cfg["lecturas_por_ciclo_max"] + cfg["escrituras_por_ciclo_max"]
    if medido:
        return (max(medido["periodo_p95_ms"], peticiones * medido["rtt_p95_ms"], medido["refresco_p95_ms"]),
                "medido")
    return max(sondeo_ms, peticiones * rtt_ms, refresco_ms or 0) + cfg["holgura_ms"], "holgura"


def calcula(cfg, sondeo_ms, rtt_ms, vel_tope_V=None, refresco_ms=0, medido=None):
    L = cfg["linea"]
    t_ef_ms, origen = t_efectivo(cfg, sondeo_ms, rtt_ms, refresco_ms, medido)
    t_min = cfg["periodos_minimos"] * t_ef_ms / 1000.0
    dt = L["intervalo_emision_min_s"]
    k = L.get("k_banda_m_s_por_V")
    sensores, vmax, vmin, problemas = [], math.inf, 0.0, []
    for nombre, s in sorted(L["sensores"].items()):
        largo = s.get("largo_activo_m")
        if s["banda"] in ("alimentacion", "fija", "medida"):
            if s["banda"] == "medida":
                # Tiempos minimos de encendido y apagado medidos con sonda vigila en
                # la escena real (no hay largo ni velocidad que suponer).
                v, on, off = None, s["encendido_min_s"], s["apagado_min_s"]
            else:
                v = L["alimentacion_m_s"] if s["banda"] == "alimentacion" else s["v_m_s"]
                on, off = largo / v, dt - largo / v
            ok = on >= t_min and off >= t_min
            if not ok:
                problemas.append("%s (%s): encendido %.2f s, apagado %.2f s, se necesitan %.2f s"
                                 % (nombre, s["banda"] if v is None else "%.2f m/s" % v, on, off, t_min))
            sensores.append({"sensor": nombre, "banda": s["banda"], "encendido_s": round(on, 3),
                             "apagado_min_s": round(off, 3), "cumple": ok})
        else:
            s_max = largo / t_min
            s_min = largo / (dt - t_min) if dt > t_min else math.inf
            vmax, vmin = min(vmax, s_max), max(vmin, s_min)
            sensores.append({"sensor": nombre, "banda": "variable", "v_max_m_s": round(s_max, 4),
                             "v_min_m_s": round(s_min, 4) if s_min != math.inf else None})
    variable = any(s["banda"] == "variable" for s in L["sensores"].values())
    if variable:
        vel_max_V = math.floor(vmax / k * 100) / 100 if vmax != math.inf else None
        if vel_max_V is not None and vel_tope_V is not None:
            vel_max_V = min(vel_max_V, vel_tope_V)
        vel_min_V = math.ceil(vmin / k * 100) / 100 if vmin != math.inf else None
        if vel_min_V is None or (vel_max_V is not None and vel_min_V > vel_max_V):
            problemas.append("no hay velocidad de banda que cumpla: minima %s V, maxima %s V" % (vel_min_V, vel_max_V))
    else:
        vel_min_V = vel_max_V = None
    return {"sondeo_ms": sondeo_ms, "rtt_ms": rtt_ms, "refresco_ms": refresco_ms or 0, "banda_variable": variable,
            "t_ef_ms": t_ef_ms, "t_ef_origen": origen, "t_min_s": round(t_min, 3),
            "periodos": cfg["periodos_minimos"],
            "vel_min_V": vel_min_V, "vel_max_V": vel_max_V, "factible": not problemas,
            "sensores": sensores, "problemas": problemas}


def tope_del_mapa():
    e = next(e for e in mr.carga()["etiquetas"] if e["nombre"] == "vel_banda_V")
    return e["rango_fisico"][1]


def imprime(nombre, r):
    print("escenario %-14s sondeo %4d ms, rtt %4d ms, refresco %4d ms -> T_ef %d ms (%s), %s lecturas = %.2f s"
          % (nombre, r["sondeo_ms"], r["rtt_ms"], r["refresco_ms"], r["t_ef_ms"], r["t_ef_origen"], r["periodos"], r["t_min_s"]))
    for s in r["sensores"]:
        if s["banda"] == "variable":
            print("    %-13s banda variable      v en [%s, %s] m/s" % (s["sensor"], s["v_min_m_s"], s["v_max_m_s"]))
        else:
            print("    %-15s banda %-12s encendido %.2f s, apagado >= %.2f s  %s"
                  % (s["sensor"], s["banda"], s["encendido_s"], s["apagado_min_s"], "cumple" if s["cumple"] else "NO CUMPLE"))
    if r["banda_variable"]:
        print("    vel_banda_V permitida: %s a %s V  %s" % (r["vel_min_V"], r["vel_max_V"],
                                                          "(factible)" if r["factible"] else "NO FACTIBLE"))
    else:
        print("    bandas de velocidad fija: %s" % ("factible" if r["factible"] else "NO FACTIBLE"))
    for p in r["problemas"]:
        print("    ! " + p)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--config", default=str(CONFIG))
    p.add_argument("--sondeo", type=float, help="periodo de sondeo en ms (con --rtt)")
    p.add_argument("--rtt", type=float, help="ida y vuelta en ms")
    p.add_argument("--refresco", type=float, default=0, help="periodo de refresco de la escena en ms")
    p.add_argument("--medido", action="store_true",
                   help="con --sondeo: usa el bloque medido si es de este sondeo (como Node-RED sin A2_RTT/A2_REFRESCO a mano)")
    p.add_argument("--escribe", action="store_true", help="guarda limites_calculados en la configuracion")
    a = p.parse_args(argv)
    ruta = pathlib.Path(a.config)
    cfg = json.loads(ruta.read_text(encoding="utf-8"))
    tope = tope_del_mapa()
    if a.sondeo is not None:
        r = calcula(cfg, a.sondeo, a.rtt or 0, tope, a.refresco, medido_vale(cfg, a.sondeo) if a.medido else None)
        imprime("manual", r)
        return 0 if r["factible"] else 1
    resultados = {}
    for esc in cfg["escenarios"]:
        r = calcula(cfg, esc["sondeo_ms"], esc["rtt_ms"], tope, esc.get("refresco_ms", 0),
                    medido_vale(cfg, esc["sondeo_ms"]) if esc.get("usa_medido") else None)
        imprime(esc["nombre"], r)
        resultados[esc["nombre"]] = {k: r[k] for k in ("sondeo_ms", "rtt_ms", "refresco_ms", "t_ef_ms", "t_ef_origen", "t_min_s",
                                                       "vel_min_V", "vel_max_V", "factible")}
    if a.escribe:
        cfg["limites_calculados"] = {"generado_por": "python3 tools/limites_planta.py --escribe",
                                     "escenarios": resultados}
        ruta.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("escrito limites_calculados en %s" % ruta)
    # Codigo 0 si el escenario por omision (el primero) es factible: un escenario
    # medido que no da (Azure a 1 FPS) se reporta, no rompe la herramienta.
    return 0 if resultados[cfg["escenarios"][0]["nombre"]]["factible"] else 1


if __name__ == "__main__":
    sys.exit(main())
