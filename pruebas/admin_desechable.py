#!/usr/bin/env python3
"""Credenciales desechables para la API de administracion de Node-RED (paso S2).
Python 3.9, sin dependencias.

Cada corrida de prueba que necesita la API de administracion genera aqui un
usuario y una contrasena aleatorios. El hash bcrypt (tools/hash_admin.js, la
misma biblioteca que el Node-RED instalado) solo vive en el entorno del
proceso de Node-RED de la prueba; nada se escribe en disco ni en el repo. La
contrasena de Ari nunca se usa ni se necesita.

    import admin_desechable as ad
    env, clave = ad.genera()                  # env -> ps.arranca(datos, **env)
    tok = ad.token(env["NODE_RED_ADMIN_USER"], clave)
    ad.pide("GET", "/flows", tok)

    eval "$(python3 pruebas/admin_desechable.py --shell)"   # para bash (prueba.sh)
"""
import http.client, json, os, pathlib, secrets, shlex, subprocess, sys, urllib.parse

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PUERTO_NR = int(os.environ.get("PUERTO", "1881"))
ENTORNO = {"PATH": "/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:" + os.environ.get("PATH", "")}


def genera():
    usuario = "prueba_" + secrets.token_hex(4)
    clave = secrets.token_urlsafe(24)
    h = subprocess.run(["node", str(RAIZ / "tools" / "hash_admin.js")], input=clave, capture_output=True,
                       text=True, check=True, env=dict(os.environ, **ENTORNO)).stdout.strip()
    return {"NODE_RED_ADMIN_USER": usuario, "NODE_RED_ADMIN_HASH": h}, clave


def pide(metodo, ruta, tok=None, cuerpo=None, formulario=None, puerto=None, cabeceras=None):
    c = http.client.HTTPConnection("127.0.0.1", puerto or PUERTO_NR, timeout=10)
    h = dict(cabeceras or {})
    datos = None
    if tok:
        h["Authorization"] = "Bearer " + tok
    if cuerpo is not None:
        datos = json.dumps(cuerpo).encode()
        h["Content-Type"] = "application/json"
    elif formulario is not None:
        datos = urllib.parse.urlencode(formulario).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    c.request(metodo, ruta, body=datos, headers=h)
    r = c.getresponse()
    texto = r.read().decode(errors="replace")
    c.close()
    return r.status, texto


def token(usuario, clave, puerto=None):
    """POST /auth/token (pagina 'Admin API: OAuth'). Regresa el token o None."""
    c, t = pide("POST", "/auth/token", formulario={"client_id": "node-red-admin", "grant_type": "password",
                                                   "scope": "*", "username": usuario, "password": clave},
                puerto=puerto)
    if c != 200:
        return None
    try:
        return json.loads(t).get("access_token")
    except ValueError:
        return None


if __name__ == "__main__":
    if sys.argv[1:] == ["--shell"]:
        env, clave = genera()
        for k, v in env.items():
            print("export %s=%s" % (k, shlex.quote(v)))
        print("ADMIN_CLAVE=%s" % shlex.quote(clave))
    else:
        sys.exit(__doc__)
