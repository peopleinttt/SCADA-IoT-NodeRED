#!/bin/bash
# Instala las paletas de la Actividad 2 en los dos userDir de Node-RED que
# usa este repo. Los dos estan fuera de git, asi que esto es lo que los
# reconstruye en una maquina nueva. Es idempotente: correrlo otra vez deja
# las mismas versiones.
#
#   ./prepara_a2.sh            -> instala en los dos userDir
#   ./prepara_a2.sh --revisa   -> solo dice que version hay en cada uno
#
# Los dos destinos:
#   node-red/runtime                          el de ./arranca.sh
#   ${TMPDIR:-/tmp}/actividad1-pruebas/userdir el de pruebas/prueba.sh
# El segundo se calcula igual que en prueba.sh. Si el sistema limpia el
# directorio temporal (al reiniciar, por ejemplo), hay que volver a correr esto.
set -euo pipefail
cd "$(dirname "$0")"
RAIZ="$PWD"

# Versiones fijas: "la ultima" cambia sola y una prueba que paso ayer puede
# fallar manana sin que nadie haya tocado el repo.
PAQUETES=(
  "node-red-contrib-modbus@5.62.0"
  "@flowfuse/node-red-dashboard@1.34.0"
)

DESTINOS=(
  "$RAIZ/node-red/runtime"
  "${TMPDIR:-/tmp}/actividad1-pruebas/userdir"
)

command -v npm >/dev/null || { echo "Falta npm en el PATH (node@22 de Homebrew)"; exit 1; }

revisa() { # userDir -> imprime la version instalada de cada paquete
  local dir="$1" p nombre version
  for p in "${PAQUETES[@]}"; do
    nombre="${p%@*}"
    version=$(node -e 'try{console.log(require(process.argv[1]).version)}catch(e){console.log("FALTA")}' \
              "$dir/node_modules/$nombre/package.json")
    printf '    %-32s %s (esperada %s)\n' "$nombre" "$version" "${p##*@}"
    [ "$version" == "${p##*@}" ] || return 1
  done
}

fallo=0
for dir in "${DESTINOS[@]}"; do
  echo "  $dir"
  if [ "${1:-}" != "--revisa" ]; then
    mkdir -p "$dir"
    # Node-RED crea este package.json en su primer arranque; si aun no existe,
    # se crea igual para que npm instale aqui y no suba a buscar otro.
    [ -f "$dir/package.json" ] || \
      printf '{\n  "name": "node-red-project",\n  "description": "userDir de Node-RED",\n  "version": "0.0.1",\n  "private": true\n}\n' > "$dir/package.json"
    npm install --prefix "$dir" --save --save-exact --no-fund --no-audit --loglevel=error "${PAQUETES[@]}"
  fi
  revisa "$dir" || fallo=1
done

if [ $fallo -ne 0 ]; then
  echo "  FALTA alguna paleta o no es la version esperada"; exit 1
fi
echo "  listo: paletas de la Actividad 2 en los dos userDir"
