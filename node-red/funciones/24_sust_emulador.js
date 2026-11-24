/* Nodo: "emulador de la estacion"  (A2-Sustituto, 3 salidas)
 *   0 -> escrituras de memoria al Modbus-Server (entradas discretas y registros de entrada)
 *   1 -> eventos, una linea JSON por evento, al archivo de la corrida
 *   2 -> estado resumido (para depurar)
 * ---------------------------------------------------------------
 * Hace de planta: lee lo que el cliente escribio (bobinas y retencion) y
 * escribe lo que la planta mediria (sensores, limites y peso), con el mismo
 * mapa que usa el cliente.
 *
 * Modelo (provisional, todas las constantes en config/sustituto_a2.json), en
 * una sola linea, x = centro de la caja en metros:
 *   emisor -> [alimentacion + bascula] -> inicio_banda_variable -> [tramo a k*vel_banda_V] -> fin
 *   - antes de inicio_banda_variable la caja avanza a alimentacion_m_s si
 *     alimentacion_on; despues, a k_banda_m_s_por_V * vel_banda_V, que puede
 *     ser negativa (la caja retrocede, pero no regresa a la bascula).
 *   - una caja no se encima en la de adelante: se detiene a hueco_min_m.
 *   - el empujador extiende en carrera_s; pasado `alcance` saca de la linea
 *     la caja que tenga enfrente.
 *
 * DETERMINISMO. El tiempo de la simulacion es tick * dt, nunca el reloj de
 * pared, y todo lo aleatorio sale de los generadores con semilla de flow.sust.
 * Con las mismas entradas desde el cliente, dos corridas dan la misma
 * secuencia de eventos. Los eventos llevan t = segundos desde que se encendio
 * el emisor por primera vez, para que el instante de arranque de Node-RED no
 * entre en la comparacion.
 */
const S = flow.get("sust");
const M = global.get("a2_mapa");
if (!S || !S.activo || !M) return null;

// ---- 1. juntar las dos respuestas del mismo pedido ------------------------
const pedido = msg.message && msg.message.payload && msg.message.payload.pedido;
if (pedido !== S.pedido || (msg.type !== "holding" && msg.type !== "coils")) return null;
S.recibido[msg.type] = pedido;
S["buf_" + msg.type] = Buffer.isBuffer(msg.payload) ? msg.payload : Buffer.from(msg.payload.data || []);
if (S.recibido.holding !== pedido || S.recibido.coils !== pedido || S.recibido.paso === pedido) return null;
S.recibido.paso = pedido;

// ---- utilidades -----------------------------------------------------------
const c = S.cfg, G = c.geometria_m, dt = S.dt, E = M.por_nombre;
const largo = c.caja.largo_m, separa = c.caja.largo_m + c.caja.hueco_min_m;
const r6 = x => Math.round(x * 1e6) / 1e6;

