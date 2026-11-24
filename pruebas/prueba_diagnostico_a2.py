#!/usr/bin/env python3
"""Pruebas del diagnostico de la Actividad 2 (C7) contra pruebas/simulador.py. Python 3.9.

    /usr/bin/python3 pruebas/prueba_diagnostico_a2.py          (~2 min, no gasta cuota)
    /usr/bin/python3 pruebas/prueba_diagnostico_a2.py --real   (UNA consulta real a Gemini)

El simulador hace de Gemini y contesta, segun su modo, un diagnostico valido o
uno de siete invalidos. El disparo es el boton de la HMI (socket.io de
Dashboard 2.0) y el periodico (inject por la API de admin). Oraculos: lo que la
pagina muestra (ningun invalido llega), el CSV de diagnosticos (cada intento
con su resultado) y el contador de consultas del simulador (tope diario).
"""
import argparse, json, pathlib, subprocess, sys, tempfile, time, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
import prueba_desviador as pd  # noqa: E402
import admin_desechable as ad  # noqa: E402
from prueba_hmi import Pagina  # noqa: E402

verifica = ps.verifica
SIM = "http://127.0.0.1:8099"


def sim(ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    r = urllib.request.Request(SIM + ruta, data=datos, method="POST" if datos else "GET",
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=5))


def filas(datos):
    out = []
    for p in sorted(datos.glob("a2_diagnosticos_*.csv")):
        for l in p.read_text(encoding="utf-8").splitlines():
            if l and not l.startswith("ts;"):
                out.append(dict(zip(["ts", "origen", "modelo", "latencia_ms", "resultado", "motivo", "nivel",
                                     "accion", "valor_pct", "tokens"], l.split(";"))))
    return out


def pide_diagnostico(pg, datos, espera_s=10):
    antes = len(filas(datos))
    pg.s.emite("widget-action", "ui_tpl_a2", {"payload": {"accion": "diagnostico"}})
    fin = time.time() + espera_s
    while time.time() < fin and len(filas(datos)) == antes:
        pg.lee(0.5)
    pg.lee(1.5)                                   # que la pagina reciba el estado de despues
    nuevas = filas(datos)[antes:]
    return nuevas[-1] if nuevas else None


