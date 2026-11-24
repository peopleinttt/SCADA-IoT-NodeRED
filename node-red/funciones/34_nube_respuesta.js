/* Nodo: "interpreta respuesta de proceso"  (A2-Nube, 2 salidas)
 *   0 -> linea del CSV de la corrida ($DATOS_DIR/a2_nube_AAAA-MM-DD.csv)
 *   1 -> pedir una sesion nueva del ingestor (tras un 401, una vez por minuto)
 * ---------------------------------------------------------------
 * Firebase contesta 200 con {"name": registroId} a un POST aceptado. Igual que
 * en la Actividad 1, el registro aceptado se anota con codigo 201 (creado);
 * la columna http guarda lo que contesto Firebase tal cual.
 * Llegan aqui tambien los rechazos locales de 33_nube_valida.js (codigo 422).
 *
 * Columnas: tipo;caja;registro_id;ts_origen;ts_escritura;latencia_ms;
 *           rtt_firebase_ms;http;codigo;resultado
 */
const dir = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
const zona = env.get("TZ_REPORTE") || "America/Mexico_City";
const dia = new Intl.DateTimeFormat("en-CA", { timeZone: zona, year: "numeric", month: "2-digit",
                                               day: "2-digit" }).format(new Date());
const b = msg.base || {}, reg = msg.registro || {};
let http = "", codigo, resultado, registroId = "", renovar = null;

if (msg.resultado && msg.resultado.codigo === 422) {
    codigo = 422; resultado = msg.resultado.motivo;
} else if (msg.statusCode >= 200 && msg.statusCode < 300) {
    http = msg.statusCode; codigo = 201; resultado = "aceptado";
    registroId = (msg.payload && msg.payload.name) || "";
} else {
    http = msg.statusCode; resultado = `http_${msg.statusCode}`;
    codigo = msg.statusCode === 401 ? 502 : 503;
    if (msg.statusCode === 401) {
        // Mismo criterio que 03_respuesta_firebase.js: el dato ya paso la
        // validacion local, asi que un 401 es credencial o reglas sin publicar.
        const ultima = flow.get("renovado_ms") || 0;
        if (Date.now() - ultima > 60000) {
            flow.set("renovado_ms", Date.now());
            global.set("fb_id_token", null);
            renovar = { payload: Date.now() };
        }
        node.error(`Firebase rechazo un registro de proceso con 401. Si las reglas con la rama ` +
                   `proceso no estan publicadas, es esto: publica firebase/database.rules.generado.json`, msg);
    }
}

// Para la HMI: el ultimo registro que Firebase acepto y el ultimo intento.
const resumenNube = global.get("a2_nube_resumen") || {};
resumenNube.ultimo_intento = { ts: new Date().toISOString(), tipo: b.tipo, codigo: codigo, resultado: resultado };
if (codigo === 201) resumenNube.ultimo_aceptado = { ts: reg.ts_escritura, tipo: b.tipo, caja: b.caja || null, registro_id: registroId };
global.set("a2_nube_resumen", resumenNube);

const k = flow.get("conteo") || { aceptados: 0, rechazados: 0 };
if (codigo === 201) k.aceptados++; else k.rechazados++;
flow.set("conteo", k);
node.status({ fill: codigo === 201 ? "green" : "red", shape: "dot",
              text: `${k.aceptados} aceptados, ${k.rechazados} no | ultimo ${b.tipo} ${resultado}` });

const latencia = (reg.ts_origen && reg.ts_escritura) ? Date.parse(reg.ts_escritura) - Date.parse(reg.ts_origen) : "";
const linea = [b.tipo || "", b.caja || "", registroId, reg.ts_origen || "", reg.ts_escritura || "",
               latencia, msg.t_write ? Date.now() - msg.t_write : "", http, codigo, resultado].join(";");
const marca = `hdr_${dia}`;
const csv = { filename: `${dir}/a2_nube_${dia}.csv`,
              payload: (flow.get(marca) ? "" : "tipo;caja;registro_id;ts_origen;ts_escritura;latencia_ms;" +
                                              "rtt_firebase_ms;http;codigo;resultado\n") + linea };
flow.set(marca, true);
return [csv, renovar];
