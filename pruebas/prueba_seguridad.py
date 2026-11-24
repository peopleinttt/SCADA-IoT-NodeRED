#!/usr/bin/env python3
"""Seguridad del puerto 1881 (paso S de la fase 2 y paso S2 de la fase 3). Python 3.9.

    /usr/bin/python3 pruebas/prueba_seguridad.py              (~60 s)
    /usr/bin/python3 pruebas/prueba_seguridad.py --sin-capa3  (solo los middleware de Node-RED y del dashboard)

Parte 1, con credenciales desechables (admin_desechable.py; el hash solo vive en
el entorno del Node-RED de la prueba):
  - sin token, toda ruta de la API de administracion que entrega contenido o
    escribe se rechaza (401), y el websocket del editor no entrega eventos;
  - con contrasena equivocada no hay token; con la correcta si, y /flows da 200;
  - con las cabeceras del tunel (cf-connecting-ip, cf-ray) todo da 403 salvo
    POST /telemetria, igual que en el paso S.
Parte 2, sin NODE_RED_ADMIN_USER ni NODE_RED_ADMIN_HASH: la API de
administracion no se sirve (404), /dashboard/a2 da 200, POST /telemetria llega
a la ingesta y los flujos corren (A2-Planta en com ok contra el sustituto).
Parte 3: el repositorio y su historial desde el inicio de la fase 3 no traen
hashes bcrypt.
"""
import base64, json, os, pathlib, re, socket, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402
import prueba_planta as pp  # noqa: E402
import admin_desechable as ad  # noqa: E402

verifica = ps.verifica
TUNEL = {"cf-connecting-ip": "203.0.113.7", "cf-ray": "8d1f2e3a4b5c6d7e-HKG"}
COMMIT_INICIO_F3 = "b23428b"          # primer commit de la fase 3 (orden y parametros)
BCRYPT = re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}")


def pide(metodo, ruta, tunel, cuerpo=None, cabeceras=None, tok=None):
    h = dict(TUNEL if tunel else {})
    h.update(cabeceras or {})
    return ad.pide(metodo, ruta, tok, cuerpo=cuerpo, cabeceras=h)


# ---- websocket minimo (RFC 6455) -----------------------------------------------
class Ws:
    def __init__(self, s, resto):
        self.s, self.resto = s, resto

    def close(self):
        self.s.close()


def ws_abre(ruta, tunel=False):
    """Regresa (primera linea de la respuesta, socket abierto o None)."""
    s = socket.create_connection(("127.0.0.1", ps.PUERTO_NR), timeout=5)
    extra = "".join("%s: %s\r\n" % kv for kv in TUNEL.items()) if tunel else ""
    s.sendall(("GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n%s\r\n" % (ruta, extra)).encode())
    buf = b""
    try:
        while b"\r\n\r\n" not in buf:
            trozo = s.recv(1024)
            if not trozo:
                break
            buf += trozo
    except socket.timeout:
        pass
    primera = buf.decode(errors="replace").split("\r\n")[0] or "(sin respuesta)"
    if " 101 " not in primera + " ":
        s.close()
        return primera, None
    return primera, Ws(s, buf.split(b"\r\n\r\n", 1)[1])


def ws_envia(w, texto):
    s = w.s
    datos = texto.encode()
    mascara = os.urandom(4)
    n = len(datos)
    cab = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + n.to_bytes(2, "big"))
    s.sendall(cab + mascara + bytes(b ^ mascara[i % 4] for i, b in enumerate(datos)))


def ws_lee(w, segundos):
    """Marcos de texto recibidos en la ventana; 'CERRADO' si el servidor cerro."""
    s = w.s
    fin = time.time() + segundos
    buf, w.resto = w.resto, b""
    marcos = []
    while time.time() < fin:
        s.settimeout(max(0.05, fin - time.time()))
        try:
            trozo = s.recv(65536)
            if not trozo:
                marcos.append("CERRADO")
                break
            buf += trozo
        except socket.timeout:
            break
        except OSError:
            marcos.append("CERRADO")
            break
        while len(buf) >= 2:
            op, n, i = buf[0] & 0x0F, buf[1] & 0x7F, 2
            if n == 126:
                if len(buf) < 4:
                    break
                n, i = int.from_bytes(buf[2:4], "big"), 4
            elif n == 127:
                if len(buf) < 10:
                    break
                n, i = int.from_bytes(buf[2:10], "big"), 10
            if len(buf) < i + n:
                break
            carga, buf = buf[i:i + n], buf[i + n:]
            if op == 0x8:
                marcos.append("CERRADO")
                return marcos
            if op == 0x1:
                marcos.append(carga.decode(errors="replace"))
    return marcos


