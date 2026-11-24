/* Nodo: "carga mapa"  (A2)
 * ---------------------------------------------------------------
 * Recibe el texto de config/mapa_registros_a2.json y lo deja en global como
 * a2_mapa, indexado por nombre. Va en global y no en flow porque el contexto
 * flow es POR PESTANA (hallazgo de la Actividad 1, BITACORA 4) y el mapa lo
 * leen A2-Sustituto y A2-Planta.
 *
 * La validacion completa es la de tools/mapa_registros.py, que corre en las
 * pruebas. Aqui solo se comprueba que cada etiqueta tenga una direccion real
 * (nunca null: un mapa con direcciones pendientes no se carga). Que esten las
 * etiquetas que cada pestana usa lo comprueba cada una: A2-Planta por sus
 * roles (26_planta_config.js) y el sustituto por su escena (24_sust_emulador.js).
 */

function falla(detalle) {
    node.error(`mapa invalido (${env.get("A2_MAPA")}): ${detalle}`, msg);
    node.status({ fill: "red", shape: "dot", text: "mapa invalido" });
    return null;
}

let mapa;
try {
    mapa = JSON.parse(msg.payload);
} catch (e) {
    return falla(`JSON.parse: ${e.message}`);
}
if (!mapa || !Array.isArray(mapa.etiquetas) || !mapa.driver) return falla("sin etiquetas o sin driver");

const porNombre = {};
for (const e of mapa.etiquetas) {
    if (!Number.isInteger(e.direccion) || e.direccion < 0) return falla(`${e.nombre}: direccion ${e.direccion}`);
    porNombre[e.nombre] = e;
}

global.set("a2_mapa", { version: mapa.version, driver: mapa.driver,
                        etiquetas: mapa.etiquetas, por_nombre: porNombre });
node.status({ fill: "green", shape: "dot", text: `${mapa.etiquetas.length} etiquetas` });
return msg;
