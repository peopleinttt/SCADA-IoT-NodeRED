#!/bin/bash
# Prueba de extremo a extremo de los flujos de Node-RED contra el simulador.
#
#   Terminal 1:  python3 pruebas/simulador.py 8099
#   Terminal 2:  ./pruebas/prueba.sh
#
# Levanta Node-RED en el puerto 1881 con un userDir temporal: NO toca la
# instancia que tengas corriendo en el 1880 ni sus flujos.
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SP="${TMPDIR:-/tmp}/actividad1-pruebas"
NRDIR="$SP/userdir"; DATOS="$SP/datos"; PUERTO=${PUERTO:-1881}; SIM=http://127.0.0.1:${SIM_PUERTO:-8099}
mkdir -p "$NRDIR" "$DATOS"

export FIREBASE_DB_URL="$SIM"
export IDENTITY_BASE_URL="$SIM"
export GEMINI_BASE_URL="$SIM"
export FIREBASE_API_KEY="llave-simulada"
export FB_INGESTOR_EMAIL="ingestor@ejemplo.mx"
export FB_INGESTOR_PASS="secreta"
export PLANTA_ID="planta_01"
export INGEST_KEY="clave-de-prueba"
export GEMINI_API_KEY="gemini-simulada"
export GEMINI_MODEL="gemini-2.5-flash"
export DATOS_DIR="$DATOS"
export TZ_REPORTE="America/Mexico_City"
export DIAG_MIN_REPETIR_MIN=0
# Paso S2: el boton de los inject (POST /inject/<id>) es de la API de
# administracion. Credenciales desechables de esta corrida: el hash solo vive
# en el entorno de este proceso y de su Node-RED; nada va a disco.
eval "$(/usr/bin/python3 "$REPO/pruebas/admin_desechable.py" --shell)" || { echo "no se generaron credenciales desechables"; exit 1; }
TOK=""

ok=0; fallo=0
verifica() { # descripcion, esperado, obtenido
  if [ "$2" == "$3" ]; then echo "  OK   $1"; ok=$((ok+1));
  else echo "  FALLA $1 -> esperaba [$2], obtuvo [$3]"; fallo=$((fallo+1)); fi
}
modo() { curl -s -X POST $SIM/__modo -H 'Content-Type: application/json' -d "{\"modo\":\"$1\"}" >/dev/null; }
estado() { curl -s $SIM/__estado; }

