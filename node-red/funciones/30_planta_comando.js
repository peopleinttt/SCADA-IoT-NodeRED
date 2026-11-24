/* Nodo: "comando de operacion"  (A2-Planta, 4 salidas)
 *   0 -> respuesta HTTP (POST /a2/planta/comando)
 *   1 -> escrituras al Flex-Write
 *   2 -> eventos al archivo de la corrida
 *   3 -> respuesta a la HMI (llamada interna, sin msg.req), con el mismo codigo
 * ---------------------------------------------------------------
 * POST /a2/planta/comando  {"accion": "marcha" | "paro" | "emisor" | "velocidad", ...}
 *   marcha               alimentacion_on = 1 y vel_banda_V = consigna
 *   paro                 vel_banda_V = 0, emisor_on = 0, alimentacion_on = 0
 *   emisor  {"valor":b}  emisor_on (encenderlo solo con la linea en marcha)
 *   velocidad {"vel_V"}  consigna 0 (paro) o dentro de [vel_min_V, vel_max_V]; si la linea esta
 *                        en marcha se aplica ya. Entre 0 y vel_min_V tampoco: dos cajas se
 *                        funden en una sola lectura (ver tools/limites_planta.py)
 *   marcha               solo con limites factibles (409) y consigna dentro del intervalo (422)
 *
 * La HMI de C6 llama a esta misma funcion. Solo se aceptan peticiones locales
 * o de la tailnet: el tunel de Cloudflare de la Actividad 1 publica el 1881 en
 * Internet, y por ahi entraria cualquiera a mover la planta.
 */
const S = flow.get("planta");
const M = global.get("a2_mapa");

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
function responde(codigo, cuerpo) {
    msg.statusCode = codigo;
    msg.payload = cuerpo;
    return msg.req ? [msg, null, null, null] : [null, null, null, { topic: "respuesta", payload: Object.assign({ codigo: codigo }, cuerpo) }];
}
function permitido(req) {
    if (!req) return true;                                  // llamada interna (HMI)
    const h = req.headers || {};
    if (h["cf-connecting-ip"] || h["cf-ray"] || h["x-forwarded-for"]) return false;
    const ip = String(req.ip || (req.socket && req.socket.remoteAddress) || "").replace(/^::ffff:/, "");
    if (ip === "127.0.0.1" || ip === "::1") return true;
    const m = ip.match(/^100\.(\d+)\./);                    // 100.64.0.0/10, Tailscale
    return !!m && Number(m[1]) >= 64 && Number(m[1]) <= 127;
}
if (!permitido(msg.req)) return responde(403, { ok: false, motivo: "origen_no_permitido" });
if (!S || !M) return responde(503, { ok: false, motivo: "planta_no_configurada" });
if (S.com !== "ok") return responde(409, { ok: false, motivo: "sin_comunicacion", com: S.com });

const cmd = (msg.payload && typeof msg.payload === "object") ? msg.payload : {};
const escrituras = [];
function escritura(etiqueta, valor, motivo) {
    const e = M.por_nombre[etiqueta];
    const palabra = e.tipo === "bool" ? !!valor : (Math.round(valor * e.escala) & 0xFFFF);
    escrituras.push({ payload: { value: palabra, fc: e.tabla === "bobina" ? 5 : 6,
                                 unitid: Number(env.get("PLANTA_UNIDAD")), address: e.direccion, quantity: 1 },
                      escritura: { etiqueta: etiqueta, valor: valor, motivo: motivo, t: Date.now() } });
}

function dentro(v) {
    return S.lim.vel_min_V !== null && v >= S.lim.vel_min_V && v <= S.lim.vel_max_V;
}

