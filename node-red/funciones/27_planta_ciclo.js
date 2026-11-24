/* Nodo: "ciclo de sondeo"  (A2-Planta, reloj de 25 ms, 3 salidas)
 *   0 -> peticion de lectura al Modbus-Flex-Getter
 *   1 -> escrituras (retraer el empujador cuando vence su tiempo)
 *   2 -> eventos al archivo de la corrida
 * ---------------------------------------------------------------
 * El periodo sale de la configuracion en tiempo de ejecucion, asi que el
 * inject solo marca el paso fino (25 ms) y aqui se decide cuando toca. Los
 * instantes de sondeo van sobre una rejilla fija (proximo += periodo): un
 * retraso no se acumula. Si un ciclo no termino cuando toca el siguiente, el
 * siguiente se salta y se cuenta; ese conteo y los periodos reales son lo
 * que se reporta como periodo efectivo.
 *
 * El ciclo es un bloque de entradas discretas y, solo mientras hay caja en
 * la bascula, antes un bloque de registros de entrada. Nunca una peticion
 * por etiqueta.
 *
 * Tambien aqui vive el perro guardian de la comunicacion: si no hubo una
 * lectura buena en lim.timeout_com_ms (el mayor entre comunicacion_timeout_ms
 * y 3 T_ef), la linea queda sin comunicacion.
 */
const S = flow.get("planta");
const M = global.get("a2_mapa");
if (!S || !M) return null;
const ahora = Date.now();
const c = S.cfg;
const R = S.roles;

function evento(nombre, extra) {
    const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
    node.send([null, null, { filename: `${dir}/a2_planta_eventos.jsonl`,
        payload: JSON.stringify(Object.assign({ ts: new Date().toISOString(), arranque: S.arranque, ev: nombre }, extra || {})) }]);
}
function escritura(etiqueta, valor, motivo, extra) {
    const e = M.por_nombre[etiqueta];
    const palabra = e.tipo === "bool" ? !!valor
        : (Math.round(valor * e.escala) & 0xFFFF);
    return { payload: { value: palabra, fc: e.tabla === "bobina" ? 5 : 6,
                        unitid: Number(env.get("PLANTA_UNIDAD")), address: e.direccion, quantity: 1 },
             escritura: Object.assign({ etiqueta: etiqueta, valor: valor, motivo: motivo, t: ahora }, extra || {}) };
}

// ---- perro guardian -----------------------------------------------------------
if ((S.com === "ok" || S.com === "reconectando") && ahora - S.ultimo_ok_ms > S.lim.timeout_com_ms) {
    S.com = "sin_comunicacion";
    S.contadores.desconexiones++;
    S.seguro = null;
    (S.timers || []).forEach(t => clearTimeout(t));     // rechazos programados: ya no valen
    S.timers = [];
    S.empujador = { estado: "reposo", caja: null, t: 0, timer: null };
    evento("sin_comunicacion", { ultima_lectura_hace_ms: ahora - S.ultimo_ok_ms, linea: S.linea });
    node.status({ fill: "red", shape: "ring", text: "SIN COMUNICACION" });
}

if (S.linea !== "en_marcha") S.marcha_desde = null;
else if (!S.marcha_desde) S.marcha_desde = ahora;

// ---- resumen para otras pestanas ----------------------------------------------------
// El contexto flow es por pestana; A2-Nube (latido) y la HMI leen esto de global.
global.set("a2_planta_resumen", {
    actuador: S.actuador, banda_variable: S.lim.banda_variable,
    ultima_caja: S.ultima_caja || null,
    cajas_por_minuto: (S.pasos_ms || []).filter(t => ahora - t < 60000).length,
    ultimas_masas: S.ultimas_masas || [],
    en_marcha_s: S.linea === "en_marcha" && S.marcha_desde ? Math.round((ahora - S.marcha_desde) / 1000) : 0,
    problemas: S.lim.problemas, sondeo_ms: S.sondeo_ms, rtt_previsto_ms: S.rtt_previsto_ms,
    com: S.com, linea: S.linea, vel_aplicada_V: S.vel_aplicada_V, emisor: S.emisor,
    alimentacion: S.alimentacion, peso_V: S.ultimo_peso_V || 0,
    ts_ultima_lectura: S.ultimo_ok_ms ? new Date(S.ultimo_ok_ms).toISOString() : null,
    cajas_acumuladas: S.contadores.salidas + S.contadores.rechazos,
    contadores: S.contadores, consigna_V: S.consigna_V, limites: S.lim
});

