#!/bin/bash
# Demostracion de la Actividad 2 con un solo comando.
#
#   ./demo_a2.sh            -> revisa, arranca Node-RED y la pagina, imprime las URL
#   ./demo_a2.sh --revisa   -> solo las revisiones, no arranca nada
#   ./demo_a2.sh --apaga    -> baja lo que levanto (por puerto, como apaga.sh)
#
# Que planta usa lo decide .env, nunca el codigo:
#   sustituto local    A2_MODBUS_HOST vacio (127.0.0.1:5020), A2_SUSTITUTO vacio o 1
#   Factory I/O        A2_MODBUS_HOST=<IP de Tailscale o de Parallels>, A2_MODBUS_PUERTO=502,
#                      A2_SUSTITUTO=0, A2_MAPA=config/mapa_registros_fio.json,
#                      A2_PLANTA_CONFIG=config/planta_fio.json
# Revisa, en este orden: limites factibles, que el Modbus conteste, que
# Firebase de sesion al ingestor y cuanta cuota de Gemini queda hoy (contador
# local; el de Google no se consulta para no gastar una peticion).
cd "$(dirname "$0")"
RAIZ="$PWD"
export PATH="/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH"
verde=$'\033[32m'; rojo=$'\033[31m'; ama=$'\033[33m'; fin=$'\033[0m'
ok()   { echo "  ${verde}OK${fin}    $*"; }
mal()  { echo "  ${rojo}FALLA${fin} $*"; FALLAS=$((FALLAS+1)); }
aviso(){ echo "  ${ama}AVISO${fin} $*"; }
FALLAS=0
PUERTO_NR=${PUERTO:-1881}; PUERTO_WEB=8123

if [ "${1:-}" == "--apaga" ]; then
  for p in $PUERTO_NR $PUERTO_WEB; do
    # Solo el que ESCUCHA en el puerto: sin -sTCP:LISTEN, lsof tambien da los
    # clientes conectados (un navegador con la HMI abierta) y se mataba a uno de esos.
    pid=$(lsof -ti tcp:$p -sTCP:LISTEN 2>/dev/null | head -1); [ -n "$pid" ] && kill "$pid" && echo "  detenido lo del puerto $p"
  done
  exit 0
fi

ENV_ARCHIVO="${ENV_ARCHIVO:-.env}"          # el ensayo usa otro archivo; ver pruebas/ensayo_demo.py
export ENV_ARCHIVO
[ -f "$ENV_ARCHIVO" ] || { echo "Falta $ENV_ARCHIVO (cp .env.example .env)"; exit 1; }
set -a; . "$ENV_ARCHIVO"; set +a
export A2_MAPA="${A2_MAPA:-$RAIZ/config/mapa_registros_a2.json}"
export A2_SUST_CONFIG="${A2_SUST_CONFIG:-$RAIZ/config/sustituto_a2.json}"
# Capa de materiales (paso M2 de la fase 3): solo actua con A2_MATERIALES=1.
export A2_MAT_CONFIG="${A2_MAT_CONFIG:-$RAIZ/config/materiales.json}"
export A2_PLANTA_CONFIG="${A2_PLANTA_CONFIG:-$RAIZ/config/planta_a2.json}"
HOST="${A2_MODBUS_HOST:-127.0.0.1}"; MBPUERTO="${A2_MODBUS_PUERTO:-5020}"
SUSTITUTO=$([ "$HOST" == "127.0.0.1" ] && [ "${A2_SUSTITUTO:-1}" != "0" ] && echo si || echo no)
P=/usr/bin/python3

echo
echo "  ACTIVIDAD 2 — demostracion"
echo "  ─────────────────────────────────────────────────────────"
echo "  planta: $([ $SUSTITUTO == si ] && echo "sustituto local" || echo "Modbus $HOST:$MBPUERTO") · mapa $(basename "$A2_MAPA") · cliente $(basename "$A2_PLANTA_CONFIG")"
echo

# ---- 1. limites ---------------------------------------------------------------------
SONDEO=$($P -c "import json,os;c=json.load(open(os.environ['A2_PLANTA_CONFIG']));print(os.environ.get('A2_SONDEO_MS') or c['sondeo_ms'])")
RTT=$($P -c "import json,os;c=json.load(open(os.environ['A2_PLANTA_CONFIG']));print(os.environ.get('A2_RTT_PREVISTO_MS') or c['rtt_previsto_ms'])")
REF=$($P -c "import json,os;c=json.load(open(os.environ['A2_PLANTA_CONFIG']));print(os.environ.get('A2_REFRESCO_MS') or c.get('refresco_ms',0))")
# Lo medido vale como en Node-RED: mismo sondeo y sin rtt ni refresco dados a mano.
MEDIDO=$([ -z "${A2_RTT_PREVISTO_MS:-}" ] && [ -z "${A2_REFRESCO_MS:-}" ] && echo --medido)
if $P tools/limites_planta.py --config "$A2_PLANTA_CONFIG" --sondeo "$SONDEO" --rtt "$RTT" --refresco "$REF" $MEDIDO > /tmp/a2_demo_limites.txt 2>&1; then
  ok "limites factibles con sondeo $SONDEO ms, rtt $RTT ms, refresco $REF ms"
