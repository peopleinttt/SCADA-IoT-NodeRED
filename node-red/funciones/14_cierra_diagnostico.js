/* Nodo: "cierra diagnostico" — confirma la escritura y deja rastro medible. */
const ok = msg.statusCode >= 200 && msg.statusCode < 300;
const d  = msg.registro_diag || {};

if (!ok) {
    node.error(`no se pudo guardar el diagnostico: HTTP ${msg.statusCode} ` +
               JSON.stringify(msg.payload).slice(0, 200), msg);
    node.status({ fill: "red", shape: "dot", text: `guardado ${msg.statusCode}` });
} else {
    node.status({ fill: "green", shape: "dot",
                  text: `${(msg.payload && msg.payload.name) || "ok"} · ${d.latencia_ms} ms` });
}

const dir  = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
const zona = env.get("TZ_REPORTE") || "America/Mexico_City";
const dia  = new Intl.DateTimeFormat("en-CA", { timeZone: zona, year: "numeric",
                                                month: "2-digit", day: "2-digit" }).format(new Date());
msg.filename = `${dir}/diagnosticos_${dia}.csv`;

const u = msg.uso || {};
const linea = [
    (msg.payload && msg.payload.name) || "",
    d.ts || "",
    d.modelo || "",
    d.latencia_ms != null ? d.latencia_ms : "",
    u.promptTokenCount || "",
    u.candidatesTokenCount || "",
    u.thoughtsTokenCount || "",
    u.totalTokenCount || "",
    (msg.diagnostico && msg.diagnostico.degradado) ? "degradado" : "estructurado",
    `"${String(d.accion_prescrita || "").replace(/"/g, "'")}"`
].join(";");

const ENC = "diagnostico_id;ts;modelo;latencia_ms;tokens_prompt;tokens_respuesta;" +
            "tokens_pensamiento;tokens_total;formato;accion_prescrita";
const marca = `hdrdiag_${dia}`;
if (!flow.get(marca)) { flow.set(marca, true); msg.payload = ENC + "\n" + linea; }
else { msg.payload = linea; }
return msg;
