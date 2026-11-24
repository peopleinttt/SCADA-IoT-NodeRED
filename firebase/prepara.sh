#!/bin/bash
# Crea las dos cuentas de servicio, averigua sus UID y genera el archivo de
# reglas listo para desplegar. No toca nada en Firebase por si solo: solo
# escribe database.rules.generado.json.
#
#   1. Consola de Firebase -> Authentication -> Sign-in method -> habilita
#      "Correo electronico/contrasena".
#   2. Copia .env.example a .env, llena los valores y corre:  ./prepara.sh
set -euo pipefail
cd "$(dirname "$0")"
[ -f ../.env ] && set -a && . ../.env && set +a

: "${FIREBASE_API_KEY:?falta FIREBASE_API_KEY en .env}"
: "${FB_INGESTOR_EMAIL:?falta FB_INGESTOR_EMAIL}"
: "${FB_INGESTOR_PASS:?falta FB_INGESTOR_PASS}"
: "${FB_VISOR_EMAIL:?falta FB_VISOR_EMAIL}"
: "${FB_VISOR_PASS:?falta FB_VISOR_PASS}"

ID=https://identitytoolkit.googleapis.com/v1/accounts

uid_de() { # correo, clave  -> imprime el localId, creando la cuenta si no existe
  local correo="$1" clave="$2" cuerpo resp uid
  cuerpo=$(printf '{"email":"%s","password":"%s","returnSecureToken":true}' "$correo" "$clave")
  resp=$(curl -s -X POST "$ID:signUp?key=$FIREBASE_API_KEY" -H 'Content-Type: application/json' -d "$cuerpo")
  uid=$(printf '%s' "$resp" | python3 -c "import json,sys;print(json.load(sys.stdin).get('localId',''))")
  if [ -z "$uid" ]; then   # ya existia: entramos en lugar de crearla
    resp=$(curl -s -X POST "$ID:signInWithPassword?key=$FIREBASE_API_KEY" -H 'Content-Type: application/json' -d "$cuerpo")
    uid=$(printf '%s' "$resp" | python3 -c "import json,sys;print(json.load(sys.stdin).get('localId',''))")
  fi
  if [ -z "$uid" ]; then
    echo "ERROR con $correo: $resp" >&2; exit 1
  fi
  printf '%s' "$uid"
}

echo "Resolviendo cuenta del ingestor ($FB_INGESTOR_EMAIL)…"
UID_ING=$(uid_de "$FB_INGESTOR_EMAIL" "$FB_INGESTOR_PASS")
echo "  UID = $UID_ING"

echo "Resolviendo cuenta del visor ($FB_VISOR_EMAIL)…"
UID_VIS=$(uid_de "$FB_VISOR_EMAIL" "$FB_VISOR_PASS")
echo "  UID = $UID_VIS"

sed -e "s/__UID_INGESTOR__/$UID_ING/g" -e "s/__UID_VISOR__/$UID_VIS/g" \
    database.rules.json > database.rules.generado.json
echo
echo "Escrito: firebase/database.rules.generado.json"
echo
echo "Siguiente paso, una de dos:"
echo "  a) firebase deploy --only database    (necesita firebase-tools y firebase login)"
echo "  b) pegar el contenido en Consola de Firebase -> Realtime Database -> Reglas -> Publicar"