def provoca_eventos():
    """Cambios de estado de nodos (status/...) y del cliente mientras se escucha."""
    for v in (0.5, 0.0):
        pide("POST", "/a2/planta/comando", False, {"accion": "velocidad", "vel_V": v})
        time.sleep(0.3)


# ---- parte 1: editor protegido con credenciales desechables -----------------------
def parte_protegida(datos, extra):
    env_adm, clave = ad.genera()
    usuario = env_adm["NODE_RED_ADMIN_USER"]
    ps.arranca(datos, A2_PLANTA_CONFIG=RAIZ / "config" / "planta_a2.json", INGEST_KEY="clave-de-prueba",
               **env_adm, **extra)
    pp.espera(lambda: pp.estado()["com"] == "ok", 30)
    c, t = pide("GET", "/auth/login", False)
    verifica("GET /auth/login anuncia el esquema credentials (sin revelar usuarios)",
             c == 200 and '"credentials"' in t and usuario not in t, (c, t[:80]))

    print("--- 1. Sin token, la API de administracion no entrega contenido ni acepta escrituras ---")
    rutas = [
        ("GET", "/flows", None), ("GET", "/flows/state", None), ("GET", "/flow/a2_planta", None),
        ("GET", "/nodes", None), ("GET", "/nodes/messages", None), ("GET", "/nodes/node-red", None),
        ("GET", "/context/global", None), ("GET", "/context/flow/a2_planta", None),
        ("GET", "/context/node/inj_diag", None), ("GET", "/settings", None), ("GET", "/settings/user", None),
        ("GET", "/diagnostics", None), ("GET", "/plugins", None), ("GET", "/plugins/messages", None),
        ("GET", "/icons", None), ("GET", "/library/local/flows", None), ("GET", "/credentials/inject/inj_diag", None),
        ("POST", "/flows", []), ("POST", "/flow", {"id": "x", "label": "x", "nodes": []}),
        ("PUT", "/flow/a2_planta", {"id": "a2_planta", "label": "x", "nodes": []}), ("DELETE", "/flow/a2_planta", None),
        ("POST", "/nodes", {"module": "x"}),
        ("DELETE", "/context/global/x", None), ("POST", "/inject/inj_diag", None), ("POST", "/debug/dbg_ing/enable", None),
        ("POST", "/settings/user", {"x": 1}), ("POST", "/library/local/flows/x", {"x": 1}),
    ]
    malos = []
    for m, ruta, cuerpo in rutas:
        c, t = pide(m, ruta, False, cuerpo)
        if c != 401:
            malos.append((m, ruta, c, t[:60]))
    verifica("%d rutas de la API de administracion sin token -> 401 (leer y escribir flujos, contexto, nodos, "
             "settings, diagnostics, plugins, inject...)" % len(rutas), not malos, malos)
    # POST /flows/state solo existe con runtimeState.enabled (apagado en settings.js): no se sirve.
    c, t = pide("POST", "/flows/state", False, {"state": "stop"})
    verifica("POST /flows/state (runtimeState apagado) no existe: 404", c == 404, (c, t[:40]))
    c, t = pide("GET", "/flows", False, tok="token-inventado")
    verifica("GET /flows con un token inventado -> 401", c == 401, (c, t[:60]))
    c_g, _ = pide("GET", "/a2/planta/estado", False)
    verifica("los flujos siguen corriendo: el estado de A2-Planta no cambio por los intentos (com ok)",
             c_g == 200 and pp.estado()["com"] == "ok")

    print("--- 2. Websocket del editor (/comms) sin autenticarse ---")
    primera, w = ws_abre("/comms")
    if w is None:
        verifica("el websocket del editor no entrega eventos sin autenticarse (no abre: %s)" % primera, True)
    else:
        ws_envia(w, json.dumps({"subscribe": "status/#"}))
        ws_envia(w, json.dumps({"subscribe": "debug"}))
        ws_envia(w, json.dumps({"subscribe": "notification/#"}))
        provoca_eventos()
        marcos = ws_lee(w, 4)
        w.close()
        eventos = [m for m in marcos if m not in ("CERRADO",) and '"auth"' not in m]
        verifica("sin autenticarse, /comms no entrega eventos en 4 s con cambios de estado provocados "
                 "(%d marcos: %s)" % (len(marcos), [m[:40] for m in marcos][:3]), not eventos, eventos[:3])
        primera2, w2 = ws_abre("/comms")
        if w2 is not None:
            ws_envia(w2, json.dumps({"auth": "token-inventado"}))
            ws_envia(w2, json.dumps({"subscribe": "status/#"}))
            provoca_eventos()
            marcos2 = ws_lee(w2, 3)
            w2.close()
            ev2 = [m for m in marcos2 if m != "CERRADO" and '"auth"' not in m]
            verifica("con un token inventado: auth fail y ningun evento (%s)" % [m[:30] for m in marcos2][:2],
                     any('"fail"' in m for m in marcos2) and not ev2, marcos2[:3])

    print("--- 3. Token: contrasena equivocada y correcta ---")
    verifica("con contrasena equivocada no se obtiene token", ad.token(usuario, clave + "x") is None)
    verifica("con un usuario que no existe no se obtiene token", ad.token("otro_" + usuario, clave) is None)
    tok = ad.token(usuario, clave)
    verifica("con la contrasena correcta se obtiene token", bool(tok))
    c, t = pide("GET", "/flows", False, tok=tok)
    try:
        flujos = json.loads(t)
        flujos = flujos.get("flows", []) if isinstance(flujos, dict) else flujos
        n_tabs = sum(1 for n in flujos if n.get("type") == "tab")
    except (ValueError, AttributeError):
        n_tabs = -1
    verifica("con ese token GET /flows -> 200 (%d pestanas)" % n_tabs, c == 200 and n_tabs >= 7, (c, t[:60]))
    # Control del punto 2: el mismo websocket SI entrega eventos autenticado.
    primera, w = ws_abre("/comms")
    if w is not None:
        ws_envia(w, json.dumps({"auth": tok}))
        ws_envia(w, json.dumps({"subscribe": "status/#"}))
        ws_envia(w, json.dumps({"subscribe": "notification/#"}))
        provoca_eventos()
        marcos = ws_lee(w, 4)
        w.close()
        ev = [m for m in marcos if m != "CERRADO" and '"auth"' not in m]
        verifica("control: autenticado, /comms dice auth ok y SI entrega eventos (%d)" % len(ev),
                 any('"ok"' in m for m in marcos) and len(ev) > 0, [m[:50] for m in marcos][:3])
    c, t = ad.pide("POST", "/auth/revoke", tok, formulario={"token": tok})
    c2, _ = pide("GET", "/flows", False, tok=tok)
    verifica("POST /auth/revoke invalida el token: /flows vuelve a 401", c == 200 and c2 == 401, (c, c2))
    return usuario, clave


