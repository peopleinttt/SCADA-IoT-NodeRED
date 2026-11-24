// Relevo TCP minimo: 127.0.0.1:<local> -> <host>:<puerto>. Node 22, sin dependencias.
//   node pruebas/relevo.mjs 5031 10.211.55.3 502
// Existe porque macOS (privacidad de "Red local") deja a node llegar a la VM de
// Parallels pero no a python3, que recibe EHOSTUNREACH: la sonda en Python va
// por aqui, por loopback. Ctrl+C lo corta (sirve tambien de interruptor).
import net from "node:net";
const [local, host, puerto] = process.argv.slice(2);
net.createServer(c => {
  const s = net.connect(Number(puerto), host);
  c.setNoDelay(true); s.setNoDelay(true);
  c.pipe(s); s.pipe(c);
  const cierra = () => { c.destroy(); s.destroy(); };
  c.on("error", cierra); s.on("error", cierra); c.on("close", cierra); s.on("close", cierra);
}).listen(Number(local), "127.0.0.1", () => console.log(`relevo 127.0.0.1:${local} -> ${host}:${puerto}`));
