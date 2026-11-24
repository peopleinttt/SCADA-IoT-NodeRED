/* Nodo: "resume estado y arma prompt"  (2 salidas: 0 = consultar, 1 = omitido)
 * ---------------------------------------------------------------
 * Tres frenos de consumo, en este orden:
 *   1. tope diario de consultas (cuota gratuita),
 *   2. omitir si el estado no cambio respecto de la consulta anterior,
 *   3. recorte duro de la longitud del prompt.
 */
const MAX_DIA      = Number(env.get("DIAG_MAX_DIA") || 200);
const MAX_CARACT   = Number(env.get("DIAG_MAX_CARACTERES") || 1800);
const UMBRAL_TEMP  = Number(env.get("UMBRAL_TEMP_C") || 75);
const UMBRAL_VIB   = Number(env.get("UMBRAL_VIB_MM_S") || 7.1);   // ISO 10816 zona C
const zona         = env.get("TZ_REPORTE") || "America/Mexico_City";

function omite(motivo, detalle) {
    node.status({ fill: "grey", shape: "ring", text: motivo });
    msg.payload = { omitido: true, motivo: motivo, detalle: detalle || "" };
    return [null, msg];
}

if (msg.statusCode !== undefined && msg.statusCode !== 200) {
    node.error(`lectura de telemetria fallida: HTTP ${msg.statusCode} ` +
               `${JSON.stringify(msg.payload).slice(0, 200)}`, msg);
    return omite("lectura_fallida", `HTTP ${msg.statusCode}`);
}

const crudo = msg.payload;
if (!crudo || typeof crudo !== "object") return omite("sin_datos", "la rama telemetria esta vacia");

// El objeto viene indexado por registroId; las claves push son ordenables
// lexicograficamente y ese orden es el cronologico de escritura.
const filas = Object.keys(crudo).sort().map(k => Object.assign({ registroId: k }, crudo[k]))
    .filter(f => f && typeof f.temperatura_C === "number" &&
                      typeof f.vibracion_mm_s === "number" && f.ts_origen);
if (filas.length < 2) return omite("muestras_insuficientes", `${filas.length} filas utiles`);

// ---- estadisticos de la ventana -----------------------------------------
const temps = filas.map(f => f.temperatura_C);
const vibs  = filas.map(f => f.vibracion_mm_s);
const prom  = a => a.reduce((s, x) => s + x, 0) / a.length;
const fmt   = x => Number(x).toFixed(2);

// Pendiente por minimos cuadrados sobre el tiempo real, en unidades por minuto.
function pendientePorMinuto(valores, tiemposMs) {
    const t0 = tiemposMs[0];
    const x = tiemposMs.map(t => (t - t0) / 60000);
    const mx = prom(x), my = prom(valores);
    let num = 0, den = 0;
    for (let i = 0; i < x.length; i++) { num += (x[i] - mx) * (valores[i] - my); den += (x[i] - mx) ** 2; }
    return den === 0 ? 0 : num / den;
}
const tiempos = filas.map(f => Date.parse(f.ts_origen));
const dTemp = pendientePorMinuto(temps, tiempos);
const dVib  = pendientePorMinuto(vibs, tiempos);

const ventanaS = (tiempos[tiempos.length - 1] - tiempos[0]) / 1000;
const ciclosIni = filas[0].ciclos_acumulados, ciclosFin = filas[filas.length - 1].ciclos_acumulados;

const resumen =
    `n=${filas.length} muestras en ${fmt(ventanaS)} s | ` +
    `temp actual ${fmt(temps[temps.length - 1])} C (min ${fmt(Math.min(...temps))}, ` +
    `prom ${fmt(prom(temps))}, max ${fmt(Math.max(...temps))}, tendencia ${fmt(dTemp)} C/min) | ` +
    `vibracion actual ${fmt(vibs[vibs.length - 1])} mm/s RMS (min ${fmt(Math.min(...vibs))}, ` +
    `prom ${fmt(prom(vibs))}, max ${fmt(Math.max(...vibs))}, tendencia ${fmt(dVib)} mm/s/min) | ` +
    `ciclos ${ciclosIni} -> ${ciclosFin} (+${ciclosFin - ciclosIni}) | ` +
    `umbrales: temp ${UMBRAL_TEMP} C, vibracion ${UMBRAL_VIB} mm/s`;

// ---- freno 1: tope diario ------------------------------------------------
const hoy = new Intl.DateTimeFormat("en-CA", { timeZone: zona, year: "numeric",
                                               month: "2-digit", day: "2-digit" }).format(new Date());
if (flow.get("diag_dia") !== hoy) { flow.set("diag_dia", hoy); flow.set("diag_conteo", 0); }
const usadas = flow.get("diag_conteo") || 0;
if (usadas >= MAX_DIA) {
    node.warn(`tope diario alcanzado (${usadas}/${MAX_DIA}): no se consulta a Gemini`);
    return omite("tope_diario", `${usadas}/${MAX_DIA}`);
}

