#!/usr/bin/env node
/* Hash bcrypt de una contrasena para adminAuth de Node-RED (paso S2).
 *
 *   printf '%s' "$CLAVE" | node tools/hash_admin.js            -> imprime el hash
 *   node tools/hash_admin.js --revisa '<hash>'                 -> exit 0 si tiene formato bcrypt
 *   node tools/hash_admin.js --compara '<hash>' < clave        -> exit 0 si la clave corresponde
 *   node tools/hash_admin.js --biblioteca                      -> que biblioteca usaria
 *
 * La contrasena entra por stdin (nunca por argumentos ni por el entorno, que
 * se ven en `ps`). Usa la MISMA biblioteca que el Node-RED instalado: se
 * resuelve desde su red.js, igual que @node-red/editor-api/lib/auth/users.js
 * (@node-rs/bcrypt y, si no esta, bcryptjs). NODE_RED_DIR elige otra instalacion.
 */
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const { createRequire } = require("module");

const BCRYPT = /^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$/;
const COSTO = 10;

function dirNodeRed() {
    if (process.env.NODE_RED_DIR) return process.env.NODE_RED_DIR;
    const bin = execSync("command -v node-red", { encoding: "utf8", shell: "/bin/bash" }).trim();
    return path.dirname(fs.realpathSync(bin));
}
function biblioteca() {
    const dir = dirNodeRed();
    // users.js vive en node_modules/@node-red/editor-api; se resuelve desde ahi.
    const desde = createRequire(path.join(dir, "node_modules", "@node-red", "editor-api", "lib", "auth", "users.js"));
    try { return { nombre: "@node-rs/bcrypt", b: desde("@node-rs/bcrypt"), dir }; }
    catch (e) { return { nombre: "bcryptjs", b: desde("bcryptjs"), dir }; }
}
function leeStdin() {
    let s = "";
    try { s = fs.readFileSync(0, "utf8"); } catch (e) { s = ""; }
    return s.replace(/\r?\n$/, "");
}

const args = process.argv.slice(2);
if (args[0] === "--revisa") process.exit(BCRYPT.test(args[1] || "") ? 0 : 1);
if (args[0] === "--biblioteca") { const b = biblioteca(); console.log(b.nombre + " (" + b.dir + ")"); process.exit(0); }
if (args[0] === "--compara") {
    const { b } = biblioteca();
    Promise.resolve(b.compare(leeStdin(), args[1] || "")).then(ok => process.exit(ok ? 0 : 1), () => process.exit(2));
} else {
    const clave = leeStdin();
    if (!clave) { console.error("contrasena vacia"); process.exit(2); }
    const { b } = biblioteca();
    process.stdout.write(b.hashSync(clave, COSTO) + "\n");
}
