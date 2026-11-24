/* Nodo: "procesa lectura"  (A2-Planta, 4 salidas)
 *   0 -> segunda peticion del ciclo (entradas discretas, si empezo por el peso)
 *   1 -> escrituras al Flex-Write
 *   2 -> eventos al archivo de la corrida
 *   3 -> paso_caja (hacia A2-Nube en C5)
 *   4 -> comandos del tablero de la escena (Start / Stop) a 30_planta_comando.js
 * ---------------------------------------------------------------
 * 1. Cambios de sensor CON ANTIRREBOTE: un cambio se acepta cuando se ve en
 *    `lecturas_para_cambio` lecturas seguidas, nunca por un pulso de una sola
 *    lectura. El instante del cambio es el de la PRIMERA lectura que lo
 *    mostro (estimado en la planta como envio + rtt/2).
 * 2. Cola FIFO de cajas entre sens_entrada y sens_salida.
 * 3. Pesaje: se abre al activarse sens_bascula. Una lectura de peso vale solo
 *    si la lectura de sensores anterior y la siguiente ven la caja en la
 *    bascula (el peso se pide entre las dos). El valor se retiene cuando
 *    `muestras_estables` lecturas seguidas caben en `banda_estable_V`. Si la
 *    caja sale de la bascula antes, se usa la ultima lectura y se marca como
 *    no estable.
 * 4. Clasificacion por tolerancia y rechazo: el empujador se programa con la
 *    posicion calculada de la caja (k x vel_banda_V) y se confirma con el
 *    limite frontal; despues se retrae y se espera el trasero.
 * 5. Consistencia: salida sin caja en la cola = fantasma; bascula sin caja
 *    por pesar = fantasma de bascula; caja que excede 1.5 veces su transito
 *    esperado = perdida. Todo queda en contadores y eventos.
 * 6. Estado seguro: la primera lectura buena tras arrancar o tras perder la
 *    comunicacion NO reanuda; escribe vel_banda_V = 0, luego emisor_on = 0
 *    y luego alimentacion_on = 0, cada una despues de confirmada la anterior
 *    (29_planta_escritura.js las encadena), y solo entonces la linea vuelve
 *    a "ok".
 */
const S = flow.get("planta");
const M = global.get("a2_mapa");
if (!S || !M) return null;
const ahora = Date.now();
const c = S.cfg;
const out = [null, [], null, [], []];
const eventos = [];