// ---- empujador que no confirmo a tiempo ------------------------------------------
const salidas = [null, [], null];
// Una sola peticion Modbus a la vez (modbus_una_peticion): Factory I/O no
// contesta las peticiones que le llegan juntas en un mismo paquete TCP.
function encola(lista) {
    if (!S.una) return lista;
    S.cola_esc.push(...lista);
    const w = despacha();
    return w ? [w] : [];
}
function despacha() {
    if (!S.una || S.esc_en_vuelo || S.ciclo.en_curso || !S.cola_esc.length) return null;
    S.esc_en_vuelo = Date.now();
    return S.cola_esc.shift();
}
if (S.una && S.esc_en_vuelo && ahora - S.esc_en_vuelo > 3000) S.esc_en_vuelo = null;   // sin respuesta: se abandona
const E = S.empujador;
if (S.actuador === "empujador" && S.com === "ok" && (E.estado === "extendiendo" || E.estado === "retrayendo") &&
    ahora - E.t > S.lim.timeout_empujador_s * 1000) {
    S.contadores.fallos_empujador++;
    evento("falla_empujador", { fase: E.estado, caja: E.caja, espera_ms: ahora - E.t });
    if (E.estado === "extendiendo") {
        const caja = S.fifo.find(k => k.id === E.caja);
        if (caja) caja.estado = "rechazo_fallido";
        salidas[1].push(escritura(R.empujador, false, "empujador_falla_retrae", { caja: E.caja }));
        if (R.alerta) salidas[1].push(escritura(R.alerta, true, "alerta_empujador"));
        // Si el limite frontal llega despues, la caja SI se empujo: se acepta
        // tarde en vez de dejarla en la cola, donde desalinearia a las demas.
        S.empujador_tardio = { caja: E.caja, t: ahora };
    }
    S.empujador = { estado: "reposo", caja: null, t: 0, timer: null };
}

// ---- desviador: caja que no llego a la salida que se le mando -----------------------
if (S.actuador === "desviador" && S.com === "ok") {
    // Sensor de rama que no baja en 3 s: se libera el desviador igual, con evento.
    if (S.desviador_ocupado && ahora - S.desviador_ocupado.t > 3000) {
        evento("sensor_de_rama_sin_bajar", { sensor: S.desviador_ocupado.sensor, caja: S.desviador_ocupado.caja });
        S.desviador_ocupado = null;
    }
    for (const caja of S.fifo.slice()) {
        const vencida = caja.estado === "desviando" && ahora - caja.t_desvio > S.lim.timeout_confirmacion_s * 1000;
        if (!vencida) continue;
        S.fifo.splice(S.fifo.indexOf(caja), 1);
        S.contadores.perdidas++;
        evento("caja_perdida", { caja: caja.id, motivo: "sin_confirmacion", destino_esperado: caja.destino,
                                 espera_ms: ahora - caja.t_desvio });
        if (R.alerta) salidas[1].push(escritura(R.alerta, true, "alerta_caja_perdida"));
    }
    if (!S.fifo.some(k => k.estado === "desviando") && !S.desviador_ocupado && S.desvio_activo && ahora >= (S.purga_hasta || 0)) {
        for (const k of S.clases) salidas[1].push(escritura(k.salida, false, "desviador_libera"));
        if (S.motriz && !S.clases.some(k => k.salida === S.motriz)) salidas[1].push(escritura(S.motriz, false, "desviador_libera"));
        S.desvio_activo = null;
    }
}

