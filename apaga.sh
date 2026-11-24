#!/bin/bash
# Baja lo que levanto enciende.sh. No toca ningun Node-RED que no sea el de
# esta actividad: mata por PUERTO, nunca por nombre de proceso.
cd "$(dirname "$0")"
for p in ${PUERTO:-1881} 8123; do
  pid=$(lsof -ti tcp:$p 2>/dev/null | head -1)
  if [ -n "$pid" ]; then kill "$pid" 2>/dev/null && echo "  detenido lo del puerto $p"; fi
done
pkill -f "cloudflared tunnel" 2>/dev/null && echo "  tunel detenido"
echo "  listo"
