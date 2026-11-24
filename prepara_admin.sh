#!/bin/bash
# Usuario y contrasena del editor de Node-RED (paso S2 de la fase 3).
#
#   ./prepara_admin.sh            -> pide usuario y contrasena (dos veces, sin mostrarla),
#                                    calcula el hash bcrypt y escribe o reemplaza
#                                    NODE_RED_ADMIN_USER y NODE_RED_ADMIN_HASH en .env
#   ./prepara_admin.sh --revisa   -> solo dice si las dos variables existen y si el hash
#                                    tiene formato bcrypt; exit 0 si todo esta bien, 1 si no
#
# No imprime la contrasena ni el hash. La contrasena va por stdin a
# tools/hash_admin.js, que usa la misma biblioteca bcrypt que el Node-RED
# instalado. El hash se escribe entre comillas simples porque lleva '$' y
# arranca.sh carga .env con bash. ENV_ARCHIVO elige otro archivo (pruebas).
# Despues de cambiarlo hay que reiniciar Node-RED (./apaga.sh y ./arranca.sh).
set -uo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH"
ENV_ARCHIVO="${ENV_ARCHIVO:-.env}"

valor() { # nombre -> valor en $ENV_ARCHIVO, sin comillas
  /usr/bin/python3 - "$ENV_ARCHIVO" "$1" <<'PY'
import sys
ruta, nombre = sys.argv[1], sys.argv[2]
v = ""
try:
    for l in open(ruta, encoding="utf-8"):
        if l.startswith(nombre + "="):
            v = l.split("=", 1)[1].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
except FileNotFoundError:
    pass
sys.stdout.write(v)
PY
}

if [ "${1:-}" == "--revisa" ]; then
  [ -f "$ENV_ARCHIVO" ] || { echo "falta $ENV_ARCHIVO"; exit 1; }
  u=$(valor NODE_RED_ADMIN_USER); h=$(valor NODE_RED_ADMIN_HASH); mal=0
  if [ -n "$u" ]; then echo "  NODE_RED_ADMIN_USER   existe"; else echo "  NODE_RED_ADMIN_USER   FALTA"; mal=1; fi
  if [ -z "$h" ]; then echo "  NODE_RED_ADMIN_HASH   FALTA"; mal=1
  elif node tools/hash_admin.js --revisa "$h"; then echo "  NODE_RED_ADMIN_HASH   existe, formato bcrypt"
  else echo "  NODE_RED_ADMIN_HASH   existe, pero NO tiene formato bcrypt"; mal=1; fi
  if [ $mal -eq 0 ]; then echo "  editor: protegido con usuario y contrasena"; else echo "  editor: deshabilitado (Node-RED no sirve el editor ni la API de administracion)"; fi
  exit $mal
fi

[ -f "$ENV_ARCHIVO" ] || { echo "Falta $ENV_ARCHIVO. Copia .env.example a .env primero."; exit 1; }
[ -t 0 ] && echo "Usuario y contrasena del editor de Node-RED (se guardan en $ENV_ARCHIVO como hash bcrypt)."
read -r -p "Usuario: " USUARIO; [ -t 0 ] || echo
if ! [[ "$USUARIO" =~ ^[A-Za-z0-9._-]{1,64}$ ]]; then echo "Usuario invalido: letras, numeros, punto, guion y guion bajo (1 a 64)."; exit 1; fi
read -r -s -p "Contrasena: " C1; echo
read -r -s -p "Repite la contrasena: " C2; echo
if [ "$C1" != "$C2" ]; then unset C1 C2; echo "Las contrasenas no coinciden. No se cambio nada."; exit 1; fi
if [ ${#C1} -lt 12 ]; then unset C1 C2; echo "La contrasena debe tener al menos 12 caracteres. No se cambio nada."; exit 1; fi
HASH=$(printf '%s' "$C1" | node tools/hash_admin.js) || { unset C1 C2; echo "No se pudo calcular el hash."; exit 1; }
unset C1 C2
node tools/hash_admin.js --revisa "$HASH" || { unset HASH; echo "El hash no tiene formato bcrypt. No se cambio nada."; exit 1; }

# Reescritura atomica: el hash va por stdin, nunca por argumentos.
printf '%s\n%s\n' "$USUARIO" "$HASH" | /usr/bin/python3 -c '
import os, sys, tempfile
ruta = sys.argv[1]
usuario, h = sys.stdin.read().split("\n")[:2]
nuevas = {"NODE_RED_ADMIN_USER": usuario, "NODE_RED_ADMIN_HASH": "'"'"'" + h + "'"'"'"}
lineas = open(ruta, encoding="utf-8").read().splitlines()
puestas = set()
for i, l in enumerate(lineas):
    for k, v in nuevas.items():
        if l.startswith(k + "="):
            lineas[i] = k + "=" + v; puestas.add(k)
faltan = [k for k in nuevas if k not in puestas]
if faltan:
    lineas += ["", "# ---- Editor de Node-RED (adminAuth); lo escribe ./prepara_admin.sh ----"]
    lineas += [k + "=" + nuevas[k] for k in faltan]
d = os.path.dirname(os.path.abspath(ruta))
fd, tmp = tempfile.mkstemp(dir=d, prefix=".env.")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write("\n".join(lineas) + "\n")
st = os.stat(ruta)
os.chmod(tmp, st.st_mode & 0o777)
os.replace(tmp, ruta)
' "$ENV_ARCHIVO" || { unset HASH; echo "No se pudo escribir $ENV_ARCHIVO."; exit 1; }
unset HASH
echo "Listo: NODE_RED_ADMIN_USER y NODE_RED_ADMIN_HASH en $ENV_ARCHIVO."
echo "Reinicia Node-RED para que lo tome (./apaga.sh y ./arranca.sh, o ./demo_a2.sh --apaga y ./demo_a2.sh)."
echo "Comprueba con: ./prepara_admin.sh --revisa"
