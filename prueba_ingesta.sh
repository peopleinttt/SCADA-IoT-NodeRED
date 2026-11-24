#!/bin/bash
# Manda una muestra de prueba a Node-RED, como si fuera el ESP32.
#   ./prueba_ingesta.sh                          -> contra localhost:1881
#   ./prueba_ingesta.sh https://xxx.ngrok-free.app  -> contra la URL publica
cd "$(dirname "$0")"
[ -f .env ] || { echo "Falta .env"; exit 1; }
set -a; . ./.env; set +a
DESTINO="${1:-http://localhost:${PUERTO:-1881}}"

TS=$(python3 -c "import datetime as d;n=d.datetime.now(d.timezone.utc);print(n.strftime('%Y-%m-%dT%H:%M:%S.')+f'{n.microsecond//1000:03d}Z')")
echo "POST $DESTINO/telemetria"
curl -s -w "\n\nHTTP %{http_code} en %{time_total}s\n" -X POST "$DESTINO/telemetria" \
  -H 'Content-Type: application/json' \
  -H "X-Ingest-Key: $INGEST_KEY" \
  -H 'ngrok-skip-browser-warning: 1' \
  -d "{\"ts_origen\":\"$TS\",\"temperatura_C\":71.2,\"vibracion_mm_s\":4.8,\"ciclos_acumulados\":1}"
echo
echo "201 = todo bien.  Cualquier otra cosa: el campo 'motivo' te dice que pasó."
