#!/usr/bin/env python3
"""Compara el diagnostico con y sin razonamiento sobre casos AMBIGUOS.

El criterio de juicio esta escrito en docs/medicion_thinking.md ANTES de correr
esto. Los tres casos usan valores que el pipeline si puede producir.
"""
import json, os, pathlib, sys, urllib.error, urllib.request

def contexto_ssl():
    """CA para HTTPS. El Python del instalador de python.org en macOS no trae
    rutas de certificados configuradas (ssl.get_default_verify_paths().cafile
    da None), asi que toda llamada HTTPS falla con CERTIFICATE_VERIFY_FAILED.
    Se usa el paquete certifi si esta; si no, se explica el arreglo en vez de
    reventar con una traza ilegible."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    if ssl.get_default_verify_paths().cafile:
        return ssl.create_default_context()
    raise SystemExit(
        "Python no encuentra los certificados raiz y no puede hablar por HTTPS.\n"
        "Arreglo, cualquiera de los dos:\n"
        "  pip3 install certifi\n"
        '  open "/Applications/Python 3.10/Install Certificates.command"')


RAIZ = pathlib.Path(__file__).resolve().parent.parent
env = {}
for l in (RAIZ / ".env").read_text().splitlines():
    if "=" in l and not l.strip().startswith("#"):
        k, v = l.split("=", 1); env[k.strip()] = v.strip()
LLAVE  = env.get("GEMINI_API_KEY"); MODELO = env.get("GEMINI_MODEL", "gemini-2.5-flash")
UT, UV = env.get("UMBRAL_TEMP_C", "75"), env.get("UMBRAL_VIB_MM_S", "7.1")

CASOS = {
"A · vibracion sube, temperatura plana":
  f"n=12 muestras en 55.00 s | temp actual 58.20 C (min 57.90, prom 58.05, max 58.30, tendencia 0.02 C/min) | "
  f"vibracion actual 9.40 mm/s RMS (min 4.10, prom 6.80, max 9.40, tendencia 3.60 mm/s/min) | ciclos 1280 -> 1317 (+37)",
"B · ambas rozando el umbral sin cruzarlo":
  f"n=12 muestras en 55.00 s | temp actual 73.60 C (min 71.80, prom 72.70, max 73.60, tendencia 1.10 C/min) | "
  f"vibracion actual 6.90 mm/s RMS (min 6.20, prom 6.55, max 6.90, tendencia 0.40 mm/s/min) | ciclos 1280 -> 1317 (+37)",
"C · ruido sin tendencia":
  f"n=12 muestras en 55.00 s | temp actual 61.40 C (min 59.80, prom 61.00, max 62.30, tendencia -0.05 C/min) | "
  f"vibracion actual 4.30 mm/s RMS (min 3.80, prom 4.35, max 5.10, tendencia 0.01 mm/s/min) | ciclos 1280 -> 1317 (+37)",
}

def prompt(resumen):
    return (f"Eres un ingeniero de mantenimiento predictivo. Analiza la telemetria y responde SOLO con JSON.\n\n"
            f"Umbrales de operacion: temperatura de alarma {UT} C; vibracion de alarma {UV} mm/s RMS "
            f"(ISO 10816, frontera zona B/C para maquina clase II).\n\nResumen del estado actual:\n{resumen}\n\n"
            f'Devuelve un objeto JSON con exactamente estas dos llaves:\n'
            f'"texto_diagnostico": maximo 60 palabras, en espanol, explicando el estado y el modo de falla mas '
            f'probable; cita los numeros que lo sustentan.\n"accion_prescrita": una sola instruccion accionable, '
            f'en imperativo, maximo 15 palabras.\nNo inventes datos que no esten arriba. Si la evidencia no alcanza '
            f'para concluir, dilo en texto_diagnostico y prescribe seguir midiendo.')

def pide(texto, presupuesto, tope=512):
    cuerpo = {"contents": [{"parts": [{"text": texto}]}],
              "generationConfig": {"temperature": 0.2, "maxOutputTokens": tope,
                  "responseMimeType": "application/json",
                  "responseSchema": {"type": "OBJECT", "properties": {
                      "texto_diagnostico": {"type": "STRING"}, "accion_prescrita": {"type": "STRING"}},
                      "required": ["texto_diagnostico", "accion_prescrita"]}}}
    if presupuesto is not None:
        cuerpo["generationConfig"]["thinkingConfig"] = {"thinkingBudget": presupuesto}
    r = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent",
        data=json.dumps(cuerpo).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": LLAVE})
    try:
        with urllib.request.urlopen(r, timeout=60, context=CTX) as x: d = json.loads(x.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    c = d["candidates"][0]
    t = "".join(p.get("text", "") for p in c["content"]["parts"])
    u = d.get("usageMetadata", {})
    try: j = json.loads(t)
    except Exception: j = {"texto_diagnostico": t, "accion_prescrita": "(no era JSON)"}
    return {"diag": j.get("texto_diagnostico", ""), "accion": j.get("accion_prescrita", ""),
            "tokens": u.get("totalTokenCount"), "pensamiento": u.get("thoughtsTokenCount") or 0,
            "finish": c.get("finishReason")}

CTX = contexto_ssl()
if not LLAVE: sys.exit("falta GEMINI_API_KEY en .env")
for nombre, resumen in CASOS.items():
    print("\n" + "=" * 78); print(nombre); print("=" * 78)
    print("entrada:", resumen[:110], "…")
    for etiqueta, presupuesto, tope in [
            ("razonamiento ENCENDIDO, tope 512 ", None, 512),
            ("razonamiento ENCENDIDO, tope 2048", None, 2048),
            ("razonamiento APAGADO,   tope 512 ", 0, 512)]:
        r = pide(prompt(resumen), presupuesto, tope)
        if "error" in r: print(f"\n  {etiqueta}: {r['error']}"); continue
        print(f"\n  {etiqueta}  [{r['tokens']} tokens, {r['pensamiento']} de pensamiento, {r['finish']}]")
        print(f"    diagnostico: {r['diag']}")
        print(f"    accion     : {r['accion']}")
