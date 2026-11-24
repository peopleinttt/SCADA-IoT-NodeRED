/* Nodo: "parsea respuesta de Gemini"  (2 salidas: 0 = ok, 1 = error)
 * ---------------------------------------------------------------
 * El nodo HTTP Request esta en modo texto a proposito: aqui se hace el
 * JSON.parse explicito para poder distinguir "la API contesto otra cosa"
 * de "la API contesto bien pero el contenido no sirve".
 */
const latencia_ms = msg.t0 ? Date.now() - msg.t0 : null;
msg.latencia_ms = latencia_ms;

function falla(motivo, detalle, pausaS) {
    if (pausaS) {
        flow.set("gemini_pausa_hasta", Date.now() + pausaS * 1000);
        flow.set("gemini_fallos", (flow.get("gemini_fallos") || 0) + 1);
    }
    node.error(`Gemini [${motivo}] ${detalle}`, msg);
    node.status({ fill: "red", shape: "dot", text: motivo });
    msg.payload = { ok: false, motivo, detalle, latencia_ms };
    return [null, msg];
}

// ---- 1. estado HTTP ------------------------------------------------------
const codigo = msg.statusCode;
const cuerpoTexto = typeof msg.payload === "string" ? msg.payload : JSON.stringify(msg.payload);

if (codigo === 429) {
    // Cuota agotada o demasiadas peticiones. Retroceso exponencial acotado.
    const fallos = (flow.get("gemini_fallos") || 0) + 1;
    const espera = Math.min(60 * Math.pow(2, fallos - 1), 900);   // 60 s .. 15 min
    let sugerencia = "";
    try {
        const e = JSON.parse(cuerpoTexto);
        const det = (e.error && e.error.details) || [];
        const retry = det.find(d => (d["@type"] || "").includes("RetryInfo"));
        if (retry && retry.retryDelay) sugerencia = ` (la API sugiere ${retry.retryDelay})`;
        const cuota = det.find(d => (d["@type"] || "").includes("QuotaFailure"));
        if (cuota) sugerencia += ` cuota: ${JSON.stringify(cuota.violations || cuota).slice(0, 180)}`;
    } catch (e) { /* el cuerpo del 429 tampoco era JSON: no importa */ }
    return falla("cuota_agotada",
                 `HTTP 429${sugerencia}. Pausa ${espera} s. Revisa el limite del ` +
                 `nivel gratuito en aistudio.google.com/rate-limit`, espera);
}
if (codigo === 503 || codigo === 500) {
    return falla("modelo_sobrecargado", `HTTP ${codigo}: ${cuerpoTexto.slice(0, 200)}`, 120);
}
if (codigo === 403) {
    return falla("acceso_denegado",
                 `HTTP 403: llave invalida o API Generative Language sin habilitar. ` +
                 cuerpoTexto.slice(0, 200), 300);
}
if (codigo === 400) {
    return falla("peticion_invalida",
                 `HTTP 400: ${cuerpoTexto.slice(0, 300)} (modelo inexistente, ` +
                 `responseSchema mal formado o thinkingConfig no soportado)`, 60);
}
if (codigo !== 200) {
    return falla("http_inesperado", `HTTP ${codigo}: ${cuerpoTexto.slice(0, 200)}`, 60);
}

// ---- 2. sobre JSON de la API --------------------------------------------
let raiz;
try {
    raiz = JSON.parse(cuerpoTexto);
} catch (e) {
    return falla("respuesta_no_json",
                 `JSON.parse fallo: ${e.message}. Primeros 200 caracteres: ` +
                 cuerpoTexto.slice(0, 200), 60);
}

if (raiz.promptFeedback && raiz.promptFeedback.blockReason) {
    return falla("prompt_bloqueado", `blockReason=${raiz.promptFeedback.blockReason}`, 0);
}
const cand = Array.isArray(raiz.candidates) ? raiz.candidates[0] : null;
if (!cand) {
    return falla("sin_candidatos", JSON.stringify(raiz).slice(0, 250), 0);
}
if (cand.finishReason && cand.finishReason !== "STOP") {
    // MAX_TOKENS es el caso tipico: el modelo se quedo sin presupuesto y el
    // texto llega truncado o vacio. Subir GEMINI_MAX_TOKENS o apagar thinking.
    return falla("generacion_incompleta",
                 `finishReason=${cand.finishReason}. Tokens: ` +
                 JSON.stringify(raiz.usageMetadata || {}), 0);
}

const partes = cand.content && cand.content.parts;
const texto = Array.isArray(partes) ? partes.map(p => p.text || "").join("").trim() : "";
if (!texto) {
    return falla("sin_texto", JSON.stringify(cand).slice(0, 250), 0);
}

// ---- 3. contenido: se pidio JSON, pero se acepta texto suelto ------------
let diag = null;
try {
    diag = JSON.parse(texto);
} catch (e) {
    const cerca = texto.match(/\{[\s\S]*\}/);          // por si vino en ```json
    if (cerca) { try { diag = JSON.parse(cerca[0]); } catch (e2) { diag = null; } }
}

let texto_diagnostico, accion_prescrita, degradado = false;
if (diag && typeof diag === "object" && diag.texto_diagnostico) {
    texto_diagnostico = String(diag.texto_diagnostico).trim();
    accion_prescrita  = String(diag.accion_prescrita || "").trim() || "revisar_manualmente";
} else {
    // Modo degradado: guardamos el texto tal cual y marcamos que no vino
    // estructurado, en vez de descartar un diagnostico que si tiene contenido.
    degradado = true;
    texto_diagnostico = texto.slice(0, 600);
    const m = texto.match(/acci[oó]n[^:]*:\s*(.+)/i);
    accion_prescrita = m ? m[1].split("\n")[0].trim().slice(0, 120) : "revisar_manualmente";
    node.warn("la respuesta no era JSON valido: se guarda en modo degradado");
}

flow.set("gemini_fallos", 0);                            // cadena sana otra vez
msg.diagnostico = {
    texto_diagnostico: texto_diagnostico,
    accion_prescrita: accion_prescrita,
    modelo: raiz.modelVersion || msg.modelo || "desconocido",
    latencia_ms: latencia_ms,
    degradado: degradado
};
msg.uso = raiz.usageMetadata || {};
node.status({ fill: "green", shape: "dot",
              text: `${latencia_ms} ms · ${(msg.uso.totalTokenCount || "?")} tokens` });
return [msg, null];
