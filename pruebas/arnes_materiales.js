#!/usr/bin/env node
/* Arnes del modelo de materiales (paso M1). Ejecuta node-red/funciones/39_mat_modelo.js,
 * el MISMO archivo que construye_flows.py incrusta en el nodo de funcion, con
 * el mismo envoltorio que usa Node-RED: function(msg, node, context, flow, global, env, RED).
 *
 *   node pruebas/arnes_materiales.js < peticiones.json > respuestas.json
 *
 * Entrada: lista JSON de mensajes. Cada uno se pasa tal cual al nodo y se
 * devuelve el mensaje que el nodo regresa. Un mensaje {accion: "secuencia",
 * cfg, pesos: [...]} lo resuelve el arnes llamando al nodo con accion "paso"
 * una vez por peso (el bucle es del arnes; la cuenta, del nodo) y regresa la
 * lista de resultados y el estado final.
 */
const fs = require("fs");
const path = require("path");

const ARCHIVO = path.join(__dirname, "..", "node-red", "funciones", "39_mat_modelo.js");
const cuerpo = fs.readFileSync(ARCHIVO, "utf8");
const avisos = [];
const nodo = { warn: m => avisos.push(String(m)), error: m => avisos.push(String(m)), status: () => {}, log: () => {} };
const sinContexto = { get: () => { throw new Error("el modelo no debe usar contexto"); },
                      set: () => { throw new Error("el modelo no debe usar contexto"); } };
// eslint-disable-next-line no-new-func
const funcion = new Function("msg", "node", "context", "flow", "global", "env", "RED", cuerpo);
const llama = msg => funcion(msg, nodo, sinContexto, sinContexto, sinContexto, sinContexto, {});

const peticiones = JSON.parse(fs.readFileSync(0, "utf8"));
const respuestas = peticiones.map(p => {
    if (p.accion === "secuencia") {
        let estado = llama({ accion: "inicial", cfg: p.cfg }).estado;
        const resultados = [];
        for (const v of p.pesos) {
            const r = llama({ accion: "paso", cfg: p.cfg, estado, paso: { peso_V: v } });
            estado = r.estado;
            resultados.push(p.solo_final ? null : r.resultado);
        }
        return { estado, resultados: p.solo_final ? [] : resultados };
    }
    return llama(JSON.parse(JSON.stringify(p)));
});
process.stdout.write(JSON.stringify({ respuestas, avisos }));