else
  mal "limites NO factibles con sondeo $SONDEO ms, rtt $RTT ms, refresco $REF ms (marcha dara 409):"
  grep "!" /tmp/a2_demo_limites.txt | head -3 | sed 's/^/        /'
fi

# ---- 2. Modbus (si es Factory I/O, antes de arrancar; si es el sustituto, despues) -----
revisa_modbus() {
  if $P tools/sonda_modbus.py --mapa "$A2_MAPA" --host "$HOST" --puerto "$MBPUERTO" --espera 5 mide "$1" -n 5 > /tmp/a2_demo_modbus.txt 2>&1; then
    ok "Modbus $HOST:$MBPUERTO contesta: $(grep 'ida y vuelta' /tmp/a2_demo_modbus.txt | sed 's/  */ /g')"
  elif grep -q "No route to host\|Errno 65" /tmp/a2_demo_modbus.txt && \
       node -e '
         const s = require("net").connect(Number(process.argv[2]), process.argv[1]);
         const t0 = Date.now(); s.setTimeout(3000, () => process.exit(1)); s.on("error", () => process.exit(1));
         s.on("connect", () => s.write(Buffer.from([0,1,0,0,0,6,Number(process.env.A2_MODBUS_UNIDAD || 1),2,0,0,0,1])));
         s.on("data", d => { console.log(Date.now() - t0); process.exit(d[7] === 2 ? 0 : 1); });
       ' "$HOST" "$MBPUERTO" > /tmp/a2_demo_modbus_node.txt 2>&1; then
    # El Python de macOS no tiene permiso de "Red local" hacia la VM; Node si.
    ok "Modbus $HOST:$MBPUERTO contesta (revisado con Node, $(cat /tmp/a2_demo_modbus_node.txt) ms; Python sin permiso de Red local)"
  else
    mal "Modbus $HOST:$MBPUERTO no contesta: $(tail -1 /tmp/a2_demo_modbus.txt)"
  fi
}
PRIMERA=$($P -c "import json,os;m=json.load(open(os.environ['A2_MAPA']));print(next((e['nombre'] for e in m['etiquetas'] if e['tabla'] in ('entrada_discreta','registro_entrada') and e['direccion'] is not None),''))")
if [ -z "$PRIMERA" ]; then
  mal "el mapa $(basename "$A2_MAPA") no tiene etiquetas de lectura con direccion (PUERTA ARI R0)"
elif [ $SUSTITUTO == no ]; then
  revisa_modbus "$PRIMERA"
fi

# ---- 3. Firebase ----------------------------------------------------------------------
if [ "${A2_NUBE:-}" != "1" ]; then
  aviso "A2_NUBE no es 1: los registros no se escriben en Firebase (falta publicar las reglas, PUERTA ARI P1)"
fi
FB=$($P - <<'EOF'
import json, os, ssl, urllib.request
try:
    import certifi; ctx = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    ctx = ssl.create_default_context()
k = os.environ.get("FIREBASE_API_KEY", "")
d = json.dumps({"email": os.environ.get("FB_INGESTOR_EMAIL"), "password": os.environ.get("FB_INGESTOR_PASS"), "returnSecureToken": True}).encode()
r = urllib.request.Request("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + k, data=d, headers={"Content-Type": "application/json"})
try:
    print("ok " + json.load(urllib.request.urlopen(r, timeout=15, context=ctx))["localId"])
except Exception as e:
    print("falla " + str(e)[:120])
EOF
)
case "$FB" in ok*) ok "Firebase da sesion al ingestor (uid ${FB#ok })";; *) mal "Firebase no da sesion: ${FB#falla }";; esac

