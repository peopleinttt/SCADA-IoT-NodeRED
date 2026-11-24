/* Nodo: "arma login del ingestor"
 * ---------------------------------------------------------------
 * Node-RED no usa el SDK de administrador: se autentica como un usuario de
 * servicio contra Identity Toolkit y usa el idToken resultante en ?auth=.
 * Asi las reglas pueden distinguir "el ingestor" de "cualquiera", sin poner
 * un secreto de base de datos (deprecado) en ningun lado.
 */
const apiKey = env.get("FIREBASE_API_KEY") || "";
const correo = env.get("FB_INGESTOR_EMAIL") || "";
const clave  = env.get("FB_INGESTOR_PASS") || "";

if (!apiKey || !correo || !clave) {
    node.warn("login omitido: falta FIREBASE_API_KEY / FB_INGESTOR_EMAIL / " +
              "FB_INGESTOR_PASS. Se usara FIREBASE_AUTH si existe.");
    node.status({ fill: "grey", shape: "ring", text: "login no configurado" });
    return null;
}

const baseId = (env.get("IDENTITY_BASE_URL") || "https://identitytoolkit.googleapis.com").replace(/\/+$/, "");
msg.url     = `${baseId}/v1/accounts:signInWithPassword?key=${encodeURIComponent(apiKey)}`;
msg.headers = { "Content-Type": "application/json" };
msg.payload = { email: correo, password: clave, returnSecureToken: true };
node.status({ fill: "blue", shape: "ring", text: "autenticando..." });
return msg;
