/* Nodo: "revisa rutas"  (A2-Planta)
 * Igual que en el sustituto: sin A2_MAPA o A2_PLANTA_CONFIG la pestana se
 * queda quieta y lo dice en su estado, sin lanzar error.
 */
const faltan = ["A2_MAPA", "A2_PLANTA_CONFIG"].filter(v => !env.get(v));
if (faltan.length) {
    node.status({ fill: "grey", shape: "ring", text: `sin ${faltan.join(", ")}: cliente quieto` });
    return null;
}
node.status({ fill: "blue", shape: "ring", text: "leyendo mapa y configuracion" });
return msg;
