/* Nodo: "boton de la HMI a comando"  (A2-HMI)
 * ---------------------------------------------------------------
 * La pagina manda {payload: {accion, ...}}. Se pasa tal
 * cual a 30_planta_comando.js (la misma logica y los mismos codigos que
 * POST /a2/planta/comando), sin msg.req: asi esa funcion sabe que es una
 * llamada interna y contesta por su salida de HMI. Lo que llega por Dashboard
 * ya paso por el filtro del tunel (settings.js), asi que aqui solo se filtra
 * la forma del mensaje.
 */
// No se mira msg.topic: Dashboard 2.0 lo reescribe con el topic del widget
// (appendTopic) en las acciones y en lo que entra a la pagina. Se distingue
// por la forma: un boton trae payload.accion.
const validas = ["marcha", "paro", "emisor", "velocidad", "diagnostico"];
if (!msg.payload || !validas.includes(msg.payload.accion)) return null;
const salida = { payload: { accion: msg.payload.accion } };
if (msg.payload.accion === "velocidad") salida.payload.vel_V = Number(msg.payload.vel_V);
if (msg.payload.accion === "emisor") salida.payload.valor = !!msg.payload.valor;
if (msg.payload.accion === "diagnostico") return [null, { payload: { origen: "hmi" }, topic: "diagnostico" }];
return [salida, null];