def casos_tunel(sin_capa3, protegido):
    print("--- 4. Cabeceras del tunel (como en el paso S): todo 403 salvo la ingesta ---")
    adm = 401 if protegido else 404
    casos = [
        ("editor  GET /", "GET", "/", None, 200 if protegido else 404),
        ("admin   GET /flows", "GET", "/flows", None, adm),
        ("admin   GET /settings", "GET", "/settings", None, adm),
        ("admin   GET /auth/login", "GET", "/auth/login", None, 200 if protegido else 404),
        ("A2      GET /a2/planta/estado", "GET", "/a2/planta/estado", None, 200),
        ("A2      POST /a2/planta/comando", "POST", "/a2/planta/comando", {"accion": "velocidad", "vel_V": 0}, 200),
        ("A1      GET /telemetria (solo POST pasa)", "GET", "/telemetria", None, 404),
    ]
    # Sin capa 3 y sin API de administracion no hay middleware de admin que
    # conteste 403: una ruta que no existe da 404 tambien por el tunel. No se
    # sirve nada; con la configuracion real (capa 3) es 403.
    inexistente_ok = (403, 404) if (sin_capa3 and not protegido) else (403,)
    for desc, m, ruta, cuerpo, sin in casos:
        c_sin, _ = pide(m, ruta, False, cuerpo)
        c_con, t = pide(m, ruta, True, cuerpo)
        esperado_con = inexistente_ok if sin == 404 else (403,)
        verifica("%-42s sin tunel %d (esperado %d), por tunel %d" % (desc, c_sin, sin, c_con),
                 c_sin == sin and c_con in esperado_con and (c_con == 404 or "origen_no_permitido" in t),
                 (c_sin, c_con, t[:80]))
    c_con, t = ad.pide("POST", "/auth/token", None, formulario={"client_id": "node-red-admin", "grant_type": "password",
                                                                "scope": "*", "username": "x", "password": "y"},
                       cabeceras=TUNEL)
    verifica("admin   POST /auth/token por tunel -> %d" % c_con, c_con in (inexistente_ok if not protegido else (403,)),
             (c_con, t[:60]))

    # La ingesta de Wokwi: por el tunel tiene que llegar a la validacion, que
    # rechaza la clave equivocada con su propio 401 (no el 403 del filtro).
    for tunel in (False, True):
        c, t = pide("POST", "/telemetria", tunel, {"ts_origen": "x"}, {"X-Ingest-Key": "mala"})
        verifica("A1      POST /telemetria %-14s -> 401 clave_invalida de la ingesta" % ("por tunel" if tunel else "sin tunel"),
                 c == 401 and "clave_invalida" in t, (c, t[:80]))
    c, t = pide("POST", "/telemetria?x=1", True, {"ts_origen": "x"}, {"X-Ingest-Key": "mala"})
    verifica("A1      POST /telemetria?x=1 por tunel tambien llega a la ingesta", c == 401, (c, t[:60]))

    c_sin, _ = pide("GET", "/dashboard", False)
    c_con, _ = pide("GET", "/dashboard", True)
    # /dashboard redirige (301) a la pagina; la pagina es /dashboard/a2.
    verifica("dash    GET /dashboard              sin tunel %d (redirige), por tunel 403" % c_sin,
             c_sin in (200, 301, 302) and c_con == 403, (c_sin, c_con))
    p_sin, _ = pide("GET", "/dashboard/a2", False)
    p_con, _ = pide("GET", "/dashboard/a2", True)
    verifica("dash    GET /dashboard/a2 (HMI)     sin tunel %d, por tunel 403" % p_sin,
             p_sin == 200 and p_con == 403, (p_sin, p_con))
    c_sin, t_sin = pide("GET", "/dashboard/socket.io/?EIO=4&transport=polling", False)
    c_con, _ = pide("GET", "/dashboard/socket.io/?EIO=4&transport=polling", True)
    if sin_capa3:
        # Solo con ioMiddleware el saludo HTTP de engine.io contesta 200;
        # el middleware corta la conexion despues. Por eso existe la capa 3.
        print("  --    socket.io sin capa 3: polling por tunel contesta %d (ioMiddleware corta despues)" % c_con)
    else:
        verifica("dash    socket.io polling          sin tunel %d con sid, por tunel 403" % c_sin,
                 c_sin == 200 and '"sid"' in t_sin and c_con == 403, (c_sin, t_sin[:60], c_con))
        w_con, _ = ws_abre("/dashboard/socket.io/?EIO=4&transport=websocket", True)
        verifica("dash    socket.io websocket por tunel -> 403", "403" in w_con, w_con)
    w_con, s1 = ws_abre("/comms", True)
    w_sin, s2 = ws_abre("/comms", False)
    for s in (s1, s2):
        if s is not None:
            s.close()
    if not protegido:
        verifica("editor  websocket /comms sin API de administracion: sin tunel no abre (%s), por tunel no abre (%s)"
                 % (w_sin, w_con), "101" not in w_sin and "101" not in w_con, (w_sin, w_con))
    elif sin_capa3:
        verifica("editor  websocket /comms: sin capa 3 el tunel SI llega (101), lo que la capa 3 cierra",
                 "101" in w_sin and "101" in w_con, (w_sin, w_con))
    else:
        verifica("editor  websocket /comms           sin tunel 101 (y pide auth), por tunel 403",
                 "101" in w_sin and "403" in w_con, (w_sin, w_con))


