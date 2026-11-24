/* Nodo: "guarda idToken"  (2 salidas: 0 = ok, 1 = fallo)
 * El token dura una hora; el inject lo renueva cada 45 min y ademas se
 * renueva en cuanto Firebase conteste 401.
 */
if (msg.statusCode !== 200 || !msg.payload || !msg.payload.idToken) {
    const detalle = (msg.payload && msg.payload.error && msg.payload.error.message) ||
                    JSON.stringify(msg.payload || {}).slice(0, 200);
    node.error(`login de Firebase fallido (HTTP ${msg.statusCode}): ${detalle}`, msg);
    node.status({ fill: "red", shape: "dot", text: `login ${msg.statusCode}` });
    global.set("fb_id_token", null);
    msg.payload = { ok: false, motivo: "login_fallido", detalle: detalle };
    return [null, msg];
}

// OJO: va en `global`, no en `flow`. El contexto flow es POR PESTANA, y el
// flujo de diagnostico vive en otra pestana: con flow.set() nunca veria el
// token y consultaria sin credencial, lo que da un 401 identico al de un
// permiso denegado. Costo encontrarlo porque el simulador no exigia auth.
const vidaS = Number(msg.payload.expiresIn || 3600);
global.set("fb_id_token", msg.payload.idToken);
global.set("fb_uid", msg.payload.localId);
global.set("fb_token_vence", Date.now() + vidaS * 1000);

node.status({ fill: "green", shape: "dot",
              text: `uid ${String(msg.payload.localId).slice(0, 8)}… ${Math.round(vidaS / 60)} min` });
node.warn(`Firebase: sesion de ingestor lista. UID = ${msg.payload.localId} ` +
          `(este es el UID que va en database.rules.json)`);

msg.payload = { ok: true, uid: msg.payload.localId, vence_en_s: vidaS };
return [msg, null];
