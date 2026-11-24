#!/bin/bash
# Dice en que paso de docs/PASO_A_PASO.md estas. Corre esto cuando no te
# acuerdes de que sigue.
cd "$(dirname "$0")"
verde=$'\033[32m'; rojo=$'\033[31m'; gris=$'\033[90m'; fin=$'\033[0m'
marca() { [ "$1" == "si" ] && echo "${verde}[x]${fin}" || echo "${rojo}[ ]${fin}"; }

# --- paso 2: .env
faltan=0
if [ -f .env ]; then
  for v in FIREBASE_DB_URL FIREBASE_API_KEY FB_INGESTOR_EMAIL FB_INGESTOR_PASS \
           FB_VISOR_EMAIL FB_VISOR_PASS INGEST_KEY GEMINI_API_KEY; do
    val=$(grep -E "^$v=" .env | cut -d= -f2-)
    if [ -z "$val" ] || echo "$val" | grep -qE "PROYECTO|AIza\.\.\.|cambia-|ejemplo\.mx"; then
      faltan=$((faltan+1))
    fi
  done
  env_ok=$([ $faltan -eq 0 ] && echo si || echo no)
else env_ok=no; faltan=8; fi

generado_ok=$([ -f firebase/database.rules.generado.json ] && echo si || echo no)
nodered_ok=$(lsof -ti tcp:${PUERTO:-1881} >/dev/null 2>&1 && echo si || echo no)
ngrok_ok=$(pgrep -f "ngrok http" >/dev/null && echo si || echo no)
pagina_ok=$(lsof -ti tcp:8123 >/dev/null 2>&1 && echo si || echo no)
# Una fila cualquiera no basta: el paso 5 se da por hecho solo si hubo una
# escritura que de verdad llego a Firebase (resultado=ok).
ingesta_ok=$(grep -lq ";ok$" datos/ingesta_*.csv 2>/dev/null && echo si || echo no)
grep -hq ";ok$" datos/ingesta_*.csv 2>/dev/null && ingesta_ok=si || ingesta_ok=no
# Si alguna escritura llego a Firebase, las reglas estan publicadas: sin ellas
# el ingestor jamas habria podido escribir.
reglas_ok=$ingesta_ok
[ "$generado_ok" == "no" ] && reglas_ok=no
export_ok=$(ls datos/corrida_*.csv >/dev/null 2>&1 && echo si || echo no)
html_ok=$(grep -q "PEGA_AQUI_TU_API_KEY" web/index.html && echo no || echo si)
sketch_ok=$(grep -q "CAMBIAME" firmware/wokwi/sketch.ino && echo no || echo si)

echo
echo "  ACTIVIDAD 1 — donde vas"
echo "  ─────────────────────────────────────────────────────────"
echo "  $(marca si) 1. Proyecto de Firebase creado          ${gris}(no se puede comprobar desde aqui)${fin}"
echo "  $(marca $env_ok) 2. .env lleno                           $([ $faltan -gt 0 ] && echo "${rojo}faltan $faltan de 8${fin}")"
if [ "$reglas_ok" == "si" ]; then
  echo "  $(marca si) 3. Reglas publicadas y funcionando"
else
  echo "  $(marca $generado_ok) 3. Cuentas creadas, reglas generadas    ${gris}falta publicarlas en la consola${fin}"
fi
echo "  $(marca $nodered_ok) 4. Node-RED corriendo                   ${gris}./arranca.sh${fin}"
# Paso S2 (fase 3 de la Actividad 2): estado del editor. Con Node-RED arriba se
# pregunta a GET /auth/login (404 = sin API de administracion); si no, se lee .env.
if [ "$nodered_ok" == "si" ]; then
  al=$(curl -s --max-time 3 -w ' %{http_code}' "http://127.0.0.1:${PUERTO:-1881}/auth/login")
  case "$al" in
    *" 404") ed="deshabilitado (Node-RED no sirve el editor ni la API de administracion)";;
    *credentials*" 200") ed="protegido con usuario y contrasena";;
    *" 200") ed="${rojo}ABIERTO sin contrasena${fin}";;
    *) ed="no se pudo saber (${al##* })";;
  esac
else
  ./prepara_admin.sh --revisa >/dev/null 2>&1 && ed="protegido en .env (Node-RED apagado)" \
    || ed="deshabilitado en .env: falta ./prepara_admin.sh (Node-RED apagado)"
fi
echo "      ${gris}editor de Node-RED:${fin} $ed"
echo "  $(marca $ingesta_ok) 5. Ingesta probada, llego a Firebase"
echo "  $(marca $ngrok_ok) 6. URL publica arriba                   ${gris}ngrok http 1881${fin}"
echo "  $(marca $sketch_ok) 7. Sketch de Wokwi configurado          ${gris}INGEST_URL e INGEST_KEY${fin}"
echo "  $(marca $html_ok) 8. index.html configurado               ${gris}bloque CONFIG${fin}"
echo "  $(marca $pagina_ok) 9. Pagina servida                       ${gris}./sirve_pagina.sh${fin}"
echo "  $(marca $export_ok) 10. Datos exportados para el reporte    ${gris}tools/exporta_corrida.py${fin}"
echo
if [ "$env_ok" == "no" ]; then
  echo "  ${rojo}SIGUE:${fin} llenar los $faltan valores que faltan en .env (paso 2)."
  echo "         Todo lo demas esta bloqueado detras de esto."
elif [ "$reglas_ok" == "no" ]; then
  echo "  ${rojo}SIGUE:${fin} ./firebase/prepara.sh  y publicar las reglas en la consola (paso 3)."
elif [ "$nodered_ok" == "no" ]; then
  if [ "$reglas_ok" == "si" ]; then
    echo "  ${rojo}SIGUE:${fin} ./arranca.sh  (paso 4). Node-RED no esta corriendo."
  else
    echo "  ${rojo}SIGUE:${fin} publicar database.rules.generado.json en la consola, y luego"
    echo "         ./arranca.sh  (paso 4). Que quedaron publicadas se comprueba en"
    echo "         el paso 5, cuando el ingestor logre escribir."
  fi
elif [ "$ingesta_ok" == "no" ]; then
  echo "  ${rojo}SIGUE:${fin} probar la ingesta con el curl del paso 5; debe contestar 201."
elif [ "$ngrok_ok" == "no" ]; then
  echo "  ${rojo}SIGUE:${fin} probar la ingesta con curl (paso 5) y levantar ngrok (paso 6)."
elif [ "$sketch_ok" == "no" ]; then
  echo "  ${rojo}SIGUE:${fin} pegar los archivos en Wokwi y poner INGEST_URL e INGEST_KEY (paso 7)."
elif [ "$html_ok" == "no" ]; then
  echo "  ${rojo}SIGUE:${fin} llenar el bloque CONFIG de web/index.html (paso 8)."
else
  echo "  ${verde}SIGUE:${fin} dejar correr la captura y exportar los datos (paso 10)."
fi
echo