function azar(fuente) {                        // mulberry32: [0, 1)
    let a = (S.rng[fuente] = (S.rng[fuente] + 0x6D2B79F5) | 0);
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function normal(fuente) {                      // Box-Muller
    const u1 = 1 - azar(fuente), u2 = azar(fuente);
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}
function sorteaMasa() {
    const m = c.masa_kg;
    if (m.distribucion === "uniforme") return m.min + (m.max - m.min) * azar("masa");
    // Normal truncada por rechazo: se vuelve a sortear en vez de recortar,
    // para no amontonar probabilidad justo en los limites.
    for (let i = 0; i < 100; i++) {
        const x = m.media + m.sd * normal("masa");
        if (x >= m.min && x <= m.max) return x;
    }
    return Math.min(m.max, Math.max(m.min, m.media));
}
const bit = (buf, a) => (buf[a >> 3] >> (a & 7)) & 1;
const reg = (buf, a) => buf.readUInt16BE(a * 2);

if (c.escena === "desviador") return pasoDesviador();

// ---- 2. entradas que escribio el cliente ------------------------------------
const ev = [];
const t = () => (S.tick0 === null ? null : r6((S.tick - S.tick0) * dt));
function evento(nombre, extra) {
    ev.push(Object.assign({ arranque: S.arranque, semilla: S.semilla, tick: S.tick, t: t(), ev: nombre }, extra || {}));
}

const ev_vel = E.vel_banda_V;
let crudo = reg(S.buf_holding, ev_vel.direccion);
if (ev_vel.tipo === "int16" && crudo >= 0x8000) crudo -= 0x10000;     // complemento a dos
let velV = crudo / ev_vel.escala;
const [vmin, vmax] = ev_vel.rango_fisico;
const ent = {
    emisor_on: bit(S.buf_coils, E.emisor_on.direccion),
    alimentacion_on: bit(S.buf_coils, E.alimentacion_on.direccion),
    emp_extender: bit(S.buf_coils, E.emp_extender.direccion),
    luz_alerta: E.luz_alerta ? bit(S.buf_coils, E.luz_alerta.direccion) : 0,
    vel_banda_V: velV
};
const prev = S.previo || { emisor_on: 0, alimentacion_on: 0, emp_extender: 0, luz_alerta: 0,
                           vel_banda_V: 0, sens: {}, peso_crudo: 0 };

if (ent.emisor_on && !prev.emisor_on && S.tick0 === null) S.tick0 = S.tick;   // origen de t
for (const k of ["emisor_on", "alimentacion_on", "emp_extender", "luz_alerta", "vel_banda_V"]) {
    if (ent[k] !== prev[k]) evento("entrada", { etiqueta: k, valor: ent[k] });
}
const fueraDeRango = velV < vmin || velV > vmax;
if (fueraDeRango) {
    // Se recorta al rango del mapa y se avisa una vez por valor distinto.
    if (!prev.fuera_de_rango || prev.vel_banda_V !== velV) {
        evento("entrada_fuera_de_rango", { etiqueta: "vel_banda_V", valor: velV });
    }
    velV = Math.min(vmax, Math.max(vmin, velV));
}

// ---- 3. emision ---------------------------------------------------------------
if (ent.emisor_on) {
    if (S.proxima_emision === null) S.proxima_emision = S.tick;          // al encender, de inmediato
    if (S.tick >= S.proxima_emision) {
        const libre = !S.cajas.some(k => Math.abs(k.x - G.emisor) < separa);
        if (libre) {
            const id = ++S.ultima_caja;
            const masa = Math.round(sorteaMasa() * 1000) / 1000;
            S.cajas.push({ id: id, masa: masa, x: G.emisor });
            evento("caja_emitida", { caja: id, masa_kg: masa });
            const e = c.emision_s;
            S.proxima_emision = S.tick + Math.max(1, Math.round((e.min + (e.max - e.min) * azar("intervalo")) / dt));
            S.retenida = false;
        } else if (!S.retenida) {
            S.retenida = true;
            evento("emision_retenida", {});
        }
    }
} else {
    S.proxima_emision = null;
}

// ---- 4. movimiento --------------------------------------------------------------
const vVar = c.k_banda_m_s_por_V * velV;
S.cajas.sort((a, b) => b.x - a.x);                                       // la de mas adelante primero
for (let i = 0; i < S.cajas.length; i++) {
    const k = S.cajas[i];
    const enVariable = k.x >= G.inicio_banda_variable;
    let x = k.x + (enVariable ? vVar : (ent.alimentacion_on ? c.alimentacion_m_s : 0)) * dt;
    if (enVariable && x < G.inicio_banda_variable) x = G.inicio_banda_variable;
    if (i > 0) x = Math.min(x, S.cajas[i - 1].x - separa);
    k.x = r6(x);
}

// ---- 5. empujador y salidas de la linea --------------------------------------------
S.emp_ext = Math.min(1, Math.max(0, S.emp_ext + (ent.emp_extender ? 1 : -1) * dt / c.empujador.carrera_s));
S.emp_ext = r6(S.emp_ext);
S.cajas = S.cajas.filter(k => {
    if (S.emp_ext >= c.empujador.alcance && Math.abs(k.x - G.empujador) < largo / 2) {
        evento("caja_rechazada", { caja: k.id, masa_kg: k.masa });
        return false;
    }
    if (k.x - largo / 2 > G.fin) {
        evento("caja_sale", { caja: k.id, masa_kg: k.masa });
        return false;
    }
    return true;
});

// ---- 6. sensores y bascula ----------------------------------------------------------
const tapa = xs => S.cajas.find(k => Math.abs(k.x - xs) <= largo / 2);
const enBascula = S.cajas.find(k => k.x >= G.bascula[0] && k.x <= G.bascula[1]);
const sens = {
    sens_entrada: tapa(G.sens_entrada),
    sens_bascula: enBascula,
    sens_salida: tapa(G.sens_salida),
    emp_lim_frontal: S.emp_ext >= 1,
    emp_lim_trasero: S.emp_ext <= 0
};
for (const k of Object.keys(sens)) {
    const v = sens[k] ? 1 : 0;
    if (v !== (prev.sens[k] || 0)) {
        evento(v ? "sensor_on" : "sensor_off",
               Object.assign({ etiqueta: k }, (sens[k] && sens[k].id) ? { caja: sens[k].id } :
                             (prev.sens_caja && prev.sens_caja[k]) ? { caja: prev.sens_caja[k] } : {}));
    }
}

const b = c.bascula;
const objetivoV = enBascula ? Math.min(10, enBascula.masa / b.plena_escala_kg * 10) : 0;
S.peso_V += (objetivoV - S.peso_V) * (1 - Math.exp(-dt / b.tau_s));
let medidoV = S.peso_V + (enBascula ? b.ruido_V * normal("ruido") : 0);
const ep = E.peso_V;
medidoV = Math.min(ep.rango_fisico[1], Math.max(ep.rango_fisico[0], medidoV));
const pesoCrudo = Math.round(medidoV * ep.escala);

// ---- 7. imagen de memoria de la planta -------------------------------------------------
function imagenDiscretas() {
    const tags = M.etiquetas.filter(e => e.tabla === "entrada_discreta");
    const bytes = new Array((Math.max(...tags.map(e => e.direccion)) >> 3) + 1).fill(0);
    for (const e of tags) if (sens[e.nombre]) bytes[e.direccion >> 3] |= 1 << (e.direccion & 7);
    return bytes;
}
function imagenRegistros() {
    const tags = M.etiquetas.filter(e => e.tabla === "registro_entrada");
    const bytes = new Array(2 * (Math.max(...tags.map(e => e.direccion)) + 1)).fill(0);
    for (const e of tags) {
        const v = e.nombre === "peso_V" ? pesoCrudo : 0;
        bytes[2 * e.direccion] = (v >> 8) & 0xFF;
        bytes[2 * e.direccion + 1] = v & 0xFF;
    }
    return bytes;
}
const escrituras = [
    { payload: { register: "discrete", address: 0, value: imagenDiscretas(), disableMsgOutput: true } },
    { payload: { register: "input", address: 0, value: imagenRegistros(), disableMsgOutput: true } }
];

// ---- 8. cierre del paso -----------------------------------------------------------------
if (S.tick0 !== null && S.tick > S.tick0 && Math.round((S.tick - S.tick0) * dt * 1e6) % Math.round(c.marca_s * 1e6) === 0) {
    evento("marca", { cajas_en_linea: S.cajas.length, emitidas: S.ultima_caja,
                      pedidos_sin_respuesta: S.pedidos_sin_respuesta });
}
S.previo = Object.assign({}, ent, {
    sens: Object.fromEntries(Object.keys(sens).map(k => [k, sens[k] ? 1 : 0])),
    sens_caja: Object.fromEntries(Object.keys(sens).filter(k => sens[k] && sens[k].id).map(k => [k, sens[k].id])),
    fuera_de_rango: fueraDeRango
});
if (S.wall0 === null) S.wall0 = Date.now();
S.tick++;

if (S.tick % 10 === 0) {
    const ritmo = (S.tick * dt * 1000) / Math.max(1, Date.now() - S.wall0);
    node.status({ fill: "green", shape: "dot",
                  text: `t ${t() === null ? "-" : t().toFixed(1)} s, ${S.cajas.length} cajas, ` +
                        `${velV.toFixed(2)} V, ritmo ${ritmo.toFixed(2)}` });
}

const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
const salidaEventos = ev.length
    ? { filename: `${dir}/a2_sustituto_eventos.jsonl`, payload: ev.map(e => JSON.stringify(e)).join("\n") }
    : null;
return [escrituras, salidaEventos,
        S.tick % 10 === 0 ? { payload: { tick: S.tick, t: t(), cajas: S.cajas, vel_banda_V: velV,
                                         peso_crudo: pesoCrudo, emp_ext: S.emp_ext } } : null];


// =========================================================================================
// Escena con desviador de ruedas (la de Sorting by Weight), bandas de velocidad
// fija. x = centro de la caja sobre la linea principal; pasado `desviador`
// cada caja sigue por su rama (left, right o forward) segun las ruedas que
// esten mandadas en ese instante, y su posicion en la rama es x - desviador.
//   emisor -> [entry_conveyor] -> at_scale_entry -> [load_scale: bascula] ->
//   at_scale_exit -> desviador -> rama: at_<rama>_entry -> fin_rama
// refresco_s > 0 publica la imagen de memoria solo cada tanto, como Factory
// I/O a ~1 FPS: la planta sigue avanzando cada tick, pero el cliente solo ve
// un cuadro nuevo cada refresco_s.
function pasoDesviador() {
    const ev = [];
    const t = () => (S.tick0 === null ? null : r6((S.tick - S.tick0) * dt));
    function evento(nombre, extra) {
        ev.push(Object.assign({ arranque: S.arranque, semilla: S.semilla, tick: S.tick, t: t(), ev: nombre }, extra || {}));
    }
    const necesarias = ["at_scale_entry", "at_scale_exit", "at_left_entry", "at_right_entry", "weight",
                        "emitter", "entry_conveyor", "load_scale", "send_left", "send_right", "send_forward"];
    const faltan = necesarias.filter(n => !E[n]);
    if (faltan.length) {
        node.status({ fill: "red", shape: "dot", text: `mapa sin ${faltan.join(", ")}` });
        return null;
    }
    const ent = {};
    for (const k of ["emitter", "entry_conveyor", "load_scale", "send_left", "send_right", "send_forward", "alarm_light"]) {
        ent[k] = E[k] ? bit(S.buf_coils, E[k].direccion) : 0;
    }
    const prev = S.previo || { sens: {} };
    if (ent.emitter && !prev.emitter && S.tick0 === null) S.tick0 = S.tick;
    for (const k of Object.keys(ent)) if (ent[k] !== (prev[k] || 0)) evento("entrada", { etiqueta: k, valor: ent[k] });

    // ---- emision -----------------------------------------------------------------
    if (ent.emitter) {
        if (S.proxima_emision === null) S.proxima_emision = S.tick;
        if (S.tick >= S.proxima_emision) {
            if (!S.cajas.some(k => k.rama === null && Math.abs(k.x - G.emisor) < separa)) {
                const id = ++S.ultima_caja;
                const masa = Math.round(sorteaMasa() * 1000) / 1000;
                S.cajas.push({ id: id, masa: masa, x: G.emisor, rama: null });
                evento("caja_emitida", { caja: id, masa_kg: masa });
                const e = c.emision_s;
                S.proxima_emision = S.tick + Math.max(1, Math.round((e.min + (e.max - e.min) * azar("intervalo")) / dt));
                S.retenida = false;
            } else if (!S.retenida) { S.retenida = true; evento("emision_retenida", {}); }
        }
    } else {
        S.proxima_emision = null;
    }

    // ---- movimiento: por tramo, la de mas adelante primero -------------------------
    const v = c.velocidad_m_s;
    const anda = k => k.rama !== null ? ent.entry_conveyor
        : (k.x < G.bascula[0] ? ent.entry_conveyor : ent.load_scale);
    for (const grupo of [null, "left", "right", "forward"]) {
        const fila = S.cajas.filter(k => k.rama === grupo).sort((a, b) => b.x - a.x);
        for (let i = 0; i < fila.length; i++) {
            const k = fila[i];
            let x = k.x + (anda(k) ? v * dt : 0);
            if (i > 0) x = Math.min(x, fila[i - 1].x - separa);
            k.x = r6(x);
        }
    }
    // Al cruzar el desviador la caja toma la rama que mandan las ruedas.
    for (const k of S.cajas) {
        if (k.rama === null && k.x >= G.desviador) {
            k.rama = ent.send_left ? "left" : ent.send_right ? "right" : "forward";
            if (!ent.send_left && !ent.send_right && !ent.send_forward) evento("sin_orden_desviador", { caja: k.id });
            if ((ent.send_left + ent.send_right + ent.send_forward) > 1) evento("desviador_ambiguo", { caja: k.id });
            evento("caja_desviada", { caja: k.id, rama: k.rama, masa_kg: k.masa });
        }
    }
    S.cajas = S.cajas.filter(k => {
        if (k.rama !== null && k.x - G.desviador - largo / 2 > G.fin_rama) {
            evento("caja_sale", { caja: k.id, masa_kg: k.masa, rama: k.rama });
            return false;
        }
        return true;
    });

    // ---- sensores y bascula ----------------------------------------------------------
    const principal = S.cajas.filter(k => k.rama === null);
    const tapa = xs => principal.find(k => Math.abs(k.x - xs) <= largo / 2);
    const tapaRama = r => S.cajas.find(k => k.rama === r && Math.abs(k.x - G.desviador - G.confirmacion) <= largo / 2);
    const enBascula = principal.find(k => k.x >= G.bascula[0] && k.x <= G.bascula[1]);
    const sens = {
        at_scale_entry: tapa(G.at_scale_entry), at_scale_exit: tapa(G.at_scale_exit),
        at_left_entry: tapaRama("left"), at_right_entry: tapaRama("right"), at_forward_entry: tapaRama("forward")
    };
    for (const k of Object.keys(sens)) {
        const val = sens[k] ? 1 : 0;
        if (val !== (prev.sens[k] || 0)) {
            evento(val ? "sensor_on" : "sensor_off",
                   Object.assign({ etiqueta: k }, sens[k] ? { caja: sens[k].id } :
                                 (prev.sens_caja && prev.sens_caja[k]) ? { caja: prev.sens_caja[k] } : {}));
        }
    }
    const b = c.bascula;
    const objetivoV = enBascula ? Math.min(10, enBascula.masa / b.plena_escala_kg * 10) : 0;
    S.peso_V += (objetivoV - S.peso_V) * (1 - Math.exp(-dt / b.tau_s));
    const ew = E.weight;
    const medidoV = Math.min(ew.rango_fisico[1], Math.max(ew.rango_fisico[0],
                             S.peso_V + (enBascula ? b.ruido_V * normal("ruido") : 0)));
    const pesoCrudo = Math.round(medidoV * ew.escala);

    if (S.tick0 !== null && S.tick > S.tick0 && Math.round((S.tick - S.tick0) * dt * 1e6) % Math.round(c.marca_s * 1e6) === 0) {
        evento("marca", { cajas_en_linea: S.cajas.length, emitidas: S.ultima_caja, pedidos_sin_respuesta: S.pedidos_sin_respuesta });
    }
    S.previo = Object.assign({}, ent, {
        sens: Object.fromEntries(Object.keys(sens).map(k => [k, sens[k] ? 1 : 0])),
        sens_caja: Object.fromEntries(Object.keys(sens).filter(k => sens[k]).map(k => [k, sens[k].id]))
    });
    if (S.wall0 === null) S.wall0 = Date.now();
    S.tick++;

    // ---- imagen de memoria (cada tick, o cada refresco_s) ----------------------------
    const cada = c.refresco_s > 0 ? Math.max(1, Math.round(c.refresco_s / dt)) : 1;
    let escrituras = null;
    if (S.tick % cada === 0) {
        const di = M.etiquetas.filter(e => e.tabla === "entrada_discreta");
        const bytesD = new Array((Math.max(...di.map(e => e.direccion)) >> 3) + 1).fill(0);
        for (const e of di) if (sens[e.nombre]) bytesD[e.direccion >> 3] |= 1 << (e.direccion & 7);
        const ir = M.etiquetas.filter(e => e.tabla === "registro_entrada");
        const bytesR = new Array(2 * (Math.max(...ir.map(e => e.direccion)) + 1)).fill(0);
        bytesR[2 * ew.direccion] = (pesoCrudo >> 8) & 0xFF;
        bytesR[2 * ew.direccion + 1] = pesoCrudo & 0xFF;
        escrituras = [
            { payload: { register: "discrete", address: 0, value: bytesD, disableMsgOutput: true } },
            { payload: { register: "input", address: 0, value: bytesR, disableMsgOutput: true } }
        ];
    }
    if (S.tick % 10 === 0) {
        node.status({ fill: "green", shape: "dot",
                      text: `desviador t ${t() === null ? "-" : t().toFixed(1)} s, ${S.cajas.length} cajas` +
                            (cada > 1 ? `, refresco ${c.refresco_s} s` : "") });
    }
    const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
    return [escrituras, ev.length ? { filename: `${dir}/a2_sustituto_eventos.jsonl`,
                                      payload: ev.map(e => JSON.stringify(e)).join("\n") } : null, null];
}
