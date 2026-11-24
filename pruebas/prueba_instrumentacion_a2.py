#!/usr/bin/env python3
"""Ensayo de C9 contra el sustituto y el simulador de Firebase. Python 3.9.

    /usr/bin/python3 pruebas/prueba_instrumentacion_a2.py               (2 min)
    /usr/bin/python3 pruebas/prueba_instrumentacion_a2.py --minutos 10  (la corrida de C9, ensayo)

Hace la corrida con el desviador (A2-Nube escribiendo en pruebas/simulador.py
en vez de Firebase), exporta la rama proceso con tools/exporta_corrida.py
--rama proceso y calcula las tres cifras con tools/analiza_corrida.py --a2.
Despues las RECALCULA por otro camino para ver que se reproducen desde los
archivos:
  periodo efectivo  <- estadistica en vivo de A2-Planta (/a2/planta/estado)
  latencia          <- CSV que escribe A2-Nube (a2_nube_DIA.csv)
  completitud       <- registro del sustituto (cajas que salieron de verdad)
"""
import argparse, csv, json, os, pathlib, statistics, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
import prueba_desviador as pd  # noqa: E402
import prueba_nube as pn  # noqa: E402

verifica = ps.verifica


def main(minutos):
    simulador = subprocess.Popen([sys.executable, str(RAIZ / "pruebas" / "simulador.py"), "8099"])
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_c9_"))
    try:
        time.sleep(1)
        pn.sim("/__reinicia")
        print("=== Ensayo de C9: %d min con el desviador, Firebase simulado (datos en %s) ===" % (minutos, datos))
        proxy = pd.arranca("local", datos, FIREBASE_DB_URL=pn.SIM, IDENTITY_BASE_URL=pn.SIM,
                           FIREBASE_API_KEY="llave-simulada", FB_INGESTOR_EMAIL="ingestor@ejemplo.mx",
                           FB_INGESTOR_PASS="secreta", PLANTA_ID="planta_01", A2_NUBE=1, A2_LATIDO_S=60)
        try:
            pp.comando(accion="marcha")
            pp.comando(accion="emisor", valor=True)
            t_ini = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            time.sleep(minutos * 60)
            pp.comando(accion="emisor", valor=False)
            # Se espera a que el SUSTITUTO saque todas las cajas, no solo a que
            # se vacie la cola del cliente: una caja confirmada en su sensor aun
            # va por la rama (primera corrida de 10 min: 103 en el cliente, 102
            # fuera en el sustituto al cortar).
            pp.espera(lambda: not pp.estado()["en_tramo"] and
                      sum(1 for x in ps.eventos(datos) if x["ev"] == "caja_emitida") ==
                      sum(1 for x in ps.eventos(datos) if x["ev"] in ("caja_sale", "caja_rechazada")), 90, paso=1)
            time.sleep(3)
            t_fin = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
            vivo = pp.estado()
            pp.comando(accion="paro")
        finally:
            proxy.detiene()
            ps.detiene()

        # ---- exportar la rama proceso del "Firebase" ---------------------------------------
        salida = datos / "proceso_c9.csv"
        env = dict(os.environ, FIREBASE_DB_URL=pn.SIM, FIREBASE_AUTH="TOKEN-SIMULADO", PLANTA_ID="planta_01",
                   FB_VISOR_EMAIL="", FB_VISOR_PASS="", FIREBASE_API_KEY="", DATOS_DIR=str(datos))
        r = subprocess.run([sys.executable, str(RAIZ / "tools" / "exporta_corrida.py"), "--rama", "proceso",
                            "--salida", str(salida)], capture_output=True, text=True, env=env)
        print("\n".join("    " + l for l in (r.stdout + r.stderr).strip().splitlines()))
        verifica("exporta_corrida.py --rama proceso exporta el CSV", r.returncode == 0 and salida.exists(), r.returncode)
        sondeo = sorted(datos.glob("a2_sondeo_*.csv"))[0]
        md = datos / "corrida_a2.md"
        r = subprocess.run([sys.executable, str(RAIZ / "tools" / "analiza_corrida.py"), "--a2", str(salida),
                            "--sondeo", str(sondeo), "--eventos", str(datos / "a2_planta_eventos.jsonl"),
                            "--sustituto", str(datos / "a2_sustituto_eventos.jsonl"), "--md", str(md)],
                           capture_output=True, text=True)
        print("\n".join("    " + l for l in (r.stdout + r.stderr).strip().splitlines()))
        verifica("analiza_corrida.py --a2 saca las tres cifras", r.returncode == 0 and md.exists(), r.returncode)
        texto = r.stdout

        # ---- recalculo por otro camino ------------------------------------------------------
        import re
        m = re.search(r"1\. periodo efectivo.*?\n\s+min ([\d.]+)\s+p50 ([\d.]+).*?\n\s+media ([\d.]+) ± ([\d.]+)", texto, re.S)
        per_media = float(m.group(3))
        v = vivo["periodo_efectivo_ms"]
        verifica("periodo efectivo del CSV (%.1f ms) = el que midio A2-Planta en vivo (%.1f ms) +-1 ms" % (per_media, v["media"]),
                 abs(per_media - v["media"]) <= 1.0, (per_media, v))
        m = re.search(r"2\. latencia.*?\n\s+min ([\d.]+)\s+p50 ([\d.]+)", texto, re.S)
        lat_p50 = float(m.group(2))
        nube = [int(f["latencia_ms"]) for f in pn.csv(datos) if f["tipo"] == "caja" and f["codigo"] == "201"]
        verifica("latencia mediana del CSV exportado (%.1f ms) = la del CSV de A2-Nube (%.1f ms)"
                 % (lat_p50, statistics.median(nube)), abs(lat_p50 - statistics.median(nube)) <= 1.0)
        m = re.search(r"3\. completitud: (\d+) registros de caja en Firebase / (\d+) cajas", texto)
        reg_fb, pasos = int(m.group(1)), int(m.group(2))
        reales = sum(1 for x in ps.eventos(datos) if x["ev"] in ("caja_sale", "caja_rechazada"))
        verifica("completitud: %d en Firebase / %d paso_caja; el sustituto saco %d" % (reg_fb, pasos, reales),
                 reg_fb == pasos == reales and reales > 0, (reg_fb, pasos, reales))
        print("  tabla: %s\n%s" % (md, md.read_text(encoding="utf-8")))
    finally:
        ps.detiene()
        simulador.terminate()


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--minutos", type=float, default=2)
    main(a.parse_args().minutos)
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
