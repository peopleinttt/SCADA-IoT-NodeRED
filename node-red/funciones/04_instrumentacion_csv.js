/* Nodo: "instrumentacion de la corrida"
 * ---------------------------------------------------------------
 * Escribe una linea delimitada por ; por cada evento ingresado.
 * De aqui salen la latencia y la frecuencia efectiva de muestreo que pide
 * la seccion 5 del reporte. El archivo se corta por dia.
 *
 * Columnas: registro_id;ts_origen;ts_escritura;latencia_ms;rtt_firebase_ms;
 *           temperatura_C;vibracion_mm_s;ciclos_acumulados;resultado
 */
const dir  = (env.get("DATOS_DIR") || "/tmp").replace(/\/+$/, "");
const zona = env.get("TZ_REPORTE") || "America/Mexico_City";

// Fecha local (no UTC) para nombrar el archivo del dia de la corrida.
const dia = new Intl.DateTimeFormat("en-CA", {
    timeZone: zona, year: "numeric", month: "2-digit", day: "2-digit"
}).format(new Date());                                  // en-CA -> YYYY-MM-DD

msg.filename = `${dir}/ingesta_${dia}.csv`;

const ENCABEZADO = "registro_id;ts_origen;ts_escritura;latencia_ms;" +
                   "rtt_firebase_ms;temperatura_C;vibracion_mm_s;" +
                   "ciclos_acumulados;resultado";

const r = msg.registro || {};
const linea = [
    msg.registroId || "",
    r.ts_origen || "",
    r.ts_escritura || "",
    msg.latencia_ms != null ? msg.latencia_ms : "",
    msg.rtt_firebase_ms != null ? msg.rtt_firebase_ms : "",
    r.temperatura_C != null ? r.temperatura_C : "",
    r.vibracion_mm_s != null ? r.vibracion_mm_s : "",
    r.ciclos_acumulados != null ? r.ciclos_acumulados : "",
    msg.resultado || ""
].join(";");

// El encabezado se escribe una sola vez por archivo y por despliegue.
// Si se redespliega a media corrida se repite: el analizador descarta las
// lineas repetidas de encabezado, no hay que limpiar el archivo a mano.
const marca = `hdr_${dia}`;
if (!flow.get(marca)) {
    flow.set(marca, true);
    msg.payload = ENCABEZADO + "\n" + linea;
} else {
    msg.payload = linea;
}
return msg;
