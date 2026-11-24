#!/bin/bash
# Corre todas las pruebas rapidas, una tras otra (nunca dos a la vez: comparten
# el puerto 1881 y el userDir de pruebas), y deja un resumen con el codigo de
# salida de cada una.
#
#   ./pruebas/bateria.sh                 -> resumen en $TMPDIR/a2_bateria/resumen.txt
#   ./pruebas/bateria.sh --con-emulador  -> ademas las reglas en el emulador de RTDB
#   SALIDA=dir ./pruebas/bateria.sh      -> otro directorio para las salidas
#
# Las largas (prueba_planta.py corrida de 200 cajas, prueba_sustituto.py
# determinismo) no van aqui: se corren a mano, ver pruebas/README.md.
# Codigo de salida: cuantas pruebas fallaron.
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
OUT="${SALIDA:-${TMPDIR:-/tmp}/a2_bateria}"
mkdir -p "$OUT"
P=/usr/bin/python3
fallos=0
: > "$OUT/resumen.txt"

puerto_libre() { ! lsof -ti tcp:"$1" >/dev/null 2>&1; }
for p in 1881 5020 5030 8099; do
  puerto_libre $p || { echo "El puerto $p esta ocupado: otra prueba o sesion lo usa. No se corre nada." | tee -a "$OUT/resumen.txt"; exit 99; }
done

corre() { # nombre, comando...
  local nombre="$1"; shift
  local t0=$(date +%s)
  "$@" > "$OUT/$nombre.txt" 2>&1
  local c=$?
  [ $c -eq 0 ] || fallos=$((fallos+1))
  local res=$(grep -E "RESULTADO|^OK$|^FAILED|Ran [0-9]+ tests|casos, [0-9]+ discrepancias" "$OUT/$nombre.txt" | tail -1)
  printf '%-26s exit=%-3s %4ss  %s\n' "$nombre" "$c" "$(( $(date +%s) - t0 ))" "$res" | tee -a "$OUT/resumen.txt"
}

corre mapa                $P pruebas/prueba_mapa.py
corre materiales_modelo   $P -u pruebas/prueba_materiales.py modelo
corre materiales_flujo    $P -u pruebas/prueba_materiales.py flujo
corre limites             $P tools/limites_planta.py
corre sustituto_funcional $P -u pruebas/prueba_sustituto.py funcional
corre sonda               $P -u pruebas/prueba_sonda.py
corre seguridad           $P -u pruebas/prueba_seguridad.py
corre planta_seguro       $P -u pruebas/prueba_planta.py seguro
corre planta_control      $P -u pruebas/prueba_planta.py control
corre nube                $P -u pruebas/prueba_nube.py
for extra in pruebas/prueba_vigila.py pruebas/prueba_desviador.py pruebas/prueba_hmi.py pruebas/prueba_diagnostico_a2.py pruebas/prueba_instrumentacion_a2.py pruebas/prueba_tablero.py pruebas/prueba_limites_linea.py; do
  [ -f "$extra" ] && corre "$(basename "$extra" .py | sed 's/^prueba_//')" $P -u "$extra"
done

python3 pruebas/simulador.py 8099 > "$OUT/simulador.log" 2>&1 &
SIM=$!; sleep 1
corre prueba_sh ./pruebas/prueba.sh
kill $SIM 2>/dev/null

if [ "${1:-}" == "--con-emulador" ]; then
  ( cd pruebas/emulador && python3 prepara_emulador.py >/dev/null && \
    nohup firebase emulators:start --only database --project demo-iot > "$OUT/emulador.log" 2>&1 & )
  for i in $(seq 1 90); do curl -s -o /dev/null "http://127.0.0.1:9000/.json?ns=demo-iot-default-rtdb" && break; sleep 1; done
  corre reglas_a1      $P pruebas/prueba_reglas.py --uid-ingestor UIDING --uid-visor UIDVIS
  corre reglas_proceso $P pruebas/prueba_reglas_proceso.py --emulador 127.0.0.1:9000
  for p in 9000 4400 4500; do lsof -ti tcp:$p 2>/dev/null | xargs kill 2>/dev/null; done
fi

echo "FIN: $fallos fallidas  (salidas en $OUT)" | tee -a "$OUT/resumen.txt"
exit $fallos
