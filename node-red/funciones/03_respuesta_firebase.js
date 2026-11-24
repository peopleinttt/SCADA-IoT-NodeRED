/* Nodo: "interpreta respuesta de Firebase"  (3 salidas)
 *   0 -> exito: sigue a la instrumentacion (CSV de la corrida)
 *   1 -> respuesta HTTP de vuelta al ESP32
 *   2 -> aviso para renovar el token de servicio
 *
 * La respuesta se manda como copia: msg sigue viajando a la instrumentacion
 * con el registro intacto, y RED.util.cloneMessage conserva msg.req/msg.res
 * para que el nodo "http response" pueda cerrar la peticion.
 */
const codigo = msg.statusCode;
const rtt    = msg.t_write ? Date.now() - msg.t_write : null;

function respuesta(estado, cuerpo) {
    const r = RED.util.cloneMessage(msg);
    r.statusCode = estado;
    r.payload = cuerpo;
    return r;
}

// Exito: Firebase devuelve { "name": "-NqAbC..." } = el registroId generado.
if (codigo >= 200 && codigo < 300) {
    const registroId = (msg.payload && msg.payload.name) || null;
    if (!registroId) {
        node.warn("Firebase respondio 2xx sin campo name; revisar print=silent");
    }
    msg.registroId = registroId;
    msg.rtt_firebase_ms = rtt;
    msg.resultado = "ok";
    flow.set("fb_401_seguidos", 0);
    node.status({ fill: "green", shape: "dot", text: `${registroId} (${rtt} ms)` });
    return [msg, respuesta(201, {
        ok: true,
        registroId: registroId,
        ts_escritura: msg.registro.ts_escritura,
        latencia_ms: msg.latencia_ms
    }), null];
}

const detalle = (msg.payload && (msg.payload.error || msg.payload)) || "sin cuerpo";
msg.resultado = `http_${codigo}`;
msg.registroId = null;

// 401. MEDIDO contra el emulador de RTDB con estas mismas reglas: ocho causas
// distintas (UID equivocado, rango fuera, marca de tiempo mal formada, campo
// extra, campo faltante, plantaId mal, tipo equivocado, cuenta sin permiso)
// devuelven EXACTAMENTE el mismo 401 {"error":"Permission denied"}. No hay
// nada en la respuesta que las separe.
//
// Por eso este nodo NO adivina la causa: se apoya en que el dato ya paso por
// "valida y sella", que replica las mismas condiciones que las reglas. Si algo
// llego hasta aqui y aun asi lo rechazaron, la causa esta del lado de la
// credencial o de las reglas publicadas, no del dato.
if (codigo === 401) {
    const seguidos = (flow.get("fb_401_seguidos") || 0) + 1;
    flow.set("fb_401_seguidos", seguidos);

    // Renovar el token en cada 401 provoca una tormenta de logins cuando la
    // causa no es el token. Se renueva una vez por minuto como mucho.
    const ultimaRenovacion = flow.get("fb_401_renovado_ms") || 0;
    const renovar = Date.now() - ultimaRenovacion > 60000;
    let pistas;
    if (seguidos >= 3 && !renovar) {
        pistas = `${seguidos} rechazos seguidos con datos que SI pasaron la ` +
                 `validacion local. Esto ya no es el token: verifica que el UID ` +
                 `del ingestor en las reglas publicadas sea el que imprime ` +
                 `firebase/prepara.sh, y que PLANTA_ID sea planta_NN.`;
    } else {
        pistas = `Puede ser el token vencido o el UID equivocado en las reglas. ` +
                 `Firebase devuelve el mismo 401 en ambos casos.`;
    }
    if (renovar) { global.set("fb_id_token", null); flow.set("fb_401_renovado_ms", Date.now()); }

    node.error(`Firebase rechazo la escritura con 401. ${pistas} ` +
               `Registro rechazado: ${JSON.stringify(msg.registro)}`, msg);
    node.status({ fill: "red", shape: "ring", text: `401 x${seguidos}` });
    return [msg,
            respuesta(502, { ok: false, motivo: "firebase_permiso_denegado",
                             detalle: pistas, rechazos_seguidos: seguidos }),
            renovar ? RED.util.cloneMessage(msg) : null];
}

// 400. Ojo: las reglas .validate NO producen 400, producen 401 (medido). Un
// 400 aqui significa JSON mal formado o ruta invalida, que son fallas de este
// flujo, no del dato del sensor.
if (codigo === 400) {
    node.error(`Firebase respondio 400 (JSON mal formado o ruta invalida, ` +
               `no es una regla .validate): ${JSON.stringify(detalle)}`, msg);
    node.status({ fill: "red", shape: "dot", text: "peticion mal formada" });
    return [msg,
            respuesta(502, { ok: false, motivo: "firebase_dato_invalido", detalle: detalle }),
            null];
}

// 429 / 5xx: base saturada o caida. El emisor reintenta.
node.error(`Firebase respondio ${codigo}: ${JSON.stringify(detalle)}`, msg);
node.status({ fill: "red", shape: "dot", text: `HTTP ${codigo}` });
return [msg,
        respuesta(503, { ok: false, motivo: "firebase_no_disponible",
                         codigo: codigo, detalle: detalle }),
        null];
