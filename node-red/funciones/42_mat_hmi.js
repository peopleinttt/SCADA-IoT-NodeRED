/* Nodo: "tarjeta Materials layer"  (A2 · Materiales, paso M2)
 * ---------------------------------------------------------------
 * Arma lo que muestra la tarjeta "Materials layer" de la HMI, en ingles. Llega
 * a la plantilla por el enlace a2_mat_hmi (link out de esta pestana, link in
 * de A2-HMI), nunca por el contexto global. Se dispara con cada paso guardado
 * (41) y cada 2 s (inject), para que la tarjeta aparezca tambien al recargar
 * la pagina. Sin A2_MATERIALES=1 no manda nada, y la tarjeta no aparece.
 *
 * Por varilla: vida consumida en % (D x 100, un decimal), nivel, pasos dentro,
 * por debajo y por encima del intervalo, ultimo rango de deformacion medido y
 * la estimacion de pasos y tiempo restantes hasta D = 1, o "no estimate yet"
 * mientras no haya al menos 100 pasos evaluados y uno con dano en esa varilla.
 * Estimacion: ritmo medio de dano (D / pasos evaluados) y tiempo medio por paso
 * (primer a ultimo ts_salida).
 */
if (env.get("A2_MATERIALES") !== "1") return null;
const ETIQUETA = { normal: "normal", preventiva: "preventive", critica: "critical", falla: "failure" };
const bloqueo = flow.get("mat_bloqueo") || null;
// El motivo interno va en espanol (registro y estado del nodo); en pantalla, en ingles.
function enIngles(m) {
    const t = [["archivo de estado ilegible", "state file unreadable"],
               ["archivo de estado de otra version de configuracion", "state file from another configuration version"], ["configuracion ilegible", "configuration file unreadable"],
               ["configuracion invalida", "invalid configuration"], ["no se pudo escribir", "could not write the data files"]];
    for (const [es, en] of t) if (m.startsWith(es)) return en + " (see Node-RED log)";
    return "see Node-RED log";
}
const E = flow.get("mat_estado");
const H = flow.get("mat_hmi") || { evaluados: 0, piezas: {} };
const cfg = flow.get("mat_cfg");

const rods = (E && cfg) ? E.laminados.map((L, i) => {
    const P = H.piezas[L.pieza] || { con_danio: 0, cambios: [], alertas: 0 };
    let estimate = null;
    if (H.evaluados >= 100 && P.con_danio >= 1 && L.D > 0) {
        const pasosRest = L.D >= 1 ? 0 : (1 - L.D) / (L.D / H.evaluados);
        const dur = (Date.parse(H.ultimo_ts) - Date.parse(H.primer_ts)) / 1000;
        const sPorPaso = H.evaluados > 1 ? dur / (H.evaluados - 1) : null;
        estimate = { steps: Math.round(pasosRest), seconds: sPorPaso === null ? null : Math.round(pasosRest * sPorPaso) };
    }
    const ult = P.cambios.length ? P.cambios[P.cambios.length - 1] : null;
    return {
        rod: L.pieza, laminate: L.id, lifePct: Math.round(L.D * 1000) / 10, D: L.D,
        level: L.nivel, levelLabel: ETIQUETA[L.nivel] || L.nivel,
        inside: L.conteos.dentro, below: L.conteos.bajo, above: L.conteos.sobre,
        lastStrainRangeUe: P.ultimo_rango_ue === undefined ? null : Math.round(P.ultimo_rango_ue * 10) / 10,
        estimate: estimate,
        lastLevelChange: ult ? { level: ETIQUETA[ult.nivel] || ult.nivel, step: ult.paso, ts: ult.ts } : null,
        levelChanges: P.cambios.map(x => ({ level: ETIQUETA[x.nivel] || x.nivel, step: x.paso })),
        alert: P.alertas ? { code: "carga_fuera_del_intervalo", text: "load above the tested range", count: P.alertas,
                             lastStep: P.ultima_alerta ? P.ultima_alerta.paso : null } : null
    };
}) : [];

msg.topic = "materiales";
msg.payload = {
    materials: true, ts: new Date().toISOString(),
    error: bloqueo ? "NOT accumulating: " + enIngles(bloqueo) : null,
    steps: E ? E.pasos : 0, noWeight: E ? E.sin_peso : 0, evaluated: H.evaluados, rods: rods
};
return msg;
