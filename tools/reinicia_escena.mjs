// Reinicia la escena de Factory I/O por Modbus: Reset, espera a que se vacie y Run.
//
//     node tools/reinicia_escena.mjs [host] [puerto] [--mapa config/mapa_registros_fio.json] [--espera 15]
//
// Host y puerto por omision de A2_MODBUS_HOST / A2_MODBUS_PUERTO (unidad A2_MODBUS_UNIDAD).
// En Node y no en Python: el Python de macOS no tiene permiso de "Red local"
// para llegar a la VM de Parallels; Node si.
//
// Secuencia (probada contra la escena el 24 oct):
//   1. todas las bobinas de actuadores en 0 (bandas y ruedas quietas);
//   2. fio_reset = 1 -> la escena se detiene (fio_running baja a 0) y se limpia;
//   3. fio_reset = 0;
//   4. espera a que este vacia: nada en la bascula ni en el desviador ni en
//      las ramas (at_scale, at_scale_exit, at_*_entry en 0), las salidas NC en 1
//      y el peso < 0.2 V. at_scale_entry puede quedar tapado: es la caja que el
//      emisor pone en la entrada al reiniciar;
//   5. fio_run = 1 y se DEJA en 1: actua por nivel (en 0 la escena se detiene;
//      un flanco 0 -> 1 -> 0 la arranca y la vuelve a parar). Se comprueba que
//      fio_running se sostiene en 1 durante 1 s.
// Codigo 0 si quedo vacia y corriendo; 1 si no se vacio o no volvio a correr; 2 sin conexion.
import net from "node:net";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const opcion = (n, def) => { const i = args.indexOf(n); return i >= 0 ? args.splice(i, 2)[1] : def; };
const mapaRuta = opcion("--mapa", path.join(raiz, "config", "mapa_registros_fio.json"));
const esperaS = Number(opcion("--espera", "15"));
const host = args[0] || process.env.A2_MODBUS_HOST || "127.0.0.1";
const puerto = Number(args[1] || process.env.A2_MODBUS_PUERTO || 502);
const unidad = Number(process.env.A2_MODBUS_UNIDAD || 1);
const E = Object.fromEntries(JSON.parse(fs.readFileSync(mapaRuta, "utf8")).etiquetas.map(e => [e.nombre, e]));
for (const n of ["fio_reset", "fio_run", "fio_running", "weight"]) {
    if (!E[n]) { console.error(`el mapa ${mapaRuta} no tiene ${n}`); process.exit(1); }
}

// ---- cliente Modbus minimo, una peticion a la vez -----------------------------
let sock, tid = 0, pendiente = null, buf = Buffer.alloc(0);
function conecta() {
    return new Promise((ok, mal) => {
        sock = net.connect(puerto, host, ok);
        sock.setNoDelay(true);
        sock.setTimeout(3000, () => sock.destroy(new Error("sin respuesta")));
        sock.on("error", e => (pendiente ? pendiente.mal(e) : mal(e)));
        sock.on("data", d => {
            buf = Buffer.concat([buf, d]);
            if (buf.length >= 6 && buf.length >= 6 + buf.readUInt16BE(4) && pendiente) {
                const largo = 6 + buf.readUInt16BE(4), r = buf.subarray(0, largo);
                buf = buf.subarray(largo);
                const p = pendiente; pendiente = null;
                r[7] & 0x80 ? p.mal(new Error(`excepcion Modbus ${r[8]}`)) : p.ok(r);
            }
        });
    });
}
function pide(fc, a, b) {
    tid = (tid + 1) & 0xffff;
    const t = Buffer.from([tid >> 8, tid & 255, 0, 0, 0, 6, unidad, fc, a >> 8, a & 255, b >> 8, b & 255]);
    return new Promise((ok, mal) => { pendiente = { ok, mal }; sock.write(t); });
}
const bobina = (dir, v) => pide(5, dir, v ? 0xff00 : 0);
const discretas = async (dir, n) => { const r = await pide(2, dir, n); return [...Array(n)].map((_, i) => !!(r[9 + (i >> 3)] >> (i & 7) & 1)); };
const entrada = async dir => (await pide(4, dir, 1)).readUInt16BE(9);
const pausa = ms => new Promise(r => setTimeout(r, ms));
const lee = async n => (await discretas(E[n].direccion, 1))[0];

async function vacia() {
    const libres = ["at_scale", "at_scale_exit", "at_left_entry", "at_forward_entry", "at_right_entry"].filter(n => E[n]);
    const nc = ["at_exit_left", "at_exit_front", "at_exit_right"].filter(n => E[n]);
    const ocupados = [];
    for (const n of libres) if (await lee(n)) ocupados.push(n);
    for (const n of nc) if (!(await lee(n))) ocupados.push(n);
    const peso = (await entrada(E.weight.direccion)) / (E.weight.escala || 1);
    if (peso >= 0.2) ocupados.push(`weight ${peso.toFixed(2)} V`);
    return ocupados;
}

async function main() {
    const t0 = Date.now(), dice = m => console.log(`  ${((Date.now() - t0) / 1000).toFixed(1).padStart(5)} s  ${m}`);
    try { await conecta(); } catch (e) { console.error(`sin conexion con ${host}:${puerto}: ${e.message}`); return 2; }
    console.log(`reinicio de la escena en ${host}:${puerto} (unidad ${unidad})`);
    const actuadores = Object.values(E).filter(e => e.tabla === "bobina" && !e.nombre.startsWith("fio_"));
    for (const e of actuadores) await bobina(e.direccion, false);
    dice(`${actuadores.length} bobinas de actuadores en 0`);
    await bobina(E.fio_reset.direccion, true);
    let fin = Date.now() + 5000;
    while (Date.now() < fin && await lee("fio_running")) await pausa(100);
    dice(`Reset = 1 -> running ${await lee("fio_running") ? 1 : 0}`);
    await pausa(300);
    await bobina(E.fio_reset.direccion, false);
    dice("Reset = 0");
    fin = Date.now() + esperaS * 1000;
    let ocupados = await vacia();
    while (ocupados.length && Date.now() < fin) { await pausa(200); ocupados = await vacia(); }
    if (ocupados.length) { dice(`NO se vacio en ${esperaS} s: ${ocupados.join(", ")}`); sock.destroy(); return 1; }
    dice("vacia: bascula, desviador, ramas y salidas libres, peso < 0.2 V");
    await bobina(E.fio_run.direccion, true);
    fin = Date.now() + 5000;
    while (Date.now() < fin && !(await lee("fio_running"))) await pausa(100);
    let corre = await lee("fio_running");
    for (let i = 0; i < 10 && corre; i++) { await pausa(100); corre = await lee("fio_running"); }
    dice(`Run = 1 (se queda) -> running ${corre ? "1, sostenido 1 s" : 0}`);
    sock.destroy();
    return corre ? 0 : 1;
}
main().then(c => process.exit(c), e => { console.error(e.message); process.exit(2); });