// ---- tablero: luces segun la linea y contadores por destino ------------------------
// Se escribe solo lo que cambio (S.tablero_escrito); tras reconectar se vacia
// y todo se vuelve a escribir.
if (S.tablero && S.com === "ok") {
    const TB = S.tablero, quiero = {};
    const luces = TB.luces || {};
    if (luces.en_marcha) quiero[luces.en_marcha] = S.linea === "en_marcha";
    if (luces.detenida) quiero[luces.detenida] = S.linea !== "en_marcha";
    if (luces.emergencia) quiero[luces.emergencia] = S.linea === "emergencia";
    for (const [destino, et] of Object.entries(TB.contadores || {})) quiero[et] = S.contadores.por_destino[destino] || 0;
    for (const [et, v] of Object.entries(quiero)) {
        if (S.tablero_escrito[et] === v) continue;
        S.tablero_escrito[et] = v;
        salidas[1].push(escritura(et, v, "tablero"));
    }
}

// ---- ciclo ------------------------------------------------------------------------
const T = S.sondeo_ms;
if (S.ciclo.en_curso) {
    // Una peticion sin respuesta mas alla del timeout del cliente se abandona.
    if (ahora - S.ciclo.t_envio > 3000) { S.ciclo.en_curso = false; S.contadores.lecturas_fallidas++; }
    salidas[1] = encola(salidas[1]);
    return salidas[1].length ? salidas : null;
}
if (S.una) {
    // Las escrituras van antes que la lectura; con una en vuelo no se lee.
    salidas[1] = encola(salidas[1]);
    if (S.esc_en_vuelo) return salidas[1].length ? salidas : null;
}
if (S.ciclo.proximo === 0) S.ciclo.proximo = ahora;
if (ahora < S.ciclo.proximo) return salidas[1].length ? salidas : null;
let saltados = -1;
while (S.ciclo.proximo <= ahora) { S.ciclo.proximo += T; saltados++; }
if (saltados > 0 && S.com === "ok") S.contadores.sondeos_saltados += saltados;

const disc = M.etiquetas.filter(e => e.tabla === "entrada_discreta").map(e => e.direccion);
const ent = M.etiquetas.filter(e => e.tabla === "registro_entrada").map(e => e.direccion);
// Con caja en la bascula el ciclo empieza por el PESO y sigue con los
// sensores: asi cada lectura de peso queda entre dos lecturas de sensores, y
// solo vale si las dos ven la caja sobre la bascula. En el orden inverso, con
// 200 ms de ida y vuelta, el peso de la ultima lectura salia con la caja ya
// fuera (primera corrida azure: -2 a -3.8 kg en las cajas con 4 muestras).
const conPeso = S.com === "ok" && (S.actuador === "empujador"
    ? ((S.crudo && S.crudo[R.bascula]) || !!S.pesaje)
    : S.fifo.some(k => k.estado === "en_bascula" || k.estado === "pesando"));
S.ciclo.n++;
S.ciclo.en_curso = true;
S.ciclo.peso_V = null;
S.ciclo.fase = conPeso ? "peso" : "discretas";
S.ciclo.t_envio = ahora;
S.ciclo.t_fase = ahora;
if (S.com === "ok") {
    if (S.ultimo_ciclo_ms !== null) {
        const p = S.estadistica.periodos_ms;
        p.push(ahora - S.ultimo_ciclo_ms);
        if (p.length > 5000) p.shift();
    }
    S.ultimo_ciclo_ms = ahora;
} else {
    S.ultimo_ciclo_ms = null;
}
S.contadores.sondeos++;
const bloque = conPeso ? ent : disc;
salidas[0] = { payload: { fc: conPeso ? 4 : 2, unitid: Number(env.get("PLANTA_UNIDAD")), address: Math.min(...bloque),
                          quantity: Math.max(...bloque) - Math.min(...bloque) + 1 },
               ciclo: S.ciclo.n, fase: S.ciclo.fase };
return salidas;