arranca_nodered() {
  # Node-RED renombra su proceso, asi que se mata por puerto y NUNCA por nombre
  # (el usuario tiene otra instancia suya en el 1880 que no se debe tocar).
  lsof -ti tcp:$PUERTO 2>/dev/null | xargs -r kill 2>/dev/null
  for i in $(seq 1 30); do
    lsof -ti tcp:$PUERTO >/dev/null 2>&1 || break
    sleep 1
  done
  cp "$REPO/node-red/flows.json" "$NRDIR/flows.json"
  node-red --userDir "$NRDIR" --settings "$REPO/node-red/settings.js" --port $PUERTO > "$SP/nodered.log" 2>&1 &
  # Espera sin la API de administracion (paso S2): la ruta de un nodo http in
  # da 404 hasta que los flujos corren; despues contesta otra cosa.
  for i in $(seq 1 60); do
    c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$PUERTO/a2/planta/estado")
    if [ "$c" != "000" ] && [ "$c" != "404" ]; then
      TOK=$(curl -s --max-time 5 "http://127.0.0.1:$PUERTO/auth/token" --data-urlencode client_id=node-red-admin \
            --data-urlencode grant_type=password --data-urlencode scope='*' \
            --data-urlencode "username=$NODE_RED_ADMIN_USER" --data-urlencode "password=$ADMIN_CLAVE" \
            | python3 -c "import json,sys;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
      [ -n "$TOK" ] && return 0
      echo "Node-RED arranco pero no dio token de administracion"; tail -20 "$SP/nodered.log"; exit 1
    fi
    sleep 1
  done
  echo "Node-RED no arranco"; tail -20 "$SP/nodered.log"; exit 1
}
inject() { curl -s -X POST -H "Authorization: Bearer $TOK" "http://127.0.0.1:$PUERTO/inject/$1" > /dev/null; }

envia() { # json, clave
  curl -s -o "$SP/resp.json" -w "%{http_code}" -X POST "http://127.0.0.1:$PUERTO/telemetria" \
    -H 'Content-Type: application/json' -H "X-Ingest-Key: ${2:-clave-de-prueba}" -d "$1"
}
motivo() { python3 -c "import json;print(json.load(open('$SP/resp.json')).get('motivo',''))" 2>/dev/null; }

ts() { python3 -c "
import datetime as dt
print((dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=$1)).strftime('%Y-%m-%dT%H:%M:%S.')+f'{(dt.datetime.now(dt.timezone.utc).microsecond//1000):03d}Z')"; }

curl -s -X GET $SIM/__reinicia > /dev/null
rm -f "$DATOS"/*.csv "$DATOS"/*.log 2>/dev/null
echo "=== 1. Validacion en el nodo de funcion ==="
arranca_nodered
sleep 3

c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70.1,\"vibracion_mm_s\":3.2}")
verifica "falta ciclos_acumulados -> 400" "400 campos_faltantes" "$c $(motivo)"

c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70.1,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":5}" "clave-mala")
verifica "clave compartida incorrecta -> 401" "401 clave_invalida" "$c $(motivo)"

c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70.1,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":5,\"humedad\":40}")
verifica "campo fuera del esquema -> 422" "422 campos_no_esperados" "$c $(motivo)"

c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":900,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":5}")
verifica "temperatura imposible -> 422" "422 valor_fuera_de_rango" "$c $(motivo)"

c=$(envia "{\"ts_origen\":\"1970-01-01T00:00:00.000Z\",\"temperatura_C\":70,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":5}")
verifica "reloj sin NTP (1970) -> 422" "422 ts_origen_demasiado_viejo" "$c $(motivo)"

c=$(envia "{\"ts_origen\":\"no-es-fecha\",\"temperatura_C\":70,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":5}")
verifica "ts_origen no parseable -> 422" "422 ts_origen_no_parseable" "$c $(motivo)"

hora_local=$(python3 -c "import datetime as d;print(d.datetime.now(d.timezone(d.timedelta(hours=-6))).strftime('%Y-%m-%dT%H:%M:%S.000-06:00'))")
c=$(envia "{\"ts_origen\":\"$hora_local\",\"temperatura_C\":70,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":5}")
verifica "ts_origen en hora local en vez de UTC -> 422" "422 ts_origen_no_es_utc" "$c $(motivo)"

c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":95,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":5}")
verifica "95 C, fuera del rango del DHT22 -> 422" "422 valor_fuera_de_rango" "$c $(motivo)"

c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70,\"vibracion_mm_s\":250,\"ciclos_acumulados\":5}")
verifica "250 mm/s, fuera del rango del transmisor -> 422" "422 valor_fuera_de_rango" "$c $(motivo)"

c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":5.5}")
verifica "ciclos no entero -> 422" "422 ciclos_no_entero" "$c $(motivo)"

echo "=== 2. Ingesta feliz (6 muestras) ==="
for i in 6 5 4 3 2 1; do
  t=$(ts $((i*5)))
  temp=$(python3 -c "print(round(70+$i*1.4,2))")
  vib=$(python3 -c "print(round(4.0+$i*0.9,2))")
  c=$(envia "{\"ts_origen\":\"$t\",\"temperatura_C\":$temp,\"vibracion_mm_s\":$vib,\"ciclos_acumulados\":$((100+i))}")
  [ "$c" == "201" ] || echo "  muestra $i devolvio $c"
done
n=$(estado | python3 -c "import json,sys;print(len(json.load(sys.stdin)['telemetria']))")
verifica "6 registros escritos en Firebase" "6" "$n"
rid=$(python3 -c "import json;print(json.load(open('$SP/resp.json')).get('registroId',''))")
verifica "la respuesta trae registroId" "si" "$([ -n "$rid" ] && echo si || echo no)"
sleep 1
hoy=$(TZ=America/Mexico_City date +%F)
verifica "CSV de instrumentacion creado" "si" "$([ -f "$DATOS/ingesta_$hoy.csv" ] && echo si || echo no)"
lineas=$(wc -l < "$DATOS/ingesta_$hoy.csv" 2>/dev/null | tr -d ' ')
verifica "CSV con encabezado + 6 filas" "7" "$lineas"

echo "=== 3. Diagnostico con Gemini (camino feliz) ==="
modo ok
inject inj_diag
sleep 4
nd=$(estado | python3 -c "import json,sys;print(len(json.load(sys.stdin)['diagnosticos']))")
verifica "diagnostico escrito en Firebase" "1" "$nd"
estado | python3 -c "
import json,sys
d=list(json.load(sys.stdin)['diagnosticos'].values())
if d:
    r=d[0]
    faltan=[k for k in ('ts','resumen_entrada','texto_diagnostico','accion_prescrita','modelo','latencia_ms') if k not in r]
    print('  campos faltantes:', faltan if faltan else 'ninguno')
    print('  accion_prescrita:', r.get('accion_prescrita'))
    print('  modelo:', r.get('modelo'), '| latencia_ms:', r.get('latencia_ms'))
    print('  ts:', r.get('ts'))
"
verifica "CSV de diagnosticos creado" "si" "$([ -f "$DATOS/diagnosticos_$hoy.csv" ] && echo si || echo no)"

ct=$(estado | python3 -c "import json,sys;print(json.load(sys.stdin)['cabeceras'].get('telemetria.json',{}).get('content-type',''))")
verifica "Firebase recibio Content-Type de msg.headers" "application/json" "$ct"
gk=$(estado | python3 -c "import json,sys;print(json.load(sys.stdin)['cabeceras'].get('gemini-2.5-flash:generateContent',{}).get('x-goog-api-key',''))")
verifica "Gemini recibio la cabecera x-goog-api-key" "gemini-simulada" "$gk"

echo "=== 4. Modos de falla de Gemini ==="
for m in cuota basura truncado texto_suelto; do
  arranca_nodered; sleep 3
  modo ok
  envia "{\"ts_origen\":\"$(ts 10)\",\"temperatura_C\":78.5,\"vibracion_mm_s\":9.8,\"ciclos_acumulados\":200}" >/dev/null
  envia "{\"ts_origen\":\"$(ts 5)\",\"temperatura_C\":79.5,\"vibracion_mm_s\":10.2,\"ciclos_acumulados\":201}" >/dev/null
  antes=$(estado | python3 -c "import json,sys;print(len(json.load(sys.stdin)['diagnosticos']))")
  modo $m
  inject inj_diag
  sleep 4
  despues=$(estado | python3 -c "import json,sys;print(len(json.load(sys.stdin)['diagnosticos']))")
  esp=$antes; [ "$m" == "texto_suelto" ] && esp=$((antes+1))
  verifica "modo '$m': diagnosticos $antes -> $esp" "$esp" "$despues"
  grep -o "Gemini \[[a-z_]*\]" "$SP/nodered.log" | tail -1 | sed 's/^/  bitacora: /'
done

echo "=== 5. Permiso denegado por reglas de Firebase ==="
arranca_nodered; sleep 3
modo permiso
c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":9}")
verifica "reglas rechazan la escritura -> 502" "502 firebase_permiso_denegado" "$c $(motivo)"
modo regla
c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":9}")
verifica "dato invalido para las reglas -> 502" "502 firebase_dato_invalido" "$c $(motivo)"
modo ok

echo "=== 6. PLANTA_ID mal escrito ==="
export PLANTA_ID="planta_7"
arranca_nodered; sleep 3
c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":9}")
verifica "planta_7 no cumple planta_NN -> 500" "500 planta_id_invalido" "$c $(motivo)"
export PLANTA_ID="planta_01"

echo "=== 7. Base inalcanzable (nodo Catch) ==="
export FIREBASE_DB_URL="http://127.0.0.1:9"
arranca_nodered; sleep 3
c=$(envia "{\"ts_origen\":\"$(ts 0)\",\"temperatura_C\":70,\"vibracion_mm_s\":3.2,\"ciclos_acumulados\":9}")
sleep 2
verifica "errores.log escrito por el nodo Catch" "si" "$([ -f "$DATOS/errores.log" ] && echo si || echo no)"
tail -1 "$DATOS/errores.log" 2>/dev/null | sed 's/^/  /'

lsof -ti tcp:$PUERTO 2>/dev/null | xargs -r kill 2>/dev/null
echo
echo "=== RESULTADO: $ok correctas, $fallo fallidas ==="
exit $fallo
