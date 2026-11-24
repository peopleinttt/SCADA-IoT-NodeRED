/* Nodo: "lee ultimas muestras"
 * ---------------------------------------------------------------
 * Consulta acotada: orderBy="$key" + limitToLast=N. Nunca se descarga la
 * rama completa, que es lo que satura la base y consume la cuota de lectura.
 * "$key" no necesita indice declarado en las reglas.
 */
const base   = (env.get("FIREBASE_DB_URL") || "").replace(/\/+$/, "");
const planta = env.get("PLANTA_ID") || "planta_01";
const n      = Math.max(2, Math.min(60, Number(env.get("DIAG_MUESTRAS") || 12)));

if (!base) {
    node.error("FIREBASE_DB_URL no esta definida", msg);
    return null;
}

// Freno por saturacion/cuota: si un error previo pidio pausa, no insistimos.
const pausaHasta = flow.get("gemini_pausa_hasta") || 0;
if (Date.now() < pausaHasta) {
    const faltan = Math.ceil((pausaHasta - Date.now()) / 1000);
    node.status({ fill: "yellow", shape: "ring", text: `en pausa ${faltan} s` });
    return null;
}

const token = global.get("fb_id_token") || env.get("FIREBASE_AUTH") || "";
let url = `${base}/plantas/${encodeURIComponent(planta)}/telemetria.json` +
          `?orderBy=%22%24key%22&limitToLast=${n}`;
if (token) url += `&auth=${encodeURIComponent(token)}`;

msg.url    = url;   // el metodo GET lo fija el nodo HTTP Request
msg.n_pedidas = n;
node.status({ fill: "blue", shape: "ring", text: `leyendo ${n} muestras` });
return msg;
