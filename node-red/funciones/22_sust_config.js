/* Nodo: "carga configuracion e inicia"  (A2-Sustituto)
 * ---------------------------------------------------------------
 * Lee config/sustituto_a2.json, aplica A2_SUST_SEMILLA si viene en el entorno
 * y deja el estado inicial de la simulacion en flow.sust.
 *
 * Todo lo aleatorio sale de tres generadores con semilla, uno por fuente
 * (masas, intervalos de emision, ruido de la bascula). Separados a proposito:
 * si mañana se cambia el ruido, las masas y los intervalos no se recorren.
 */
function falla(detalle) {
    node.error(`configuracion del sustituto invalida (${env.get("A2_SUST_CONFIG")}): ${detalle}`, msg);
    node.status({ fill: "red", shape: "dot", text: "configuracion invalida" });
    return null;
}

let c;
try {
    c = JSON.parse(msg.payload);
} catch (e) {
    return falla(`JSON.parse: ${e.message}`);
}

const num = x => typeof x === "number" && Number.isFinite(x);
const g = c.geometria_m || {};
const escena = c.escena || "empujador";
let chequeos;
if (escena === "desviador") {
    // emisor < at_scale_entry < bascula[0] < bascula[1] < at_scale_exit < desviador;
    // en cada rama: confirmacion < fin_rama (distancias desde el desviador)
    const orden = [g.emisor, g.at_scale_entry, g.bascula && g.bascula[0], g.bascula && g.bascula[1],
                   g.at_scale_exit, g.desviador];
    if (!orden.every(num) || !num(g.confirmacion) || !num(g.fin_rama)) return falla("geometria_m incompleta (desviador)");
    for (let i = 1; i < orden.length; i++) {
        if (orden[i] <= orden[i - 1]) return falla("geometria_m fuera de orden: emisor < at_scale_entry < bascula < at_scale_exit < desviador");
    }
    if (!(g.confirmacion < g.fin_rama)) return falla("geometria_m: confirmacion < fin_rama");
    chequeos = [[c.velocidad_m_s > 0, "velocidad_m_s"], [!(c.refresco_s < 0), "refresco_s"]];
} else {
    const orden = [g.emisor, g.sens_entrada, g.bascula && g.bascula[0], g.bascula && g.bascula[1],
                   g.inicio_banda_variable, g.empujador, g.sens_salida, g.fin];
    if (!orden.every(num)) return falla("geometria_m incompleta");
    for (let i = 1; i < orden.length; i++) {
        // emisor < entrada < bascula[0] < bascula[1] <= inicio_variable <= empujador < salida < fin
        const igualPermitido = (i === 4 || i === 5);
        if (igualPermitido ? orden[i] < orden[i - 1] : orden[i] <= orden[i - 1]) {
            return falla("geometria_m fuera de orden: emisor < sens_entrada < bascula < " +
                         "inicio_banda_variable <= empujador < sens_salida < fin");
        }
    }
    chequeos = [[num(c.alimentacion_m_s), "alimentacion_m_s"], [num(c.k_banda_m_s_por_V), "k_banda_m_s_por_V"],
                [c.empujador && c.empujador.carrera_s > 0 && c.empujador.alcance > 0 && c.empujador.alcance <= 1, "empujador"]];
}
chequeos = chequeos.concat([
    [c.caja && c.caja.largo_m > 0, "caja.largo_m"],
    [c.caja && c.caja.hueco_min_m >= 0, "caja.hueco_min_m"],
    [c.emision_s && c.emision_s.min > 0 && c.emision_s.max >= c.emision_s.min, "emision_s"],
    [c.masa_kg && ["normal", "uniforme"].includes(c.masa_kg.distribucion) &&
     c.masa_kg.min > 0 && c.masa_kg.max > c.masa_kg.min, "masa_kg"],
    [c.bascula && c.bascula.plena_escala_kg > 0 && c.bascula.tau_s > 0 && c.bascula.ruido_V >= 0, "bascula"],
    [c.marca_s > 0, "marca_s"]
]);
const mal = chequeos.filter(([ok]) => !ok).map(([, nombre]) => nombre);
if (mal.length) return falla(`valores invalidos: ${mal.join(", ")}`);

const semillaEnv = env.get("A2_SUST_SEMILLA");
const semilla = (semillaEnv !== undefined && semillaEnv !== "") ? Number(semillaEnv) : c.semilla;
if (!Number.isInteger(semilla)) return falla(`semilla no entera: ${semilla}`);

// Semilla de cada fuente: mezcla de la semilla con una constante distinta.
function mezcla(x) {
    x = Math.imul(x ^ (x >>> 16), 0x85ebca6b);
    x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
    return (x ^ (x >>> 16)) | 0;
}
const activo = env.get("SUST_ACTIVO") !== false;
const dt = Number(env.get("SUST_DT_S"));

flow.set("sust", {
    activo: activo,
    cfg: c,
    dt: dt,
    semilla: semilla,
    arranque: new Date().toISOString(),
    rng: { masa: mezcla(semilla ^ 0x1b873593), intervalo: mezcla(semilla ^ 0x2545f491),
           ruido: mezcla(semilla ^ 0x68e31da4) },
    pedido: 0, recibido: {}, pedidos_sin_respuesta: 0,
    tick: 0, tick0: null, wall0: null,
    cajas: [], ultima_caja: 0, proxima_emision: null, retenida: false,
    emp_ext: 0, peso_V: 0,
    previo: null
});

node.status(activo
    ? { fill: "green", shape: "dot", text: `${escena}, semilla ${semilla}, dt ${dt} s, puerto ${env.get("SUST_PUERTO")}` }
    : { fill: "grey", shape: "ring", text: "apagado (A2_SUSTITUTO=0)" });
msg.payload = { activo, semilla, dt, puerto: env.get("SUST_PUERTO"), host: env.get("SUST_HOST") };
return msg;
