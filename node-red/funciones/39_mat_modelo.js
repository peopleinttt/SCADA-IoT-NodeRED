/* Nodo: "modelo de materiales"  (A2 · Materiales, paso M1 de la fase 3)
 *
 * Funcion pura: no lee ni escribe contexto, archivos ni red. Todo entra y sale
 * por msg, asi que el arnes de pruebas (pruebas/arnes_materiales.js) ejecuta
 * ESTE MISMO ARCHIVO con el mismo protocolo que usa el flujo; no hay copia del
 * codigo. construye_flows.py lo incrusta tal cual en flows.json.
 *
 * Fuente de los numeros: config/materiales.json (Anexo A de la orden) y
 * docs/PARAMETROS_MATERIALES.md. Nada se ajusta aqui.
 *
 * Protocolo (msg.accion):
 *   "valida"   msg.cfg [, msg.apaga = [codigos]]  -> msg.payload = {ok, errores:[{codigo, ruta, detalle}]}
 *              (msg.apaga solo lo usa la prueba de mutacion: apaga reglas)
 *   "inicial"  msg.cfg                           -> msg.estado (D = 0, conteos en 0, generadores sembrados)
 *   "paso"     msg.cfg, msg.estado, msg.paso = {peso_V}
 *                                                -> msg.estado (nuevo), msg.resultado = [{por laminado}]
 *   "punto"    msg.cfg, msg.laminado (indice), msg.peso_V, msg.D
 *                                                -> msg.payload: la cuenta de un paso sin ruido y sin estado
 *   "rigidez"  msg.cfg, msg.laminado, msg.D      -> msg.payload = d(D)
 *
 * Definiciones (orden, paso M1; version 2 de la configuracion, paso R de
 * docs/ORDEN_A2_FASE_3_CIERRE.md):
 *   peso_modelo_V: con c(x) = floor(x * 100 + 0.5) (centesimas de volt enteras,
 *   la resolucion del registro), si |c(peso_V) - c(nivel)| <= c(tolerancia_V)
 *   para un nivel de ajuste_nivel.niveles_V, peso_modelo_V = nivel; si no,
 *   peso_modelo_V = peso_V. ajustado = (peso_modelo_V != peso_V).
 *   f = peso_modelo_V / senal_ref_V   (f puede pasar de 1)
 *   sigma_max = sigma_ref * (R_ref + (1 - R_ref) * f), sigma_min = sigma_ref * R_ref
 *   intervalo ensayado: [nivel_min_pct, nivel_max_pct] % de sigma_uts, extremos incluidos
 *   region: bajo | dentro | sobre
 *   N_ajuste = (sigma_max / a)^(1/b), N_usado = min(N_ajuste, n_tope_ciclos)
 *   dentro suma ciclos_por_paso / N_usado; bajo y sobre no suman (sobre levanta
 *   la alerta carga_fuera_del_intervalo). Nunca se extrapola. D nunca decrece.
 *   nivel: normal < 0.5 <= preventiva < 0.8 <= critica < 1.0 <= falla
 *   d(D): interpolacion lineal en la tabla rigidez; con D > 1 el ultimo valor
 *   galga = delta_sigma / (E0_MPa * (1 - d(D_antes))) * 1e6 + ruido N(0, ruido_sd_ue)
 *   un paso sin peso no se evalua (sin_peso) y no consume numeros del generador.
 *
 * Generador: mulberry32 + Box-Muller, como 24_sust_emulador.js; uno por
 * laminado, sembrado con mezcla(semilla + i * 0x9E3779B9) (la mezcla de
 * 22_sust_config.js). tools/materiales.py hace la misma cuenta en Python.
 */
