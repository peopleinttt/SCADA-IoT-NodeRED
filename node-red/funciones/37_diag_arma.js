/* Nodo: "arma consulta de diagnostico"  (A2-Diagnostico, 2 salidas: 0 = consultar, 1 = omitido)
 * ---------------------------------------------------------------
 * Disparo: bajo demanda desde la HMI (topic "diagnostico") o periodico
 * (inject cada A2_DIAG_PERIODO_MIN, 60 por omision) y este ultimo SOLO con la
 * linea en marcha. El diagnostico es un consejo: nada aqui mueve la planta.
 *
 * Frenos de cuota, los de la Actividad 1 (docs/BITACORA.md 3.2 y 3.3):
 *   - tope diario propio, A2_DIAG_MAX_DIA (15): la cuota gratuita es de 20
 *     peticiones por dia y por modelo, y la comparte con la pestana de la A1;
 *   - limitador de 1 por minuto (nodo delay detras de este);
 *   - maxOutputTokens 2048 y thinkingBudget 0: con 512 el razonamiento se
 *     comia el presupuesto y la respuesta llegaba truncada (hallazgo 3.2).
 * El prompt y la respuesta van en ingles (se ven en el video).
 */
const P = global.get("a2_planta_resumen");
function omite(motivo, detalle) {
    node.status({ fill: "grey", shape: "ring", text: motivo });
    msg.payload = { omitido: true, motivo: motivo, detalle: detalle || "" };
    return [null, msg];
}
if (!P) return omite("sin_planta", "A2-Planta no ha publicado su resumen");
const periodico = msg.topic !== "diagnostico";
if (periodico && P.linea !== "en_marcha") return omite("linea_detenida", "el disparo periodico solo corre con la linea en marcha");

const zona = env.get("TZ_REPORTE") || "America/Mexico_City";
const hoy = new Intl.DateTimeFormat("en-CA", { timeZone: zona, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
if (flow.get("dia") !== hoy) { flow.set("dia", hoy); flow.set("conteo", 0); }
const tope = Number(env.get("A2_DIAG_MAX_DIA") || 15);
const usadas = flow.get("conteo") || 0;
if (usadas >= tope) return omite("tope_diario", `${usadas}/${tope}`);
const clave = env.get("GEMINI_API_KEY") || "";
if (!clave) return omite("sin_api_key", "define GEMINI_API_KEY");

// ---- estado de la planta para el prompt -----------------------------------------------
const masas = (P.ultimas_masas || []).map(x => x.kg).filter(x => typeof x === "number");
const prom = a => a.length ? a.reduce((s, x) => s + x, 0) / a.length : null;
const sd = a => { const m = prom(a); return a.length > 1 ? Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1)) : 0; };
const fija = !P.banda_variable;
const k = P.contadores || {};
const estado = {
    actuator: P.actuador === "desviador" ? "3-way wheel diverter sorting by weight" : "reject pusher",
    line: P.linea === "en_marcha" ? "running" : P.linea === "emergencia" ? "emergency_stop" : "stopped", communication: P.com,
    running_time_s: P.en_marcha_s || 0, boxes_per_minute: P.cajas_por_minuto || 0,
    boxes_sorted: P.cajas_acumuladas || 0, boxes_lost: (k.perdidas || 0) + (k.perdidas_desconexion || 0),
    misrouted: k.desvios_erroneos || 0, by_destination: k.por_destino || {},
    last_masses_kg: masas.slice(-12),
    mass_mean_kg: masas.length ? Math.round(prom(masas) * 100) / 100 : null,
    mass_sd_kg: masas.length ? Math.round(sd(masas) * 100) / 100 : null,
    belt: fija ? "fixed speed" : `variable, applied ${P.vel_aplicada_V} V (allowed ${P.limites.vel_min_V}-${P.limites.vel_max_V} V)`,
    timing_limits_feasible: !!(P.limites && P.limites.factible)
};
const tele = global.get("a2_esp32_ultima");
if (tele) estado.esp32_activity1 = tele;

const acciones = fija ? ["mantener", "detener_y_programar_mantenimiento"]
                      : ["mantener", "reducir_velocidad", "detener_y_programar_mantenimiento"];
const texto =
`You are a maintenance engineer for a weight-sorting conveyor station. Answer ONLY with JSON.
Plant state (JSON): ${JSON.stringify(estado)}
Return an object with exactly these keys:
"texto_diagnostico": in English, at most 60 words, the state and the most likely issue, citing the numbers.
"nivel_estimado": one of "normal", "preventiva", "critica".
"accion_codigo": one of ${acciones.map(a => `"${a}"`).join(", ")}.${fija ? " The belts run at fixed speed: do not suggest changing speed." : ""}
${fija ? "" : '"valor_pct": integer 0 to 30, ONLY when accion_codigo is "reducir_velocidad" (omit it otherwise).\n'}"justificacion": in English, at most 30 words.
This is advice only; it never moves the plant. Do not invent data that is not above.`;

const modelo = env.get("GEMINI_MODEL") || "gemini-2.5-flash";
const propiedades = {
    texto_diagnostico: { type: "STRING" },
    nivel_estimado: { type: "STRING", enum: ["normal", "preventiva", "critica"] },
    accion_codigo: { type: "STRING", enum: acciones },
    justificacion: { type: "STRING" }
};
if (!fija) propiedades.valor_pct = { type: "INTEGER" };
msg.url = `${(env.get("GEMINI_BASE_URL") || "https://generativelanguage.googleapis.com").replace(/\/+$/, "")}/v1beta/models/${modelo}:generateContent`;
msg.headers = { "Content-Type": "application/json", "x-goog-api-key": clave };
msg.payload = {
    contents: [{ parts: [{ text: texto }] }],
    generationConfig: {
        temperature: 0.2, maxOutputTokens: 2048, responseMimeType: "application/json",
        responseSchema: { type: "OBJECT", properties: propiedades,
                          required: ["texto_diagnostico", "nivel_estimado", "accion_codigo", "justificacion"] },
        thinkingConfig: { thinkingBudget: 0 }
    }
};
msg.diag = { modelo: modelo, fija: fija, acciones: acciones, origen: periodico ? "periodico" : "hmi",
             t0: Date.now(), estado: estado };
flow.set("conteo", usadas + 1);
node.status({ fill: "blue", shape: "dot", text: `consulta ${usadas + 1}/${tope} (${msg.diag.origen})` });
return [msg, null];