# ---- parte 2: sin credenciales ---------------------------------------------------------
def parte_sin_credenciales(datos, extra):
    ps.arranca(datos, A2_PLANTA_CONFIG=RAIZ / "config" / "planta_a2.json", INGEST_KEY="clave-de-prueba", **extra)
    corre = pp.espera(lambda: pp.estado()["com"] == "ok", 30)
    log = (datos / "nodered.log").read_text(encoding="utf-8", errors="replace")
    verifica("el registro de Node-RED dice que el editor y la API quedan deshabilitados y por que",
             "Admin UI disabled" in log and "DESHABILITADOS (falta NODE_RED_ADMIN_USER y NODE_RED_ADMIN_HASH)" in log)
    print("--- 5. Sin NODE_RED_ADMIN_USER ni NODE_RED_ADMIN_HASH ---")
    rutas = [("GET", "/"), ("GET", "/flows"), ("GET", "/settings"), ("GET", "/context/global"), ("GET", "/nodes"),
             ("GET", "/auth/login"), ("POST", "/auth/token"), ("POST", "/flows"), ("POST", "/inject/inj_diag"),
             ("GET", "/diagnostics"), ("GET", "/red/red.min.js")]
    res = [(m, r, pide(m, r, False, [] if m == "POST" else None)[0]) for m, r in rutas]
    verifica("la API de administracion y el editor no se sirven: %d rutas -> 404" % len(rutas),
             all(c == 404 for _, _, c in res), [x for x in res if x[2] != 404])
    c, _ = pide("GET", "/dashboard/a2", False)
    verifica("GET /dashboard/a2 -> 200", c == 200, c)
    c, t = pide("POST", "/telemetria", False, {"ts_origen": "x"}, {"X-Ingest-Key": "mala"})
    verifica("POST /telemetria llega a la ingesta (401 clave_invalida de su validacion)",
             c == 401 and "clave_invalida" in t, (c, t[:60]))
    c, t = pide("POST", "/telemetria", False, {"ts_origen": "x"}, {"X-Ingest-Key": "clave-de-prueba"})
    verifica("con la clave correcta la ingesta valida el cuerpo (400, no 404)", c == 400, (c, t[:60]))
    verifica("los flujos corren: A2-Planta en com ok contra el sustituto", corre and pp.estado()["com"] == "ok")
    c, r = pp.comando(accion="velocidad", vel_V=0)
    verifica("POST /a2/planta/comando responde (%d)" % c, c == 200, (c, r))


