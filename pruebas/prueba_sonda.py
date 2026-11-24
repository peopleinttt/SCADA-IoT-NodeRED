#!/usr/bin/env python3
"""Pruebas de la sonda Modbus (C3) contra la planta sustituta. Python 3.9.

    /usr/bin/python3 pruebas/prueba_sonda.py          (~1 min)

La sonda se invoca por su linea de comandos, como la va a usar Ari contra
Azure. Para cada etiqueta hay un oraculo que no es la sonda:
  - escrituras: el registro de eventos del emulador (lo que la planta leyo)
    y la palabra cruda leida con el cliente directo;
  - lecturas: la planta se congela (alimentacion y banda en 0) con una caja
    tapando el sensor que se quiere leer, y el valor esperado sale de los
    eventos del emulador (que caja, con que masa).
"""
import json, pathlib, re, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402  (arranque de Node-RED, mapa, verifica)
from modbus_tcp import Cliente  # noqa: E402

SONDA = [sys.executable, str(RAIZ / "tools" / "sonda_modbus.py"), "--host", "127.0.0.1", "--puerto", "5020"]
E, CFG, verifica = ps.E, ps.CFG, ps.verifica


def sonda(*args, destino=None):
    r = subprocess.run((destino or SONDA) + list(args), capture_output=True, text=True, timeout=20)
    return r.returncode, (r.stdout + r.stderr).strip()


def valor(salida):
    """'peso_V = 5.12 V   (...)' -> 5.12 ; 'sens_entrada = 1 (...)' -> 1.0"""
    m = re.search(r"= (-?[0-9.]+)", salida)
    return float(m.group(1)) if m else None


def ps_env_archivo():
    """Nombres A2_MODBUS_* con valor en ../.env (sin leer los valores)."""
    ruta = RAIZ / ".env"
    if not ruta.exists():
        return set()
    return {l.split("=", 1)[0].strip() for l in ruta.read_text(encoding="utf-8").splitlines()
            if l.strip().startswith("A2_MODBUS_") and l.split("=", 1)[1].strip()}


def espera_sensor(c, nombre, limite_s=30):
    fin = time.time() + limite_s
    while time.time() < fin:
        if c.lee_discretas(E[nombre]["direccion"], 1)[0]:
            return True
        time.sleep(0.02)
    return False


