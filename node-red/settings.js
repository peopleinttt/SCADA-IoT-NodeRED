/* settings.js del repositorio para Node-RED (Actividades 1 y 2). Sin credenciales.
 *
 * Lo usan ./arranca.sh y pruebas/prueba.sh con --settings; el userDir sigue
 * siendo el de cada uno (flujos y paletas).
 *
 * POR QUE EXISTE. tunel.sh publica TODO el puerto 1881 en un tunel rapido de
 * Cloudflare para que Wokwi alcance la ingesta. Con el settings.js por omision
 * el editor quedaba en Internet sin contrasena, y con la HMI de C6 tambien sus
 * botones. Regla: toda peticion que llega por el tunel (trae cf-connecting-ip
 * o cf-ray, que pone cloudflared) se rechaza con 403, salvo POST /telemetria,
 * la ingesta de la Actividad 1.
 *
 * Tres capas, de la mas especifica a la mas general:
 *   1. httpAdminMiddleware y httpNodeMiddleware: editor, API de admin y rutas
 *      de los nodos http in.
 *   2. dashboard.middleware y dashboard.ioMiddleware: rutas y socket.io de
 *      Dashboard 2.0 (@flowfuse/node-red-dashboard 1.34.0 los ofrece).
 *   3. Filtro en el servidor HTTP (eventos request y upgrade). Hace falta
 *      porque socket.io (engine.io) atiende su ruta antes que express: con
 *      ioMiddleware solo se puede cortar la conexion despues del saludo, no
 *      contestar 403. Este filtro contesta 403 antes que nadie, tambien al
 *      intento de websocket.
 *
 * EDITOR Y API DE ADMINISTRACION (paso S2 de la fase 3). El filtro anterior
 * reconoce cabeceras, no identidades: desde la red local o la tailnet el
 * editor quedaba abierto. Ahora:
 *   - Con NODE_RED_ADMIN_USER y NODE_RED_ADMIN_HASH (hash bcrypt) en el entorno,
 *     adminAuth de tipo "credentials" con ese unico usuario y permisos "*".
 *     Formato tomado de la pagina "Securing Node-RED" y comprobado contra
 *     @node-red/editor-api 5.0.9 (lib/auth/users.js: @node-rs/bcrypt o bcryptjs).
 *   - Si falta cualquiera de las dos, o el hash no tiene formato bcrypt,
 *     httpAdminRoot = false: Node-RED no sirve ni el editor ni la API de
 *     administracion (lo dice en su registro: "Admin UI disabled", y aqui otra
 *     linea con el motivo). Los flujos, el dashboard, /a2/planta/* y la ingesta
 *     siguen funcionando porque viven en httpNodeRoot. Sin credenciales el
 *     editor se cierra, nunca se abre. No hay contrasena por omision.
 *   - /dashboard/a2 y /a2/planta/* no usan adminAuth (no hay httpNodeAuth: la
 *     ingesta del ESP32 dejaria de funcionar). Siguen abiertos a la red local y
 *     a la tailnet y cerrados al tunel por las tres capas de arriba.
 */
const http = require("http");

const BCRYPT = /^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$/;
const ADMIN_USUARIO = process.env.NODE_RED_ADMIN_USER || "";
const ADMIN_HASH = process.env.NODE_RED_ADMIN_HASH || "";
const ADMIN_PROTEGIDO = !!ADMIN_USUARIO && BCRYPT.test(ADMIN_HASH);
if (ADMIN_PROTEGIDO) {
    console.log("[a2-seguridad] editor y API de administracion PROTEGIDOS con usuario y contrasena (adminAuth)");
} else {
    const motivo = !ADMIN_USUARIO || !ADMIN_HASH
        ? "falta " + ["NODE_RED_ADMIN_USER", "NODE_RED_ADMIN_HASH"].filter(v => !process.env[v]).join(" y ")
        : "NODE_RED_ADMIN_HASH no tiene formato bcrypt";
    console.log("[a2-seguridad] editor y API de administracion DESHABILITADOS (" + motivo +
                "); flujos, dashboard, /a2/planta/* e ingesta siguen. Ver ./prepara_admin.sh");
}

const POR_TUNEL_PERMITIDAS = [{ metodo: "POST", ruta: "/telemetria" }];

function porTunel(headers) {
    return !!(headers && (headers["cf-connecting-ip"] || headers["cf-ray"]));
}
function permitidaPorTunel(req) {
    const ruta = String(req.url || "").split("?")[0].replace(/\/+$/, "") || "/";
    return POR_TUNEL_PERMITIDAS.some(p => p.metodo === req.method && p.ruta === ruta);
}
const CUERPO_403 = JSON.stringify({ ok: false, motivo: "origen_no_permitido",
                                    detalle: "por el tunel publico solo se acepta POST /telemetria" });

function filtroExpress(req, res, next) {
    if (porTunel(req.headers) && !permitidaPorTunel(req)) {
        res.status(403).set("Content-Type", "application/json").send(CUERPO_403);
        return;
    }
    next();
}

// ---- capa 3: el servidor HTTP del proceso ---------------------------------------
// A2_FILTRO_SERVIDOR=0 la apaga, solo para que pruebas/prueba_seguridad.py
// --sin-capa3 demuestre que las capas 1 y 2 cubren lo suyo por si solas.
const emitir = http.Server.prototype.emit;
if (process.env.A2_FILTRO_SERVIDOR !== "0") http.Server.prototype.emit = function (evento, req, resOSocket, ...resto) {
    if ((evento === "request" || evento === "upgrade") && req && porTunel(req.headers) && !permitidaPorTunel(req)) {
        if (evento === "request") {
            resOSocket.writeHead(403, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(CUERPO_403) });
            resOSocket.end(CUERPO_403);
        } else {
            resOSocket.end("HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n");
        }
        return true;
    }
    return emitir.call(this, evento, req, resOSocket, ...resto);
};

module.exports = {
    flowFile: "flows.json",
    flowFilePretty: true,
    uiPort: process.env.PORT || 1880,

    httpAdminRoot: ADMIN_PROTEGIDO ? "/" : false,
    httpNodeRoot: "/",
    adminAuth: ADMIN_PROTEGIDO ? {
        type: "credentials",
        users: [{ username: ADMIN_USUARIO, password: ADMIN_HASH, permissions: "*" }]
    } : undefined,
    httpAdminMiddleware: filtroExpress,
    httpNodeMiddleware: filtroExpress,

    dashboard: {
        middleware: filtroExpress,
        // Reemplaza al de Dashboard 2.0, asi que repite lo que el suyo hace:
        // rechaza websocket directo y peticiones de otro origen.
        ioMiddleware: function (socket, next) {
            if (porTunel(socket.handshake.headers)) {
                socket.disconnect(true);
                return;
            }
            if (socket.client.conn.request.url.indexOf("transport=websocket") !== -1) {
                socket.client.conn.close();
                return;
            }
            if (socket.handshake.xdomain === false) return next();
            socket.disconnect(true);
        }
    },

    diagnostics: { enabled: true, ui: true },
    runtimeState: { enabled: false, ui: false },
    logging: { console: { level: "info", metrics: false, audit: false } },
    exportGlobalContextKeys: false,
    externalModules: {},
    editorTheme: { projects: { enabled: false }, codeEditor: { lib: "monaco" } },
    functionExternalModules: true,
    functionTimeout: 0,
    functionGlobalContext: {},
    debugMaxLength: 1000,
    mqttReconnectTime: 15000,
    serialReconnectTime: 15000
};
