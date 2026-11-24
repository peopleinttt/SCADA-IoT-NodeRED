#!/bin/bash
# Levanta el tunel publico que necesita Wokwi para alcanzar tu Node-RED.
#
#   ./tunel.sh          -> arranca cloudflared y deja la URL en tunel.url
#   ./tunel.sh --url    -> solo imprime la URL del tunel que ya corre
#
# Se usa Cloudflare y no ngrok por una razon medida el 2026-08-25: el ESP32
# simulado de Wokwi NO logra completar el apreton de manos TLS contra el borde
# de ngrok (falla a los ~6.7 s), pero SI lo completa contra Cloudflare
# (6.2 s) y contra example.com. Comprobado desde dentro del simulador.
set -euo pipefail
cd "$(dirname "$0")"
LOG=/tmp/cloudflared-actividad1.log
PUERTO="${PUERTO:-1881}"

if [ "${1:-}" == "--url" ]; then
  grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG" 2>/dev/null | head -1
  exit 0
fi

# bin/cloudflared gana si existe (asi se armo en la MacBook). Si no, se usa el
# del PATH: en la Mac mini viene de Homebrew en /opt/homebrew/bin.
CLOUDFLARED=./bin/cloudflared
[ -x "$CLOUDFLARED" ] || CLOUDFLARED="$(command -v cloudflared || true)"
[ -n "$CLOUDFLARED" ] || { echo "Falta cloudflared: ni bin/cloudflared ni en el PATH"; exit 1; }
lsof -ti tcp:"$PUERTO" >/dev/null 2>&1 || echo "AVISO: no hay nada escuchando en el puerto $PUERTO (./arranca.sh)"

pkill -f "cloudflared tunnel --url http://localhost:$PUERTO" 2>/dev/null || true
sleep 1
: > "$LOG"
nohup "$CLOUDFLARED" tunnel --url "http://localhost:$PUERTO" --no-autoupdate >> "$LOG" 2>&1 &

echo "Levantando el tunel…"
for i in $(seq 1 30); do
  URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG" 2>/dev/null | head -1)
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "${URL:-}" ] || { echo "No aparecio la URL. Revisa $LOG"; exit 1; }

echo "$URL" > tunel.url
echo
echo "  URL publica : $URL"
echo "  endpoint    : $URL/telemetria"
echo
echo "  Sigue:  ./prepara_wokwi.sh    (toma esta URL solo)"
echo "  El tunel corre en segundo plano. Para pararlo:"
echo "    pkill -f 'cloudflared tunnel'"
