/* Nodo: "guarda y separa"  (A2 · Materiales, paso M2; libs: fs)
 * ---------------------------------------------------------------
 * Recibe lo que regresa el modelo (39_mat_modelo.js):
 *   topic "carga"    respuesta a "valida"  -> a 40 como "validada"
 *   topic "inicial"  estado inicial        -> se guarda; a 40 "siguiente"
 *   topic "paso"     estado nuevo y resultado por laminado
 *
 * Por cada paso con peso escribe DOS archivos por separado, una linea por
 * paso y laminado:
 *   $DATOS_DIR/a2_materiales_medido.jsonl  lo que un sistema real mediria
 *       ts_salida, caja, pieza, peso_V, peso_estable, f, sigma_max_MPa,
 *       delta_sigma_MPa, deformacion_ue, paso
 *   $DATOS_DIR/a2_materiales_verdad.jsonl  la verdad del modelo
 *       ts_salida, caja, pieza, peso_V, peso_modelo_V, ajustado, region, N_usado,
 *       dD, D, d, nivel, paso   (peso_modelo_V y ajustado: ajuste al nivel, paso R)
 * D es el valor despues del paso; d = d(D). La galga uso D antes del paso.
 * Un paso sin peso no deja lineas: solo cuenta en sin_peso.
 *
 * El estado ($DATOS_DIR/a2_materiales_estado.json) se escribe de forma
 * atomica (archivo temporal y rename) cada vez que cambia.
 *
 * SEPARACION. La verdad (region, N, dD, D, d, nivel) vive solo en el contexto
 * flow de esta pestana y en su archivo. Al contexto global va solo lo medido
 * (global.a2_mat_medido: ultimos 30 pasos por laminado y conteos de pasos). A
 * la HMI llega por el enlace de esta pestana (42_mat_hmi.js), no por global.
 * Salidas: 0 -> tarjeta de la HMI (42); 1 -> de vuelta a 40 (siguiente / validada)
 */
const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
const rutaEstado = `${dir}/a2_materiales_estado.json`;
const ULTIMOS = 30;

function guardaEstado(estado) {
    fs.mkdirSync(dir, { recursive: true });
    const tmp = `${rutaEstado}.tmp-${Date.now()}`;
    fs.writeFileSync(tmp, JSON.stringify(estado));
    fs.renameSync(tmp, rutaEstado);
    flow.set("mat_estado", estado);
}

if (msg.topic === "carga") return [null, { topic: "validada", payload: msg.payload }];

if (msg.topic === "inicial") {
    guardaEstado(msg.estado);
    flow.set("mat_listo", true);
    node.status({ fill: "green", shape: "dot", text: "estado inicial guardado (D = 0)" });
    return [{ topic: "hmi", hmi_aviso: true }, { topic: "siguiente" }];
}

if (msg.topic !== "paso") return null;
const c = msg.caja || {};
const estado = msg.estado;
try {
    if (!msg.sin_peso) {
        const medido = [], verdad = [];
        for (const r of msg.resultado) {
            medido.push({ ts_salida: c.ts_salida, caja: c.caja, pieza: r.pieza, peso_V: c.peso_V,
                          peso_estable: c.peso_estable, f: r.f, sigma_max_MPa: r.sigma_max_MPa,
                          delta_sigma_MPa: r.delta_sigma_MPa, deformacion_ue: r.deformacion_ue, paso: estado.pasos });
            verdad.push({ ts_salida: c.ts_salida, caja: c.caja, pieza: r.pieza, peso_V: r.peso_V,
                          peso_modelo_V: r.peso_modelo_V, ajustado: r.ajustado, region: r.region, N_usado: r.N_usado,
                          dD: r.dD, D: r.D, d: r.d, nivel: r.nivel, paso: estado.pasos });
        }
        fs.mkdirSync(dir, { recursive: true });
        fs.appendFileSync(`${dir}/a2_materiales_medido.jsonl`, medido.map(x => JSON.stringify(x)).join("\n") + "\n");
        fs.appendFileSync(`${dir}/a2_materiales_verdad.jsonl`, verdad.map(x => JSON.stringify(x)).join("\n") + "\n");

        // Lo medido, al contexto global (sin un solo campo de la verdad).
        const G = global.get("a2_mat_medido") || { laminados: {} };
        for (const m of medido) {
            const l = G.laminados[m.pieza] || [];
            l.push(m);
            while (l.length > ULTIMOS) l.shift();
            G.laminados[m.pieza] = l;
        }
        G.pasos = estado.pasos;
        G.sin_peso = estado.sin_peso;
        global.set("a2_mat_medido", G);

        // Para la tarjeta de la HMI (contexto flow de esta pestana).
        const H = flow.get("mat_hmi") || { evaluados: 0, primer_ts: null, ultimo_ts: null, piezas: {} };
        H.evaluados += 1;
        H.primer_ts = H.primer_ts || c.ts_salida;
        H.ultimo_ts = c.ts_salida;
        msg.resultado.forEach(r => {
            const P = H.piezas[r.pieza] || { con_danio: 0, cambios: [], alertas: 0 };
            P.ultimo_rango_ue = r.deformacion_ue;
            if (r.dD > 0) P.con_danio += 1;
            if (r.alerta) { P.alertas += 1; P.ultima_alerta = { alerta: r.alerta, paso: estado.pasos, ts: c.ts_salida }; }
            if (r.cambio_nivel) P.cambios.push({ nivel: r.nivel, paso: estado.pasos, ts: c.ts_salida });
            H.piezas[r.pieza] = P;
        });
        flow.set("mat_hmi", H);
    }
    guardaEstado(estado);
} catch (e) {
    flow.set("mat_bloqueo", "no se pudo escribir: " + e.message);
    node.error("capa de materiales: " + e.message);
    node.status({ fill: "red", shape: "dot", text: "NO acumula: no se pudo escribir" });
    flow.set("mat_ocupado", false);
    return [{ topic: "hmi", hmi_aviso: true }, null];
}
flow.set("mat_ocupado", false);
node.status({ fill: "green", shape: "dot", text: `paso ${estado.pasos}: ` +
              estado.laminados.map(L => `${L.id} D=${L.D.toFixed(4)} ${L.nivel}`).join(", ") });
return [{ topic: "hmi", hmi_aviso: true }, { topic: "siguiente" }];
