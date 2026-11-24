/* Nodo: "carga configuracion y limites"  (A2-Planta)
 * ---------------------------------------------------------------
 * Lee la configuracion (A2_PLANTA_CONFIG: config/planta_a2.json con empujador,
 * config/planta_desviador.json con desviador), fija el periodo de sondeo
 * (A2_SONDEO_MS), el tiempo de ida y vuelta previsto (A2_RTT_PREVISTO_MS) y
 * el refresco de la escena (A2_REFRESCO_MS), y calcula con ellos si la linea
 * es factible y, si hay banda variable, la velocidad permitida.
 *
 * La cuenta es LA MISMA que tools/limites_planta.py (ahi esta explicada); las
 * pruebas comparan las dos. Si cambia una, cambia la otra.
 */
function falla(detalle) {
    node.error(`configuracion de la planta invalida (${env.get("A2_PLANTA_CONFIG")}): ${detalle}`, msg);
    node.status({ fill: "red", shape: "dot", text: "configuracion invalida" });
    return null;
}
const M = global.get("a2_mapa");
if (!M) return falla("no hay mapa cargado");

let c;
try { c = JSON.parse(msg.payload); } catch (e) { return falla(`JSON.parse: ${e.message}`); }
const num = x => typeof x === "number" && Number.isFinite(x);
const L = c.linea || {};
// Actuador: "empujador" (C4, se queda para la regresion) o "desviador" (la
// escena Sorting by Weight: desviador de ruedas de tres salidas).
const actuador = c.actuador || "empujador";
if (!["empujador", "desviador"].includes(actuador)) return falla(`actuador desconocido: ${actuador}`);
// Roles: que etiqueta del mapa hace cada cosa. Asi el mapa real de Factory
// I/O entra cambiando la configuracion, no el codigo. Sin roles, los nombres
// de C4.
const R = Object.assign(actuador === "empujador"
    ? { entrada: "sens_entrada", bascula: "sens_bascula", salida: "sens_salida", peso: "peso_V",
        velocidad: "vel_banda_V", emisor: "emisor_on", alimentacion: ["alimentacion_on"], alerta: "luz_alerta",
        empujador: "emp_extender", lim_frontal: "emp_lim_frontal", lim_trasero: "emp_lim_trasero" }
    : {}, c.roles || {});
if (typeof R.alimentacion === "string") R.alimentacion = [R.alimentacion];
R.alimentacion = R.alimentacion || [];
const obligatorios = actuador === "empujador"
    ? ["entrada", "bascula", "salida", "peso", "empujador", "lim_frontal", "lim_trasero"]
    : ["entrada", "fin_bascula", "peso"];
const sinRol = obligatorios.filter(k => !R[k]);
if (sinRol.length) return falla(`faltan roles: ${sinRol.join(", ")}`);
const usadas = Object.values(R).flat().filter(Boolean);
let clases = [];
if (actuador === "desviador") {
    clases = (c.desviador && c.desviador.clases) || [];
    if (!clases.length) return falla("desviador sin clases");
    for (const k of clases) {
        if (!k.salida || !k.destino) return falla(`clase ${k.nombre}: falta salida o destino`);
        usadas.push(k.salida);
        if (k.confirma) usadas.push(k.confirma);
    }
    if (clases.some((k, i) => i < clases.length - 1 && !num(k.hasta_kg))) return falla("clases: hasta_kg numerico salvo la ultima");
}
// Factory I/O (Sorting by Weight): las ruedas solo giran con la salida
// "motriz" (send_forward); send_left y send_right solo las orientan. Sin
// ninguna, la caja se queda parada sobre el desviador.
const motriz = (actuador === "desviador" && c.desviador.motriz) || null;
if (motriz) usadas.push(motriz);
// Pesaje detenido: con la banda en marcha el peso de la escena no se asienta.
// Al llegar la caja a `en_bascula` se detienen `detiene`, se espera
// `espera_ms`, se toma la mediana de `muestras` lecturas y se sueltan `suelta`;
// `reanuda_al_salir` vuelve a andar cuando la caja deja `fin_bascula`.
const det = (actuador === "desviador" && c.bascula && c.bascula.pesaje_detenido) || null;
if (det) {
    if (!R.en_bascula) return falla("pesaje_detenido sin rol en_bascula");
    if (!num(det.espera_ms) || !num(det.muestras) || det.muestras < 1) return falla("pesaje_detenido: espera_ms y muestras");
    if (det.espera_max_ms !== undefined && !(num(det.espera_max_ms) && det.espera_max_ms >= det.espera_ms)) return falla("pesaje_detenido: espera_max_ms >= espera_ms");
    if (det.separa_ms !== undefined && !num(det.separa_ms)) return falla("pesaje_detenido: separa_ms");
    for (const k of ["detiene", "separa", "suelta", "reanuda_al_salir"]) {
        if (k === "separa" && det[k] === undefined) continue;
        if (!Array.isArray(det[k])) return falla(`pesaje_detenido.${k} debe ser una lista`);
        usadas.push(...det[k]);
    }
}
// Tablero de la escena (opcional): botones Start / Stop / Emergency stop (los
// NC valen 1 sin presionar), luces segun el estado de la linea y contadores
// por destino.
const T = c.tablero || null;
const botones = [];
if (T) {
    for (const k of ["start", "stop", "emergencia"]) {
        if (!T[k]) continue;
        if (!T[k].etiqueta) return falla(`tablero.${k} sin etiqueta`);
        // Lecturas propias del boton para aceptar un cambio (cierre de la fase 4: Stop
        // con una sola lectura, ya que detener es la direccion segura). Sin la clave,
        // el boton usa lecturas_para_cambio general.
        const lp = T[k].lecturas_para_cambio;
        if (lp !== undefined && !(Number.isInteger(lp) && lp >= 1)) return falla(`tablero.${k}.lecturas_para_cambio debe ser entero >= 1: ${lp}`);
        if (lp !== undefined && k === "emergencia") return falla("tablero.emergencia actua por nivel: no lleva lecturas_para_cambio propio");
        botones.push(T[k].etiqueta);
    }
    usadas.push(...botones, ...Object.values(T.luces || {}), ...Object.values(T.contadores || {}));
}
const noEnMapa = usadas.filter(n => !M.por_nombre[n]);
if (noEnMapa.length) return falla(`etiquetas que no estan en el mapa: ${[...new Set(noEnMapa)].join(", ")}`);

