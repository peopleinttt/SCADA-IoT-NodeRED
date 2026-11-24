/* Nodo: "estado de la planta"  (A2-Planta)
 * GET /a2/planta/estado -> resumen en JSON: comunicacion, linea, limites,
 * cola, contadores y periodo efectivo del sondeo. Mismo filtro de origen que
 * los comandos.
 */
const S = flow.get("planta");
const h = (msg.req && msg.req.headers) || {};
const ip = String((msg.req && (msg.req.ip || (msg.req.socket && msg.req.socket.remoteAddress))) || "").replace(/^::ffff:/, "");
const tailnet = /^100\.(\d+)\./.exec(ip);
const local = ip === "127.0.0.1" || ip === "::1" || (tailnet && Number(tailnet[1]) >= 64 && Number(tailnet[1]) <= 127);
if (h["cf-connecting-ip"] || h["cf-ray"] || h["x-forwarded-for"] || !local) {
    msg.statusCode = 403;
    msg.payload = { ok: false, motivo: "origen_no_permitido" };
    return msg;
}
if (!S) {
    msg.statusCode = 503;
    msg.payload = { ok: false, motivo: "planta_no_configurada" };
    return msg;
}
function resumen(a) {
    if (!a.length) return null;
    const o = a.slice().sort((x, y) => x - y);
    const q = p => o[Math.min(o.length - 1, Math.floor(p * (o.length - 1)))];
    const media = o.reduce((s, x) => s + x, 0) / o.length;
    const sd = Math.sqrt(o.reduce((s, x) => s + (x - media) ** 2, 0) / o.length);
    return { n: o.length, min: o[0], p50: q(0.5), p95: q(0.95), max: o[o.length - 1],
             media: Math.round(media * 10) / 10, sd: Math.round(sd * 10) / 10 };
}
msg.statusCode = 200;
msg.payload = {
    ok: true, actuador: S.actuador, roles: S.roles, clases: S.clases, ultima_caja: S.ultima_caja || null,
    com: S.com, linea: S.linea, emergencia: !!S.emergencia, tablero_escrito: S.tablero_escrito || {}, consigna_V: S.consigna_V, vel_aplicada_V: S.vel_aplicada_V,
    emisor: S.emisor, alimentacion: S.alimentacion,
    sondeo_ms: S.sondeo_ms, rtt_previsto_ms: S.rtt_previsto_ms, limites: S.lim,
    en_tramo: S.fifo.map(k => ({ id: k.id, masa_kg: k.masa, clase: k.clase, estado: k.estado })),
    contadores: S.contadores,
    balance: { entradas: S.contadores.entradas,
               salidas_mas_rechazos_mas_en_tramo_mas_perdidas: S.contadores.salidas + S.contadores.rechazos +
                   S.fifo.length + S.contadores.perdidas + S.contadores.perdidas_desconexion +
                   (S.contadores.descartadas_emergencia || 0) },
    periodo_efectivo_ms: resumen(S.estadistica.periodos_ms),
    rtt_medido_ms: resumen(S.estadistica.rtt_ms),
    min_lecturas_por_pulso: S.estadistica.min_muestras_encendido,
    empujador: { estado: S.empujador.estado, caja: S.empujador.caja },
    crudo: S.crudo || null
};
return msg;
