#!/bin/bash
# Genera el sketch con la URL publica y la clave ya puestas, listo para pegar
# en Wokwi. Si no le pasas la URL, la saca de ngrok si esta corriendo.
#
#   ./prepara_wokwi.sh                                  -> toma la URL de ngrok
#   ./prepara_wokwi.sh https://algo.ngrok-free.dev      -> URL explicita
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo "Falta .env"; exit 1; }
set -a; . ./.env; set +a

URL="${1:-}"
if [ -z "$URL" ]; then
  # Primero el tunel de Cloudflare, que es el que funciona con Wokwi.
  # '|| true' es obligatorio: con 'set -e' un grep sin coincidencias aborta
  # el script en silencio, que fue justo lo que paso la primera vez.
  for L in /tmp/cloudflared-actividad1.log /tmp/cf.log; do
    [ -f "$L" ] || continue
    URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$L" 2>/dev/null | head -1 || true)
    [ -n "$URL" ] && break
  done
  if [ -z "$URL" ] && [ -f tunel.url ]; then URL=$(cat tunel.url); fi
  # Si no hay, se cae a ngrok. Acepta tanto el tunel HTTPS como el TCP. El TCP se traduce a http://
  # porque es TCP puro sin TLS: es la salida cuando el ESP32 simulado no
  # logra completar el apreton de manos TLS.
  [ -z "$URL" ] && URL=$(curl -s --max-time 5 http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c "
import json,sys
try:
    ts = json.load(sys.stdin).get('tunnels',[])
    tcp = [t for t in ts if t.get('proto')=='tcp']
    if tcp: print(tcp[0]['public_url'].replace('tcp://','http://'))
    else:
        for t in ts:
            if t.get('proto')=='https': print(t['public_url']); break
except Exception: pass" || true)
fi
if [ -z "$URL" ]; then
  echo "No encontre la URL publica. Levanta ngrok con 'ngrok http 1881'"
  echo "o pasala a mano: ./prepara_wokwi.sh https://algo.ngrok-free.dev"
  exit 1
fi
URL="${URL%/}"
URL="${URL/#tcp:\/\//http://}"   # por si la pasan a mano como tcp://

SALIDA="firmware/wokwi/sketch.configurado.ino"
python3 - "$URL" "$INGEST_KEY" "$SALIDA" <<'PY'
import pathlib, sys
url, clave, salida = sys.argv[1], sys.argv[2], sys.argv[3]
s = pathlib.Path("firmware/wokwi/sketch.ino").read_text()
antes = s
s = s.replace('#define INGEST_URL   "https://CAMBIAME.ngrok-free.app/telemetria"',
              f'#define INGEST_URL   "{url}/telemetria"')
s = s.replace('#define INGEST_KEY   "CAMBIAME-clave-larga-y-aleatoria"',
              f'#define INGEST_KEY   "{clave}"')
if s == antes:
    sys.exit("no encontre las lineas a sustituir en sketch.ino")
pathlib.Path(salida).write_text(s)
print(f"  {salida} generado")
PY

cat "$SALIDA" | pbcopy 2>/dev/null && COPIADO=" (y copiado al portapapeles)" || COPIADO=""
echo
echo "  URL publica : $URL/telemetria"
echo "  Clave       : ${INGEST_KEY:0:12}…"
echo "  Archivo     : $SALIDA$COPIADO"
echo
echo "  Pegalo en la pestana sketch.ino de Wokwi. Ojo: si reinicias ngrok"
echo "  la URL cambia y hay que volver a generar y pegar."