function evento(nombre, extra) {
    eventos.push(Object.assign({ ts: new Date().toISOString(), arranque: S.arranque, ev: nombre }, extra || {}));
}
function archivoEventos(lista) {
    if (!lista.length) return null;
    const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
    return { filename: `${dir}/a2_planta_eventos.jsonl`, payload: lista.map(e => JSON.stringify(e)).join("\n") };
}
function escritura(etiqueta, valor, motivo, extra) {
    const e = M.por_nombre[etiqueta];
    const palabra = e.tipo === "bool" ? !!valor : (Math.round(valor * e.escala) & 0xFFFF);
    return { payload: { value: palabra, fc: e.tabla === "bobina" ? 5 : 6,
                        unitid: Number(env.get("PLANTA_UNIDAD")), address: e.direccion, quantity: 1 },
             escritura: Object.assign({ etiqueta: etiqueta, valor: valor, motivo: motivo, t: Date.now() }, extra || {}) };
}
// Una linea por ciclo terminado en $DATOS_DIR/a2_sondeo_DIA.csv: de aqui salen
// el periodo efectivo del sondeo y su variacion (docs/INSTRUMENTACION_A2.md).
// Se juntan de 20 en 20 para no escribir el disco 4 veces por segundo.
function lineaSondeo() {
    const zona = env.get("TZ_REPORTE") || "America/Mexico_City";
    S.sondeo_buf = S.sondeo_buf || [];
    S.sondeo_buf.push([S.ciclo.n, S.ciclo.t_envio, new Date(S.ciclo.t_envio).toISOString(),
                       Date.now() - S.ciclo.t_envio, S.ciclo.peso_V !== null ? 2 : 1, S.com,
                       S.contadores.sondeos_saltados].join(";"));
    if (S.sondeo_buf.length < 20) return null;
    const dia = new Intl.DateTimeFormat("en-CA", { timeZone: zona, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
    const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
    const marca = `hdr_sondeo_${dia}`;
    const cabeza = flow.get(marca) ? "" : "ciclo;t_inicio_ms;ts_inicio;duracion_ms;peticiones;com;saltados_acumulados\n";
    flow.set(marca, true);
    const lineas = S.sondeo_buf.join("\n");
    S.sondeo_buf = [];
    return { filename: `${dir}/a2_sondeo_${dia}.csv`, payload: cabeza + lineas };
}
function mediana(a) {
    if (!a.length) return null;
    const o = a.slice().sort((x, y) => x - y), m = o.length >> 1;
    return o.length % 2 ? o[m] : (o[m - 1] + o[m]) / 2;
}
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
function termina() {
    S.ciclo.en_curso = false;
    out[1] = encola(out[1]);
    out[2] = [archivoEventos(eventos), lineaSondeo()].filter(Boolean);
    if (S.ciclo.n % 8 === 0) {
        const k = S.contadores;
        node.status(S.com === "ok"
            ? { fill: S.lim.factible ? "green" : "yellow", shape: "dot",
                text: `${S.linea} ${S.vel_aplicada_V} V | en tramo ${S.fifo.length} | ` +
                      `entran ${k.entradas} salen ${k.salidas} rechazo ${k.rechazos} perdidas ${k.perdidas}` }
            : { fill: "red", shape: "ring", text: S.com });
    }
    return out;
}

// ---- respuesta del ciclo en curso ---------------------------------------------------
if (msg.ciclo !== S.ciclo.n || msg.fase !== S.ciclo.fase || !S.ciclo.en_curso) return null;
if (msg.error || !Array.isArray(msg.payload)) {
    S.contadores.lecturas_fallidas++;
    S.ciclo.en_curso = false;
    return null;
}
const rtt = ahora - S.ciclo.t_fase;
S.estadistica.rtt_ms.push(rtt);
if (S.estadistica.rtt_ms.length > 5000) S.estadistica.rtt_ms.shift();
S.ultimo_ok_ms = ahora;

const R = S.roles;
const SEGUIDOS = S.seguidos;

if (msg.fase === "peso") {
    // Primera mitad del ciclo con caja en la bascula: se guarda el peso y se
    // piden los sensores. El peso se usa solo si los sensores confirman.
    const ep = M.por_nombre[R.peso];
    S.ciclo.peso_V = msg.payload[ep.direccion - msg.modbusRequest.address] / ep.escala;
    S.ultimo_peso_V = S.ciclo.peso_V;
    const disc = M.etiquetas.filter(e => e.tabla === "entrada_discreta").map(e => e.direccion);
    S.ciclo.fase = "discretas";
    S.ciclo.t_fase = Date.now();
    out[0] = { payload: { fc: 2, unitid: Number(env.get("PLANTA_UNIDAD")), address: Math.min(...disc),
                          quantity: Math.max(...disc) - Math.min(...disc) + 1 },
               ciclo: S.ciclo.n, fase: "discretas" };
    return out;
}

if (msg.fase === "discretas") {
    const base = msg.payload.length ? msg.modbusRequest.address : 0;
    const crudo = {};
    for (const s of SEGUIDOS) crudo[s] = !!msg.payload[M.por_nombre[s].direccion - base];
    const previo = S.crudo;
    S.crudo = crudo;

    // ---- sin comunicacion confirmada: secuencia segura antes de nada -----------
    if (S.com !== "ok") {
        if (S.com !== "reconectando") {
            if (S.fifo.length) {
                S.contadores.perdidas_desconexion += S.fifo.length;
                evento("cajas_descartadas_por_desconexion", { cajas: S.fifo.map(k => k.id) });
            }
            S.fifo = [];
            S.pesaje = null;
            (S.timers || []).forEach(t => clearTimeout(t));
            S.timers = [];
            S.empujador = { estado: "reposo", caja: null, t: 0, timer: null };
            S.linea = "detenida";
            S.desvio_activo = null;
            S.desviador_ocupado = null;
            S.cola_esc = [];
            S.esc_en_vuelo = null;
            S.tablero_escrito = {};             // luces y contadores se vuelven a escribir
            // Secuencia segura, armada desde los roles: velocidad a 0 (si hay
            // banda variable), emisor apagado y luego cada banda apagada. Cada
            // paso sale cuando 29_planta_escritura.js confirma el anterior.
            const pasos = [];
            if (R.velocidad) pasos.push({ etiqueta: R.velocidad, valor: 0 });
            if (R.emisor) pasos.push({ etiqueta: R.emisor, valor: false });
            for (const a of R.alimentacion) pasos.push({ etiqueta: a, valor: false });
            // Con desviador, al final las ruedas (y la motriz) apagadas.
            const ruedas = [...new Set(S.clases.map(k => k.salida).concat(S.motriz ? [S.motriz] : []))];
            for (const r of ruedas) pasos.push({ etiqueta: r, valor: false });
            S.purga_hasta = 0;
            evento("reconexion_inicia", { antes: S.com_previa || "iniciando", pasos: pasos.map(x => x.etiqueta) });
            if (pasos.length) {
                S.com = "reconectando";
                S.seguro = { i: 0, pasos: pasos };
                out[1].push(escritura(pasos[0].etiqueta, pasos[0].valor, "seguro", { paso: 0 }));
            } else {
                S.com = "ok";
                evento("reconexion_completa", { orden: [], linea: "detenida" });
            }
        }
        // Mientras tanto los sensores se toman como estan, sin generar flancos:
        // una caja que ya tapaba un sensor no se cuenta como una caja nueva.
        for (const s of SEGUIDOS) Object.assign(S.deb[s], { estado: crudo[s], cuenta: 0, t_primero: null, muestras: 0 });
        return termina();
    }

    // ---- antirrebote -----------------------------------------------------------------
    const tMuestra = S.ciclo.t_fase + rtt / 2;
    const tsLectura = new Date(ahora).toISOString();
    const N = c.lecturas_para_cambio;
    // Lecturas por senal: un boton del tablero puede traer las suyas (tablero.<boton>.
    // lecturas_para_cambio; cierre de la fase 4: Stop con 1). Lo demas usa N.
    const TB = S.tablero || {};
    const lecturasDe = s => { for (const k of ["start", "stop"]) { const b = TB[k];
        if (b && b.etiqueta === s && b.lecturas_para_cambio !== undefined) return b.lecturas_para_cambio; } return N; };
    const flancos = [];
    for (const s of SEGUIDOS) {
        const d = S.deb[s], v = crudo[s], Ns = lecturasDe(s);
        if (d.estado === null) { Object.assign(d, { estado: v, cuenta: 0, muestras: 0 }); continue; }
        if (v === d.estado) {
            d.cuenta = 0;
            d.muestras++;
            continue;
        }
        if (d.cuenta === 0) { d.t_primero = tMuestra; d.ts_primero = tsLectura; }
        d.cuenta++;
        if (d.cuenta >= Ns) {
            if (d.estado === true) {                       // termina un pulso: cuantas lecturas lo vieron
                const m = S.estadistica.min_muestras_encendido;
                m[s] = Math.min(m[s] === undefined ? Infinity : m[s], d.muestras);
            }
            flancos.push({ s: s, valor: v, t: d.t_primero, ts: d.ts_primero });
            Object.assign(d, { estado: v, cuenta: 0, muestras: Ns });
        }
    }
    S.ciclo.flancos = flancos;
    if (S.tablero) tablero(flancos);
    if (S.actuador === "desviador") {
        logicaDesviador(S.ciclo.peso_V);
        return termina();
    }
    const pesoValido = S.ciclo.peso_V !== null && previo && previo[R.bascula] && crudo[R.bascula];
    logica(pesoValido ? S.ciclo.peso_V : null);
    return termina();
}
return null;

// =========================================================================================
// Tablero de la escena. Un boton NC vale 1 sin presionar: "presionado" es su
// valor invertido. Start y Stop actuan en el flanco de presionar y van a la
// misma funcion de comandos que el POST y la HMI (mismas reglas: 409 sin
// limites factibles, etc.). Emergency stop actua por NIVEL, asi tambien vale
// si ya estaba presionado al arrancar: mientras este presionado la linea queda
// en "emergencia" con todo apagado y marcha se rechaza; al soltarlo queda
// detenida hasta el siguiente Start.
function tablero(flancos) {
    const T = S.tablero;
    const presionado = (b, v) => (b.nc ? !v : !!v);
    for (const f of flancos) {
        for (const [k, accion] of [["start", "marcha"], ["stop", "paro"]]) {
            const b = T[k];
            if (b && f.s === b.etiqueta && presionado(b, f.valor)) {
                evento("boton", { boton: k, etiqueta: b.etiqueta, accion: accion });
                out[4].push({ payload: { accion: accion }, origen: "tablero" });
            }
        }
    }
    const E = T.emergencia;
    if (!E || S.deb[E.etiqueta].estado === null) return;
    const ahoraPresionado = presionado(E, S.deb[E.etiqueta].estado);
    if (ahoraPresionado && !S.emergencia) {
        S.emergencia = true;
        S.linea = "emergencia";
        S.contadores.emergencias++;
        S.purga_hasta = 0;
        if (S.fifo.length) {
            S.contadores.descartadas_emergencia += S.fifo.length;
            evento("cajas_descartadas_por_emergencia", { cajas: S.fifo.map(k => k.id) });
        }
        S.fifo = [];
        S.desvio_activo = null;
        S.desviador_ocupado = null;
        S.cola_esc = [];                    // lo que estuviera en cola ya no se manda
        const apaga = [];
        if (R.velocidad) apaga.push([R.velocidad, 0]);
        if (R.emisor) apaga.push([R.emisor, false]);
        for (const a of R.alimentacion) apaga.push([a, false]);
        for (const r of new Set(S.clases.map(k => k.salida).concat(S.motriz ? [S.motriz] : []))) apaga.push([r, false]);
        for (const [et, v] of apaga) out[1].push(escritura(et, v, "emergencia"));
        evento("paro_de_emergencia", { etiqueta: E.etiqueta, apaga: apaga.map(x => x[0]) });
    } else if (!ahoraPresionado && S.emergencia) {
        S.emergencia = false;
        S.linea = "detenida";
        evento("emergencia_liberada", { etiqueta: E.etiqueta, linea: "detenida" });
    }
}

function logica(pesoV) {
    const L = c.linea, k = L.k_banda_m_s_por_V;
    for (const f of S.ciclo.flancos || []) {
        if (f.s === R.salida && f.valor) {
            const caja = S.fifo.shift();
            if (!caja) {
                S.contadores.fantasmas++;
                evento("caja_fantasma", { sensor: R.salida, ts: f.ts });
            } else {
                const fallido = caja.estado === "rechazo_pendiente" || caja.estado === "rechazo_fallido";
                if (fallido) S.contadores.rechazos_fallidos++;
                S.contadores.salidas++;
                pasoCaja(caja, "salida", f.ts, fallido);
            }
        } else if (f.s === R.bascula && f.valor) {
            const caja = S.fifo.find(x => x.masa === null && !x.pesando);
            if (!caja) {
                S.contadores.fantasmas_bascula++;
                evento("caja_fantasma", { sensor: R.bascula, ts: f.ts });
            } else {
                caja.pesando = true;
                S.pesaje = { caja: caja.id, muestras: [] };
            }
        } else if (f.s === R.bascula && !f.valor) {
            if (S.pesaje) cierraPesaje(f.t);
        } else if (f.s === R.entrada && f.valor) {
            const caja = { id: S.proxima_caja++, ts_entrada: f.ts, t_entrada: f.t, masa: null, peso_V: null,
                           estable: null, clase: null, estado: "en_tramo", t_marcha_s: 0 };
            S.fifo.push(caja);
            S.contadores.entradas++;
            evento("caja_entra", { caja: caja.id, ts_entrada: f.ts });
        } else if (f.s === R.lim_frontal && f.valor) {
            const E = S.empujador, T = S.empujador_tardio;
            if (E.estado === "reposo" && T && Date.now() - T.t < 10000) {
                S.empujador_tardio = null;
                const i = S.fifo.findIndex(x => x.id === T.caja);
                if (i >= 0) {
                    const caja = S.fifo.splice(i, 1)[0];
                    S.contadores.rechazos++;
                    evento("confirmacion_tardia", { caja: caja.id });
                    pasoCaja(caja, "rechazo", f.ts, false);
                }
            } else if (E.estado === "extendiendo") {
                const i = S.fifo.findIndex(x => x.id === E.caja);
                if (i >= 0) {
                    const caja = S.fifo.splice(i, 1)[0];
                    S.contadores.rechazos++;
                    pasoCaja(caja, "rechazo", f.ts, false);
                }
                S.empujador = { estado: "retrayendo", caja: E.caja, t: Date.now(), timer: null };
                out[1].push(escritura(R.empujador, false, "retrae", { caja: E.caja }));
            }
        } else if (f.s === R.lim_trasero && f.valor) {
            if (S.empujador.estado === "retrayendo") S.empujador = { estado: "reposo", caja: null, t: 0, timer: null };
        }
    }

    // ---- muestra de peso ---------------------------------------------------------------
    if (S.pesaje && pesoV !== null) {
        const p = S.pesaje;
        p.muestras.push(pesoV);
        const caja = S.fifo.find(x => x.id === p.caja);
        const n = c.bascula.muestras_estables;
        if (caja && caja.masa === null && p.muestras.length >= n) {
            const ult = p.muestras.slice(-n);
            if (Math.max(...ult) - Math.min(...ult) <= c.bascula.banda_estable_V) {
                // Se retiene la ULTIMA lectura de la ventana, no el promedio: la
                // bascula se asienta desde abajo y el promedio arrastra el tramo
                // que aun subia (primera prueba: -0.08 y -0.15 kg, siempre abajo).
                const v = ult[n - 1];
                caja.peso_V = Math.round(v * 1000) / 1000;
                caja.masa = Math.round(v / 10 * c.bascula.plena_escala_kg * 1000) / 1000;
                caja.estable = true;
            }
        }
    }

    // ---- cajas que no salen --------------------------------------------------------------
    const dtS = S.ultima_logica_ms ? (ahora - S.ultima_logica_ms) / 1000 : 0;
    S.ultima_logica_ms = ahora;
    const vC = S.vel_aplicada_V * k;
    if (S.linea === "en_marcha" && S.alimentacion && vC > 0) {
        const esperado = L.entrada_a_fin_bascula_m / L.alimentacion_m_s + L.bascula_a_salida_m / vC;
        const limite = 1.5 * esperado + 3 * S.lim.t_ef_ms / 1000;
        for (const caja of S.fifo.slice()) {
            caja.t_marcha_s += dtS;
            if (caja.t_marcha_s > limite) {
                S.fifo.splice(S.fifo.indexOf(caja), 1);
                S.contadores.perdidas++;
                evento("caja_perdida", { caja: caja.id, ts_entrada: caja.ts_entrada,
                                         en_marcha_s: Math.round(caja.t_marcha_s * 10) / 10,
                                         limite_s: Math.round(limite * 10) / 10 });
                if (R.alerta) out[1].push(escritura(R.alerta, true, "alerta_caja_perdida"));
            }
        }
    }
}

function cierraPesaje(tFuera) {
    const p = S.pesaje;
    S.pesaje = null;
    const caja = S.fifo.find(x => x.id === p.caja);
    if (!caja) return;
    caja.pesando = false;
    if (caja.masa === null) {
        if (p.muestras.length) {
            const v = p.muestras[p.muestras.length - 1];
            caja.peso_V = Math.round(v * 1000) / 1000;
            caja.masa = Math.round(v / 10 * c.bascula.plena_escala_kg * 1000) / 1000;
        }
        caja.estable = false;
    }
    const cl = c.clasificacion;
    caja.clase = (caja.masa !== null && Math.abs(caja.masa - cl.masa_nominal_kg) <= cl.tolerancia_kg) ? "dentro" : "fuera";
    evento("caja_pesada", { caja: caja.id, masa_kg: caja.masa, peso_V: caja.peso_V, estable: caja.estable,
                            muestras: p.muestras.length, clase: caja.clase });
    if (caja.clase === "fuera") programaEmpujador(caja, tFuera);
}

function programaEmpujador(caja, tFuera) {
    const vC = S.vel_aplicada_V * c.linea.k_banda_m_s_por_V;
    if (!(vC > 0)) {
        caja.estado = "rechazo_fallido";
        evento("rechazo_imposible", { caja: caja.id, motivo: "banda detenida" });
        return;
    }
    // La caja dejo la bascula en algun momento entre la lectura anterior y la
    // primera que la vio fuera: se toma la mitad de ese intervalo. Al llegar al
    // empujador debe haber avanzado bascula_a_empujador_m.
    const rttMed = mediana(S.estadistica.rtt_ms.slice(-50)) || S.rtt_previsto_ms;
    const tGolpe = tFuera - S.sondeo_ms / 2 + c.linea.bascula_a_empujador_m / vC * 1000;
    const tOrden = tGolpe - rttMed / 2 - c.empujador.alcance_s * 1000;
    const espera = Math.max(0, tOrden - Date.now());
    caja.estado = "rechazo_pendiente";
    evento("rechazo_programado", { caja: caja.id, orden_en_ms: Math.round(espera), tarde: tOrden < Date.now() });
    const id = caja.id;
    const t = setTimeout(() => {
        const S2 = flow.get("planta");
        if (!S2) return;
        S2.timers = (S2.timers || []).filter(x => x !== t);
        const caja2 = S2.fifo.find(x => x.id === id);
        const ev = [];
        if (!caja2) return;
        if (S2.com !== "ok" || S2.empujador.estado !== "reposo") {
            caja2.estado = "rechazo_fallido";
            ev.push({ ts: new Date().toISOString(), arranque: S2.arranque, ev: "rechazo_no_ejecutado", caja: id,
                      motivo: S2.com !== "ok" ? S2.com : `empujador ${S2.empujador.estado}` });
            node.send([null, null, archivoEventos(ev), null]);
            return;
        }
        S2.empujador = { estado: "extendiendo", caja: id, t: Date.now(), timer: null };
        node.send([null, [escritura(R.empujador, true, "rechazo", { caja: id })], null, null]);
    }, espera);
    S.timers = (S.timers || []).concat([t]);
}

function pasoCaja(caja, destino, tsSalida, rechazoFallido) {
    const p = {
        ev: "paso_caja", caja: caja.id, masa_kg: caja.masa, peso_V: caja.peso_V, peso_estable: caja.estable,
        clase: caja.clase, destino: destino, rechazo_fallido: !!rechazoFallido,
        ts_entrada: caja.ts_entrada, ts_salida: tsSalida,
        cajas_acumuladas: S.contadores.salidas + S.contadores.rechazos,
        vel_banda_V: S.vel_aplicada_V
    };
    if (S.contadores.por_destino[destino] !== undefined) S.contadores.por_destino[destino]++;
    S.ultima_caja = { caja: caja.id, masa_kg: caja.masa, destino: destino, ts: tsSalida };
    // Instantes de los ultimos pasos, para las cajas por minuto de la HMI.
    S.pasos_ms = (S.pasos_ms || []).filter(t => Date.now() - t < 60000).concat([Date.now()]);
    // Las ultimas 30 masas con su destino, para el diagnostico (C7).
    S.ultimas_masas = (S.ultimas_masas || []).concat([{ kg: caja.masa, destino: destino }]).slice(-30);
    if (!S.marcha_desde && S.linea === "en_marcha") S.marcha_desde = Date.now();
    evento("paso_caja", p);
    out[3].push({ payload: p, topic: "paso_caja" });
}

// =========================================================================================
// Desviador de ruedas (escena Sorting by Weight): la caja entra a la bascula
// (flanco de subida de `entrada`), se pesa mientras va sobre ella (de la
// bajada de `entrada` a la subida de `fin_bascula`), al llegar a
// `fin_bascula` se clasifica y se mandan las ruedas a la salida de su clase,
// y se confirma con el sensor de entrada de esa salida. La cola es FIFO: si
// confirma un sensor que no es el esperado por la caja mas vieja, la caja
// salio por otro lado (desvio erroneo) y se cuenta como tal.
function logicaDesviador(pesoV) {
    const L = c.linea, B = c.bascula, D = S.detenido;
    for (const f of S.ciclo.flancos || []) {
        const claseConf = S.clases.find(k => k.confirma === f.s);
        if (claseConf && f.valor) {
            const caja = S.fifo.find(x => x.estado === "desviando");
            if (!caja && ahora < (S.purga_hasta || 0) + 1000) {
                // La caja que estaba parada sobre el desviador al arrancar.
                S.contadores.purgadas++;
                evento("caja_purgada", { sensor: f.s, ts: f.ts });
                continue;
            }
            if (!caja) {
                S.contadores.fantasmas++;
                evento("caja_fantasma", { sensor: f.s, ts: f.ts });
                continue;
            }
            S.fifo.splice(S.fifo.indexOf(caja), 1);
            const erroneo = caja.confirma !== f.s;
            if (erroneo) {
                S.contadores.desvios_erroneos++;
                evento("desvio_erroneo", { caja: caja.id, esperado: caja.destino, real: claseConf.destino });
                if (R.alerta) out[1].push(escritura(R.alerta, true, "alerta_desvio_erroneo"));
            }
            S.contadores.salidas++;
            pasoCaja(caja, claseConf.destino, f.ts, erroneo);
            // La caja entro a su rama pero su cola puede seguir sobre el
            // desviador: las ruedas no cambian hasta que el sensor baje.
            S.desviador_ocupado = { sensor: f.s, caja: caja.id, t: ahora };
        } else if (claseConf && !f.valor) {
            if (S.desviador_ocupado && S.desviador_ocupado.sensor === f.s) S.desviador_ocupado = null;
        } else if (D && f.s === R.entrada) {
            // Con pesaje detenido la caja nace al llegar a la bascula: en la
            // escena las cajas se forman pegadas en la entrada y su sensor no
            // baja entre una y otra.
            continue;
        } else if (f.s === R.entrada && f.valor) {
            const caja = { id: S.proxima_caja++, ts_entrada: f.ts, t_entrada: f.t, masa: null, peso_V: null,
                           estable: null, clase: null, estado: "entrando", t_marcha_s: 0, muestras: [] };
            S.fifo.push(caja);
            S.contadores.entradas++;
            evento("caja_entra", { caja: caja.id, ts_entrada: f.ts });
        } else if (f.s === R.entrada && !f.valor) {
            const caja = S.fifo.find(x => x.estado === "entrando");
            if (caja) caja.estado = "en_bascula";
        } else if (D && f.s === R.en_bascula && f.valor) {
            if (S.linea !== "en_marcha") continue;
            if (S.fifo.some(x => x.estado === "separando" || x.estado === "pesando" || x.estado === "pesado")) {
                S.contadores.fantasmas_bascula++;          // otra caja ya esta en la bascula
                evento("caja_fantasma", { sensor: R.en_bascula, ts: f.ts });
                continue;
            }
            const caja = { id: S.proxima_caja++, ts_entrada: f.ts, t_entrada: f.t, masa: null, peso_V: null,
                           estable: null, clase: null, estado: "separando", t_llega: ahora, t_marcha_s: 0, muestras: [] };
            S.fifo.push(caja);
            S.contadores.entradas++;
            evento("caja_entra", { caja: caja.id, ts_entrada: f.ts, sensor: R.en_bascula });
            // La entrada para ya. La bascula para despues: si la caja anterior
            // (ya soltada) sigue sobre ella, cuando la deje (baja fin_bascula);
            // si se parara ahora, esa caja se atora entre la bascula y el
            // desviador. Pasa con cajas que llegan pegadas.
            for (const b of D.detiene) out[1].push(escritura(b, false, "pesaje", { caja: caja.id }));
        } else if (D && f.s === R.fin_bascula && !f.valor) {
            const sale = S.fifo.find(x => x.estado === "desviando" && !x.fuera_bascula);
            if (sale) sale.fuera_bascula = true;
            // La caja dejo la bascula: vuelve a entrar la siguiente.
            if (S.linea === "en_marcha" && !S.fifo.some(x => ["separando", "pesando", "pesado"].includes(x.estado))) {
                for (const b of D.reanuda_al_salir) out[1].push(escritura(b, true, "reanuda"));
            }
        } else if (!D && f.s === R.fin_bascula && f.valor) {
            const caja = S.fifo.find(x => x.estado === "en_bascula" || x.estado === "entrando");
            if (!caja) {
                S.contadores.fantasmas_bascula++;
                evento("caja_fantasma", { sensor: R.fin_bascula, ts: f.ts });
                continue;
            }
            clasificaYDesvia(caja);
        }
    }

    // ---- pesaje detenido: mediana con la caja quieta, y se suelta ------------------
    if (D) {
        const sep = S.fifo.find(x => x.estado === "separando");
        if (sep && ahora - sep.t_llega >= (D.separa_ms || 0) &&
            !S.fifo.some(x => x.estado === "desviando" && !x.fuera_bascula)) {
            for (const b of D.separa || []) out[1].push(escritura(b, false, "pesaje", { caja: sep.id }));
            sep.estado = "pesando";
            sep.t_paro = ahora;
        }
        const caja = S.fifo.find(x => x.estado === "pesando");
        if (caja && pesoV !== null && pesoV !== undefined && ahora - caja.t_paro >= D.espera_ms) {
            caja.muestras.push(pesoV);
            const ult = caja.muestras.slice(-D.muestras);
            const estable = ult.length === D.muestras && Math.max(...ult) - Math.min(...ult) <= B.banda_estable_V;
            // Si la ventana no cabe en la banda se sigue leyendo, hasta espera_max_ms.
            if (estable || (ult.length === D.muestras && ahora - caja.t_paro >= (D.espera_max_ms || D.espera_ms))) {
                const v = mediana(ult);
                caja.peso_V = Math.round(v * 1000) / 1000;
                caja.masa = Math.round(v / 10 * B.plena_escala_kg * 1000) / 1000;
                caja.estable = estable;
                caja.estado = "pesado";
            }
        }
        // Se suelta solo con el desviador libre: cambiar las ruedas con otra
        // caja encima la mandaria por la salida de esta.
        const lista = S.fifo.find(x => x.estado === "pesado");
        if (lista && S.linea === "en_marcha" && !S.fifo.some(x => x.estado === "desviando") && !S.desviador_ocupado &&
            ahora >= (S.purga_hasta || 0)) {
            clasificaYDesvia(lista);
            for (const b of D.suelta) out[1].push(escritura(b, true, "suelta", { caja: lista.id }));
        }
    }

    // ---- muestra de peso: va a la caja que esta sobre la bascula -------------------
    if (!D && pesoV !== null && pesoV !== undefined) {
        const caja = S.fifo.find(x => x.estado === "en_bascula");
        if (caja) {
            caja.muestras.push(pesoV);
            const n = B.muestras_estables, ult = caja.muestras.slice(-n);
            if (caja.masa === null && ult.length === n && Math.min(...ult) >= (B.minimo_V || 0) &&
                Math.max(...ult) - Math.min(...ult) <= B.banda_estable_V) {
                caja.peso_V = Math.round(ult[n - 1] * 1000) / 1000;
                caja.masa = Math.round(ult[n - 1] / 10 * B.plena_escala_kg * 1000) / 1000;
                caja.estable = true;
            }
        }
    }

    // ---- cajas que no llegan a la salida de la bascula ------------------------------
    const dtS = S.ultima_logica_ms ? (ahora - S.ultima_logica_ms) / 1000 : 0;
    S.ultima_logica_ms = ahora;
    if (S.linea === "en_marcha") {
        const limite = S.lim.limite_fin_bascula_s;                // 26_planta_config.js (paso H)
        for (const caja of S.fifo.slice()) {
            if (caja.estado === "desviando") continue;          // de esas se ocupa 27_planta_ciclo.js
            // Con pesaje detenido las bandas paran: el reloj corre solo con ellas andando.
            if (D && S.fifo.some(x => ["separando", "pesando", "pesado"].includes(x.estado))) continue;
            caja.t_marcha_s += dtS;
            if (caja.t_marcha_s > limite) {
                S.fifo.splice(S.fifo.indexOf(caja), 1);
                S.contadores.perdidas++;
                evento("caja_perdida", { caja: caja.id, motivo: "no_llego_a_fin_bascula",
                                         en_marcha_s: Math.round(caja.t_marcha_s * 10) / 10 });
                if (R.alerta) out[1].push(escritura(R.alerta, true, "alerta_caja_perdida"));
            }
        }
    }
}

function clasificaYDesvia(caja) {
    const B = c.bascula;
    if (caja.masa === null) {
        if (caja.muestras.length) {
            // Sin ventana estable: la lectura mas alta, que es la del tramo ya asentado.
            const v = Math.max(...caja.muestras);
            caja.peso_V = Math.round(v * 1000) / 1000;
            caja.masa = Math.round(v / 10 * B.plena_escala_kg * 1000) / 1000;
        }
        caja.estable = false;
    }
    const k = caja.masa === null ? S.clases[S.clases.length - 1]
        : S.clases.find(x => x.hasta_kg === null || x.hasta_kg === undefined || caja.masa <= x.hasta_kg);
    caja.clase = k.nombre;
    caja.destino = k.destino;
    caja.confirma = k.confirma;
    caja.estado = "desviando";
    caja.t_desvio = Date.now();
    evento("caja_pesada", { caja: caja.id, masa_kg: caja.masa, peso_V: caja.peso_V, estable: caja.estable,
                            muestras: caja.muestras.length, clase: k.nombre, destino: k.destino });
    const otra = S.fifo.find(x => x !== caja && x.estado === "desviando" && x.destino !== k.destino);
    if (otra) evento("desvio_en_conflicto", { caja: caja.id, pendiente: otra.id, destino_pendiente: otra.destino });
    // Primero se apagan las otras salidas y luego se enciende la de la clase,
    // para que nunca queden dos encendidas a la vez.
    // Con motriz (Factory I/O), la motriz queda encendida junto con la de la clase.
    const enciende = S.motriz ? [...new Set([S.motriz, k.salida])] : [k.salida];
    for (const x of S.clases) if (!enciende.includes(x.salida)) out[1].push(escritura(x.salida, false, "desvio", { caja: caja.id }));
    for (const s of enciende) out[1].push(escritura(s, true, "desvio", { caja: caja.id }));
    S.desvio_activo = k.salida;
    if (!k.confirma) {
        // Salida sin sensor propio: no hay con que confirmar. Se da por buena y
        // se marca; la consistencia no la cubre.
        S.fifo.splice(S.fifo.indexOf(caja), 1);
        S.contadores.salidas++;
        S.contadores.sin_confirmar++;
        pasoCaja(caja, k.destino, new Date().toISOString(), false);
    }
}
