#!/bin/bash
# Sirve web/index.html por HTTP. Hace falta porque la pagina usa modulos ES:
# abrirla con doble clic (file://) no funciona, el navegador los bloquea.
cd "$(dirname "$0")"
PUERTO="${PUERTO:-8123}"
echo "Pagina en  http://localhost:$PUERTO/index.html"
echo "Con datos de ejemplo (sin Firebase):  http://localhost:$PUERTO/index.html?demo=1"
echo "Ctrl+C para detener."
exec python3 -m http.server "$PUERTO" --directory web
