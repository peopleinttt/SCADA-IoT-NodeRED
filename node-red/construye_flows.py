#!/usr/bin/env python3
"""Ensambla flows.json a partir de los .js de funciones/.

Se mantiene el codigo de los nodos de funcion en archivos aparte para poder
leerlo, versionarlo y citarlo en el reporte sin pelear con el escapado de JSON.
Uso:  python3 construye_flows.py   ->  reescribe flows.json
"""
import json, pathlib, sys

RAIZ = pathlib.Path(__file__).parent
FUN = RAIZ / "funciones"

def js(nombre):
    ruta = FUN / nombre
    if not ruta.exists():
        sys.exit(f"falta {ruta}")
    return ruta.read_text(encoding="utf-8").rstrip() + "\n"

TAB_ING, TAB_DIAG = "a1_ingesta", "a1_diagnostico"

def fn(id_, nombre, archivo, x, y, z, wires, outputs=1):
    return {"id": id_, "type": "function", "z": z, "name": nombre,
            "func": js(archivo), "outputs": outputs, "timeout": 0,
            "noerr": 0, "initialize": "", "finalize": "", "libs": [],
            "x": x, "y": y, "wires": wires}

def http_req(id_, nombre, metodo, ret, x, y, z, wires):
    return {"id": id_, "type": "http request", "z": z, "name": nombre,
            "method": metodo, "ret": ret, "paytoqs": "ignore", "url": "",
            "tls": "", "persist": False, "proxy": "", "insecureHTTPParser": False,
            "authType": "", "senderr": False, "headers": [],
            "x": x, "y": y, "wires": wires}

def archivo(id_, nombre, x, y, z):
    return {"id": id_, "type": "file", "z": z, "name": nombre,
            "filename": "filename", "filenameType": "msg", "appendNewline": True,
            "createDir": True, "overwriteFile": "false", "encoding": "none",
            "x": x, "y": y, "wires": [[]]}

def dbg(id_, nombre, x, y, z, prop="payload"):
    return {"id": id_, "type": "debug", "z": z, "name": nombre, "active": True,
            "tosidebar": True, "console": False, "tostatus": False,
            "complete": prop, "targetType": "msg", "statusVal": "",
            "statusType": "auto", "x": x, "y": y, "wires": []}

def comentario(id_, nombre, info, x, y, z):
    return {"id": id_, "type": "comment", "z": z, "name": nombre, "info": info,
            "x": x, "y": y, "wires": []}

flows = []

# ===========================================================================
# Pestana 1 — ingesta
# ===========================================================================
flows.append({"id": TAB_ING, "type": "tab", "label": "A1 · Ingesta", "disabled": False,
              "info": (
"# Cadena de ingesta\n\n"
"`ESP32 (Wokwi) -> http in -> validacion -> HTTP Request POST -> Firebase RTDB`\n\n"
"El POST se hace contra `.../telemetria.json` para que Firebase genere un\n"
"`registroId` nuevo por evento (push). PATCH o PUT sobrescribirian.\n\n"
"Variables de entorno necesarias: `FIREBASE_DB_URL`, `PLANTA_ID`, `INGEST_KEY`,\n"
"`DATOS_DIR` y, para el login automatico, `FIREBASE_API_KEY`,\n"
"`FB_INGESTOR_EMAIL`, `FB_INGESTOR_PASS`.\n"), "env": []})

flows.append(comentario("c_ing", "1 · Telemetria del ESP32",
    "POST http://<host>:1880/telemetria con el JSON del emisor.", 120, 60, TAB_ING))

flows.append({"id": "http_in_tel", "type": "http in", "z": TAB_ING, "name": "POST /telemetria",
              "url": "/telemetria", "method": "post", "upload": False,
              "skipBodyParsing": False, "swaggerDoc": "",
              "x": 150, "y": 120, "wires": [["fn_valida"]]})

flows.append(fn("fn_valida", "valida y sella ts_escritura", "01_valida_telemetria.js",
                400, 120, TAB_ING, [["fn_prepara"], ["http_resp"]], outputs=2))

flows.append(fn("fn_prepara", "arma POST a Firebase", "02_prepara_escritura.js",
                660, 100, TAB_ING, [["http_fb_write"], ["http_resp"]], outputs=2))

flows.append(http_req("http_fb_write", "POST telemetria.json", "POST", "obj",
                      900, 100, TAB_ING, [["fn_resp_fb"]]))

flows.append(fn("fn_resp_fb", "interpreta respuesta", "03_respuesta_firebase.js",
                1120, 100, TAB_ING,
                [["fn_csv", "dbg_ing"], ["http_resp"], ["fn_login_prep"]], outputs=3))

flows.append({"id": "http_resp", "type": "http response", "z": TAB_ING,
              "name": "respuesta al ESP32", "statusCode": "", "headers": {},
              "x": 1360, "y": 180, "wires": []})

flows.append(fn("fn_csv", "instrumentacion CSV", "04_instrumentacion_csv.js",
                1340, 40, TAB_ING, [["file_csv"]]))
flows.append(archivo("file_csv", "ingesta_AAAA-MM-DD.csv", 1580, 40, TAB_ING))
flows.append(dbg("dbg_ing", "registro escrito", 1360, 100, TAB_ING, "registro"))

# --- credencial de servicio ------------------------------------------------
flows.append(comentario("c_login", "2 · Sesion del ingestor (idToken, 1 h)",
    "Renueva cada 45 min y tambien cuando Firebase contesta 401.",
    120, 300, TAB_ING))

flows.append({"id": "inj_login", "type": "inject", "z": TAB_ING, "name": "cada 45 min",
              "props": [{"p": "payload"}], "repeat": "2700", "crontab": "",
              "once": True, "onceDelay": "1", "topic": "", "payload": "",
              "payloadType": "date", "x": 160, "y": 360, "wires": [["fn_login_prep"]]})

