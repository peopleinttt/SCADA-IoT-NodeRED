/* Nodo: "valida el diagnostico"  (A2-Diagnostico, 2 salidas: 0 = valido, 1 = fallo)
 * ---------------------------------------------------------------
 * Validacion ESTRICTA. Lo que no cumple se registra como fallo y no llega a
 * la HMI: global.a2_diag_ultimo solo cambia con un diagnostico valido.
 *   - HTTP 200, cuerpo JSON, candidato con finishReason STOP y texto;
 *   - el texto es JSON con exactamente texto_diagnostico, nivel_estimado,
 *     accion_codigo, justificacion y, solo con reducir_velocidad, valor_pct;
 *   - nivel en {normal, preventiva, critica}; accion en las ofrecidas (sin
 *     reducir_velocidad con banda fija); valor_pct entero de 0 a 30.
 * Sin modo degradado: en la Actividad 1 el texto suelto se guardaba igual; aqui
 * la orden pide que nada invalido llegue a la pantalla.
 */
const d = msg.diag || {};
const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
const zona = env.get("TZ_REPORTE") || "America/Mexico_City";
const dia = new Intl.DateTimeFormat("en-CA", { timeZone: zona, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
const latencia = d.t0 ? Date.now() - d.t0 : null;

function linea(resultado, motivo, x) {
    const marca = `hdr_${dia}`;
    const cab = flow.get(marca) ? "" : "ts;origen;modelo;latencia_ms;resultado;motivo;nivel;accion;valor_pct;tokens_total\n";
    flow.set(marca, true);
    return { filename: `${dir}/a2_diagnosticos_${dia}.csv`,
             payload: cab + [new Date().toISOString(), d.origen || "", d.modelo || "", latencia, resultado, motivo,
                             (x && x.nivel_estimado) || "", (x && x.accion_codigo) || "",
                             (x && x.valor_pct !== undefined) ? x.valor_pct : "", (msg.uso && msg.uso.totalTokenCount) || ""].join(";") };
}
function falla(motivo, detalle) {
    const k = (flow.get("fallos") || 0) + 1;
    flow.set("fallos", k);
    node.warn(`diagnostico invalido (${motivo}): ${detalle}`);
    node.status({ fill: "red", shape: "dot", text: `fallo ${motivo} (${k})` });
    return [null, linea("fallo", motivo, null)];
}

if (msg.statusCode !== 200) return falla(`http_${msg.statusCode}`, String(typeof msg.payload === "string" ? msg.payload : JSON.stringify(msg.payload)).slice(0, 200));
let raiz;
try { raiz = typeof msg.payload === "string" ? JSON.parse(msg.payload) : msg.payload; } catch (e) { return falla("respuesta_no_json", e.message); }
const cand = raiz && Array.isArray(raiz.candidates) ? raiz.candidates[0] : null;
if (!cand) return falla("sin_candidatos", JSON.stringify(raiz).slice(0, 200));
if (cand.finishReason && cand.finishReason !== "STOP") return falla("generacion_incompleta", cand.finishReason);
const texto = ((cand.content && cand.content.parts) || []).map(p => p.text || "").join("").trim();
if (!texto) return falla("sin_texto", "");
msg.uso = raiz.usageMetadata || {};
let x;
try { x = JSON.parse(texto); } catch (e) { return falla("contenido_no_json", texto.slice(0, 120)); }
if (!x || typeof x !== "object" || Array.isArray(x)) return falla("contenido_no_objeto", texto.slice(0, 120));

const base = ["texto_diagnostico", "nivel_estimado", "accion_codigo", "justificacion"];
const permitidas = base.concat(x.accion_codigo === "reducir_velocidad" ? ["valor_pct"] : []);
const faltan = base.filter(k => !(k in x)), sobran = Object.keys(x).filter(k => !permitidas.includes(k));
if (faltan.length) return falla("faltan_campos", faltan.join(","));
if (sobran.length) return falla("campos_no_esperados", sobran.join(","));
if (typeof x.texto_diagnostico !== "string" || !x.texto_diagnostico.trim() || x.texto_diagnostico.length > 800) return falla("texto_invalido", "");
if (typeof x.justificacion !== "string" || !x.justificacion.trim() || x.justificacion.length > 400) return falla("justificacion_invalida", "");
if (!["normal", "preventiva", "critica"].includes(x.nivel_estimado)) return falla("nivel_invalido", String(x.nivel_estimado));
if (!(d.acciones || []).includes(x.accion_codigo)) return falla("accion_invalida", `${x.accion_codigo} (ofrecidas: ${(d.acciones || []).join(",")})`);
if (x.accion_codigo === "reducir_velocidad" && !(Number.isInteger(x.valor_pct) && x.valor_pct >= 0 && x.valor_pct <= 30)) {
    return falla("valor_pct_invalido", String(x.valor_pct));
}

const ok = Object.assign({}, x, { ts: new Date().toISOString(), modelo: raiz.modelVersion || d.modelo, origen: d.origen,
                                  latencia_ms: latencia });
global.set("a2_diag_ultimo", ok);
node.status({ fill: "green", shape: "dot", text: `${x.nivel_estimado} · ${x.accion_codigo} · ${latencia} ms` });
return [{ payload: ok }, linea("valido", "", x)];