const R = S.roles;
switch (cmd.accion) {
    case "velocidad": {
        if (!R.velocidad || !S.lim.banda_variable) {
            return responde(422, { ok: false, motivo: "velocidad_no_aplica",
                                   detalle: "las bandas de esta escena son de velocidad fija" });
        }
        const v = Number(cmd.vel_V);
        if (!Number.isFinite(v) || (v !== 0 && !dentro(v))) {
            return responde(422, { ok: false, motivo: "velocidad_fuera_de_limite", vel_V: cmd.vel_V,
                                   permitido: { paro: 0, intervalo: [S.lim.vel_min_V, S.lim.vel_max_V] },
                                   detalle: `con sondeo ${S.sondeo_ms} ms y rtt ${S.rtt_previsto_ms} ms cada sensor ` +
                                            `se ve ${S.cfg.periodos_minimos} lecturas encendido y apagado solo entre ` +
                                            `${S.lim.vel_min_V} y ${S.lim.vel_max_V} V` });
        }
        S.consigna_V = Math.round(v * 100) / 100;
        if (S.linea === "en_marcha") escritura(R.velocidad, S.consigna_V, "consigna");
        break;
    }
    case "marcha":
        if (S.emergencia) return responde(409, { ok: false, motivo: "paro_de_emergencia" });
        if (!S.lim.factible) {
            return responde(409, { ok: false, motivo: "limites_no_factibles", problemas: S.lim.problemas,
                                   sondeo_ms: S.sondeo_ms, rtt_previsto_ms: S.rtt_previsto_ms });
        }
        if (S.lim.banda_variable && !dentro(S.consigna_V)) {
            return responde(422, { ok: false, motivo: "consigna_fuera_de_intervalo", consigna_V: S.consigna_V,
                                   intervalo: [S.lim.vel_min_V, S.lim.vel_max_V] });
        }
        S.linea = "en_marcha";
        for (const a of R.alimentacion) escritura(a, true, "marcha");
        if (R.velocidad && S.lim.banda_variable) escritura(R.velocidad, S.consigna_V, "marcha");
        if (S.motriz && S.purga_ms) {
            // Una caja que quedo parada sobre el desviador (ruedas apagadas) se
            // lleva de frente antes de mandar la primera: si no, tomaria la
            // orden de la siguiente caja.
            for (const k of S.clases) if (k.salida !== S.motriz) escritura(k.salida, false, "purga");
            escritura(S.motriz, true, "purga");
            S.purga_hasta = Date.now() + S.purga_ms;
            S.desvio_activo = S.motriz;
        }
        const D = S.detenido;
        if (D && S.deb[R.en_bascula] && S.deb[R.en_bascula].estado === true &&
            !S.fifo.some(x => x.estado === "pesando" || x.estado === "pesado")) {
            // Una caja que ya estaba en la bascula no da flanco: se adopta y se pesa.
            S.fifo.push({ id: S.proxima_caja++, ts_entrada: new Date().toISOString(), t_entrada: Date.now(), masa: null,
                          peso_V: null, estable: null, clase: null, estado: "pesando", t_paro: Date.now(),
                          t_marcha_s: 0, muestras: [], adoptada: true });
            S.contadores.entradas++;
            for (const b of D.detiene.concat(D.separa || [])) escritura(b, false, "pesaje");
        }
        break;
    case "paro":
        S.linea = S.emergencia ? "emergencia" : "detenida";      // el E-stop presionado manda
        S.desviador_ocupado = null;
        if (R.velocidad) escritura(R.velocidad, 0, "paro");
        if (R.emisor) escritura(R.emisor, false, "paro");
        for (const a of R.alimentacion) escritura(a, false, "paro");
        break;
    case "emisor": {
        const on = cmd.valor === true || cmd.valor === 1 || cmd.valor === "1";
        if (on && S.linea !== "en_marcha") return responde(409, { ok: false, motivo: "linea_detenida" });
        if (!R.emisor) return responde(422, { ok: false, motivo: "sin_emisor" });
        escritura(R.emisor, on, "emisor");
        break;
    }
    default:
        return responde(400, { ok: false, motivo: "accion_desconocida", validas: ["marcha", "paro", "emisor", "velocidad"] });
}

const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
const ev = { filename: `${dir}/a2_planta_eventos.jsonl`,
             payload: JSON.stringify({ ts: new Date().toISOString(), arranque: S.arranque, ev: "comando",
                                       accion: cmd.accion, origen: msg.origen || (msg.req ? "http" : "hmi"),
                                       consigna_V: S.consigna_V, linea: S.linea }) };
msg.statusCode = 200;
msg.payload = { ok: true, accion: cmd.accion, linea: S.linea, consigna_V: S.consigna_V };
const envia = encola(escrituras);
if (!msg.req) return [null, envia, ev, { topic: "respuesta", payload: Object.assign({ codigo: 200 }, msg.payload) }];
return [msg, envia, ev, null];
