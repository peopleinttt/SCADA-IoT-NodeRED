/* Nodo: "estado para la HMI"  (A2-HMI, cada 0.5 s)
 * ---------------------------------------------------------------
 * Junta en un mensaje lo que la pagina muestra: el resumen de A2-Planta, el
 * ultimo registro aceptado por Firebase (A2-Nube), el ultimo diagnostico
 * (A2-Diagnostico, si existe) y, si la cadena del ESP32 de la Actividad 1
 * esta corriendo, su ultima telemetria. Esa sale de la ultima linea del CSV
 * de instrumentacion que escribe la Actividad 1 ($DATOS_DIR/ingesta_DIA.csv),
 * para no tocar sus pestanas; se muestra solo si tiene menos de 60 s.
 * Todo lo que se ve va en ingles (regla 7 de la fase 2).
 */
const P = global.get("a2_planta_resumen");
const N = global.get("a2_nube_resumen") || {};
const D = global.get("a2_diag_ultimo") || null;

let esp32 = null;
try {
    const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
    const zona = env.get("TZ_REPORTE") || "America/Mexico_City";
    const dia = new Intl.DateTimeFormat("en-CA", { timeZone: zona, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
    const ruta = `${dir}/ingesta_${dia}.csv`;
    const st = fs.statSync(ruta);
    if (Date.now() - st.mtimeMs < 60000) {
        const lineas = fs.readFileSync(ruta, "utf8").trim().split("\n");
        const c = lineas[lineas.length - 1].split(";");
        if (c[8] === "ok") esp32 = { ts: c[1], temperature_C: Number(c[5]), vibration_mm_s: Number(c[6]), cycles: Number(c[7]) };
    }
} catch (e) { /* sin CSV de hoy: la cadena del ESP32 no esta corriendo */ }
global.set("a2_esp32_ultima", esp32);       // el diagnostico (C7) la usa si esta

if (!P) {
    msg.topic = "estado";
    msg.payload = { ready: false, esp32: esp32 };
    return msg;
}
const comLabel = { ok: "Online", sin_comunicacion: "NO COMMUNICATION", reconectando: "Reconnecting (safe state)",
                   iniciando: "Starting" }[P.com] || P.com;
msg.topic = "estado";
msg.payload = {
    ready: true, ts: new Date().toISOString(),
    actuator: P.actuador, variableBelt: !!P.banda_variable,
    comm: P.com, commLabel: comLabel, line: P.linea === "en_marcha" ? "Running" : P.linea === "emergencia" ? "Emergency stop" : "Stopped", running: P.linea === "en_marcha",
    emitter: !!P.emisor, setpointV: P.consigna_V, appliedV: P.vel_aplicada_V,
    velMinV: P.limites ? P.limites.vel_min_V : null, velMaxV: P.limites ? P.limites.vel_max_V : null,
    feasible: P.limites ? !!P.limites.factible : false, problems: P.problemas || [],
    pollMs: P.sondeo_ms, rttMs: P.rtt_previsto_ms, tEfMs: P.limites ? P.limites.t_ef_ms : null,
    boxesIn: P.contadores.entradas, boxesOut: P.cajas_acumuladas, perMinute: P.cajas_por_minuto,
    byDestination: P.contadores.por_destino, lost: P.contadores.perdidas + P.contadores.perdidas_desconexion,
    misrouted: P.contadores.desvios_erroneos || 0,
    lastBox: P.ultima_caja ? { id: P.ultima_caja.caja, massKg: P.ultima_caja.masa_kg, destination: P.ultima_caja.destino,
                               ts: P.ultima_caja.ts } : null,
    firebase: N.ultimo_aceptado ? { ts: N.ultimo_aceptado.ts, kind: N.ultimo_aceptado.tipo === "caja" ? "box" : "heartbeat",
                                    id: N.ultimo_aceptado.registro_id } : null,
    firebaseLast: N.ultimo_intento ? { code: N.ultimo_intento.codigo, ts: N.ultimo_intento.ts } : null,
    firebaseOn: env.get("A2_NUBE") === "1",
    diagnosis: D, esp32: esp32
};
return msg;
