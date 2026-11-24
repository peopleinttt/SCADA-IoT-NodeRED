#!/bin/bash
# Arranca Node-RED con los flujos de la Actividad 1 y las variables de .env.
#
#   ./arranca.sh              -> puerto 1881, userDir propio (node-red/runtime)
#   PUERTO=1890 ./arranca.sh  -> otro puerto
#   ./arranca.sh --recargar   -> vuelve a copiar flows.json encima del runtime
#
# Usa un userDir aparte a proposito: si ya tienes Node-RED en el 1880 con tus
# propios flujos, esto no lo toca ni le cambia nada.
set -euo pipefail
cd "$(dirname "$0")"
RAIZ="$PWD"

# ENV_ARCHIVO elige otro archivo de variables (lo usa el ensayo de la demo
# para no gastar cuota de Gemini ni tocar la base real); por omision, .env.
ENV_ARCHIVO="${ENV_ARCHIVO:-.env}"
[ -f "$ENV_ARCHIVO" ] || { echo "Falta $ENV_ARCHIVO. Copia .env.example a .env y llenalo."; exit 1; }
set -a; . "$ENV_ARCHIVO"; set +a

# Actividad 2: rutas de la configuracion, si .env no las fija. Node-RED no
# sabe donde esta el repo, asi que se las pasa este script.
export A2_MAPA="${A2_MAPA:-$RAIZ/config/mapa_registros_a2.json}"
export A2_SUST_CONFIG="${A2_SUST_CONFIG:-$RAIZ/config/sustituto_a2.json}"
# Capa de materiales (paso M2 de la fase 3): solo actua con A2_MATERIALES=1.
export A2_MAT_CONFIG="${A2_MAT_CONFIG:-$RAIZ/config/materiales.json}"
export A2_PLANTA_CONFIG="${A2_PLANTA_CONFIG:-$RAIZ/config/planta_a2.json}"

PUERTO="${PUERTO:-1881}"
RUNTIME="$RAIZ/node-red/runtime"
mkdir -p "$RUNTIME" "${DATOS_DIR:-$RAIZ/datos}"

# El runtime es una copia. Si el repo cambio y el runtime se quedo atras,
# Node-RED arrancaria con flujos viejos SIN avisar, y uno acaba depurando
# codigo que no es el que corre. Aqui se detecta y se actualiza, guardando la
# copia anterior por si habia ediciones hechas desde el editor.
if [ ! -f "$RUNTIME/flows.json" ]; then
  cp node-red/flows.json "$RUNTIME/flows.json"
  echo "flows.json copiado al runtime"
elif ! cmp -s node-red/flows.json "$RUNTIME/flows.json"; then
  cp "$RUNTIME/flows.json" "$RUNTIME/flows.json.anterior"
  cp node-red/flows.json "$RUNTIME/flows.json"
  echo "AVISO: el runtime tenia flujos distintos a los del repo; se actualizo."
  echo "       La version anterior quedo en node-red/runtime/flows.json.anterior"
elif [ "${1:-}" == "--recargar" ]; then
  cp node-red/flows.json "$RUNTIME/flows.json"
  echo "flows.json recargado (ya era identico)"
fi

if lsof -ti tcp:"$PUERTO" >/dev/null 2>&1; then
  echo "El puerto $PUERTO ya esta ocupado. Cierra lo que este ahi o usa PUERTO=otro."
  exit 1
fi

faltan=()
for v in FIREBASE_DB_URL PLANTA_ID INGEST_KEY GEMINI_API_KEY; do
  [ -n "${!v:-}" ] || faltan+=("$v")
done
[ ${#faltan[@]} -eq 0 ] || echo "AVISO: sin valor -> ${faltan[*]}"

# Paso S2: con NODE_RED_ADMIN_USER y un NODE_RED_ADMIN_HASH bcrypt el editor
# pide usuario y contrasena; si falta algo, Node-RED no sirve el editor ni la
# API de administracion (node-red/settings.js). La misma regla que ahi.
if [ -n "${NODE_RED_ADMIN_USER:-}" ] && [[ "${NODE_RED_ADMIN_HASH:-}" =~ ^\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}$ ]]; then
  echo "Editor: PROTEGIDO con usuario y contrasena (adminAuth)"
else
  echo "Editor: DESHABILITADO (sin NODE_RED_ADMIN_USER y NODE_RED_ADMIN_HASH validos; ver ./prepara_admin.sh)."
  echo "        Flujos, HMI, /a2/planta/* e ingesta funcionan igual."
fi
echo "Node-RED en http://localhost:$PUERTO"
echo "  endpoint de ingesta: http://localhost:$PUERTO/telemetria"
echo "  datos de la corrida: ${DATOS_DIR:-$RAIZ/datos}"
echo
exec node-red --userDir "$RUNTIME" --settings "$RAIZ/node-red/settings.js" --port "$PUERTO"