const faltan = ["sondeo_ms", "rtt_previsto_ms", "holgura_ms", "lecturas_por_ciclo_max",
                "escrituras_por_ciclo_max", "periodos_minimos", "lecturas_para_cambio",
                "comunicacion_timeout_ms"].filter(k => !num(c[k]))
    .concat((actuador === "empujador"
             ? ["k_banda_m_s_por_V", "alimentacion_m_s", "intervalo_emision_min_s", "largo_caja_m",
                "entrada_a_fin_bascula_m", "bascula_a_empujador_m", "bascula_a_salida_m"]
             : ["intervalo_emision_min_s"])
            .filter(k => !num(L[k])).map(k => "linea." + k));
if (faltan.length) return falla(`faltan o no son numeros: ${faltan.join(", ")}`);
// Desviador (cierre de la fase 4, paso H): los dos limites de recorrido salen de tiempos
// medidos si linea los trae completos; si no, de distancia y velocidad, como antes.
const MEDIDOS = ["t_pesada_a_confirmacion_s", "t_entrada_a_parada_s"];
const DISTANCIAS = ["velocidad_fija_m_s", "largo_caja_m", "entrada_a_fin_bascula_m", "fin_bascula_a_confirmacion_m"];
const conTiempos = actuador === "desviador" && MEDIDOS.every(k => num(L[k]) && L[k] > 0);
if (actuador === "desviador" && !conTiempos && !DISTANCIAS.every(k => num(L[k]))) {
    return falla("linea del desviador: faltan los tiempos medidos (" + MEDIDOS.join(", ") +
                 ") o, en su lugar, distancia y velocidad completas (" + DISTANCIAS.join(", ") + ")");
}
if (!L.sensores || !c.bascula) return falla("faltan linea.sensores o bascula");
if (actuador === "empujador") {
    if (!c.clasificacion || !c.empujador) return falla("faltan clasificacion o empujador");
    if (!num(c.empujador.carrera_s) || !num(c.empujador.margen_s) || !num(c.empujador.alcance_s)) return falla("empujador: carrera_s, margen_s y alcance_s");
}

const sondeoEnv = Number(env.get("A2_SONDEO_MS"));
const rttEnv = env.get("A2_RTT_PREVISTO_MS");
const refEnv = env.get("A2_REFRESCO_MS");
const lecEnv = Number(env.get("A2_LECTURAS_PARA_CAMBIO"));
const sondeo = sondeoEnv > 0 ? sondeoEnv : c.sondeo_ms;
const rtt = (rttEnv !== undefined && rttEnv !== "") ? Number(rttEnv) : c.rtt_previsto_ms;
// Refresco de la escena (ms): Factory I/O a 1 FPS en la VM no cambia sus
// valores mas de una vez por segundo, por rapido que se lea.
const refresco = (refEnv !== undefined && refEnv !== "") ? Number(refEnv) : (c.refresco_ms || 0);
// Lecturas seguidas para aceptar un cambio: 2 por omision; 1 solo con la
// escena real si el refresco no da para 2 (sus sensores no rebotan).
if (lecEnv >= 1) c.lecturas_para_cambio = lecEnv;