def parte_repo():
    print("--- 6. Ningun hash bcrypt ni contrasena en el repositorio ni en el historial de la fase 3 ---")
    archivos = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=str(RAIZ),
                              capture_output=True, text=True).stdout.split("\n")
    con = []
    for a in archivos:
        p = RAIZ / a
        if a and p.is_file() and p.stat().st_size < 5_000_000 and p.suffix not in (".pdf", ".docx", ".png", ".jpg"):
            if BCRYPT.search(p.read_text(encoding="utf-8", errors="replace")):
                con.append(a)
    verifica("arbol de trabajo (%d archivos versionados o por versionar): sin hashes bcrypt" % len(archivos), not con, con)
    hist = subprocess.run(["git", "log", "-p", "%s^..HEAD" % COMMIT_INICIO_F3], cwd=str(RAIZ),
                          capture_output=True, text=True).stdout
    verifica("historial desde %s (fase 3): sin hashes bcrypt" % COMMIT_INICIO_F3, not BCRYPT.search(hist))
    sospechosas = re.findall(r"^\+.*NODE_RED_ADMIN_(?:HASH|PASS\w*)=['\"]?[^'\"\s]+", hist, re.M)
    verifica("historial: ninguna asignacion con valor de NODE_RED_ADMIN_HASH", not sospechosas, sospechosas[:3])


def main(sin_capa3):
    extra = {"A2_FILTRO_SERVIDOR": "0"} if sin_capa3 else {}
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_seguridad_"))
    print("=== Parte 1: editor protegido con credenciales desechables%s (datos en %s) ==="
          % (", SIN el filtro del servidor" if sin_capa3 else "", datos))
    parte_protegida(datos, extra)
    casos_tunel(sin_capa3, True)
    datos2 = pathlib.Path(tempfile.mkdtemp(prefix="a2_seguridad_sin_"))
    print("=== Parte 2: sin credenciales (datos en %s) ===" % datos2)
    parte_sin_credenciales(datos2, extra)
    casos_tunel(sin_capa3, False)
    print("=== Parte 3: repositorio ===")
    parte_repo()


if __name__ == "__main__":
    try:
        main("--sin-capa3" in sys.argv)
    finally:
        ps.detiene()
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