# ---- 4. cuota de Gemini (contador local, no gasta peticiones) ---------------------------
HOY=$(TZ="${TZ_REPORTE:-America/Mexico_City}" date +%F)
DD="${DATOS_DIR:-$RAIZ/datos}"
USADAS_A2=$(tail -n +2 "$DD/a2_diagnosticos_$HOY.csv" 2>/dev/null | wc -l | tr -d ' ')
USADAS_A1=$(tail -n +2 "$DD/diagnosticos_$HOY.csv" 2>/dev/null | wc -l | tr -d ' ')
TOPE=${A2_DIAG_MAX_DIA:-15}
QUEDAN=$(( TOPE - USADAS_A2 )); [ $QUEDAN -lt 0 ] && QUEDAN=0
GQ=$(( 20 - USADAS_A2 - USADAS_A1 ))
[ $QUEDAN -gt 0 ] && ok "Gemini: quedan $QUEDAN de $TOPE consultas de A2 hoy (A1 uso $USADAS_A1; cuota de Google ~$GQ de 20 por modelo)" \
                  || aviso "Gemini: tope diario de A2 alcanzado ($USADAS_A2/$TOPE): el boton de diagnostico no consultara"

[ "${1:-}" == "--revisa" ] && { echo; echo "  $FALLAS revisiones fallidas"; exit $FALLAS; }

# ---- arranque ---------------------------------------------------------------------------
echo
# Con Factory I/O, la escena se reinicia por Modbus antes de arrancar: Reset,
# espera a que se vacie y Run (tools/reinicia_escena.mjs; en Node porque el
# Python de macOS no tiene permiso de "Red local" hacia la VM).
if [ $SUSTITUTO == no ] && grep -q '"fio_reset"' "$A2_MAPA"; then
  if node tools/reinicia_escena.mjs "$HOST" "$MBPUERTO" --mapa "$A2_MAPA" > /tmp/a2_demo_reinicio.txt 2>&1; then
    ok "escena reiniciada por Modbus: Reset, vacia y Run"
  else
    mal "la escena no se reinicio: $(tail -1 /tmp/a2_demo_reinicio.txt)"
  fi
fi
if lsof -ti tcp:$PUERTO_NR >/dev/null 2>&1; then
  ok "Node-RED ya estaba en el $PUERTO_NR"
else
  nohup ./arranca.sh > /tmp/actividad2-nodered.log 2>&1 &
  # Espera sin la API de administracion (paso S2): la ruta de un nodo da 404 hasta que corren los flujos.
  for i in $(seq 1 60); do
    c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$PUERTO_NR/a2/planta/estado")
    [ "$c" != "000" ] && [ "$c" != "404" ] && break; sleep 1
  done
  lsof -ti tcp:$PUERTO_NR >/dev/null 2>&1 && ok "Node-RED arriba en el $PUERTO_NR" || mal "Node-RED no arranco: /tmp/actividad2-nodered.log"
fi
if [ $SUSTITUTO == si ] && [ -n "$PRIMERA" ]; then
  for i in $(seq 1 20); do $P tools/sonda_modbus.py --mapa "$A2_MAPA" --espera 1 lee "$PRIMERA" >/dev/null 2>&1 && break; sleep 0.5; done
  revisa_modbus "$PRIMERA"
fi
# A2-Planta carga su configuracion ~1 s despues de arrancar los flujos y luego
# hace la secuencia segura: se espera hasta 20 s a que diga com = ok.
EST=""
for i in $(seq 1 40); do
  EST=$(curl -s "http://127.0.0.1:$PUERTO_NR/a2/planta/estado" | $P -c "import json,sys;e=json.load(sys.stdin);print(e['com'], e['actuador'], 'factible' if e['limites']['factible'] else 'NO-factible')" 2>/dev/null)
  case "$EST" in ok*) break;; esac
  sleep 0.5
done
[ -n "$EST" ] && ok "A2-Planta: $EST" || mal "A2-Planta no contesta en /a2/planta/estado"
$P tools/genera_config_web.py > /tmp/actividad2-config-web.txt 2>&1 \
  && ok "grafica configurada (web/config_a2.js, cuenta del visor, no se versiona)" \
  || mal "no se pudo escribir web/config_a2.js: $(tail -1 /tmp/actividad2-config-web.txt)"
if ! lsof -ti tcp:$PUERTO_WEB >/dev/null 2>&1; then
  nohup $P -m http.server $PUERTO_WEB --directory web > /tmp/actividad2-web.log 2>&1 &
  sleep 1
fi
TS=$(/Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4 2>/dev/null | head -1)
echo
echo "  HMI       http://localhost:$PUERTO_NR/dashboard/a2"
[ -n "$TS" ] && echo "            http://$TS:$PUERTO_NR/dashboard/a2   (otro equipo de la tailnet)"
echo "  Grafica   http://localhost:$PUERTO_WEB/proceso.html"
echo "  Editor    http://localhost:$PUERTO_NR/   (por el tunel publico da 403)"
echo "  Guion     docs/DEMO_A2.md"
echo
echo "  $FALLAS revisiones fallidas"
exit $FALLAS