const M = (function () {
    const CAMPOS = {
        raiz: ["version", "fuente", "carga", "ajuste_nivel", "n_tope_ciclos", "ciclos_por_paso", "umbrales_D", "galga", "laminados"],
        carga: ["sigma_ref_MPa", "R_ref", "senal_ref_V"],
        ajuste_nivel: ["niveles_V", "tolerancia_V"],
        umbrales_D: ["preventiva", "critica", "falla"],
        galga: ["ruido_sd_ue", "semilla"],
        laminado: ["id", "pieza", "a_MPa", "b", "sigma_uts_MPa", "E0_GPa", "nivel_min_pct", "nivel_max_pct", "rigidez"]
    };
    const NIVELES = ["normal", "preventiva", "critica", "falla"];

    function esNum(x) { return typeof x === "number" && Number.isFinite(x); }

    function valida(cfg, apaga) {
        const off = new Set(apaga || []);
        const errores = [];
        const err = (codigo, ruta, detalle) => { if (!off.has(codigo)) errores.push({ codigo, ruta, detalle }); };
        const objeto = x => x !== null && typeof x === "object" && !Array.isArray(x);
        function campos(obj, lista, ruta) {
            if (!objeto(obj)) { err("tipo_invalido", ruta, "se esperaba un objeto"); return false; }
            for (const k of Object.keys(obj)) if (!lista.includes(k)) err("campo_desconocido", ruta + "." + k, "campo no definido");
            for (const k of lista) if (!(k in obj)) err("campo_faltante", ruta + "." + k, "falta");
            return true;
        }
        function positivo(v, ruta) { if (!esNum(v) || v <= 0) err("valor_invalido", ruta, "debe ser un numero > 0: " + v); }
        if (!campos(cfg, CAMPOS.raiz, "cfg")) return { ok: errores.length === 0, errores };
        if (cfg.version !== 2) err("version_no_soportada", "cfg.version", "solo se conoce la version 2: " + cfg.version);
        if (typeof cfg.fuente !== "string") err("tipo_invalido", "cfg.fuente", "texto");
        if (objeto(cfg.carga) && "senal_plena_escala_V" in cfg.carga)
            err("senal_plena_escala_obsoleta", "cfg.carga.senal_plena_escala_V",
                "la version 2 usa senal_ref_V (7.5 V no es la plena escala de la bascula)");
        if (campos(cfg.carga, CAMPOS.carga, "cfg.carga")) {
            positivo(cfg.carga.sigma_ref_MPa, "cfg.carga.sigma_ref_MPa");
            positivo(cfg.carga.senal_ref_V, "cfg.carga.senal_ref_V");
            const R = cfg.carga.R_ref;
            if (!esNum(R) || R < 0 || R >= 1) err("valor_invalido", "cfg.carga.R_ref", "debe estar en [0, 1): " + R);
        }
        if (campos(cfg.ajuste_nivel, CAMPOS.ajuste_nivel, "cfg.ajuste_nivel")) {
            const n = cfg.ajuste_nivel.niveles_V, tol = cfg.ajuste_nivel.tolerancia_V;
            if (!Array.isArray(n) || !n.every(esNum)) err("tipo_invalido", "cfg.ajuste_nivel.niveles_V", "lista de numeros (puede estar vacia)");
            else if (n.some((x, k) => x <= 0 || (k > 0 && !(x > n[k - 1]))))
                err("niveles_desordenados", "cfg.ajuste_nivel.niveles_V", "numeros positivos en orden creciente: " + JSON.stringify(n));
            if (!esNum(tol) || tol < 0) err("tolerancia_invalida", "cfg.ajuste_nivel.tolerancia_V", "debe ser >= 0: " + tol);
            else if (Array.isArray(n) && n.length > 1 && n.every(esNum)) {
                const sep = Math.min(...n.slice(1).map((x, k) => x - n[k]));
                if (sep > 0 && !(tol < sep / 2))
                    err("tolerancia_invalida", "cfg.ajuste_nivel.tolerancia_V", `debe ser menor que la mitad de la separacion minima (${sep}): ${tol}`);
            }
        }
        positivo(cfg.n_tope_ciclos, "cfg.n_tope_ciclos");
        positivo(cfg.ciclos_por_paso, "cfg.ciclos_por_paso");
        if (campos(cfg.umbrales_D, CAMPOS.umbrales_D, "cfg.umbrales_D")) {
            const u = cfg.umbrales_D;
            if (![u.preventiva, u.critica, u.falla].every(esNum)) err("tipo_invalido", "cfg.umbrales_D", "numeros");
            else if (!(0 < u.preventiva && u.preventiva < u.critica && u.critica < u.falla))
                err("umbrales_desordenados", "cfg.umbrales_D", `se requiere 0 < preventiva < critica < falla: ${u.preventiva}, ${u.critica}, ${u.falla}`);
        }
        if (campos(cfg.galga, CAMPOS.galga, "cfg.galga")) {
            if (!esNum(cfg.galga.ruido_sd_ue) || cfg.galga.ruido_sd_ue < 0) err("valor_invalido", "cfg.galga.ruido_sd_ue", ">= 0");
            if (!Number.isInteger(cfg.galga.semilla)) err("valor_invalido", "cfg.galga.semilla", "entero");
        }
        if (!Array.isArray(cfg.laminados) || cfg.laminados.length === 0) {
            err("tipo_invalido", "cfg.laminados", "lista no vacia");
        } else {
            const ids = new Set();
            cfg.laminados.forEach((L, i) => {
                const r = "cfg.laminados[" + i + "]";
                if (!campos(L, CAMPOS.laminado, r)) return;
                if (typeof L.id !== "string" || !L.id || ids.has(L.id)) err("valor_invalido", r + ".id", "texto unico");
                ids.add(L.id);
                if (typeof L.pieza !== "string" || !L.pieza) err("valor_invalido", r + ".pieza", "texto");
                if (!esNum(L.b)) err("tipo_invalido", r + ".b", "numero");
                else if (L.b >= 0) err("b_no_negativo", r + ".b", "el exponente debe ser < 0: " + L.b);
                if (!esNum(L.a_MPa)) err("tipo_invalido", r + ".a_MPa", "numero");
                else if (L.a_MPa <= 0) err("a_no_positivo", r + ".a_MPa", "debe ser > 0: " + L.a_MPa);
                positivo(L.sigma_uts_MPa, r + ".sigma_uts_MPa");
                positivo(L.E0_GPa, r + ".E0_GPa");
                if (!esNum(L.nivel_min_pct) || !esNum(L.nivel_max_pct)) err("tipo_invalido", r + ".nivel_*_pct", "numeros");
                else if (L.nivel_min_pct >= L.nivel_max_pct)
                    err("intervalo_invertido", r, `nivel_min_pct (${L.nivel_min_pct}) debe ser menor que nivel_max_pct (${L.nivel_max_pct})`);
                const t = L.rigidez;
                if (!Array.isArray(t) || t.length < 2 || !t.every(p => Array.isArray(p) && p.length === 2 && p.every(esNum))) {
                    err("tipo_invalido", r + ".rigidez", "lista de al menos 2 pares [D, d] numericos");
                    return;
                }
                if (t[0][0] !== 0 || t[0][1] !== 0) err("rigidez_no_empieza_en_cero", r + ".rigidez[0]", "debe ser [0, 0]: " + JSON.stringify(t[0]));
                for (let k = 0; k < t.length; k++) {
                    if (t[k][0] < 0 || t[k][0] > 1) err("rigidez_D_fuera_de_rango", r + ".rigidez[" + k + "]", "D en [0, 1]: " + t[k][0]);
                    if (k > 0 && !(t[k][0] > t[k - 1][0])) err("rigidez_D_no_creciente", r + ".rigidez[" + k + "]", `D debe crecer: ${t[k - 1][0]} -> ${t[k][0]}`);
                    if (k > 0 && t[k][1] < t[k - 1][1]) err("rigidez_d_decreciente", r + ".rigidez[" + k + "]", `d no puede bajar: ${t[k - 1][1]} -> ${t[k][1]}`);
                }
            });
        }
        return { ok: errores.length === 0, errores };
    }

    // ---- generador con semilla ----------------------------------------------------
    function mezcla(x) {
        x = Math.imul(x ^ (x >>> 16), 0x85ebca6b);
        x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
        return (x ^ (x >>> 16)) | 0;
    }
    function semillaLaminado(semilla, i) { return mezcla((semilla + Math.imul(i, 0x9E3779B9)) | 0); }
    function azar(g) {                                 // mulberry32: [0, 1); g = {s}
        const a = (g.s = (g.s + 0x6D2B79F5) | 0);
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    }
    function normal(g) {                               // Box-Muller, como el sustituto
        const u1 = 1 - azar(g), u2 = azar(g);
        return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    }

    // ---- cuentas ------------------------------------------------------------------
    function rigidez(L, D) {
        const t = L.rigidez;
        if (D <= t[0][0]) return t[0][1];
        if (D >= t[t.length - 1][0]) return t[t.length - 1][1];
        for (let k = 1; k < t.length; k++) {
            if (D <= t[k][0]) {
                const [D0, d0] = t[k - 1], [D1, d1] = t[k];
                return d0 + (d1 - d0) * (D - D0) / (D1 - D0);
            }
        }
        return t[t.length - 1][1];
    }
    function nivel(cfg, D) {
        const u = cfg.umbrales_D;
        return D >= u.falla ? "falla" : D >= u.critica ? "critica" : D >= u.preventiva ? "preventiva" : "normal";
    }
    // Ajuste al nivel en centesimas de volt enteras; floor(x + 0.5) y no
    // Math.round, para que JS y Python den lo mismo.
    function cent(x) { return Math.floor(x * 100 + 0.5); }
    function pesoModelo(cfg, peso_V) {
        const A = cfg.ajuste_nivel, c = cent(peso_V), t = cent(A.tolerancia_V);
        for (const n of A.niveles_V) if (Math.abs(c - cent(n)) <= t) return { peso_modelo_V: n, ajustado: n !== peso_V };
        return { peso_modelo_V: peso_V, ajustado: false };
    }
    function carga(cfg, peso_modelo_V) {
        const c = cfg.carga;
        const f = peso_modelo_V / c.senal_ref_V;
        const sigma_max = c.sigma_ref_MPa * (c.R_ref + (1 - c.R_ref) * f);
        const sigma_min = c.sigma_ref_MPa * c.R_ref;
        return { f, sigma_max, sigma_min, delta_sigma: sigma_max - sigma_min };
    }
    // La cuenta de un laminado en un paso, sin ruido y sin estado.
    function punto(cfg, L, peso_V, D_antes) {
        const a = pesoModelo(cfg, peso_V);
        const q = Object.assign({ peso_V, peso_modelo_V: a.peso_modelo_V, ajustado: a.ajustado }, carga(cfg, a.peso_modelo_V));
        const lo = L.nivel_min_pct / 100 * L.sigma_uts_MPa, hi = L.nivel_max_pct / 100 * L.sigma_uts_MPa;
        const region = q.sigma_max < lo ? "bajo" : q.sigma_max > hi ? "sobre" : "dentro";
        let N_ajuste = null, N_usado = null, dD = 0;
        if (region === "dentro") {
            N_ajuste = Math.pow(q.sigma_max / L.a_MPa, 1 / L.b);
            N_usado = Math.min(N_ajuste, cfg.n_tope_ciclos);
            dD = cfg.ciclos_por_paso / N_usado;
        }
        const d_antes = rigidez(L, D_antes);
        const galga_sin_ruido = q.delta_sigma / (L.E0_GPa * 1000 * (1 - d_antes)) * 1e6;
        return Object.assign(q, { region, N_ajuste, N_usado, dD, d_antes, galga_sin_ruido,
                                  intervalo_MPa: [lo, hi] });
    }
    function inicial(cfg) {
        return {
            version: 1, cfg_version: cfg.version,
            pasos: 0, sin_peso: 0,
            laminados: cfg.laminados.map((L, i) => ({
                id: L.id, pieza: L.pieza, D: 0, nivel: "normal",
                conteos: { dentro: 0, bajo: 0, sobre: 0 },
                rng: semillaLaminado(cfg.galga.semilla, i)
            }))
        };
    }
    function paso(cfg, estado, peso_V) {
        const E = JSON.parse(JSON.stringify(estado));
        E.pasos += 1;
        if (!esNum(peso_V)) {
            E.sin_peso += 1;
            return { estado: E, resultado: null, sin_peso: true };
        }
        const resultado = cfg.laminados.map((L, i) => {
            const S = E.laminados[i];
            const p = punto(cfg, L, peso_V, S.D);
            const g = { s: S.rng };
            const ruido = cfg.galga.ruido_sd_ue * normal(g);
            S.rng = g.s;
            S.conteos[p.region] += 1;
            const nivel_antes = S.nivel;
            S.D = S.D + p.dD;                          // dD >= 0: D nunca decrece
            S.nivel = nivel(cfg, S.D);
            return {
                id: L.id, pieza: L.pieza, peso_V: p.peso_V, peso_modelo_V: p.peso_modelo_V, ajustado: p.ajustado,
                f: p.f, sigma_max_MPa: p.sigma_max, delta_sigma_MPa: p.delta_sigma,
                deformacion_ue: p.galga_sin_ruido + ruido, region: p.region, N_ajuste: p.N_ajuste,
                N_usado: p.N_usado, dD: p.dD, D: S.D, d: rigidez(L, S.D), nivel: S.nivel,
                cambio_nivel: S.nivel !== nivel_antes,
                alerta: p.region === "sobre" ? "carga_fuera_del_intervalo" : null
            };
        });
        return { estado: E, resultado, sin_peso: false };
    }
    return { valida, inicial, paso, punto, rigidez, nivel, carga, pesoModelo, semillaLaminado, NIVELES };
})();

switch (msg.accion) {
    case "valida":
        msg.payload = M.valida(msg.cfg, msg.apaga);
        return msg;
    case "inicial":
        msg.estado = M.inicial(msg.cfg);
        return msg;
    case "paso": {
        const r = M.paso(msg.cfg, msg.estado, msg.paso ? msg.paso.peso_V : undefined);
        msg.estado = r.estado;
        msg.resultado = r.resultado;
        msg.sin_peso = r.sin_peso;
        return msg;
    }
    case "punto":
        msg.payload = M.punto(msg.cfg, msg.cfg.laminados[msg.laminado], msg.peso_V, msg.D || 0);
        return msg;
    case "rigidez":
        msg.payload = M.rigidez(msg.cfg.laminados[msg.laminado], msg.D);
        return msg;
    default:
        node.warn("modelo de materiales: accion desconocida " + msg.accion);
        return null;
}
