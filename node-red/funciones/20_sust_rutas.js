/* Nodo: "revisa rutas"  (A2-Sustituto)
 * ---------------------------------------------------------------
 * El mapa y la configuracion del sustituto se leen de archivo en el arranque,
 * con las rutas de A2_MAPA y A2_SUST_CONFIG (arranca.sh las fija si .env no).
 * Si faltan, la pestana se queda quieta y lo dice en su estado, sin lanzar
 * error: un error aqui caeria en los Catch y ensuciaria la bitacora de la
 * Actividad 1, cuyo arnes corre sin estas variables.
 */
const faltan = ["A2_MAPA", "A2_SUST_CONFIG"].filter(v => !env.get(v));
if (faltan.length) {
    node.status({ fill: "grey", shape: "ring", text: `sin ${faltan.join(", ")}: sustituto quieto` });
    return null;
}
node.status({ fill: "blue", shape: "ring", text: "leyendo mapa y configuracion" });
return msg;