def simulado():
    simulador = subprocess.Popen([sys.executable, str(RAIZ / "pruebas" / "simulador.py"), "8099"])
    try:
        time.sleep(1)
        sim("/__reinicia")
        datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_diag_"))
        print("=== Diagnostico con el empujador (banda variable), Gemini simulado (datos en %s) ===" % datos)
        proxy = pp.arranca("local", datos, GEMINI_BASE_URL=SIM, GEMINI_API_KEY="gemini-simulada",
                           A2_DIAG_POR_MINUTO=600, A2_DIAG_MAX_DIA=10)
        try:
            pg = Pagina()
            pg.espera(lambda p: p.estado.get("ready"), 15)
            sim("/__modo", {"modo": "ok"})
            f = pide_diagnostico(pg, datos)
            verifica("boton Request diagnosis -> diagnostico valido", f and f["resultado"] == "valido", f)
            d0 = pg.estado.get("diagnosis")
            verifica("y la pagina lo muestra (nivel, accion, texto en ingles)",
                     d0 and d0["nivel_estimado"] == "normal" and d0["accion_codigo"] == "mantener"
                     and "boxes" in d0["texto_diagnostico"], d0)
            for modo, motivo in (("a2_nivel_malo", "nivel_invalido"), ("a2_accion_mala", "accion_invalida"),
                                 ("a2_pct_fuera", "valor_pct_invalido"), ("a2_pct_sobra", "campos_no_esperados"),
                                 ("a2_falta", "faltan_campos"), ("a2_extra", "campos_no_esperados"),
                                 ("a2_no_json", "contenido_no_json"), ("basura", "respuesta_no_json")):
                sim("/__modo", {"modo": modo})
                f = pide_diagnostico(pg, datos)
                verifica("respuesta %-15s -> fallo %-20s y la pagina sigue con el anterior" % (modo, motivo),
                         f and f["resultado"] == "fallo" and f["motivo"] == motivo
                         and pg.estado.get("diagnosis", {}).get("ts") == d0["ts"], (f, pg.estado.get("diagnosis")))
            sim("/__modo", {"modo": "a2_reducir"})
            f = pide_diagnostico(pg, datos)
            verifica("con banda variable, reducir_velocidad 10 %% es valido", f and f["resultado"] == "valido"
                     and f["accion"] == "reducir_velocidad" and f["valor_pct"] == "10", f)
            # Tope diario: A2_DIAG_MAX_DIA=10 en esta corrida y ya van 10 consultas
            # (1 valida + 8 invalidas + reducir): la undecima no debe salir.
            antes = sim("/__estado").get("a2_consultas")
            f = pide_diagnostico(pg, datos)
            despues = sim("/__estado").get("a2_consultas")
            verifica("con el tope diario alcanzado (10), el boton ya no consulta (simulador %s -> %s)" % (antes, despues),
                     despues == antes, (antes, despues, f))
        finally:
            proxy.detiene()
            ps.detiene()

        print("=== Disparo periodico y banda fija (desviador) ===")
        datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_diag_desv_"))
        # El boton del inject es de la API de administracion: credenciales
        # desechables de esta corrida (paso S2 de la fase 3).
        env_adm, clave_adm = ad.genera()
        proxy = pd.arranca("local", datos, GEMINI_BASE_URL=SIM, GEMINI_API_KEY="gemini-simulada", A2_DIAG_POR_MINUTO=600,
                           **env_adm)
        tok = ad.token(env_adm["NODE_RED_ADMIN_USER"], clave_adm)
        verifica("token de administracion desechable", bool(tok))
        try:
            pg = Pagina()
            pg.espera(lambda p: p.estado.get("ready"), 15)
            sim("/__modo", {"modo": "ok"})
            antes = sim("/__estado").get("a2_consultas")
            ad.pide("POST", "/inject/inj_diag2", tok)
            time.sleep(2)
            verifica("periodico con la linea detenida: no consulta",
                     sim("/__estado").get("a2_consultas") == antes)
            c, r = pp.comando(accion="marcha")
            verifica("marcha -> 200", c == 200, (c, r))
            pp.espera(lambda: pp.estado()["linea"] == "en_marcha", 5)
            time.sleep(0.5)                      # el resumen global se refresca en el siguiente ciclo
            ad.pide("POST", "/inject/inj_diag2", tok)
            time.sleep(2)
            verifica("periodico con la linea en marcha: consulta", sim("/__estado").get("a2_consultas") == antes + 1)
            sim("/__modo", {"modo": "a2_reducir"})
            f = pide_diagnostico(pg, datos)
            verifica("con banda fija, reducir_velocidad no se ofrece y se rechaza (accion_invalida)",
                     f and f["resultado"] == "fallo" and f["motivo"] == "accion_invalida", f)
            pp.comando(accion="paro")
        finally:
            proxy.detiene()
    finally:
        ps.detiene()
        simulador.terminate()


def real():
    """Una sola consulta real, para confirmar el formato. Gasta 1 de la cuota del dia."""
    import os
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_diag_real_"))
    env = {}
    for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in l and not l.strip().startswith("#"):
            k, v = l.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    print("=== UNA consulta real a Gemini (%s) ===" % env.get("GEMINI_MODEL"))
    proxy = pd.arranca("local", datos, GEMINI_BASE_URL="https://generativelanguage.googleapis.com",
                       GEMINI_API_KEY=env.get("GEMINI_API_KEY", ""), GEMINI_MODEL=env.get("GEMINI_MODEL", "gemini-2.5-flash"))
    try:
        pg = Pagina()
        pg.espera(lambda p: p.estado.get("ready"), 15)
        pp.comando(accion="marcha"); pp.comando(accion="emisor", valor=True)
        pg.espera(lambda p: p.estado["boxesOut"] >= 3, 90)
        # La real tarda: el 24 oct, 13.1 s (la espera de 10 s la dio por perdida).
        f = pide_diagnostico(pg, datos, espera_s=60)
        pg.espera(lambda p: p.estado.get("diagnosis") is not None, 15)
        print("  fila del CSV: %s" % f)
        print("  diagnostico en la pagina: %s" % json.dumps(pg.estado.get("diagnosis"), ensure_ascii=False))
        verifica("la respuesta real pasa la validacion estricta", f and f["resultado"] == "valido", f)
        pp.comando(accion="paro")
    finally:
        proxy.detiene()
        ps.detiene()


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--real", action="store_true")
    (real if a.parse_args().real else simulado)()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