// ---- limites (misma cuenta que tools/limites_planta.py) ------------------------
// Con lo medido (bloque "medido", tomado con este mismo sondeo y sin rtt ni
// refresco dados a mano) la holgura fija se reemplaza por los p95 medidos.
// Misma regla que tools/limites_planta.py (t_efectivo).
const peticiones = c.lecturas_por_ciclo_max + c.escrituras_por_ciclo_max;
const m = c.medido;
const aMano = (rttEnv !== undefined && rttEnv !== "") || (refEnv !== undefined && refEnv !== "");
const medidoVale = !!m && m.sondeo_ms === sondeo && !aMano &&
    [m.periodo_p95_ms, m.rtt_p95_ms, m.refresco_p95_ms].every(num);
const tEfMs = medidoVale
    ? Math.max(m.periodo_p95_ms, peticiones * m.rtt_p95_ms, m.refresco_p95_ms)
    : Math.max(sondeo, peticiones * rtt, refresco) + c.holgura_ms;
const tMin = c.periodos_minimos * tEfMs / 1000;
const dt = L.intervalo_emision_min_s;
let vmax = Infinity, vmin = 0;
const problemas = [];
for (const nombre of Object.keys(L.sensores).sort()) {
    const s = L.sensores[nombre], largo = s.largo_activo_m;
    if (s.banda === "alimentacion" || s.banda === "fija" || s.banda === "medida") {
        // "medida": tiempos minimos medidos con sonda vigila en la escena real.
        const v = s.banda === "alimentacion" ? L.alimentacion_m_s : s.v_m_s;
        const on = s.banda === "medida" ? s.encendido_min_s : largo / v;
        const off = s.banda === "medida" ? s.apagado_min_s : dt - on;
        if (on < tMin || off < tMin) problemas.push(`${nombre}: encendido ${on.toFixed(2)} s, apagado ${off.toFixed(2)} s, se necesitan ${tMin.toFixed(2)} s`);
    } else {
        vmax = Math.min(vmax, largo / tMin);
        vmin = Math.max(vmin, dt > tMin ? largo / (dt - tMin) : Infinity);
    }
}
const variable = Object.values(L.sensores).some(s => s.banda === "variable");
let velMaxV = null, velMinV = null;
if (variable) {
    const k = L.k_banda_m_s_por_V;
    const etVel = M.por_nombre[(c.roles && c.roles.velocidad) || "vel_banda_V"];
    const tope = etVel ? etVel.rango_fisico[1] : Infinity;
    velMaxV = Math.min(Math.floor(vmax / k * 100) / 100, tope);
    velMinV = Number.isFinite(vmin) ? Math.ceil(vmin / k * 100) / 100 : null;
    if (velMinV === null || velMinV > velMaxV) problemas.push(`sin velocidad posible: minima ${velMinV} V, maxima ${velMaxV} V`);
}

// Tiempo para confirmar el empujador: su carrera, la ida y vuelta, y las
// lecturas que pide el antirrebote mas una. Fijo en 1.5 s fallaba en Azure:
// la confirmacion tarda ~2 s con 650 ms entre lecturas.
const timeoutEmp = actuador === "empujador"
    ? c.empujador.carrera_s + (c.lecturas_para_cambio + 1) * tEfMs / 1000 + rtt / 1000 + c.empujador.margen_s : null;
// Desviador: de la decision al pesar al sensor de confirmacion, mas el antirrebote y una
// holgura de 1.5 veces. Con tiempos medidos (paso H) se suma comunicacion_timeout_ms: un
// hueco de comunicacion menor que ese tiempo no dispara la secuencia segura, asi que el
// limite tiene que tolerarlo (antes esa holgura venia de distancias sobrestimadas).
const holguraCom = c.comunicacion_timeout_ms / 1000;
const timeoutConf = actuador !== "desviador" ? null : conTiempos
    ? 1.5 * L.t_pesada_a_confirmacion_s + (c.lecturas_para_cambio + 1) * tEfMs / 1000 + rtt / 1000 + holguraCom
    : 1.5 * L.fin_bascula_a_confirmacion_m / L.velocidad_fija_m_s + (c.lecturas_para_cambio + 1) * tEfMs / 1000 + rtt / 1000;
// Cajas que no llegan a la salida de la bascula (lo aplica 28_planta_lectura.js).
const limiteFinBascula = actuador !== "desviador" ? null : conTiempos
    ? 1.5 * L.t_entrada_a_parada_s + 3 * tEfMs / 1000 + holguraCom
    : 1.5 * L.entrada_a_fin_bascula_m / L.velocidad_fija_m_s + 3 * tEfMs / 1000;

