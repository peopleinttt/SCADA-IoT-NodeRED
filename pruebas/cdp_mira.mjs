// Mira una pagina abierta en Chrome por el protocolo de DevTools (Node 22, sin
// dependencias: WebSocket nativo). Uso:
//   node pruebas/cdp_mira.mjs <puerto_devtools> <segundos> <cada_s> <archivo_png>
// Imprime una linea JSON por muestra con window.__a2 y el numero de
// navegaciones (cargas de pagina) vistas desde que se conecto.
const [puerto, segundos, cada, png] = process.argv.slice(2);
const lista = await (await fetch(`http://127.0.0.1:${puerto}/json`)).json();
const pagina = lista.find(t => t.type === "page");
const ws = new WebSocket(pagina.webSocketDebuggerUrl);
let id = 0, navegaciones = 0;
const pendientes = new Map();
const manda = (method, params = {}) => new Promise(ok => { const i = ++id; pendientes.set(i, ok); ws.send(JSON.stringify({ id: i, method, params })); });
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && pendientes.has(m.id)) { pendientes.get(m.id)(m.result); pendientes.delete(m.id); }
  if (m.method === "Page.frameNavigated" && !m.params.frame.parentId) navegaciones++;
};
await new Promise(ok => { ws.onopen = ok; });
await manda("Page.enable");
const fin = Date.now() + Number(segundos) * 1000;
while (Date.now() < fin) {
  const r = await manda("Runtime.evaluate", { expression: "JSON.stringify(window.__a2 || null)", returnByValue: true });
  console.log(JSON.stringify({ t: Date.now(), a2: JSON.parse(r.result.value || "null"), navegaciones }));
  await new Promise(ok => setTimeout(ok, Number(cada) * 1000));
}
if (png) {
  const s = await manda("Page.captureScreenshot", { format: "png" });
  (await import("node:fs")).writeFileSync(png, Buffer.from(s.data, "base64"));
}
ws.close();