flows.append(fn("fn_login_prep", "arma login", "05_login_firebase.js",
                380, 360, TAB_ING, [["http_login"]]))

flows.append(http_req("http_login", "signInWithPassword", "POST", "obj",
                      620, 360, TAB_ING, [["fn_login_store"]]))

flows.append(fn("fn_login_store", "guarda idToken", "06_guarda_token.js",
                860, 360, TAB_ING, [["dbg_login"], ["dbg_login_err"]], outputs=2))

flows.append(dbg("dbg_login", "sesion lista", 1080, 320, TAB_ING))
flows.append(dbg("dbg_login_err", "login fallido", 1080, 400, TAB_ING))

# --- errores no atrapados --------------------------------------------------
flows.append({"id": "catch_ing", "type": "catch", "z": TAB_ING,
              "name": "fallos de transporte", "scope": None, "uncaught": True,
              "x": 170, "y": 460, "wires": [["fn_err_ing"]]})
flows.append(fn("fn_err_ing", "bitacora de errores", "15_errores.js",
                420, 460, TAB_ING, [["file_err_ing", "dbg_err_ing"]]))
flows.append(archivo("file_err_ing", "errores.log", 660, 460, TAB_ING))
flows.append(dbg("dbg_err_ing", "error", 660, 520, TAB_ING))

# ===========================================================================
# Pestana 2 — diagnostico con Gemini
# ===========================================================================
flows.append({"id": TAB_DIAG, "type": "tab", "label": "A1 · Diagnostico (Gemini)",
              "disabled": False, "info": (
"# Capa de diagnostico\n\n"
"`inject -> limitador -> GET telemetria (limitToLast) -> prompt -> Gemini ->`\n"
"`JSON.parse -> POST diagnosticos.json`\n\n"
"Tres frenos de consumo: limitador de tasa (1/min), tope diario\n"
"(`DIAG_MAX_DIA`) y omision cuando el estado no cambio\n"
"(`DIAG_MIN_REPETIR_MIN`). El prompt se recorta a `DIAG_MAX_CARACTERES`.\n"), "env": []})

flows.append(comentario("c_diag", "3 · Diagnostico periodico",
    "El periodo real es el del inject; el limitador es el techo duro.",
    120, 60, TAB_DIAG))

# Cada 30 min, no cada 5: con 20 peticiones diarias en el nivel gratuito,
# un diagnostico cada 5 minutos agota la cuota en menos de dos horas.
# Para la grabacion se dispara a mano con el boton del nodo.
flows.append({"id": "inj_diag", "type": "inject", "z": TAB_DIAG, "name": "cada 30 min",
              "props": [{"p": "payload"}], "repeat": "1800", "crontab": "",
              "once": True, "onceDelay": "20", "topic": "", "payload": "",
              "payloadType": "date", "x": 150, "y": 120, "wires": [["delay_rate"]]})

flows.append({"id": "delay_rate", "type": "delay", "z": TAB_DIAG,
              "name": "maximo 1 por minuto", "pauseType": "rate", "timeout": "5",
              "timeoutUnits": "seconds", "rate": "1", "nbRateUnits": "1",
              "rateUnits": "minute", "randomFirst": "1", "randomLast": "5",
              "randomUnits": "seconds", "drop": True, "allowrate": False,
              "outputs": 1, "x": 370, "y": 120, "wires": [["fn_lee"]]})

flows.append(fn("fn_lee", "arma GET acotado", "10_lee_telemetria.js",
                590, 120, TAB_DIAG, [["http_fb_read"]]))

flows.append(http_req("http_fb_read", "GET telemetria.json", "GET", "obj",
                      800, 120, TAB_DIAG, [["fn_prompt"]]))

flows.append(fn("fn_prompt", "resume estado y arma prompt", "11_arma_prompt.js",
                1030, 120, TAB_DIAG, [["http_gemini"], ["dbg_omitido"]], outputs=2))

flows.append(dbg("dbg_omitido", "consulta omitida", 1280, 200, TAB_DIAG))

flows.append(http_req("http_gemini", "POST generateContent", "POST", "txt",
                      1270, 100, TAB_DIAG, [["fn_parse"]]))

flows.append(fn("fn_parse", "JSON.parse de la respuesta", "12_parsea_gemini.js",
                1490, 100, TAB_DIAG, [["fn_diag_prep"], ["dbg_err_gemini"]], outputs=2))

flows.append(dbg("dbg_err_gemini", "fallo de Gemini", 1730, 180, TAB_DIAG))

flows.append(fn("fn_diag_prep", "arma POST del diagnostico", "13_escribe_diagnostico.js",
                1730, 60, TAB_DIAG, [["http_fb_diag"]]))

flows.append(http_req("http_fb_diag", "POST diagnosticos.json", "POST", "obj",
                      1960, 60, TAB_DIAG, [["fn_cierra"]]))

flows.append(fn("fn_cierra", "cierra y mide", "14_cierra_diagnostico.js",
                2180, 60, TAB_DIAG, [["file_diag", "dbg_diag"]]))

flows.append(archivo("file_diag", "diagnosticos_AAAA-MM-DD.csv", 2400, 20, TAB_DIAG))
flows.append(dbg("dbg_diag", "diagnostico guardado", 2400, 100, TAB_DIAG, "registro_diag"))

flows.append({"id": "catch_diag", "type": "catch", "z": TAB_DIAG,
              "name": "fallos de transporte", "scope": None, "uncaught": True,
              "x": 170, "y": 300, "wires": [["fn_err_diag"]]})
flows.append(fn("fn_err_diag", "bitacora de errores", "15_errores.js",
                420, 300, TAB_DIAG, [["file_err_diag", "dbg_err_diag"]]))