// Sensores con antirrebote, en el orden en que se procesan sus flancos
// (aguas abajo primero).
const sensoresSeguidos = actuador === "empujador"
    ? [R.salida, R.bascula, R.entrada, R.lim_frontal, R.lim_trasero]
    : [...new Set(clases.map(k => k.confirma).filter(Boolean))].concat(det ? [R.fin_bascula, R.en_bascula, R.entrada]
                                                                         : [R.fin_bascula, R.entrada]);
sensoresSeguidos.push(...botones.filter(b => !sensoresSeguidos.includes(b)));
const deb = {};
for (const s of sensoresSeguidos) deb[s] = { estado: null, cuenta: 0, t_primero: null, ts_primero: null, muestras: 0 };
const porDestino = {};
for (const d of (actuador === "empujador" ? ["salida", "rechazo"] : clases.map(k => k.destino))) porDestino[d] = 0;

flow.set("planta", {
    cfg: c, sondeo_ms: sondeo, rtt_previsto_ms: rtt,
    refresco_ms: refresco, actuador: actuador, roles: R, clases: clases, seguidos: sensoresSeguidos,
    una: !!c.modbus_una_peticion, cola_esc: [], esc_en_vuelo: null,
    tablero: T, tablero_escrito: {}, emergencia: false,
    motriz: motriz, detenido: det, purga_ms: (actuador === "desviador" && c.desviador.purga_ms) || 0, purga_hasta: 0,
    lim: { t_ef_ms: tEfMs, t_ef_origen: medidoVale ? "medido" : "holgura", t_min_s: Math.round(tMin * 1000) / 1000, vel_min_V: velMinV, vel_max_V: velMaxV,
           banda_variable: variable, refresco_ms: refresco, lecturas_para_cambio: c.lecturas_para_cambio,
           factible: problemas.length === 0, problemas: problemas,
           timeout_empujador_s: timeoutEmp === null ? null : Math.round(timeoutEmp * 100) / 100,
           timeout_confirmacion_s: timeoutConf === null ? null : Math.round(timeoutConf * 100) / 100,
           limite_fin_bascula_s: limiteFinBascula,          // sin redondear: 28 lo compara tal cual, como antes
           limites_de: actuador !== "desviador" ? null : (conTiempos ? "tiempos_medidos" : "distancia_y_velocidad"),
           // Sin lectura buena en este tiempo, la linea queda sin comunicacion.
           // Crece con el sondeo: con un periodo mayor que el valor fijo, el
           // perro guardian saltaria entre dos lecturas sanas.
           timeout_com_ms: Math.max(c.comunicacion_timeout_ms, 3 * tEfMs) },
    com: "iniciando", linea: "detenida", consigna_V: 0, vel_aplicada_V: 0, emisor: false, alimentacion: false,
    seguro: null,
    ciclo: { n: 0, en_curso: false, fase: null, t_envio: 0, proximo: 0 },
    ultimo_ok_ms: 0, ultimo_ciclo_ms: null,
    deb: deb, fifo: [], proxima_caja: 1, pesaje: null,
    empujador: { estado: "reposo", caja: null, t: 0, timer: null },
    contadores: { entradas: 0, salidas: 0, rechazos: 0, perdidas: 0, perdidas_desconexion: 0,
                  fantasmas: 0, fantasmas_bascula: 0, rechazos_fallidos: 0, fallos_empujador: 0,
                  sondeos: 0, sondeos_saltados: 0, lecturas_fallidas: 0, escrituras_fallidas: 0,
                  desconexiones: 0, desvios_erroneos: 0, sin_confirmar: 0, purgadas: 0, emergencias: 0, descartadas_emergencia: 0,
                  por_destino: porDestino },
    estadistica: { periodos_ms: [], rtt_ms: [], min_muestras_encendido: {} },
    arranque: new Date().toISOString()
});

if (problemas.length) node.warn(`limites no factibles con sondeo ${sondeo} ms y rtt ${rtt} ms: ${problemas.join(" | ")}`);
node.status(problemas.length
    ? { fill: "yellow", shape: "ring", text: `NO factible: ${problemas[0]}` }
    : { fill: "green", shape: "dot", text: `${actuador}, sondeo ${sondeo} ms, rtt ${rtt} ms` +
                                                 (variable ? `, vel ${velMinV}..${velMaxV} V` : ", bandas fijas") });
msg.payload = { sondeo_ms: sondeo, rtt_previsto_ms: rtt, limites: flow.get("planta").lim };
return msg;
