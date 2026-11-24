#!/usr/bin/env python3
"""Prueba del modo vigila de la sonda (R1) contra el sustituto. Python 3.9.

    /usr/bin/python3 pruebas/prueba_vigila.py          (~1 min)

La sonda vigila a traves de proxy_retardo.py (20 ms de ida y vuelta) mientras
la prueba mueve la planta directo en el 5020: 4 cajas y un ciclo del
empujador. Oraculos:
  - pulsos: el registro de eventos del sustituto (sensor_on / sensor_off);
  - periodo de refresco: el tick del sustituto (0.1 s), que vigila debe
    encontrar porque una vuelta (dos peticiones de ~20 ms) es mas corta;
  - duracion de pulso: largo de caja / velocidad de la banda de alimentacion.
"""
import json, pathlib, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
from proxy_retardo import Proxy  # noqa: E402
from modbus_tcp import Cliente  # noqa: E402

verifica, E, CFG = ps.verifica, ps.E, ps.CFG
SENSORES = ["sens_entrada", "sens_bascula", "sens_salida", "emp_lim_frontal", "emp_lim_trasero"]


def main():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_vigila_"))
    print("=== vigila contra el sustituto por un proxy de 20 ms (datos en %s) ===" % datos)
    ps.arranca(datos)
    verifica("el sustituto avanza", ps.espera_emulador())
    proxy = Proxy(5030, ("127.0.0.1", 5020), 20).inicia()
    salida = datos / "vigila.json"
    try:
        sonda = subprocess.Popen([sys.executable, str(RAIZ / "tools" / "sonda_modbus.py"), "--host", "127.0.0.1",
                                  "--puerto", "5030", "vigila", "-s", "48", "--json", str(salida)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(1.5)
        with Cliente("127.0.0.1", 5020) as c:
            ps.enciende_linea(c, 5.0)
            time.sleep(4)
            c.escribe_bobina(E["emp_extender"]["direccion"], True)
            time.sleep(1.2)
            c.escribe_bobina(E["emp_extender"]["direccion"], False)
            fin = time.time() + 30
            while time.time() < fin and sum(1 for x in ps.eventos(datos) if x["ev"] == "caja_emitida") < 4:
                time.sleep(0.2)
            c.escribe_bobina(E["emisor_on"]["direccion"], False)
        texto, _ = sonda.communicate(timeout=90)
    finally:
        proxy.detiene()
        ps.detiene()
    print("\n".join("    " + l for l in texto.splitlines()))
    verifica("vigila termina con codigo 0", sonda.returncode == 0, sonda.returncode)
    v = json.loads(salida.read_text(encoding="utf-8"))
    ev = ps.eventos(datos)
    emitidas = sum(1 for x in ev if x["ev"] == "caja_emitida")
    salen = sum(1 for x in ev if x["ev"] in ("caja_sale", "caja_rechazada"))
    verifica("las %d cajas salieron antes de que vigila terminara" % emitidas, emitidas == salen == 4, (emitidas, salen))
    for s in SENSORES:
        clave = next(k for k in v["por_direccion"] if "(%s)" % s in k)
        subidas_v = sum(1 for x in v["cambios"] if x["dir"] == clave and x["a"] == 1)
        bajadas_v = sum(1 for x in v["cambios"] if x["dir"] == clave and x["a"] == 0)
        # El tick 0 es el estado inicial (empujador retraido): ocurre antes de
        # que vigila lea por primera vez, asi que para vigila no es un cambio.
        subidas_s = sum(1 for x in ev if x["ev"] == "sensor_on" and x["etiqueta"] == s and x["tick"] > 0)
        bajadas_s = sum(1 for x in ev if x["ev"] == "sensor_off" and x["etiqueta"] == s and x["tick"] > 0)
        verifica("%-16s vigila %d subidas / %d bajadas = sustituto %d / %d" % (s, subidas_v, bajadas_v, subidas_s, bajadas_s),
                 (subidas_v, bajadas_v) == (subidas_s, bajadas_s) and subidas_s > 0)
    # El tick del sustituto sale de un inject de Node-RED y varia: un tick tarde
    # seguido de uno a tiempo quedan a ~50 ms. El refresco es un MINIMO por
    # definicion y recoge esa variacion; la mediana del intervalo de peso_V es
    # la que debe dar el tick (primera corrida: minimo 0.051 s).
    clave_p = next(k for k in v["por_direccion"] if "(peso_V)" in k)
    med = v["por_direccion"][clave_p]["intervalo_mediana_s"]
    verifica("mediana del intervalo de peso_V = tick del sustituto (0.1 s): vigila %.3f s" % med,
             med is not None and 0.08 <= med <= 0.13)
    verifica("refresco (minimo, %.3f s) <= mediana" % v["refresco_s"], v["refresco_s"] is not None and v["refresco_s"] <= med)
    esperado = CFG["caja"]["largo_m"] / CFG["alimentacion_m_s"]
    clave = next(k for k in v["por_direccion"] if "(sens_entrada)" in k)
    durs = [p["segundos"] for p in v["por_direccion"][clave]["pulsos"]]
    verifica("pulso de sens_entrada = largo / alimentacion = %.2f s +-0.2 (vigila %s)" % (esperado, [round(d, 2) for d in durs]),
             durs and all(abs(d - esperado) <= 0.2 for d in durs))
    verifica("ida y vuelta medida >= 20 ms del proxy (mediana %.1f ms)" % v["rtt_ms"]["p50"], v["rtt_ms"]["min"] >= 20)


if __name__ == "__main__":
    main()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