flows.append(archivo("file_err_diag", "errores.log", 660, 300, TAB_DIAG))
flows.append(dbg("dbg_err_diag", "error", 660, 360, TAB_DIAG))

# ===========================================================================
# Pestana A2 — planta sustituta (Modbus-Server + emulador de la estacion)
# ===========================================================================
# Los buffers del Modbus-Server salen de los limites del driver que declara el
# mapa: asi el sustituto contesta igual que Factory I/O cuando un cliente lee
# fuera de rango. El nodo mide su buffer en unidades de 8 bytes: un bit por
# bobina o entrada discreta, dos bytes por registro.
MAPA = json.loads((RAIZ.parent / "config" / "mapa_registros_a2.json").read_text(encoding="utf-8"))
LIM = MAPA["driver"]["limites"]
def bloques8(nbytes):
    return -(-nbytes // 8)

TAB_SUST = "a2_sustituto"
SUST_DT_S = "0.1"     # paso fijo de la simulacion = periodo del inject del tick

flows.append({"id": TAB_SUST, "type": "tab", "label": "A2 · Sustituto (planta simulada)",
              "disabled": False, "info": (
"# Planta sustituta\n\n"
"Sirve el mismo mapa de registros que Factory I/O (`config/mapa_registros_a2.json`)\n"
"desde un nodo Modbus-Server y emula la estacion: emision de cajas con masa\n"
"aleatoria de semilla fija, avance segun `vel_banda_V`, sensores en el orden\n"
"entrada, bascula y salida, peso mientras la caja esta en la bascula y\n"
"empujador con sus limites. Geometria y constantes en `config/sustituto_a2.json`.\n\n"
"Variables: `A2_MAPA`, `A2_SUST_CONFIG` (rutas, las fija arranca.sh),\n"
"`A2_SUSTITUTO` (0 lo apaga: el servidor queda en un puerto efimero y el\n"
"emulador no avanza), `A2_SUST_PUERTO` (5020), `A2_SUST_HOST` (127.0.0.1),\n"
"`A2_SUST_SEMILLA` (sobrescribe la del archivo).\n"),
              # Valores por omision: JSONata evaluado al desplegar. Los nombres
              # son distintos a los del proceso para no buscarse a si mismos.
              "env": [
                  {"name": "SUST_ACTIVO", "type": "jsonata",
                   "value": "$env(\"A2_SUSTITUTO\") = \"0\" ? false : true"},
                  {"name": "SUST_PUERTO", "type": "jsonata",
                   "value": "$env(\"A2_SUSTITUTO\") = \"0\" ? \"0\" : "
                            "($env(\"A2_SUST_PUERTO\") ? $env(\"A2_SUST_PUERTO\") : \"5020\")"},
                  {"name": "SUST_HOST", "type": "jsonata",
                   "value": "$env(\"A2_SUST_HOST\") ? $env(\"A2_SUST_HOST\") : \"127.0.0.1\""},
                  {"name": "SUST_DT_S", "type": "str", "value": SUST_DT_S},
              ]})

flows.append(comentario("c_sust", "A2 · Planta sustituta en Modbus TCP",
    "Cliente -> 127.0.0.1:5020 con el mismo mapa que Factory I/O.", 140, 40, TAB_SUST))

# --- arranque: mapa y configuracion ------------------------------------------
flows.append({"id": "inj_sust_carga", "type": "inject", "z": TAB_SUST, "name": "al arrancar",
              "props": [{"p": "payload"}], "repeat": "", "crontab": "",
              "once": True, "onceDelay": "0.5", "topic": "", "payload": "",
              "payloadType": "date", "x": 140, "y": 100, "wires": [["fn_sust_rutas"]]})
flows.append(fn("fn_sust_rutas", "revisa rutas", "20_sust_rutas.js",
                320, 100, TAB_SUST, [["file_in_mapa"]]))

def archivo_entrada(id_, nombre, variable, x, y, z, wires):
    return {"id": id_, "type": "file in", "z": z, "name": nombre,
            "filename": variable, "filenameType": "env", "format": "utf8",
            "chunk": False, "sendError": False, "encoding": "utf8", "allProps": False,
            "x": x, "y": y, "wires": wires}

flows.append(archivo_entrada("file_in_mapa", "lee A2_MAPA", "A2_MAPA",
                             500, 100, TAB_SUST, [["fn_sust_mapa"]]))
flows.append(fn("fn_sust_mapa", "carga mapa", "21_carga_mapa.js",
                680, 100, TAB_SUST, [["file_in_sust_cfg"]]))
flows.append(archivo_entrada("file_in_sust_cfg", "lee A2_SUST_CONFIG", "A2_SUST_CONFIG",
                             880, 100, TAB_SUST, [["fn_sust_cfg"]]))
flows.append(fn("fn_sust_cfg", "carga configuracion e inicia", "22_sust_config.js",
                1100, 100, TAB_SUST, [["dbg_sust_cfg"]]))
flows.append(dbg("dbg_sust_cfg", "sustituto listo", 1320, 100, TAB_SUST))

# --- ciclo de simulacion ------------------------------------------------------
flows.append({"id": "inj_sust_tick", "type": "inject", "z": TAB_SUST, "name": f"tick {SUST_DT_S} s",
              "props": [{"p": "payload"}], "repeat": SUST_DT_S, "crontab": "",
              "once": True, "onceDelay": "1", "topic": "", "payload": "",
              "payloadType": "date", "x": 140, "y": 200, "wires": [["fn_sust_pide"]]})
flows.append(fn("fn_sust_pide", "pide memoria", "23_sust_pide_memoria.js",
                320, 200, TAB_SUST, [["mb_sust_server"]]))
flows.append({"id": "mb_sust_server", "type": "modbus-server", "z": TAB_SUST,
              "name": "Modbus-Server (mismo mapa que Factory I/O)", "logEnabled": False,
              "hostname": "${SUST_HOST}", "serverPort": "${SUST_PUERTO}",
              "responseDelay": 1, "delayUnit": "ms",
              "coilsBufferSize": bloques8(LIM["bobina"] // 8),
              "holdingBufferSize": bloques8(LIM["registro_retencion"] * 2),
              "inputBufferSize": bloques8(LIM["registro_entrada"] * 2),
              "discreteBufferSize": bloques8(LIM["entrada_discreta"] // 8),
              "showErrors": False, "showStatusActivities": False,
              # salidas: holding, coils, input, discrete, mensaje
              "x": 580, "y": 200, "wires": [["fn_sust_emu"], ["fn_sust_emu"], [], [], []]})
flows.append(fn("fn_sust_emu", "emulador de la estacion", "24_sust_emulador.js",
                880, 200, TAB_SUST, [["mb_sust_server"], ["file_sust_ev"], ["dbg_sust_estado"]],
                outputs=3))
flows.append(archivo("file_sust_ev", "a2_sustituto_eventos.jsonl", 1130, 220, TAB_SUST))
flows.append(dict(dbg("dbg_sust_estado", "estado del emulador", 1120, 280, TAB_SUST), active=False))

flows.append({"id": "catch_sust", "type": "catch", "z": TAB_SUST,
              "name": "errores del sustituto", "scope": None, "uncaught": False,
              "x": 160, "y": 340, "wires": [["dbg_sust_err"]]})
flows.append(dict(dbg("dbg_sust_err", "error del sustituto", 400, 340, TAB_SUST, "error"),
                  console=True))

# ===========================================================================
# Pestana A2 — cliente de la planta (Factory I/O o el sustituto)
# ===========================================================================
TAB_PLANTA = "a2_planta"
flows.append({"id": TAB_PLANTA, "type": "tab", "label": "A2 · Planta (cliente Modbus)",
              "disabled": False, "info": (
"# Cliente de la planta\n\n"
"Sondeo por bloque (entradas discretas; registros de entrada solo con caja en la\n"
"bascula), cola FIFO de cajas entre `sens_entrada` y `sens_salida`, pesaje con\n"
"valor estable, clasificacion por tolerancia, rechazo con empujador confirmado\n"
"por limites y estado seguro al perder la comunicacion.\n\n"
"Destino: `A2_MODBUS_HOST`, `A2_MODBUS_PUERTO`, `A2_MODBUS_UNIDAD` (por omision\n"
"el sustituto, 127.0.0.1:5020, unidad 1). Periodo: `A2_SONDEO_MS` o\n"
"`config/planta_a2.json`. Comandos: `POST /a2/planta/comando`; estado:\n"
"`GET /a2/planta/estado` (solo local o tailnet).\n"),
              "env": [
                  {"name": "PLANTA_HOST", "type": "jsonata",
                   "value": "$env(\"A2_MODBUS_HOST\") ? $env(\"A2_MODBUS_HOST\") : \"127.0.0.1\""},
                  {"name": "PLANTA_PUERTO", "type": "jsonata",
                   "value": "$env(\"A2_MODBUS_PUERTO\") ? $env(\"A2_MODBUS_PUERTO\") : \"5020\""},
                  {"name": "PLANTA_UNIDAD", "type": "jsonata",
                   "value": "$env(\"A2_MODBUS_UNIDAD\") ? $env(\"A2_MODBUS_UNIDAD\") : \"1\""},
              ]})

flows.append(comentario("c_planta", "A2 · Cliente Modbus de la estacion",
    "Mismo mapa que el sustituto y que Factory I/O.", 140, 40, TAB_PLANTA))

# Nodo de configuracion dentro de la pestana, para que ${PLANTA_HOST} se
# resuelva con las variables de esta pestana. Sin bufferCommands: una orden
# guardada durante un corte llegaria a la planta DESPUES de reconectar, antes
# o en medio de la secuencia segura.
flows.append({"id": "mb_planta_cliente", "type": "modbus-client", "z": TAB_PLANTA,
              "name": "planta (A2_MODBUS_*)", "clienttype": "tcp", "bufferCommands": False,
              "stateLogEnabled": False, "queueLogEnabled": False, "failureLogEnabled": True,
              "tcpHost": "${PLANTA_HOST}", "tcpPort": "${PLANTA_PUERTO}", "tcpType": "DEFAULT",
              "serialPort": "/dev/ttyUSB", "serialType": "RTU-BUFFERD", "serialBaudrate": "9600",
              "serialDatabits": "8", "serialStopbits": "1", "serialParity": "none",
              "serialConnectionDelay": "100", "serialAsciiResponseStartDelimiter": "0x3A",
              "unit_id": "${PLANTA_UNIDAD}", "commandDelay": "1", "clientTimeout": "1500",
              "reconnectOnTimeout": True, "reconnectTimeout": "2000", "parallelUnitIdsAllowed": True,
              "showErrors": False, "showWarnings": True, "showLogs": True})

# --- arranque ------------------------------------------------------------------
flows.append({"id": "inj_planta_carga", "type": "inject", "z": TAB_PLANTA, "name": "al arrancar",
              "props": [{"p": "payload"}], "repeat": "", "crontab": "",
              "once": True, "onceDelay": "0.7", "topic": "", "payload": "",
              "payloadType": "date", "x": 140, "y": 100, "wires": [["fn_planta_rutas"]]})
flows.append(fn("fn_planta_rutas", "revisa rutas", "25_planta_rutas.js",
                320, 100, TAB_PLANTA, [["file_in_planta_mapa"]]))
flows.append(archivo_entrada("file_in_planta_mapa", "lee A2_MAPA", "A2_MAPA",
                             500, 100, TAB_PLANTA, [["fn_planta_mapa"]]))
flows.append(fn("fn_planta_mapa", "carga mapa", "21_carga_mapa.js",
                680, 100, TAB_PLANTA, [["file_in_planta_cfg"]]))
flows.append(archivo_entrada("file_in_planta_cfg", "lee A2_PLANTA_CONFIG", "A2_PLANTA_CONFIG",
                             880, 100, TAB_PLANTA, [["fn_planta_cfg"]]))
flows.append(fn("fn_planta_cfg", "carga configuracion y limites", "26_planta_config.js",
                1110, 100, TAB_PLANTA, [["dbg_planta_cfg"]]))
flows.append(dbg("dbg_planta_cfg", "limites de la planta", 1340, 100, TAB_PLANTA))

# --- sondeo ----------------------------------------------------------------------
flows.append({"id": "inj_planta_reloj", "type": "inject", "z": TAB_PLANTA, "name": "reloj 25 ms",
              "props": [{"p": "payload"}], "repeat": "0.025", "crontab": "",
              "once": True, "onceDelay": "1.5", "topic": "", "payload": "",
              "payloadType": "date", "x": 140, "y": 200, "wires": [["fn_planta_ciclo"]]})
flows.append(fn("fn_planta_ciclo", "ciclo de sondeo", "27_planta_ciclo.js",
                330, 200, TAB_PLANTA, [["mb_planta_lee"], ["mb_planta_escribe"], ["file_planta_ev"]],
                outputs=3))
flows.append({"id": "mb_planta_lee", "type": "modbus-flex-getter", "z": TAB_PLANTA,
              "name": "lee bloque", "showStatusActivities": False, "showErrors": False,
              "showWarnings": True, "logIOActivities": False, "server": "mb_planta_cliente",
              "useIOFile": False, "ioFile": "", "useIOForPayload": False,
              "emptyMsgOnFail": True, "keepMsgProperties": True, "delayOnStart": False,
              "enableDeformedMessages": False, "startDelayTime": "",
              "x": 560, "y": 200, "wires": [["fn_planta_lectura"], []]})
flows.append(fn("fn_planta_lectura", "procesa lectura", "28_planta_lectura.js",
                800, 200, TAB_PLANTA,
                [["mb_planta_lee"], ["mb_planta_escribe"], ["file_planta_ev"],
                 ["link_planta_paso", "dbg_planta_paso"], ["fn_planta_cmd"]], outputs=5))
flows.append({"id": "mb_planta_escribe", "type": "modbus-flex-write", "z": TAB_PLANTA,
              "name": "escribe", "showStatusActivities": False, "showErrors": False,
              "showWarnings": True, "server": "mb_planta_cliente",
              "emptyMsgOnFail": True, "keepMsgProperties": True, "delayOnStart": False,
              "startDelayTime": "", "x": 800, "y": 320, "wires": [["fn_planta_escr"], []]})
flows.append(fn("fn_planta_escr", "confirma escritura", "29_planta_escritura.js",
                1040, 320, TAB_PLANTA, [["mb_planta_escribe"], ["file_planta_ev"]], outputs=2))
flows.append(archivo("file_planta_ev", "a2_planta_eventos.jsonl", 1300, 260, TAB_PLANTA))
flows.append({"id": "link_planta_paso", "type": "link out", "z": TAB_PLANTA,
              "name": "a2_paso_caja", "mode": "link", "links": ["link_nube_paso", "link_mat_paso"], "x": 1060, "y": 200,
              "wires": []})
flows.append(dict(dbg("dbg_planta_paso", "paso_caja", 1080, 160, TAB_PLANTA), active=False))

# --- operacion ---------------------------------------------------------------------
flows.append({"id": "http_planta_cmd", "type": "http in", "z": TAB_PLANTA, "name": "POST /a2/planta/comando",
              "url": "/a2/planta/comando", "method": "post", "upload": False,
              "skipBodyParsing": False, "swaggerDoc": "", "x": 170, "y": 420, "wires": [["fn_planta_cmd"]]})
flows.append(fn("fn_planta_cmd", "comando de operacion", "30_planta_comando.js",
                420, 420, TAB_PLANTA, [["http_planta_resp"], ["mb_planta_escribe"], ["file_planta_ev"],
                                       ["link_planta_resp_hmi"]], outputs=4))
# La HMI entra por aqui: misma funcion y mismos codigos que el POST.
flows.append({"id": "link_planta_cmd_hmi", "type": "link in", "z": TAB_PLANTA, "name": "a2_hmi_comando",
              "links": ["link_hmi_cmd"], "x": 170, "y": 380, "wires": [["fn_planta_cmd"]]})
flows.append({"id": "link_planta_resp_hmi", "type": "link out", "z": TAB_PLANTA, "name": "a2_hmi_respuesta",
              "mode": "link", "links": ["link_hmi_resp"], "x": 660, "y": 390, "wires": []})
flows.append({"id": "http_planta_est", "type": "http in", "z": TAB_PLANTA, "name": "GET /a2/planta/estado",
              "url": "/a2/planta/estado", "method": "get", "upload": False,
              "skipBodyParsing": False, "swaggerDoc": "", "x": 160, "y": 480, "wires": [["fn_planta_est"]]})
flows.append(fn("fn_planta_est", "estado de la planta", "31_planta_estado.js",
                420, 480, TAB_PLANTA, [["http_planta_resp"]]))
flows.append({"id": "http_planta_resp", "type": "http response", "z": TAB_PLANTA,
              "name": "respuesta", "statusCode": "", "headers": {}, "x": 660, "y": 450, "wires": []})

flows.append({"id": "catch_planta", "type": "catch", "z": TAB_PLANTA,
              "name": "errores del cliente", "scope": None, "uncaught": False,
              "x": 160, "y": 560, "wires": [["dbg_planta_err"]]})
flows.append(dict(dbg("dbg_planta_err", "error del cliente", 400, 560, TAB_PLANTA, "error"), console=True))

# ===========================================================================
# Pestana A2 — nube: rama /plantas/{plantaId}/proceso en Firebase
# ===========================================================================
TAB_NUBE = "a2_nube"
flows.append({"id": TAB_NUBE, "type": "tab", "label": "A2 · Nube (rama proceso)", "disabled": False,
              "info": (
"# Registros de proceso en Firebase\n\n"
"Un registro por caja que sale del tramo (de A2-Planta) mas un latido cada\n"
"`A2_LATIDO_S` (60 s), por POST a `/plantas/{PLANTA_ID}/proceso.json` con el\n"
"idToken del ingestor. Validacion local con las mismas condiciones que las\n"
"reglas. Nada se escribe sin `A2_NUBE=1`.\n"), "env": []})
flows.append(comentario("c_nube", "A2 · Rama proceso",
    "Una escritura por caja + un latido por minuto: no satura la base.", 140, 40, TAB_NUBE))
flows.append({"id": "link_nube_paso", "type": "link in", "z": TAB_NUBE, "name": "a2_paso_caja",
              "links": ["link_planta_paso"], "x": 130, "y": 100, "wires": [["fn_nube_registro"]]})
flows.append({"id": "inj_nube_latido", "type": "inject", "z": TAB_NUBE, "name": "reloj 1 s",
              "props": [{"p": "payload"}, {"p": "topic", "vt": "str"}], "repeat": "1", "crontab": "",
              "once": True, "onceDelay": "3", "topic": "latido", "payload": "",
              "payloadType": "date", "x": 140, "y": 160, "wires": [["fn_nube_registro"]]})
flows.append(fn("fn_nube_registro", "arma registro de proceso", "32_nube_registro.js",
                360, 130, TAB_NUBE, [["fn_nube_valida"]]))
flows.append(fn("fn_nube_valida", "valida y arma POST", "33_nube_valida.js",
                590, 130, TAB_NUBE, [["delay_nube"], ["fn_nube_resp"]], outputs=2))
flows.append({"id": "delay_nube", "type": "delay", "z": TAB_NUBE, "name": "maximo 2 por segundo",
              "pauseType": "rate", "timeout": "5", "timeoutUnits": "seconds", "rate": "2",
              "nbRateUnits": "1", "rateUnits": "second", "randomFirst": "1", "randomLast": "5",
              "randomUnits": "seconds", "drop": False, "allowrate": False, "outputs": 1,
              "x": 800, "y": 110, "wires": [["http_nube_post"]]})
flows.append(http_req("http_nube_post", "POST proceso.json", "POST", "obj",
                      1000, 110, TAB_NUBE, [["fn_nube_resp"]]))
flows.append(fn("fn_nube_resp", "interpreta respuesta", "34_nube_respuesta.js",
                1210, 130, TAB_NUBE, [["file_nube_csv"], ["fn_nube_login"]], outputs=2))
flows.append(archivo("file_nube_csv", "a2_nube_AAAA-MM-DD.csv", 1440, 110, TAB_NUBE))
# Sesion propia para renovar tras un 401: el token vive en global y lo
# comparte con la Actividad 1, pero esta pestana no toca la de ingesta.
flows.append(fn("fn_nube_login", "arma login", "05_login_firebase.js",
                1440, 200, TAB_NUBE, [["http_nube_login"]]))
flows.append(http_req("http_nube_login", "signInWithPassword", "POST", "obj",
                      1640, 200, TAB_NUBE, [["fn_nube_token"]]))
flows.append(fn("fn_nube_token", "guarda idToken", "06_guarda_token.js",
                1840, 200, TAB_NUBE, [[], ["dbg_nube_err"]], outputs=2))
flows.append({"id": "catch_nube", "type": "catch", "z": TAB_NUBE,
              "name": "errores de la nube", "scope": None, "uncaught": False,
              "x": 160, "y": 300, "wires": [["dbg_nube_err"]]})
flows.append(dict(dbg("dbg_nube_err", "error de la nube", 420, 300, TAB_NUBE, "error"), console=True))

# ===========================================================================
# Pestana A2 — HMI con Dashboard 2.0 (textos en ingles)
# ===========================================================================
TAB_HMI = "a2_hmi"
flows.append({"id": TAB_HMI, "type": "tab", "label": "A2 · HMI (Dashboard 2.0)", "disabled": False,
              "info": ("# HMI de la estacion\n\nPagina /dashboard/a2. Los botones pasan por "
                       "`30_planta_comando.js` (mismos codigos que POST /a2/planta/comando) y la "
                       "respuesta, con su 409 o 422, vuelve a la pagina. El tunel publico da 403 "
                       "(node-red/settings.js).\n"), "env": []})
flows.append({"id": "ui_base_a2", "type": "ui-base", "name": "A2 Station", "path": "/dashboard", "appIcon": "",
              "includeClientData": True, "acceptsClientConfig": ["ui-notification", "ui-control"],
              "showPathInSidebar": False, "headerContent": "page", "navigationStyle": "none",
              "titleBarStyle": "default", "showReconnectNotification": True, "notificationDisplayTime": 1,
              "showDisconnectNotification": True, "allowInstall": False})
flows.append({"id": "ui_theme_a2", "type": "ui-theme", "name": "A2 Theme",
              "colors": {"surface": "#1f2a37", "primary": "#0d74ce", "bgPage": "#f3f4f6",
                         "groupBg": "#ffffff", "groupOutline": "#d9d9e0"},
              "sizes": {"density": "default", "pagePadding": "12px", "groupGap": "12px",
                        "groupBorderRadius": "6px", "widgetGap": "12px"}})
flows.append({"id": "ui_page_a2", "type": "ui-page", "name": "Weight sorting station", "ui": "ui_base_a2",
              "path": "/a2", "icon": "factory", "layout": "grid", "theme": "ui_theme_a2",
              "breakpoints": [{"name": "Default", "px": 0, "cols": 3}, {"name": "Tablet", "px": 576, "cols": 6},
                              {"name": "Small Desktop", "px": 768, "cols": 9}, {"name": "Desktop", "px": 1024, "cols": 12}],
              "order": 1, "className": "", "visible": "true", "disabled": "false"})
flows.append({"id": "ui_group_a2", "type": "ui-group", "name": "Station", "page": "ui_page_a2", "width": 12,
              "height": 1, "order": 1, "showTitle": False, "className": "", "visible": "true", "disabled": "false",
              "groupType": "default"})
flows.append(comentario("c_hmi", "A2 · HMI", "Estado cada segundo -> plantilla; botones -> A2-Planta.", 140, 40, TAB_HMI))
# Cada 0.5 s: con 1 s, una desconexion se veia justo en timeout_com_ms + 1 s
# (3.0 s contra 3.0 s), sin margen.
flows.append({"id": "inj_hmi", "type": "inject", "z": TAB_HMI, "name": "cada 0.5 s",
              "props": [{"p": "payload"}], "repeat": "0.5", "crontab": "", "once": True, "onceDelay": "2",
              "topic": "", "payload": "", "payloadType": "date", "x": 130, "y": 100, "wires": [["fn_hmi_estado"]]})
flows.append(dict(fn("fn_hmi_estado", "estado para la HMI", "35_hmi_estado.js", 330, 100, TAB_HMI, [["ui_tpl_a2"]]),
                  libs=[{"var": "fs", "module": "fs"}]))
flows.append({"id": "ui_tpl_a2", "type": "ui-template", "z": TAB_HMI, "group": "ui_group_a2", "page": "", "ui": "",
              "name": "Station HMI", "order": 1, "width": 12, "height": 0, "head": "",
              "format": (RAIZ / "hmi" / "a2_hmi.vue").read_text(encoding="utf-8"),
              "storeOutMessages": True, "passthru": False, "resendOnRefresh": True, "templateScope": "local",
              "className": "", "x": 560, "y": 140, "wires": [["fn_hmi_cmd"]]})
flows.append(fn("fn_hmi_cmd", "boton de la HMI a comando", "36_hmi_comando.js",
                790, 140, TAB_HMI, [["link_hmi_cmd"], ["link_hmi_diag"]], outputs=2))
flows.append({"id": "link_hmi_cmd", "type": "link out", "z": TAB_HMI, "name": "a2_hmi_comando", "mode": "link",
              "links": ["link_planta_cmd_hmi"], "x": 990, "y": 120, "wires": []})
flows.append({"id": "link_hmi_diag", "type": "link out", "z": TAB_HMI, "name": "a2_diag_pedido", "mode": "link",
              "links": ["link_diag_pedido"], "x": 990, "y": 170, "wires": []})
flows.append({"id": "link_hmi_resp", "type": "link in", "z": TAB_HMI, "name": "a2_hmi_respuesta",
              "links": ["link_planta_resp_hmi"], "x": 150, "y": 180, "wires": [["ui_tpl_a2"]]})

# ===========================================================================
# Pestana A2 — diagnostico con Gemini (consejo, nunca mueve la planta)
# ===========================================================================
TAB_DIAG2 = "a2_diagnostico"
flows.append({"id": TAB_DIAG2, "type": "tab", "label": "A2 · Diagnostico (Gemini)", "disabled": False,
              "info": ("# Diagnostico de la estacion\n\nBajo demanda desde la HMI y cada 60 min con la linea "
                       "en marcha. Tope propio A2_DIAG_MAX_DIA (15), limitador 1/min, maxOutputTokens 2048, "
                       "thinkingBudget 0. Validacion estricta: lo invalido no llega a la HMI.\n"),
              # El limitador es de 1 por minuto; A2_DIAG_POR_MINUTO lo sube solo para las pruebas.
              "env": [{"name": "DIAG2_POR_MINUTO", "type": "jsonata",
                       "value": "$env(\"A2_DIAG_POR_MINUTO\") ? $env(\"A2_DIAG_POR_MINUTO\") : \"1\""}]})
flows.append(comentario("c_diag2", "A2 · Diagnostico", "Texto en ingles; solo consejo.", 140, 40, TAB_DIAG2))
flows.append({"id": "link_diag_pedido", "type": "link in", "z": TAB_DIAG2, "name": "a2_diag_pedido",
              "links": ["link_hmi_diag"], "x": 140, "y": 100, "wires": [["delay_diag2"]]})
flows.append({"id": "inj_diag2", "type": "inject", "z": TAB_DIAG2, "name": "cada 60 min",
              "props": [{"p": "payload"}, {"p": "topic", "vt": "str"}], "repeat": "3600", "crontab": "",
              "once": False, "onceDelay": "", "topic": "periodico", "payload": "", "payloadType": "date",
              "x": 140, "y": 160, "wires": [["delay_diag2"]]})
flows.append({"id": "delay_diag2", "type": "delay", "z": TAB_DIAG2, "name": "maximo 1 por minuto",
              "pauseType": "rate", "timeout": "5", "timeoutUnits": "seconds", "rate": "${DIAG2_POR_MINUTO}", "nbRateUnits": "1",
              "rateUnits": "minute", "randomFirst": "1", "randomLast": "5", "randomUnits": "seconds",
              "drop": True, "allowrate": False, "outputs": 1, "x": 360, "y": 130, "wires": [["fn_diag2_arma"]]})
flows.append(fn("fn_diag2_arma", "arma consulta", "37_diag_arma.js", 580, 130, TAB_DIAG2,
                [["http_diag2"], ["dbg_diag2_omitido"]], outputs=2))
flows.append(dict(dbg("dbg_diag2_omitido", "consulta omitida", 800, 190, TAB_DIAG2), active=False))
flows.append(http_req("http_diag2", "POST generateContent", "POST", "txt", 800, 110, TAB_DIAG2, [["fn_diag2_valida"]]))
flows.append(fn("fn_diag2_valida", "valida el diagnostico", "38_diag_valida.js", 1020, 130, TAB_DIAG2,
                [["dbg_diag2"], ["file_diag2"]], outputs=2))
flows.append(dbg("dbg_diag2", "diagnostico valido", 1240, 100, TAB_DIAG2))
flows.append(archivo("file_diag2", "a2_diagnosticos_AAAA-MM-DD.csv", 1260, 160, TAB_DIAG2))
flows.append({"id": "catch_diag2", "type": "catch", "z": TAB_DIAG2, "name": "errores del diagnostico",
              "scope": None, "uncaught": False, "x": 160, "y": 260, "wires": [["dbg_diag2_err"]]})
flows.append(dict(dbg("dbg_diag2_err", "error del diagnostico", 420, 260, TAB_DIAG2, "error"), console=True))

# ===========================================================================
# Pestana A2 — capa de materiales (paso M2 de la fase 3). Solo con A2_MATERIALES=1.
# ===========================================================================
TAB_MAT = "a2_materiales"
flows.append({"id": TAB_MAT, "type": "tab", "label": "A2 · Materiales (capa de materiales)", "disabled": False,
              "info": ("# Capa de materiales minima\n\nDos varillas virtuales (laminados 0:0 y 9:1, Jen y Huang 2021) "
                       "con la historia de carga de los paso_caja. Modelo: 39_mat_modelo.js (funcion pura, la misma que "
                       "ejecutan las pruebas). Configuracion: A2_MAT_CONFIG (config/materiales.json). Estado en "
                       "$DATOS_DIR/a2_materiales_estado.json; lo medido y la verdad en archivos separados. La verdad no "
                       "va al contexto global: a la HMI llega por el enlace a2_mat_hmi. No escribe en la planta, en "
                       "Firebase ni consulta a Gemini. Sin A2_MATERIALES=1 no hace nada.\n")})
flows.append(comentario("c_mat", "A2 · Materiales", "paso_caja -> entrada -> modelo -> guarda y separa -> HMI", 160, 40, TAB_MAT))
flows.append({"id": "link_mat_paso", "type": "link in", "z": TAB_MAT, "name": "a2_paso_caja",
              "links": ["link_planta_paso"], "x": 120, "y": 120, "wires": [["fn_mat_entrada"]]})
flows.append({"id": "inj_mat_arranque", "type": "inject", "z": TAB_MAT, "name": "al iniciar",
              "props": [{"p": "payload"}, {"p": "topic", "vt": "str"}], "repeat": "", "crontab": "",
              "once": True, "onceDelay": "0.5", "topic": "arranque", "payload": "", "payloadType": "date",
              "x": 140, "y": 180, "wires": [["fn_mat_entrada"]]})
flows.append(dict(fn("fn_mat_entrada", "entrada de materiales", "40_mat_entrada.js", 360, 140, TAB_MAT,
                     [["fn_mat_modelo"], ["fn_mat_hmi"]], outputs=2), libs=[{"var": "fs", "module": "fs"}]))
flows.append(fn("fn_mat_modelo", "modelo de materiales", "39_mat_modelo.js", 600, 140, TAB_MAT, [["fn_mat_salida"]]))
flows.append(dict(fn("fn_mat_salida", "guarda y separa", "41_mat_salida.js", 840, 140, TAB_MAT,
                     [["fn_mat_hmi"], ["fn_mat_entrada"]], outputs=2), libs=[{"var": "fs", "module": "fs"}]))
flows.append({"id": "inj_mat_hmi", "type": "inject", "z": TAB_MAT, "name": "cada 2 s",
              "props": [{"p": "payload"}], "repeat": "2", "crontab": "", "once": True, "onceDelay": "1",
              "topic": "", "payload": "", "payloadType": "date", "x": 860, "y": 240, "wires": [["fn_mat_hmi"]]})
flows.append(fn("fn_mat_hmi", "tarjeta Materials layer", "42_mat_hmi.js", 1080, 200, TAB_MAT, [["link_mat_hmi"]]))
flows.append({"id": "link_mat_hmi", "type": "link out", "z": TAB_MAT, "name": "a2_mat_hmi", "mode": "link",
              "links": ["link_hmi_mat"], "x": 1260, "y": 200, "wires": []})
flows.append({"id": "catch_mat", "type": "catch", "z": TAB_MAT, "name": "errores de materiales",
              "scope": None, "uncaught": False, "x": 160, "y": 300, "wires": [["dbg_mat_err"]]})
flows.append(dict(dbg("dbg_mat_err", "error de materiales", 420, 300, TAB_MAT, "error"), console=True))
# En A2-HMI: la tarjeta recibe por enlace, no por el contexto global.
flows.append({"id": "link_hmi_mat", "type": "link in", "z": TAB_HMI, "name": "a2_mat_hmi",
              "links": ["link_mat_hmi"], "x": 150, "y": 230, "wires": [["ui_tpl_a2"]]})

# ---------------------------------------------------------------------------
salida = RAIZ / "flows.json"
salida.write_text(json.dumps(flows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

ids = [n["id"] for n in flows]
assert len(ids) == len(set(ids)), "hay ids repetidos"
validos = set(ids)
for n in flows:
    for salidas in n.get("wires", []):
        for destino in salidas:
            assert destino in validos, f"{n['id']} apunta a {destino}, que no existe"
    if n["type"] == "function":
        assert len(n["wires"]) == n["outputs"], f"{n['id']}: outputs != wires"
print(f"flows.json escrito: {len(flows)} nodos, {salida.stat().st_size} bytes")
