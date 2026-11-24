/* Nodo: "arma POST del diagnostico"
 * Escribe en /plantas/{plantaId}/diagnosticos.json con POST, igual que la
 * telemetria: una clave push nueva por diagnostico.
 */
const base   = (env.get("FIREBASE_DB_URL") || "").replace(/\/+$/, "");
const planta = env.get("PLANTA_ID") || "planta_01";
const zona   = env.get("TZ_REPORTE") || "America/Mexico_City";

function tsISO(fecha) {
    const fmt = new Intl.DateTimeFormat("en-US", {
        timeZone: zona, hourCycle: "h23",
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
        fractionalSecondDigits: 3, timeZoneName: "longOffset"
    });
    const p = {};
    for (const parte of fmt.formatToParts(fecha)) p[parte.type] = parte.value;
    if (p.hour === "24") p.hour = "00";
    let off = (p.timeZoneName || "GMT+00:00").replace("GMT", "");
    if (off === "" || off === "Z") off = "+00:00";
    return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}.${p.fractionalSecond}${off}`;
}

if (!/^planta_[0-9]{2}$/.test(planta)) {
    node.error(`PLANTA_ID="${planta}" no cumple el formato planta_NN que exigen ` +
               `las reglas. El diagnostico no se guarda.`, msg);
    return null;
}

const d = msg.diagnostico;
msg.registro_diag = {
    ts:                tsISO(new Date()),
    resumen_entrada:   String(msg.resumen_entrada || "").slice(0, 1000),
    texto_diagnostico: d.texto_diagnostico.slice(0, 2000),
    accion_prescrita:  d.accion_prescrita.slice(0, 300),
    modelo:            d.modelo,
    latencia_ms:       d.latencia_ms
};

const token = global.get("fb_id_token") || env.get("FIREBASE_AUTH") || "";
let url = `${base}/plantas/${encodeURIComponent(planta)}/diagnosticos.json`;
if (token) url += `?auth=${encodeURIComponent(token)}`;

msg.url     = url;
msg.headers = { "Content-Type": "application/json" };
msg.payload = msg.registro_diag;
return msg;
