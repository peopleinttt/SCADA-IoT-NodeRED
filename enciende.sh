#!/bin/bash
# Enciende lo que falte y deja todo corriendo en segundo plano.
# Es idempotente: lo que ya esta arriba no se toca.
#
#   ./enciende.sh     -> levanta Node-RED, el tunel y la pagina
#   ./apaga.sh        -> los baja
#
# Los registros quedan en /tmp/actividad1-*.log
cd "$(dirname "$0")"
RAIZ="$PWD"
PUERTO_NR="${PUERTO:-1881}"
PUERTO_WEB=8123
verde=$'\033[32m'; ama=$'\033[33m'; fin=$'\033[0m'

[ -f .env ] || { echo "Falta .env"; exit 1; }

# ---- Node-RED ------------------------------------------------------------
if lsof -ti tcp:$PUERTO_NR >/dev/null 2>&1; then
  echo "  ${verde}ya estaba${fin}  Node-RED     http://localhost:$PUERTO_NR"
else
  echo "  ${ama}levantando${fin} Node-RED…"
  nohup ./arranca.sh > /tmp/actividad1-nodered.log 2>&1 &
  for i in $(seq 1 40); do
    # sin la API de administracion (paso S2): la ruta de un nodo da 404 hasta que corren los flujos
    c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$PUERTO_NR/a2/planta/estado")
    [ "$c" != "000" ] && [ "$c" != "404" ] && break
    sleep 1
  done
  lsof -ti tcp:$PUERTO_NR >/dev/null 2>&1 \
    && echo "  ${verde}listo${fin}      Node-RED     http://localhost:$PUERTO_NR" \
    || echo "  FALLO Node-RED, revisa /tmp/actividad1-nodered.log"
fi

# ---- tunel publico -------------------------------------------------------
if pgrep -f "cloudflared tunnel" >/dev/null 2>&1; then
  echo "  ${verde}ya estaba${fin}  Tunel        $(cat tunel.url 2>/dev/null)"
else
  echo "  ${ama}levantando${fin} tunel…"
  ./tunel.sh >/dev/null 2>&1
  echo "  ${verde}listo${fin}      Tunel        $(cat tunel.url 2>/dev/null)"
  echo
  echo "  ${ama}OJO:${fin} el tunel es nuevo, asi que la URL cambio. El sketch de"
  echo "       Wokwi apunta a la vieja. Corre ./prepara_wokwi.sh y vuelve a pegarlo."
fi

# ---- pagina --------------------------------------------------------------
if lsof -ti tcp:$PUERTO_WEB >/dev/null 2>&1; then
  echo "  ${verde}ya estaba${fin}  Pagina       http://localhost:$PUERTO_WEB/index.html"
else
  echo "  ${ama}levantando${fin} pagina…"
  nohup python3 -m http.server $PUERTO_WEB --directory web > /tmp/actividad1-web.log 2>&1 &
  # Sondear el puerto, no dormir un rato fijo: el servidor tarda un instante
  # en enlazarse y un sleep corto reporta un fallo que no existe.
  for i in $(seq 1 15); do
    lsof -ti tcp:$PUERTO_WEB >/dev/null 2>&1 && break
    sleep 1
  done
  lsof -ti tcp:$PUERTO_WEB >/dev/null 2>&1 \
    && echo "  ${verde}listo${fin}      Pagina       http://localhost:$PUERTO_WEB/index.html" \
    || echo "  FALLO la pagina, revisa /tmp/actividad1-web.log"
fi

echo
echo "  Falta solo darle Play en Wokwi para que empiecen a llegar muestras."
