/* Nodo: "entrada de materiales"  (A2 · Materiales, paso M2; libs: fs)
 * ---------------------------------------------------------------
 * Entradas:
 *   topic "arranque"   inject al iniciar: carga configuracion y estado
 *   topic "paso_caja"  enlace a2_paso_caja de A2-Planta (segundo destino)
 *   topic "validada"   de 41_mat_salida: respuesta del modelo a "valida"
 *   topic "siguiente"  de 41_mat_salida: el paso anterior (o el estado inicial) ya se guardo
 * Salidas: 0 -> modelo (39_mat_modelo.js); 1 -> tarjeta de la HMI (42_mat_hmi.js)
 *
 * Sin A2_MATERIALES=1 no hace nada: no lee ni crea archivos, no manda nada.
 *
 * Configuracion: A2_MAT_CONFIG (arranca.sh pone config/materiales.json). Se
 * valida con el mismo modelo (39_mat_modelo.js, accion "valida") antes de usarla.
 *
 * Estado: $DATOS_DIR/a2_materiales_estado.json. D es vida consumida: al
 * arrancar se carga, no se reinicia con Node-RED. Si el archivo existe y no se
 * puede leer o no corresponde a la configuracion, la pestana NO acumula y lo
 * dice (estado del nodo y tarjeta de la HMI). No reinicia en silencio. Lo
 * mismo si el estado es de otra version de configuracion (cfg_version, paso R).
 *
 * Un paso a la vez: mientras un paso va por el modelo y la escritura, los que
 * llegan esperan en una cola (flow.mat_cola). Asi el estado que entra al
 * modelo siempre es el que dejo el paso anterior.
 */
if (env.get("A2_MATERIALES") !== "1") {
    node.status({ fill: "grey", shape: "ring", text: "apagado (A2_MATERIALES distinto de 1)" });
    return null;
}
const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
const rutaEstado = `${dir}/a2_materiales_estado.json`;

function bloquea(motivo) {
    flow.set("mat_bloqueo", motivo);
    node.status({ fill: "red", shape: "dot", text: "NO acumula: " + motivo });
    node.error("capa de materiales: no acumula (" + motivo + ")");
    return { topic: "hmi", hmi_aviso: true };
}

// Un paso a la vez: toma el siguiente de la cola si nada va en vuelo.
function despacha(extraHmi) {
    const cola = flow.get("mat_cola") || [];
    if (!flow.get("mat_listo") || flow.get("mat_ocupado") || cola.length === 0) return extraHmi ? [null, extraHmi] : null;
    const p = cola.shift();
    flow.set("mat_cola", cola);
    flow.set("mat_ocupado", true);
    return [{ topic: "paso", accion: "paso", cfg: flow.get("mat_cfg"), estado: flow.get("mat_estado"),
              paso: { peso_V: p.peso_V }, caja: p }, extraHmi || null];
}

// ---- carga (al arrancar, o al primer mensaje si el inject todavia no llego) -------
if (!flow.get("mat_cargado")) {
    flow.set("mat_cargado", true);
    flow.set("mat_cola", msg.topic === "paso_caja" && msg.payload ? [msg.payload] : []);
    flow.set("mat_ocupado", false);
    const rutaCfg = env.get("A2_MAT_CONFIG");
    let cfg = null;
    try {
        if (!rutaCfg) throw new Error("falta A2_MAT_CONFIG");
        cfg = JSON.parse(fs.readFileSync(rutaCfg, "utf8"));
    } catch (e) {
        return [null, bloquea("configuracion ilegible: " + e.message)];
    }
    flow.set("mat_cfg", cfg);
    node.status({ fill: "blue", shape: "ring", text: "validando configuracion" });
    // La validacion la hace el modelo; su respuesta vuelve por 41 con topic "validada".
    return [{ topic: "carga", accion: "valida", cfg: cfg }, null];
}

if (flow.get("mat_bloqueo")) {
    if (msg.topic === "paso_caja") node.status({ fill: "red", shape: "dot", text: "NO acumula: " + flow.get("mat_bloqueo") });
    return null;
}

if (msg.topic === "validada") {
    const cfg = flow.get("mat_cfg");
    if (!msg.payload || !msg.payload.ok) {
        return [null, bloquea("configuracion invalida: " + (msg.payload ? msg.payload.errores.map(e => e.codigo + " " + e.ruta).join(", ") : "?"))];
    }
    if (!fs.existsSync(rutaEstado)) {
        // Primera vez: estado inicial del modelo; 41 lo guarda y avisa con "siguiente".
        return [{ topic: "inicial", accion: "inicial", cfg: cfg }, null];
    }
    let estado = null;
    try {
        estado = JSON.parse(fs.readFileSync(rutaEstado, "utf8"));
    } catch (e) {
        return [null, bloquea("archivo de estado ilegible: " + e.message)];
    }
    // Paso R (fase 3): un estado de otra version de la configuracion no se continua.
    if (estado && estado.cfg_version !== cfg.version) {
        return [null, bloquea("archivo de estado de otra version de configuracion: estado " +
                              estado.cfg_version + ", configuracion " + cfg.version)];
    }
    try {
        const ids = cfg.laminados.map(L => L.id).join(",");
        if (!estado || estado.version !== 1 || !Array.isArray(estado.laminados) ||
            estado.laminados.map(L => L.id).join(",") !== ids ||
            !estado.laminados.every(L => typeof L.D === "number" && L.D >= 0 && Number.isInteger(L.rng) && L.conteos) ||
            !Number.isInteger(estado.pasos)) {
            throw new Error("no corresponde a la configuracion (" + ids + ")");
        }
    } catch (e) {
        return [null, bloquea("archivo de estado ilegible: " + e.message)];
    }
    node.status({ fill: "green", shape: "dot", text: `estado cargado: ${estado.pasos} pasos, ` +
                  estado.laminados.map(L => `${L.id} D=${L.D.toFixed(4)}`).join(", ") });
    flow.set("mat_estado", estado);
    flow.set("mat_listo", true);
    return despacha({ topic: "hmi", hmi_aviso: true });
}

if (msg.topic === "paso_caja" && msg.payload) {
    const cola = flow.get("mat_cola") || [];
    cola.push(msg.payload);
    flow.set("mat_cola", cola);
}
// "arranque" (ya cargado), "paso_caja" y "siguiente": despachar si se puede.
return despacha(null);