def main():
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_sonda_"))
    print("=== 0. Arranque del sustituto (datos en %s) ===" % datos)
    ps.arranca(datos)
    verifica("el emulador avanza", ps.espera_emulador())
    c = Cliente("127.0.0.1", 5020)

    print("=== 1. Lista y lectura inicial de las etiquetas de lectura ===")
    rc, out = sonda("lista")
    verifica("lista muestra las 11 etiquetas", rc == 0 and len(out.splitlines()) == 11, out)
    iniciales = {"sens_entrada": 0, "sens_bascula": 0, "sens_salida": 0,
                 "emp_lim_frontal": 0, "emp_lim_trasero": 1, "peso_V": 0.0}
    for nombre, esperado in iniciales.items():
        rc, out = sonda("lee", nombre)
        verifica("lee %-16s = %s" % (nombre, esperado), rc == 0 and valor(out) == esperado, out)
    rc, out = sonda("lee", "todas")
    verifica("lee todas da 11 lineas", rc == 0 and len(out.splitlines()) == 11, out)

    print("=== 2. Escritura y lectura de cada etiqueta de escritura ===")
    casos = [("emisor_on", "1", 1), ("emisor_on", "0", 0), ("alimentacion_on", "1", 1),
             ("alimentacion_on", "0", 0), ("emp_extender", "1", 1), ("emp_extender", "0", 0),
             ("luz_alerta", "1", 1), ("luz_alerta", "0", 0),
             ("vel_banda_V", "5", 5.0), ("vel_banda_V", "-2", -2.0), ("vel_banda_V", "-10", -10.0),
             ("vel_banda_V", "10", 10.0), ("vel_banda_V", "-0.01", -0.01), ("vel_banda_V", "0", 0.0)]
    crudos = {"-2": 65336, "-10": 64536, "10": 1000, "-0.01": 65535}
    for nombre, texto_valor, esperado in casos:
        rc, out = sonda("escribe", nombre, texto_valor)
        ok = rc == 0 and valor(out) == esperado
        detalle = out
        if nombre == "vel_banda_V" and texto_valor in crudos:
            palabra = c.lee_retencion(E[nombre]["direccion"], 1)[0]
            ok = ok and palabra == crudos[texto_valor] and ("palabra %d" % palabra) in out
            detalle = "%s | cliente directo: %d" % (out, palabra)
        verifica("escribe %-15s %-5s -> lee %s" % (nombre, texto_valor, esperado), ok, detalle)
        time.sleep(0.25)                     # al menos dos ticks: que la planta lo lea
    vistos = [(e["etiqueta"], e["valor"]) for e in ps.eventos(datos) if e["ev"] == "entrada"]
    esperados = [(n, v) for n, _, v in casos]
    # Cada escritura debe aparecer en lo que leyo la planta, en el mismo orden.
    verifica("la planta leyo las 14 escrituras, en orden, con su valor",
             vistos[-len(esperados):] == esperados, vistos[-len(esperados):])

    print("=== 3. Lecturas con la planta congelada ===")
    # Banda y alimentacion en marcha hasta que una caja tape sens_entrada; luego todo a 0.
    def congela_en(sensor, quita):
        c.escribe_registro(E["vel_banda_V"]["direccion"], ps.palabra("vel_banda_V", 5.0))
        c.escribe_bobina(E["alimentacion_on"]["direccion"], True)
        c.escribe_bobina(E["emisor_on"]["direccion"], True)
        llego = espera_sensor(c, sensor)
        for q in quita:
            if q == "vel_banda_V":
                c.escribe_registro(E[q]["direccion"], 0)
            else:
                c.escribe_bobina(E[q]["direccion"], False)
        time.sleep(1.5)                      # > 3 tau de la bascula
        return llego

    congela_en("sens_entrada", ["emisor_on", "alimentacion_on", "vel_banda_V"])
    rc, out = sonda("lee", "sens_entrada")
    verifica("caja detenida en la entrada: lee sens_entrada = 1", rc == 0 and valor(out) == 1, out)

    congela_en("sens_bascula", ["emisor_on", "alimentacion_on", "vel_banda_V"])
    ev = ps.eventos(datos)
    caja = [e["caja"] for e in ev if e["ev"] == "sensor_on" and e["etiqueta"] == "sens_bascula"][-1]
    masa = next(e["masa_kg"] for e in ev if e["ev"] == "caja_emitida" and e["caja"] == caja)
    esperado = masa / CFG["bascula"]["plena_escala_kg"] * 10
    rc, out = sonda("lee", "sens_bascula")
    verifica("caja detenida en la bascula: lee sens_bascula = 1", rc == 0 and valor(out) == 1, out)
    rc, out = sonda("lee", "peso_V")
    verifica("lee peso_V = masa de la caja %d (%.3f kg -> %.3f V) +-0.05 V" % (caja, masa, esperado),
             rc == 0 and valor(out) is not None and abs(valor(out) - esperado) <= 0.05, out)

    congela_en("sens_salida", ["emisor_on", "alimentacion_on", "vel_banda_V"])
    rc, out = sonda("lee", "sens_salida")
    verifica("caja detenida en la salida: lee sens_salida = 1", rc == 0 and valor(out) == 1, out)

    sonda("escribe", "emp_extender", "1")
    time.sleep(CFG["empujador"]["carrera_s"] + 0.5)
    rc1, f = sonda("lee", "emp_lim_frontal")
    rc2, t = sonda("lee", "emp_lim_trasero")
    verifica("empujador extendido: frontal 1, trasero 0",
             rc1 == rc2 == 0 and valor(f) == 1 and valor(t) == 0, "%s | %s" % (f, t))
    sonda("escribe", "emp_extender", "0")
    c.cierra()

    print("=== 4. Rechazos y errores ===")
    rc, out = sonda("escribe", "sens_entrada", "1")
    verifica("escribir una entrada discreta -> codigo 1, solo lectura", rc == 1 and "solo lectura" in out, out)
    rc, out = sonda("escribe", "peso_V", "3")
    verifica("escribir un registro de entrada -> codigo 1", rc == 1 and "solo lectura" in out, out)
    rc, out = sonda("escribe", "vel_banda_V", "10.5")
    verifica("10.5 V fuera del rango del mapa -> codigo 1", rc == 1 and "fuera" in out, out)
    rc, out = sonda("escribe", "emisor_on", "talvez")
    verifica("booleana con valor que no es 1/0 -> codigo 1", rc == 1, out)
    rc, out = sonda("lee", "no_existe")
    verifica("etiqueta inexistente -> codigo 1", rc == 1 and "no existe" in out, out)
    otro = [sys.executable, str(RAIZ / "tools" / "sonda_modbus.py"), "--host", "127.0.0.1",
            "--puerto", "5099", "--espera", "1"]
    rc, out = sonda("lee", "peso_V", destino=otro)
    verifica("sin servidor en el puerto -> codigo 2", rc == 2 and "sin conexion" in out, out)
    if "A2_MODBUS_HOST" in ps_env_archivo():
        print("  (se omite el caso de host por omision: .env ya fija A2_MODBUS_HOST)")
    else:
        rc, out = sonda("lee", "vel_banda_V", destino=SONDA[:2] + ["--puerto", "5020"])
        verifica("sin --host ni A2_MODBUS_HOST va a 127.0.0.1", rc == 0, out)

    print("=== 5. Destino desde el entorno (A2_MODBUS_*) ===")
    import os
    env = dict(os.environ, A2_MODBUS_HOST="127.0.0.1", A2_MODBUS_PUERTO="5099")
    r = subprocess.run(SONDA[:2] + ["--espera", "1", "lee", "peso_V"], capture_output=True, text=True, env=env)
    verifica("A2_MODBUS_PUERTO=5099 del entorno manda la sonda a 5099", r.returncode == 2 and ":5099" in r.stderr,
             r.stderr.strip())
    env["A2_MODBUS_PUERTO"] = "5020"
    r = subprocess.run(SONDA[:2] + ["lee", "peso_V"], capture_output=True, text=True, env=env)
    verifica("y con A2_MODBUS_PUERTO=5020 lee bien", r.returncode == 0, r.stdout + r.stderr)

    print("=== 6. Tiempo de ida y vuelta (mide) ===")
    def estadisticos(salida):
        m = re.search(r"min ([0-9.]+)\s+mediana ([0-9.]+)\s+p95 ([0-9.]+)\s+max ([0-9.]+)", salida)
        n = re.search(r"lecturas\s+(\d+) de (\d+)", salida)
        return (tuple(float(x) for x in m.groups()) if m else None,
                tuple(int(x) for x in n.groups()) if n else None)
    rc, out = sonda("mide", "peso_V", "-n", "30")
    print("\n".join("    " + l for l in out.splitlines()))
    est, cuenta = estadisticos(out)
    verifica("directo: 30 de 30 lecturas, min <= mediana <= p95 <= max",
             rc == 0 and cuenta == (30, 30) and est and est[0] <= est[1] <= est[2] <= est[3], out)
    verifica("directo: mediana local por debajo de 20 ms", est and est[1] < 20, est)

    from proxy_retardo import Proxy
    proxy = Proxy(5030, ("127.0.0.1", 5020), 200).inicia()
    try:
        rc, out = sonda("mide", "vel_banda_V", "-n", "20",
                        destino=SONDA[:2] + ["--host", "127.0.0.1", "--puerto", "5030"])
    finally:
        proxy.detiene()
    print("\n".join("    " + l for l in out.splitlines()))
    est, cuenta = estadisticos(out)
    # Oraculo: el proxy agrega 200 ms exactos; lo medido es 200 + lo local.
    verifica("con proxy de 200 ms: 20 de 20 y min >= 200 ms", rc == 0 and cuenta == (20, 20) and est and est[0] >= 200, out)
    verifica("con proxy de 200 ms: mediana entre 200 y 230 ms", est and 200 <= est[1] <= 230, est)
    rc, out = sonda("mide", "peso_V", "-n", "0")
    verifica("mide -n 0 -> codigo 1", rc == 1, out)
    rc, out = sonda("mide", "peso_V", "-n", "3", destino=otro)
    verifica("mide sin servidor -> codigo 2", rc == 2, out)


if __name__ == "__main__":
    try:
        main()
    finally:
        ps.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
