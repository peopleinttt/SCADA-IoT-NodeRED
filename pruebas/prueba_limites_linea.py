#!/usr/bin/env python3
"""Limites de recorrido del desviador (paso H del cierre de la fase 4). Python 3.9. ~1.5 min.

    /usr/bin/python3 pruebas/prueba_limites_linea.py

  1. Con config/planta_desviador.json (distancia y velocidad), los dos limites que
     publica A2-Planta son los de la formula de antes del cambio:
       timeout_confirmacion_s = 1.5 x fin_bascula_a_confirmacion_m / velocidad_fija_m_s
                                + (N + 1) x T_ef + rtt                   (redondeado a 0.01)
       limite_fin_bascula_s   = 1.5 x entrada_a_fin_bascula_m / velocidad_fija_m_s + 3 x T_ef
  2. Con config/planta_fio.json (tiempos medidos), los de la formula nueva:
       1.5 x t_pesada_a_confirmacion_s + (N + 1) x T_ef + rtt + comunicacion_timeout
       1.5 x t_entrada_a_parada_s + 3 x T_ef + comunicacion_timeout
  3. Mutacion: una configuracion del desviador sin ninguna de las dos formas completas
     se rechaza (503 y el motivo en el registro de Node-RED); con solo uno de los dos
     tiempos y sin distancias, tambien.
Node-RED con el sustituto del desviador (1) o con el mapa de Factory I/O hacia un
puerto Modbus sin servidor (2 y 3): los limites se calculan al cargar la
configuracion, sin necesidad de planta.
"""
import json, pathlib, sys, tempfile, time, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
sys.path.insert(0, str(RAIZ / "tools"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
import prueba_desviador as pd  # noqa: E402

verifica = ps.verifica


def estado_crudo():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:%d/a2/planta/estado" % ps.PUERTO_NR, timeout=5)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def fio(tmp, cfg, nombre):
    ruta = tmp / ("planta_%s.json" % nombre)
    ruta.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    datos = tmp / ("datos_%s" % nombre)
    datos.mkdir()
    ps.arranca(datos, A2_MAPA=RAIZ / "config" / "mapa_registros_fio.json", A2_PLANTA_CONFIG=ruta, A2_SUSTITUTO=0,
               A2_MODBUS_HOST="127.0.0.1", A2_MODBUS_PUERTO=5097, A2_MODBUS_UNIDAD=1)
    time.sleep(2)
    return datos


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_limites_"))
    print("=== 1. Sustituto del desviador (distancia y velocidad): los limites de antes ===")
    datos = tmp / "desviador"
    datos.mkdir()
    proxy, ok = None, False
    try:
        proxy = pd.arranca("local", datos)
        lim = pp.estado()["limites"]
    finally:
        ps.detiene()
        if proxy:
            proxy.detiene()
    c = json.load(open(str(RAIZ / "config" / "planta_desviador.json")))
    L, tef, N = c["linea"], lim["t_ef_ms"], c["lecturas_para_cambio"]
    rtt = c["rtt_previsto_ms"]
    conf_antes = round(1.5 * L["fin_bascula_a_confirmacion_m"] / L["velocidad_fija_m_s"] + (N + 1) * tef / 1000 + rtt / 1000, 2)
    fin_antes = 1.5 * L["entrada_a_fin_bascula_m"] / L["velocidad_fija_m_s"] + 3 * tef / 1000
    verifica("timeout_confirmacion_s %s = formula de antes %s (T_ef %s ms)" % (lim["timeout_confirmacion_s"], conf_antes, tef),
             lim["timeout_confirmacion_s"] == conf_antes, lim)
    verifica("limite_fin_bascula_s %.6f = formula de antes %.6f" % (lim["limite_fin_bascula_s"], fin_antes),
             abs(lim["limite_fin_bascula_s"] - fin_antes) < 1e-12 and lim["limites_de"] == "distancia_y_velocidad", lim)

    print("=== 2. Factory I/O (tiempos medidos): la formula nueva ===")
    cfio = json.load(open(str(RAIZ / "config" / "planta_fio.json")))
    try:
        fio(tmp, cfio, "fio")
        lim = pp.estado()["limites"]
    finally:
        ps.detiene()
    L, tef, N = cfio["linea"], lim["t_ef_ms"], cfio["lecturas_para_cambio"]
    com = cfio["comunicacion_timeout_ms"] / 1000
    conf = round(1.5 * L["t_pesada_a_confirmacion_s"] + (N + 1) * tef / 1000 + cfio["rtt_previsto_ms"] / 1000 + com, 2)
    fin = 1.5 * L["t_entrada_a_parada_s"] + 3 * tef / 1000 + com
    verifica("timeout_confirmacion_s %s = 1.5 x %s + %d x %s ms + rtt + %.1f s = %s"
             % (lim["timeout_confirmacion_s"], L["t_pesada_a_confirmacion_s"], N + 1, tef, com, conf),
             lim["timeout_confirmacion_s"] == conf and lim["limites_de"] == "tiempos_medidos", lim)
    verifica("limite_fin_bascula_s %.4f = 1.5 x %s + 3 x %s ms + %.1f s = %.4f" % (lim["limite_fin_bascula_s"],
             L["t_entrada_a_parada_s"], tef, com, fin), abs(lim["limite_fin_bascula_s"] - fin) < 1e-12, lim)

    print("=== 3. Mutacion: sin ninguna forma completa, la configuracion se rechaza ===")
    for nombre, quita in (("sin_tiempos_ni_distancias", ["t_pesada_a_confirmacion_s", "t_entrada_a_parada_s"]),
                          ("un_solo_tiempo", ["t_entrada_a_parada_s"])):
        cm = json.loads(json.dumps(cfio))
        for k in quita:
            cm["linea"].pop(k, None)
        try:
            datos = fio(tmp, cm, nombre)
            codigo, _ = estado_crudo()
            log = (datos / "nodered.log").read_text(encoding="utf-8", errors="replace")
        finally:
            ps.detiene()
        verifica("%s: estado %s y el registro dice 'faltan los tiempos medidos'" % (nombre, codigo),
                 codigo == 503 and "faltan los tiempos medidos" in log, (codigo, log[-300:]))
    print("=== 4. Control: con los tiempos completos la misma configuracion carga (no es la prueba la que la rechaza) ===")
    try:
        fio(tmp, cfio, "control")
        codigo, cuerpo = estado_crudo()
    finally:
        ps.detiene()
    verifica("con los dos tiempos: estado %s con limites" % codigo, codigo == 200 and cuerpo and cuerpo.get("limites"), codigo)


if __name__ == "__main__":
    try:
        main()
    finally:
        ps.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
