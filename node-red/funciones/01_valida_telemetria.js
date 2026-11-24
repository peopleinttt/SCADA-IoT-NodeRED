/* Nodo: "valida y sella"  (2 salidas: 0 = aceptado, 1 = rechazado)
 * -----------------------------------------------------------------
 * 1. Autentica el POST con el secreto compartido (el tunel es publico).
 * 2. Verifica que esten TODOS los campos del esquema, con tipo y rango.
 * 3. Agrega ts_escritura con Intl.DateTimeFormat.
 * Si algo falta o no cuadra, el mensaje se rechaza: no se completa ni se
 * adivina, porque un dato inventado contamina toda la corrida.
 */

const ZONA = env.get("TZ_REPORTE") || "America/Mexico_City";

// ---- ts_escritura: ISO-8601 con desplazamiento, armado con Intl ----------
// No se usa toISOString(): SIEMPRE emite "Z", y la regla de Firebase exige
// desplazamiento numerico. Tampoco se usa getTimezoneOffset(), que dependeria
// de la zona horaria del proceso (la de un contenedor suele ser UTC). Con Intl
// la zona es un dato de configuracion explicito, no ambiente heredado.
function tsEscrituraISO(fecha, zona) {
    const fmt = new Intl.DateTimeFormat("en-US", {
        timeZone: zona,
        hourCycle: "h23",
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
        fractionalSecondDigits: 3,
        timeZoneName: "longOffset"
    });
    const p = {};
    for (const parte of fmt.formatToParts(fecha)) p[parte.type] = parte.value;
    if (p.hour === "24") p.hour = "00";                       // ICU antiguo
    let off = (p.timeZoneName || "GMT+00:00").replace("GMT", "");
    if (off === "" || off === "Z") off = "+00:00";            // caso UTC
    return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}` +
           `.${p.fractionalSecond}${off}`;
}

function rechaza(motivo, detalle, codigo) {
    node.status({ fill: "red", shape: "dot", text: motivo });
    node.warn(`rechazado (${motivo}): ${detalle}`);
    msg.statusCode = codigo || 400;
    msg.payload = { ok: false, motivo: motivo, detalle: detalle };
    return [null, msg];
}

// ---- 1. secreto compartido ----------------------------------------------
const claveEsperada = env.get("INGEST_KEY") || "";
const claveRecibida = (msg.req && msg.req.headers && msg.req.headers["x-ingest-key"]) || "";
if (claveEsperada) {
    if (claveRecibida !== claveEsperada) {
        return rechaza("clave_invalida", "cabecera X-Ingest-Key ausente o incorrecta", 401);
    }
} else {
    node.warn("INGEST_KEY vacia: el endpoint esta ACEPTANDO CUALQUIER POST");
}

// ---- 2. esquema ----------------------------------------------------------
const ESPERADOS = ["ts_origen", "temperatura_C", "vibracion_mm_s", "ciclos_acumulados"];
const cuerpo = msg.payload;

if (cuerpo === null || typeof cuerpo !== "object" || Array.isArray(cuerpo)) {
    return rechaza("cuerpo_invalido", "se esperaba un objeto JSON", 400);
}

const faltantes = ESPERADOS.filter(c => !(c in cuerpo));
if (faltantes.length) {
    return rechaza("campos_faltantes", faltantes.join(","), 400);
}

const sobrantes = Object.keys(cuerpo).filter(c => ESPERADOS.indexOf(c) === -1);
if (sobrantes.length) {
    // El esquema de Firebase esta congelado; un campo extra lo rompe rio abajo.
    return rechaza("campos_no_esperados", sobrantes.join(","), 422);
}

// ts_origen: cadena ISO-8601 que ademas tenga sentido en el tiempo
if (typeof cuerpo.ts_origen !== "string") {
    return rechaza("ts_origen_no_es_cadena", typeof cuerpo.ts_origen, 422);
}
const tOrigenMs = Date.parse(cuerpo.ts_origen);
if (!Number.isFinite(tOrigenMs)) {
    return rechaza("ts_origen_no_parseable", cuerpo.ts_origen, 422);
}
// El esquema congela ts_origen en UTC (termina en Z) y ts_escritura en hora
// local con desplazamiento. Las reglas de Firebase lo exigen con regex, asi
// que se rechaza aqui para que el error salga en el borde y no en la base.
if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(cuerpo.ts_origen)) {
    return rechaza("ts_origen_no_es_utc",
                   `se esperaba AAAA-MM-DDTHH:MM:SS.mmmZ, llego ${cuerpo.ts_origen}`, 422);
}
const ahora = new Date();
const desfaseS = (ahora.getTime() - tOrigenMs) / 1000;
const TOLERANCIA_FUTURO_S = Number(env.get("TOL_FUTURO_S") || 120);
const TOLERANCIA_PASADO_S = Number(env.get("TOL_PASADO_S") || 3600);
if (desfaseS < -TOLERANCIA_FUTURO_S) {
    return rechaza("ts_origen_en_el_futuro", `${desfaseS.toFixed(1)} s`, 422);
}
if (desfaseS > TOLERANCIA_PASADO_S) {
    return rechaza("ts_origen_demasiado_viejo", `${desfaseS.toFixed(1)} s`, 422);
}

// numericos: tipo, finitud y rango fisico del sensor
function numeroEnRango(nombre, valor, min, max) {
    if (typeof valor !== "number" || !Number.isFinite(valor)) {
        return `${nombre} no es numero finito (${JSON.stringify(valor)})`;
    }
    if (valor < min || valor > max) {
        return `${nombre}=${valor} fuera de [${min}, ${max}]`;
    }
    return null;
}
// Los limites son los del instrumento, no numeros redondos: el DHT22 mide
// -40 a 80 C (hoja de datos AM2302) y el transmisor de vibracion tiene fondo
// de escala de 50 mm/s. Se deja el doble en vibracion para que la ruta del
// acelerometro (VIB_FUENTE 1) quepa, pero un valor mayor a 100 mm/s RMS en
// una maquina clase II no es una lectura: es una derivacion que salio mal.
// Estos rangos son los MISMOS que en firebase/database.rules.json; si cambia
// uno hay que cambiar el otro, o el rechazo se muda a la base de datos.
const errores = [
    numeroEnRango("temperatura_C", cuerpo.temperatura_C, -40, 80),
    numeroEnRango("vibracion_mm_s", cuerpo.vibracion_mm_s, 0, 100),
    numeroEnRango("ciclos_acumulados", cuerpo.ciclos_acumulados, 0, 2147483647)
].filter(Boolean);
if (errores.length) {
    return rechaza("valor_fuera_de_rango", errores.join(" | "), 422);
}
if (!Number.isInteger(cuerpo.ciclos_acumulados)) {
    return rechaza("ciclos_no_entero", String(cuerpo.ciclos_acumulados), 422);
}

// ---- 3. sello de escritura ----------------------------------------------
let tsEscritura;
try {
    tsEscritura = tsEscrituraISO(ahora, ZONA);
} catch (e) {
    // Intl lanza RangeError si TZ_REPORTE no es una zona valida.
    return rechaza("zona_horaria_invalida",
                   `TZ_REPORTE="${ZONA}" no es una zona IANA valida (${e.message})`, 500);
}

// Post-condicion. Firebase devuelve el MISMO 401 "Permission denied" para un
// permiso denegado que para una marca de tiempo mal formada, asi que un
// ts_escritura invalido se veria como un problema de credenciales y mandaria a
// depurar al lugar equivocado. Se comprueba aqui, donde el mensaje es legible.
const RE_LOCAL = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}$/;
if (!RE_LOCAL.test(tsEscritura)) {
    return rechaza("ts_escritura_mal_formado",
                   `se genero "${tsEscritura}" con TZ_REPORTE="${ZONA}"; ` +
                   `las reglas exigen desplazamiento numerico`, 500);
}
if (/[+-]00:00$/.test(tsEscritura)) {
    // Pasa la regla, pero "hora local del ingestor" seria UTC, que no es lo
    // que congela el enunciado. Se avisa sin detener la ingesta.
    node.warn(`ts_escritura sale en +00:00 (TZ_REPORTE="${ZONA}"). Pasa las ` +
              `reglas, pero deja de ser hora local. Usa America/Mexico_City.`);
}

msg.registro = {
    ts_origen:         cuerpo.ts_origen,
    ts_escritura:      tsEscritura,
    temperatura_C:     cuerpo.temperatura_C,
    vibracion_mm_s:    cuerpo.vibracion_mm_s,
    ciclos_acumulados: cuerpo.ciclos_acumulados
};
msg.latencia_ms = ahora.getTime() - tOrigenMs;

const n = (flow.get("ingesta_ok") || 0) + 1;
flow.set("ingesta_ok", n);
node.status({ fill: "green", shape: "dot",
              text: `#${n} lat ${msg.latencia_ms} ms  ${cuerpo.temperatura_C}C ${cuerpo.vibracion_mm_s}mm/s` });

return [msg, null];
