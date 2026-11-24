/* Nodo: "valida y arma POST a proceso"  (A2-Nube, 2 salidas: 0 = POST, 1 = rechazado)
 * ---------------------------------------------------------------
 * Mismas condiciones que firebase/database.rules.json para la rama proceso.
 * Firebase contesta el MISMO 401 para un permiso negado que para un campo
 * fuera de rango (hallazgo 3.1 de la Actividad 1), asi que el rechazo se hace
 * aqui, donde el motivo se puede escribir. Si cambia un rango aqui, cambia
 * en las reglas, o el rechazo se muda a la base.
 *
 * POST sobre .../proceso.json: una clave push por registro, nada se
 * sobrescribe.
 */
const zona = env.get("TZ_REPORTE") || "America/Mexico_City";
const base = (env.get("FIREBASE_DB_URL") || "").replace(/\/+$/, "");
const planta = env.get("PLANTA_ID") || "planta_01";
const b = msg.base || {};

function rechaza(motivo, detalle) {
    node.warn(`registro de proceso rechazado (${motivo}): ${detalle}`);
    node.status({ fill: "red", shape: "dot", text: motivo });
    msg.resultado = { codigo: 422, motivo: motivo, detalle: detalle };
    return [null, msg];
}
// ts_escritura con desplazamiento, igual que 01_valida_telemetria.js
function tsLocal(fecha) {
    const fmt = new Intl.DateTimeFormat("en-US", {
        timeZone: zona, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3,
        timeZoneName: "longOffset" });
    const p = {};
    for (const x of fmt.formatToParts(fecha)) p[x.type] = x.value;
    if (p.hour === "24") p.hour = "00";
    let off = (p.timeZoneName || "GMT+00:00").replace("GMT", "");
    if (off === "" || off === "Z") off = "+00:00";
    return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}.${p.fractionalSecond}${off}`;
}

if (!base) return rechaza("config_incompleta", "falta FIREBASE_DB_URL");
if (!/^planta_[0-9]{2}$/.test(planta)) return rechaza("planta_id_invalido", planta);

const num = (x, lo, hi) => typeof x === "number" && Number.isFinite(x) && x >= lo && x <= hi;
const r2 = (x, d) => Math.round(x * Math.pow(10, d)) / Math.pow(10, d);
const reg = {
    ts_origen: b.ts_origen,
    ts_escritura: tsLocal(new Date()),
    vel_banda_V: typeof b.vel_banda_V === "number" ? r2(b.vel_banda_V, 2) : b.vel_banda_V,
    peso_V: typeof b.peso_V === "number" ? r2(b.peso_V, 3) : b.peso_V,
    cajas_acumuladas: b.cajas_acumuladas,
    estado_linea: b.estado_linea
};
// destino solo en registros de caja: salida/rechazo con el empujador, o la
// salida del desviador (left, right, forward). Lo usa la grafica de C8.
if (b.tipo === "caja" && b.destino) reg.destino = b.destino;
if (b.tipo === "caja" && b.caja_masa_kg !== null && b.caja_masa_kg !== undefined) {
    reg.caja_masa_kg = typeof b.caja_masa_kg === "number" ? r2(b.caja_masa_kg, 3) : b.caja_masa_kg;
}

const errores = [];
if (typeof reg.ts_origen !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(reg.ts_origen)) errores.push(`ts_origen ${reg.ts_origen}`);
if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}$/.test(reg.ts_escritura)) errores.push(`ts_escritura ${reg.ts_escritura}`);
if (!num(reg.vel_banda_V, -10, 10)) errores.push(`vel_banda_V ${reg.vel_banda_V}`);
if (!num(reg.peso_V, 0, 10)) errores.push(`peso_V ${reg.peso_V}`);
if ("caja_masa_kg" in reg && !num(reg.caja_masa_kg, 0, 20)) errores.push(`caja_masa_kg ${reg.caja_masa_kg}`);
if (!Number.isInteger(reg.cajas_acumuladas) || reg.cajas_acumuladas < 0) errores.push(`cajas_acumuladas ${reg.cajas_acumuladas}`);
if (!/^(en_marcha|detenida|sin_comunicacion|reconectando|iniciando|emergencia)$/.test(String(reg.estado_linea))) errores.push(`estado_linea ${reg.estado_linea}`);
if ("destino" in reg && !/^(salida|rechazo|left|right|forward)$/.test(String(reg.destino))) errores.push(`destino ${reg.destino}`);
if (errores.length) return rechaza("valor_fuera_del_esquema", errores.join(" | "));

const token = global.get("fb_id_token") || env.get("FIREBASE_AUTH") || "";
let url = `${base}/plantas/${encodeURIComponent(planta)}/proceso.json`;
if (token) url += `?auth=${encodeURIComponent(token)}`;
msg.url = url;
msg.headers = { "Content-Type": "application/json" };
msg.registro = reg;
msg.payload = reg;
msg.t_write = Date.now();
return [msg, null];
