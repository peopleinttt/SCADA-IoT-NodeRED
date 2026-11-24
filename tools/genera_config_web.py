#!/usr/bin/env python3
"""Escribe web/config_a2.js desde ../.env para la grafica de la Actividad 2. Python 3.9.

    python3 tools/genera_config_web.py

El archivo NO se versiona (.gitignore): lleva el correo y la clave del visor.
Esa cuenta solo puede leer (las reglas lo garantizan), pero la regla 4 de la
fase 1 pide que ninguna credencial entre al repositorio. demo_a2.sh lo corre.
"""
import json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
env = {}
for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
    l = l.strip()
    if l and not l.startswith("#") and "=" in l:
        k, v = l.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
url = env.get("FIREBASE_DB_URL", "").rstrip("/")
m = re.match(r"https://([a-z0-9-]+?)(-default-rtdb)?\.", url)
if not url or not m or not env.get("FB_VISOR_EMAIL"):
    sys.exit("faltan FIREBASE_DB_URL o FB_VISOR_EMAIL en .env")
proyecto = m.group(1)
cfg = {"firebase": {"apiKey": env.get("FIREBASE_API_KEY", ""), "authDomain": proyecto + ".firebaseapp.com",
                    "databaseURL": url, "projectId": proyecto},
       "visor": {"correo": env["FB_VISOR_EMAIL"], "clave": env.get("FB_VISOR_PASS", "")},
       "planta": env.get("PLANTA_ID", "planta_01"), "muestras": 300}
salida = RAIZ / "web" / "config_a2.js"
salida.write_text("// Generado por tools/genera_config_web.py desde .env. No se versiona.\n"
                  "window.CONFIG_A2 = " + json.dumps(cfg, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
print("escrito %s (proyecto %s, planta %s)" % (salida, proyecto, cfg["planta"]))
