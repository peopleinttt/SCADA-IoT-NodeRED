/* Nodo: "arma POST a Firebase"
 * ---------------------------------------------------------------
 * POST (no PATCH ni PUT) sobre .../telemetria.json para que Firebase
 * genere una clave push nueva por evento: cada muestra es un registroId
 * distinto y ninguna sobrescribe a la anterior.
 */
const base   = (env.get("FIREBASE_DB_URL") || "").replace(/\/+$/, "");
const planta = env.get("PLANTA_ID") || "planta_01";

if (!base) {
    node.error("FIREBASE_DB_URL no esta definida", msg);
    msg.statusCode = 500;
    msg.payload = { ok: false, motivo: "config_incompleta",
                    detalle: "falta FIREBASE_DB_URL" };
    return [null, msg];
}


// Las reglas exigen que la planta se llame planta_NN, con dos digitos y cero a
// la izquierda. Un "planta_7" o un "planta_007" no fallan por formato: fallan
// con PERMISSION_DENIED, y uno acaba depurando permisos cuando el problema es
// el nombre. Se detiene aqui, con el motivo escrito.
if (!/^planta_[0-9]{2}$/.test(planta)) {
    node.error(`PLANTA_ID="${planta}" no cumple el formato planta_NN que exigen ` +
               `las reglas (dos digitos, con cero a la izquierda). ` +
               `Corrige PLANTA_ID en .env y en CONFIG.planta del index.html.`, msg);
    msg.statusCode = 500;
    msg.payload = { ok: false, motivo: "planta_id_invalido", detalle: planta };
    return [null, msg];
}

// Credencial: primero el idToken vivo del login automatico; si no hay,
// el valor fijo de FIREBASE_AUTH (secreto de BD o token manual).
const token = global.get("fb_id_token") || env.get("FIREBASE_AUTH") || "";
if (!token) {
    node.warn("sin credencial de Firebase: la escritura fallara si las reglas " +
              "estan bien puestas (asi debe ser)");
}

let url = `${base}/plantas/${encodeURIComponent(planta)}/telemetria.json`;
if (token) url += `?auth=${encodeURIComponent(token)}`;

msg.url     = url;   // el metodo POST lo fija el nodo HTTP Request, no msg
msg.headers = { "Content-Type": "application/json" };
msg.payload = msg.registro;
msg.t_write = Date.now();
// Para depurar sin exponer la credencial en la barra de estado ni en debug.
msg.url_visible = url.replace(/([?&]auth=)[^&]+/, "$1<oculto>");
return [msg, null];
