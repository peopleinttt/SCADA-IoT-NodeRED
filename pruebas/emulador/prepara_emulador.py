#!/usr/bin/env python3
"""Deja el emulador listo con las reglas REALES del repo y UID de prueba."""
import json, pathlib
raiz = pathlib.Path(__file__).resolve().parent
reglas = (raiz.parent.parent / "firebase" / "database.rules.json").read_text()
reglas = reglas.replace("__UID_INGESTOR__", "UIDING").replace("__UID_VISOR__", "UIDVIS")
(raiz / "database.rules.json").write_text(reglas)
(raiz / "firebase.json").write_text(json.dumps({
    "database": {"rules": "database.rules.json"},
    "emulators": {"database": {"host": "127.0.0.1", "port": 9000}, "ui": {"enabled": False}}
}, indent=2))
print("database.rules.json y firebase.json escritos con UIDING / UIDVIS")
print("ahora:  npx firebase emulators:start --only database --project demo-iot")