// ---- freno 2: estado sin cambios ----------------------------------------
// Se compara el estado redondeado, no el resumen completo: asi el ruido de
// centesimas no dispara consultas, pero un cambio real si.
const huella = [
    Math.round(temps[temps.length - 1]),
    Math.round(vibs[vibs.length - 1] * 2) / 2,
    temps[temps.length - 1] >= UMBRAL_TEMP,
    vibs[vibs.length - 1] >= UMBRAL_VIB,
    ciclosFin
].join("|");
const MIN_ENTRE_IGUALES_MS = Number(env.get("DIAG_MIN_REPETIR_MIN") || 30) * 60000;
if (flow.get("diag_huella") === huella &&
    Date.now() - (flow.get("diag_ultimo_ms") || 0) < MIN_ENTRE_IGUALES_MS) {
    return omite("estado_sin_cambio", huella);
}

// ---- prompt --------------------------------------------------------------
const historial = filas.slice(-Math.min(filas.length, 12))
    .map(f => `${f.ts_origen};${fmt(f.temperatura_C)};${fmt(f.vibracion_mm_s)};${f.ciclos_acumulados}`)
    .join("\n");

let texto =
`Eres un ingeniero de mantenimiento predictivo. Analiza la telemetria de la maquina ${env.get("PLANTA_ID") || "planta_01"} y responde SOLO con JSON.

Umbrales de operacion: temperatura de alarma ${UMBRAL_TEMP} C; vibracion de alarma ${UMBRAL_VIB} mm/s RMS (ISO 10816, frontera zona B/C para maquina clase II).

Resumen del estado actual:
${resumen}

Historial reciente (ts_origen;temperatura_C;vibracion_mm_s;ciclos_acumulados):
${historial}

Devuelve un objeto JSON con exactamente estas dos llaves:
"texto_diagnostico": maximo 60 palabras, en espanol, explicando el estado y el modo de falla mas probable; cita los numeros que lo sustentan.
"accion_prescrita": una sola instruccion accionable, en imperativo, maximo 15 palabras.
No inventes datos que no esten arriba. Si la evidencia no alcanza para concluir, dilo en texto_diagnostico y prescribe seguir midiendo.`;

if (texto.length > MAX_CARACT) {
    // Recorte duro: se sacrifica historial, nunca el resumen ni las instrucciones.
    const sobra = texto.length - MAX_CARACT;
    const historialCorto = historial.slice(sobra + 40);
    texto = texto.replace(historial, "…(recortado)\n" + historialCorto);
    node.warn(`prompt recortado a ${texto.length} caracteres`);
}

// ---- cuerpo de la peticion ----------------------------------------------
const modelo = env.get("GEMINI_MODEL") || "gemini-2.5-flash";
msg.modelo = modelo;
msg.resumen_entrada = resumen;
msg.huella = huella;
const baseGemini = (env.get("GEMINI_BASE_URL") || "https://generativelanguage.googleapis.com").replace(/\/+$/, "");
msg.url = `${baseGemini}/v1beta/models/${modelo}:generateContent`;
msg.headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": env.get("GEMINI_API_KEY") || ""
};
msg.payload = {
    contents: [{ parts: [{ text: texto }] }],
    generationConfig: {
        temperature: 0.2,
        maxOutputTokens: Number(env.get("GEMINI_MAX_TOKENS") || 512),
        responseMimeType: "application/json",
        responseSchema: {
            type: "OBJECT",
            properties: {
                texto_diagnostico: { type: "STRING" },
                accion_prescrita:  { type: "STRING" }
            },
            required: ["texto_diagnostico", "accion_prescrita"]
        }
    }
};
// thinkingBudget solo aplica a los modelos 2.5 con razonamiento. Se manda
// unicamente si esta configurado, para no romper con otros modelos.
const presupuesto = env.get("GEMINI_THINKING_BUDGET");
if (presupuesto !== undefined && presupuesto !== "") {
    msg.payload.generationConfig.thinkingConfig = { thinkingBudget: Number(presupuesto) };
}

// MEDIDO el 2026-08-25 contra la API real: con el razonamiento encendido, los
// tokens de pensamiento salen del MISMO presupuesto de maxOutputTokens. Con
// tope 512 el modelo gasto ~490 pensando y devolvio JSON truncado con
// finishReason MAX_TOKENS en los tres casos ambiguos que se probaron. O se
// apaga el razonamiento, o el tope sube a 2048. Ver docs/medicion_thinking.md
const razonando = (presupuesto === undefined || presupuesto === "" || Number(presupuesto) > 0);
const tope = Number(env.get("GEMINI_MAX_TOKENS") || 512);
if (razonando && tope < 1500) {
    node.warn(`GEMINI_MAX_TOKENS=${tope} con razonamiento encendido: el modelo ` +
              `va a gastar el presupuesto pensando y devolver texto truncado. ` +
              `Pon GEMINI_THINKING_BUDGET=0 o sube el tope a 2048.`);
}

if (!msg.headers["x-goog-api-key"]) {
    node.error("GEMINI_API_KEY no esta definida", msg);
    return omite("sin_api_key", "define GEMINI_API_KEY");
}

msg.t0 = Date.now();
flow.set("diag_conteo", usadas + 1);
flow.set("diag_huella", huella);
flow.set("diag_ultimo_ms", Date.now());
node.status({ fill: "blue", shape: "dot",
              text: `consulta ${usadas + 1}/${MAX_DIA} · ${texto.length} car` });
return [msg, null];
