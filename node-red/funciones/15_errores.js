/* Nodo: "bitacora de errores" — colgado de un nodo Catch de alcance total.
 * Aqui aterrizan los fallos de transporte (DNS, TLS, timeout, socket cerrado)
 * que no llegan a producir un statusCode, y cualquier excepcion no atrapada
 * dentro de los nodos de funcion.
 */
// Los mensajes de error de Node-RED incluyen la URL completa, y esa URL
// lleva ?auth=<idToken>. Se tapa antes de escribir nada a disco.
function tapaSecretos(t) {
    return String(t)
        .replace(/([?&]auth=)[^&\s"']+/gi, "$1<oculto>")
        .replace(/([?&]key=)[^&\s"']+/gi, "$1<oculto>")
        .replace(/(x-goog-api-key["':\s]+)[^,\s"'}]+/gi, "$1<oculto>");
}

const e = msg.error || {};
const origen = (e.source && e.source.name) || (e.source && e.source.id) || "desconocido";
const texto  = tapaSecretos(e.message || "sin mensaje");

let clase = "desconocido";
if (/ENOTFOUND|EAI_AGAIN/i.test(texto))            clase = "dns_no_resuelve";
else if (/ECONNREFUSED/i.test(texto))              clase = "conexion_rechazada";
else if (/ETIMEDOUT|timeout/i.test(texto))         clase = "tiempo_agotado";
else if (/certificate|TLS|SSL/i.test(texto))       clase = "tls_invalido";
else if (/ECONNRESET|socket hang up/i.test(texto)) clase = "conexion_cortada";
else if (/JSON/i.test(texto))                      clase = "parseo";

const conteo = (flow.get("errores_" + clase) || 0) + 1;
flow.set("errores_" + clase, conteo);

node.status({ fill: "red", shape: "dot", text: `${clase} x${conteo}` });

const dir  = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
msg.filename = `${dir}/errores.log`;
msg.payload = `${new Date().toISOString()};${clase};${origen};${String(texto).replace(/[\r\n]+/g, " ").slice(0, 300)}`;
return msg;
