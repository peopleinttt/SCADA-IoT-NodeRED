/* Nodo: "arma registro de proceso"  (A2-Nube)
 * ---------------------------------------------------------------
 * Dos entradas posibles:
 *   topic "paso_caja"  -> un registro por caja que sale del tramo (de A2-Planta)
 *   topic "latido"     -> reloj de 1 s; decide si toca latido:
 *       - linea en marcha: cada A2_LATIDO_S (60 s por omision);
 *       - linea fuera de marcha y el mismo estado_linea que el latido anterior:
 *         cada A2_LATIDO_REPOSO_S (900 s por omision);
 *       - estado_linea distinto del ultimo latido: latido inmediato (en el
 *         siguiente tic, a menos de 1 s del cambio).
 * Asi la base recibe una escritura por caja mas un latido por minuto con la
 * linea en marcha, y uno cada 15 min con ella detenida: del 24 oct al 8 nov,
 * con la linea detenida, quedaron 21688 latidos de 60 s en la base real (E2,
 * fase 3). Cada cambio de estado sigue dejando rastro al momento.
 *
 * ts_origen es el instante de la lectura Modbus en Node-RED: para una caja,
 * la lectura que vio el flanco de salida (o la confirmacion del rechazo);
 * para un latido, la ultima lectura buena. Si la planta lleva tiempo sin
 * comunicacion, el latido lo deja ver: ts_origen se queda atras.
 *
 * Nada se escribe sin A2_NUBE=1: hasta que Ari publique las reglas con la rama
 * proceso, cada escritura seria un 401 contra la base real.
 */
if (env.get("A2_NUBE") !== "1") {
    node.status({ fill: "grey", shape: "ring", text: "apagado (A2_NUBE distinto de 1)" });
    return null;
}
const R = global.get("a2_planta_resumen");
if (!R) {
    node.status({ fill: "grey", shape: "ring", text: "esperando a A2-Planta" });
    return null;
}
const estadoLinea = R.com === "ok" ? R.linea : R.com;

if (msg.topic === "latido") {
    const enMarcha = estadoLinea === "en_marcha";
    const periodoS = enMarcha ? Number(env.get("A2_LATIDO_S") || 60) : Number(env.get("A2_LATIDO_REPOSO_S") || 900);
    const periodoMs = Math.max(5, periodoS) * 1000;
    const ultimo = flow.get("ultimo_latido_ms") || 0;
    const cambio = flow.get("ultimo_latido_estado") !== estadoLinea;
    if (!cambio && Date.now() - ultimo < periodoMs) return null;
    flow.set("ultimo_latido_ms", Date.now());
    flow.set("ultimo_latido_estado", estadoLinea);
    msg.base = {
        tipo: "latido", caja: null,
        ts_origen: R.ts_ultima_lectura || new Date().toISOString(),
        vel_banda_V: R.vel_aplicada_V, peso_V: R.peso_V,
        cajas_acumuladas: R.cajas_acumuladas, estado_linea: estadoLinea
    };
    return msg;
}

if (msg.topic === "paso_caja" && msg.payload) {
    const p = msg.payload;
    msg.base = {
        tipo: "caja", caja: p.caja, destino: p.destino,
        ts_origen: p.ts_salida,
        vel_banda_V: p.vel_banda_V, peso_V: p.peso_V === null ? 0 : p.peso_V,
        caja_masa_kg: p.masa_kg,
        cajas_acumuladas: p.cajas_acumuladas, estado_linea: estadoLinea
    };
    return msg;
}
return null;
