/* Nodo: "confirma escritura"  (A2-Planta, 2 salidas)
 *   0 -> siguiente escritura de la secuencia segura, al Flex-Write
 *   1 -> eventos al archivo de la corrida
 * ---------------------------------------------------------------
 * Cada escritura viaja con msg.escritura = {etiqueta, valor, motivo}. Aqui se
 * registra lo que la planta YA acepto (vel_aplicada_V, emisor, alimentacion)
 * y se encadena la secuencia segura de reconexion, armada desde los roles en
 * 28_planta_lectura.js (con empujador: vel_banda_V = 0, emisor_on = 0,
 * alimentacion_on = 0; con desviador: emisor y cada banda apagados):
 *     paso 0 --confirmado--> paso 1 --confirmado--> ... --> com = ok
 * Escribirlas en ese orden y una tras otra es el punto: si se mandaran juntas,
 * nada garantiza cual llega primero ni que la segunda no se pierda.
 */
const S = flow.get("planta");
const M = global.get("a2_mapa");
const w = msg.escritura;
if (!S || !M || !w) return null;
const ok = !msg.error && msg.payload !== "";
// Con una peticion a la vez, esta era la que estaba en vuelo: sale la siguiente.
if (S.una) S.esc_en_vuelo = null;
function despacha() {
    if (!S.una || S.esc_en_vuelo || S.ciclo.en_curso || !S.cola_esc.length) return null;
    S.esc_en_vuelo = Date.now();
    return S.cola_esc.shift();
}
const ev = [];
function evento(nombre, extra) {
    ev.push(Object.assign({ ts: new Date().toISOString(), arranque: S.arranque, ev: nombre }, extra || {}));
}
function salida(siguiente) {
    const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
    return [siguiente || null,
            ev.length ? { filename: `${dir}/a2_planta_eventos.jsonl`, payload: ev.map(e => JSON.stringify(e)).join("\n") } : null];
}
function escritura(etiqueta, valor, motivo, paso) {
    const e = M.por_nombre[etiqueta];
    const palabra = e.tipo === "bool" ? !!valor : (Math.round(valor * e.escala) & 0xFFFF);
    return { payload: { value: palabra, fc: e.tabla === "bobina" ? 5 : 6,
                        unitid: Number(env.get("PLANTA_UNIDAD")), address: e.direccion, quantity: 1 },
             escritura: { etiqueta: etiqueta, valor: valor, motivo: motivo, paso: paso, t: Date.now() } };
}

evento(ok ? "escritura" : "escritura_fallida",
       { etiqueta: w.etiqueta, valor: w.valor, motivo: w.motivo, caja: w.caja, ms: Date.now() - w.t,
         error: ok ? undefined : String((msg.error && msg.error.message) || msg.error || "sin respuesta") });

if (!ok) {
    S.contadores.escrituras_fallidas++;
    if (w.motivo === "tablero" && S.tablero_escrito) delete S.tablero_escrito[w.etiqueta];
    if (w.motivo === "seguro") {
        // Sin confirmacion no hay estado seguro: se vuelve a "sin_comunicacion"
        // y la siguiente lectura buena empieza la secuencia otra vez.
        S.com = "sin_comunicacion";
        S.seguro = null;
        evento("reconexion_fallida", { paso: w.etiqueta });
    }
    return salida(despacha());
}

const R = S.roles;
if (w.etiqueta === R.velocidad) S.vel_aplicada_V = w.valor;
if (w.etiqueta === R.emisor) S.emisor = !!w.valor;
if (R.alimentacion.includes(w.etiqueta)) S.alimentacion = !!w.valor;

if (w.motivo === "seguro" && S.com === "reconectando" && S.seguro) {
    const i = S.seguro.i + 1;
    if (i < S.seguro.pasos.length) {
        S.seguro.i = i;
        const p = S.seguro.pasos[i];
        if (S.una) {
            S.cola_esc.unshift(escritura(p.etiqueta, p.valor, "seguro", i));
            return salida(despacha());
        }
        return salida(escritura(p.etiqueta, p.valor, "seguro", i));
    }
    const orden = S.seguro.pasos.map(p => `${p.etiqueta}=${p.valor === false ? 0 : p.valor}`);
    S.com = "ok";
    S.seguro = null;
    S.linea = "detenida";
    S.ultimo_ciclo_ms = null;
    evento("reconexion_completa", { orden: orden, linea: "detenida" });
    node.status({ fill: "green", shape: "dot", text: "comunicacion ok, linea detenida" });
}
return salida(despacha());
