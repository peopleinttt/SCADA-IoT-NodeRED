#!/usr/bin/env python3
"""Verificacion del mapa real contra Factory I/O (R2). Python 3.9.

    node pruebas/relevo.mjs 5031 10.211.55.3 502 &       # si python no tiene permiso de "Red local"
    /usr/bin/python3 pruebas/prueba_fio.py --puerto 5031  (~3 min, Sorting by Weight en Play)
    /usr/bin/python3 pruebas/prueba_fio.py cliente -s 240 (A2-Planta contra la escena, ~5 min)

Con config/mapa_registros_fio.json:
  1. sonda vigila (por nombre del mapa) ve cambiar cada sensor de cajas en su
     direccion mientras pasan cajas;
  2. sonda escribe mueve lo que cada nombre dice, observado en los sensores:
     bandas (entry_conveyor, load_scale) y ruedas (send_left / send_right /
     send_forward -> la caja entra por esa salida); luces y contadores se
     escriben y se leen de vuelta (su efecto es visual en el tablero).
Escribir en la escena esta permitido: es un simulador (orden de la fase 2).

Modo cliente: Node-RED (A2-Planta con config/planta_fio.json: pesaje detenido,
ruedas con motriz) controla la escena; esta prueba solo LEE, por su cuenta, y
es el oraculo: el peso de cada caja en el instante en que el cliente la suelta
(sube load_scale con la caja en at_scale) da la clase esperada, y la salida NC
que baja da el destino real. Se comparan en orden (FIFO) con lo que reporta el
cliente.
"""
import argparse, json, math, os, pathlib, subprocess, sys, tempfile, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ / "pruebas"))
import prueba_sustituto as ps  # noqa: E402  (solo verifica/resultado)
from modbus_tcp import Cliente  # noqa: E402

verifica = ps.verifica
MAPA = str(RAIZ / "config" / "mapa_registros_fio.json")
E = {e["nombre"]: e for e in json.load(open(MAPA))["etiquetas"]}


def sonda(host, puerto, *args):
    r = subprocess.run([sys.executable, str(RAIZ / "tools" / "sonda_modbus.py"), "--mapa", MAPA, "--host", host,
                        "--puerto", str(puerto)] + list(args), capture_output=True, text=True, timeout=400)
    return r.returncode, r.stdout + r.stderr


def flancos(c, nombre, segundos, valor=1):
    """Cuantas veces la entrada pasa a `valor` en `segundos`."""
    d, n, previo, fin = E[nombre]["direccion"], 0, None, time.time() + segundos
    while time.time() < fin:
        v = c.lee_discretas(d, 1)[0]
        if previo is not None and v != previo and v == bool(valor):
            n += 1
        previo = v
        time.sleep(0.02)
    return n


def main(host, puerto):
    print("=== Mapa real contra Factory I/O en %s:%d ===" % (host, puerto))
    if not reinicia(os.environ.get("A2_MODBUS_HOST", "10.211.55.3")):
        return
    c = Cliente(host, puerto, unidad=1)
    c.conecta()
    try:
        bandas = ["entry_conveyor", "load_scale", "left_conveyor", "right_conveyor", "front_conveyor"]
        for b in bandas:
            sonda(host, puerto, "escribe", b, "1")
        print("--- vigila 60 s con el mapa ---")
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="a2_fio_"))
        rc, out = sonda(host, puerto, "vigila", "-s", "60", "--json", str(tmp / "v.json"))
        print("\n".join("    " + l for l in out.strip().splitlines()[:18]))
        v = json.load(open(str(tmp / "v.json")))
        for s in ("at_scale_entry", "at_scale", "at_scale_exit", "at_forward_entry", "at_exit_front"):
            k = next((k for k in v["por_direccion"] if "(%s)" % s in k), None)
            verifica("vigila ve cambiar %-16s en la entrada discreta %d" % (s, E[s]["direccion"]),
                     k is not None and v["por_direccion"][k]["cambios"] >= 2, k)

        print("--- escribe mueve lo que su nombre dice ---")
        rc, out = sonda(host, puerto, "escribe", "entry_conveyor", "0")
        verifica("escribe entry_conveyor 0 -> lee 0", rc == 0 and "= 0" in out, out)
        time.sleep(3)          # una caja ya montada en el sensor la arrastra la banda de la bascula
        n = flancos(c, "at_scale_entry", 6)
        verifica("con entry_conveyor apagada no entra ninguna caja a la bascula (%d flancos)" % n, n == 0)
        sonda(host, puerto, "escribe", "entry_conveyor", "1")
        n = flancos(c, "at_scale_entry", 10, valor=1) + flancos(c, "at_scale_entry", 0.1, valor=0)
        verifica("con entry_conveyor encendida vuelven a entrar cajas", n >= 1, n)
        # send_forward es la motriz de las ruedas; send_left y send_right solo
        # las orientan: para mandar a un lado van send_forward + send_<lado>
        # (sin la motriz la caja se queda sobre el desviador o sale de frente).
        # La orden se da en el flanco de at_scale_exit; el destino real se
        # confirma con la salida NC de cada rama (baja a 0).
        ruedas = {"left": "send_left", "forward": "send_forward", "right": "send_right"}
        salidas = {"left": "at_exit_left", "forward": "at_exit_front", "right": "at_exit_right"}
        plan = ["left", "forward", "right"] * 3
        pendientes, resultados, previo, fin = [], [], None, time.time() + 150
        while (plan or pendientes) and time.time() < fin:
            d = c.lee_discretas(0, 9)
            if previo is not None:
                sale = d[E["at_scale_exit"]["direccion"]]
                if sale and not previo[E["at_scale_exit"]["direccion"]] and plan:
                    destino = plan.pop(0)
                    quiero = {"send_forward", ruedas[destino]}
                    for bob in ruedas.values():
                        if bob not in quiero:
                            c.escribe_bobina(E[bob]["direccion"], False)
                    for bob in quiero:
                        c.escribe_bobina(E[bob]["direccion"], True)
                    pendientes.append(destino)
                for k, sal in salidas.items():
                    a = E[sal]["direccion"]
                    if previo[a] and not d[a] and pendientes:       # NC: baja a 0 al salir una caja
                        resultados.append((pendientes.pop(0), k))
            previo = d
            time.sleep(0.01)
        bien = sum(1 for mandado, real in resultados if mandado == real)
        print("    mandado -> salio por: %s" % resultados)
        verifica("ruedas mandadas al llegar cada caja: %d de %d cajas salen por donde se mando" % (bien, len(resultados)),
                 len(resultados) >= 6 and bien == len(resultados))
        for k in ("left", "forward", "right"):
            verifica("send_%-8s mueve cajas a la salida %s" % (k, k), any(m == r == k for m, r in resultados))
        for otra in ("send_left", "send_right", "send_forward"):
            sonda(host, puerto, "escribe", otra, "0")
        for luz in ("start_light", "reset_light", "stop_light"):
            r1, o1 = sonda(host, puerto, "escribe", luz, "1")
            r0, o0 = sonda(host, puerto, "escribe", luz, "0")
            verifica("escribe %-11s 1 y 0 -> se lee de vuelta (visual en el tablero)" % luz,
                     r1 == r0 == 0 and "= 1" in o1 and "= 0" in o0, (o1, o0))
        for i, cont in enumerate(("left_count", "forward_count", "right_count")):
            rc, out = sonda(host, puerto, "escribe", cont, str(7 + i))
            verifica("escribe %-13s %d -> palabra %d (entero, sin escala)" % (cont, 7 + i, 7 + i),
                     rc == 0 and "palabra %d" % (7 + i) in out, out)
            sonda(host, puerto, "escribe", cont, "0")
        rc, out = sonda(host, puerto, "escribe", "weight", "3")
        verifica("weight es de solo lectura: escribe -> codigo 1", rc == 1 and "solo lectura" in out, out)
    finally:
        c.cierra()


def clase_de(peso_V, clases, plena_escala_kg):
    """Destino esperado de un peso en volts. Convierte con la plena escala de la
    configuracion, como A2-Planta (masa = V / 10 x plena_escala_kg, redondeada a
    gramos); asi el criterio en volts no depende de la unidad (paso U)."""
    masa = math.floor(peso_V / 10.0 * plena_escala_kg * 1000 + 0.5) / 1000.0   # Math.round de JS
    for k in clases:
        if k["hasta_kg"] is None or masa <= k["hasta_kg"]:
            return k["destino"]


def reinicia(host_escena):
    """Reset, vaciado y Run por Modbus (tools/reinicia_escena.mjs, en Node: llega directo a la VM)."""
    r = subprocess.run(["node", str(RAIZ / "tools" / "reinicia_escena.mjs"), host_escena, "502", "--mapa", MAPA],
                       capture_output=True, text=True, timeout=60)
    print("\n".join("    " + l for l in r.stdout.strip().splitlines()))
    verifica("escena reiniciada por Modbus: Reset, vacia y Run (codigo %d)" % r.returncode, r.returncode == 0, r.stderr)
    return r.returncode == 0


def cliente(host, puerto, segundos, cajas=None, materiales=False):
    import prueba_planta as pp
    planta = json.load(open(str(RAIZ / "config" / "planta_fio.json")))
    clases = planta["desviador"]["clases"]
    plena = planta["bascula"]["plena_escala_kg"]
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_fio_cliente_"))
    nr_host = os.environ.get("A2_MODBUS_HOST", "10.211.55.3")
    print("=== A2-Planta contra Factory I/O (Node-RED -> %s:502; oraculo por %s:%d; datos en %s) ===" % (nr_host, host, puerto, datos))
    # La escena se reinicia por Modbus antes de cada corrida: sin cajas de la
    # corrida anterior en el desviador, en las bandas de salida o en el piso.
    if not reinicia(nr_host):
        return datos
    o = Cliente(host, puerto, unidad=1)
    o.conecta()
    # --materiales (paso L de la fase 3): la capa de materiales encendida, con su
    # estado en este mismo directorio de datos (nuevo, asi que parte de D = 0).
    extra = {"A2_MATERIALES": 1, "A2_MAT_CONFIG": RAIZ / "config" / "materiales.json"} if materiales else {}
    ps.arranca(datos, A2_MAPA=MAPA, A2_PLANTA_CONFIG=RAIZ / "config" / "planta_fio.json", A2_SUSTITUTO=0,
               A2_MODBUS_HOST=nr_host, A2_MODBUS_PUERTO=502, A2_MODBUS_UNIDAD=1, **extra)
    esperado, real = [], []
    try:
        verifica("A2-Planta conecta con la escena (com ok)", pp.espera(lambda: pp.estado()["com"] == "ok", 30))
        st = pp.estado()
        verifica("limites factibles con sondeo %d ms (T_ef %d ms)" % (st["sondeo_ms"], st["limites"]["t_ef_ms"]),
                 st["limites"]["factible"], st["limites"]["problemas"])
        c, r = pp.comando(accion="marcha")
        verifica("marcha -> 200", c == 200, (c, r))
        salidas = {E["at_exit_left"]["direccion"]: "left", E["at_exit_front"]["direccion"]: "forward",
                   E["at_exit_right"]["direccion"]: "right"}
        a_bas, b_load = E["at_scale"]["direccion"], E["load_scale"]["direccion"]
        if cajas:
            segundos = max(segundos, 8 * cajas + 120)          # tope; se corta al llegar a `cajas` salidas
        previo, load_prev, peso, t_off, serie, fin = None, None, None, None, [], time.time() + segundos
        crudo_max = None    # paso L: mayor valor crudo de weight con load_scale apagada y la caja en at_scale
        t_suelta, t_sin_correr = [], None
        cambio, durac = {}, {}              # duraciones encendido/apagado por sensor, vistas por el oraculo
        while time.time() < fin:
            d = o.lee_discretas(0, 16)
            load = o.lee_bobinas(b_load, 1)[0]
            # Suelta = load_scale vuelve a 1 despues de estar en 0 al menos 0.5 s
            # (el pesaje dura >= 0.85 s). Si al oraculo le falto leer el peso (un
            # tropiezo del relevo), la suelta se cuenta igual, sin peso, para no
            # desalinear el orden de las cajas.
            if load_prev is False and load and t_off is not None and time.time() - t_off >= 0.5:
                if serie:
                    ult = [v for tt, v in serie if tt >= serie[-1][0] - 0.3]
                    esperado.append((peso, clase_de(peso, clases, plena), max(ult) - min(ult), crudo_max))
                else:
                    esperado.append((None, None, None, crudo_max))
                t_suelta.append(time.time())
                peso = None
            if load or load_prev is None:
                t_off, serie, crudo_max = None, [], None
            elif t_off is None:
                t_off = time.time()
            if not load and d[a_bas] and t_off is not None:
                # Se lee durante todo el pesaje para el maximo crudo (paso L); el
                # peso y su serie siguen tomandose solo desde 0.5 s, como antes.
                crudo = o.lee_entrada(E["weight"]["direccion"], 1)[0]
                crudo_max = crudo if crudo_max is None else max(crudo_max, crudo)
                if time.time() - t_off >= 0.5:
                    peso = crudo / 100.0                                   # caja quieta en la bascula
                    serie.append((time.time(), peso))
            if previo is not None:
                ahora = time.time()
                for i in range(9):
                    if d[i] != previo[i]:
                        if i in cambio:
                            durac.setdefault(i, {True: [], False: []})[previo[i]].append(ahora - cambio[i])
                        cambio[i] = ahora
                for a, dest in salidas.items():
                    if previo[a] and not d[a]:
                        real.append(dest)
                        if cajas and len(real) % 25 == 0:
                            print("    ... %d cajas fuera" % len(real), flush=True)
            previo, load_prev = d, load
            if cajas and len(real) >= cajas:
                break
            if not d[E["fio_running"]["direccion"]]:
                t_sin_correr = t_sin_correr or time.time()
                if time.time() - t_sin_correr > 2:
                    verifica("la escena sigue corriendo durante la prueba", False, "fio_running = 0 por mas de 2 s")
                    break
            else:
                t_sin_correr = None
            time.sleep(0.015)
        t_paro = time.time()
        pp.comando(accion="paro")         # apaga las bandas: se compara solo lo que ya salio
        time.sleep(1)
        st = pp.estado()
    finally:
        o.cierra()
        ps.detiene()
    ev = [json.loads(l) for l in (datos / "a2_planta_eventos.jsonl").read_text().splitlines() if l.strip()]
    pasos = [e for e in ev if e["ev"] == "paso_caja"]
    k = st["contadores"]
    print("    oraculo: %d cajas soltadas, %d salidas NC; cliente: %d pasos" % (len(esperado), len(real), len(pasos)))
    print("    por destino (cliente): %s | purgadas %d" % (k["por_destino"], k.get("purgadas", 0)))
    # Una caja que estaba parada sobre el desviador sale de frente con la purga
    # del arranque, sin haber pasado por la bascula: no es de ninguna soltada.
    for _ in range(k.get("purgadas", 0)):
        if "forward" in real[:3]:
            real.remove("forward")
    n = min(len(esperado), len(real))
    sin_peso = [i for i in range(n) if esperado[i][0] is None]
    if sin_peso:
        print("    sueltas sin peso del oraculo (tropiezo de lectura): %s" % sin_peso)
    (datos / "oraculo.json").write_text(json.dumps({"esperado": esperado, "real": real, "t_suelta": t_suelta}))
    bien = sum(1 for i in range(n) if esperado[i][1] == real[i])
    malas = [(i, esperado[i], real[i]) for i in range(n) if esperado[i][1] != real[i] and esperado[i][0] is not None]
    verifica("al menos 15 cajas clasificadas en %d s (%d)" % (segundos, n), n >= 15)
    verifica("cada caja sale por la salida de su peso (oraculo): %d de %d (%d sin peso del oraculo)" % (bien, n, len(sin_peso)),
             n > 0 and not malas and len(sin_peso) <= max(1, n // 50), malas[:5])
    verifica("las tres salidas se usan", set(real[:n]) == {"left", "forward", "right"}, sorted(set(real)))
    m = min(len(pasos), n)
    verifica("el cliente reporta el mismo destino que la salida real, caja por caja (%d)" % m,
             m >= n - 1 and all(pasos[i]["destino"] == real[i] for i in range(m)),
             [(p["destino"], r) for p, r in zip(pasos, real) if p["destino"] != r][:5])
    # El oraculo lee el peso cada ~20 ms; si en sus ultimos 0.3 s antes de la
    # suelta vario mas de 0.05 V, la caja aun se movia y los dos pueden haber
    # leido puntos distintos de la oscilacion: esas se reportan, no se comparan.
    quietas = [i for i in range(m) if esperado[i][0] is not None and esperado[i][2] <= 0.05]
    movidas = [(pasos[i]["peso_V"], esperado[i][0], round(esperado[i][2], 2)) for i in range(m)
               if esperado[i][0] is not None and esperado[i][2] > 0.05]
    print("    cajas que el oraculo vio moverse al soltarlas (cliente, oraculo, variacion): %s" % movidas)
    verifica("pesos del cliente = pesos del oraculo (+-0.05 V) en las %d cajas quietas" % len(quietas),
             all(abs(pasos[i]["peso_V"] - esperado[i][0]) <= 0.05 for i in quietas),
             [(pasos[i]["peso_V"], esperado[i][0]) for i in quietas if abs(pasos[i]["peso_V"] - esperado[i][0]) > 0.05][:5])
    verifica("y la misma clase en todas las que el oraculo peso (%d)" % (m - len([i for i in sin_peso if i < m])),
             all(clase_de(pasos[i]["peso_V"], clases, plena) == esperado[i][1] for i in range(m) if esperado[i][0] is not None))
    # Caidas: toda caja soltada mas de 12 s antes del paro tuvo tiempo de llegar
    # a su salida NC (la ultima tarda ~6 s); si falta alguna, se cayo o se atoro.
    viejas = sum(1 for t in t_suelta if t_paro - t > 12)
    verifica("ninguna caja se cae ni se atora: %d soltadas con mas de 12 s antes del paro, %d salidas" % (viejas, len(real)),
             len(real) >= viejas, (viejas, len(real)))
    if cajas:
        verifica("%d cajas por la salida de su peso (%d)" % (cajas, n), n >= cajas)
    verifica("T_ef sale de lo medido (%s ms, %s)" % (st["limites"]["t_ef_ms"], st["limites"].get("t_ef_origen")),
             st["limites"].get("t_ef_origen") == "medido")
    ramas = {s: v for s, v in (st.get("min_lecturas_por_pulso") or {}).items() if s in ("at_left_entry", "at_forward_entry", "at_right_entry")}
    verifica("cada pulso de los sensores de rama visto en al menos 3 lecturas %s" % ramas,
             len(ramas) == 3 and min(ramas.values()) >= 3, ramas)
    verifica("sin desvios erroneos, perdidas ni fantasmas (%d / %d / %d)"
             % (k["desvios_erroneos"], k["perdidas"], k["fantasmas"] + k["fantasmas_bascula"]),
             k["desvios_erroneos"] == 0 and k["perdidas"] == 0 and k["fantasmas"] + k["fantasmas_bascula"] == 0, k)
    # Factibilidad bajo control: cada sensor que sigue el cliente, encendido y
    # apagado al menos t_min; y el cliente vio cada pulso en >= 3 lecturas.
    lim = st["limites"]
    print("    tiempos bajo control (oraculo, s) contra t_min %.2f s:" % lim["t_min_s"])
    seguidos = [n for n in planta["linea"]["sensores"]]
    cortos = []
    for nombre in seguidos:
        dd = durac.get(E[nombre]["direccion"], {True: [], False: []})
        on, off = min(dd[True] or [None]) if dd[True] else None, min(dd[False]) if dd[False] else None
        print("      %-17s encendido min %s  apagado min %s  (%d pulsos)" % (nombre, "%.2f" % on if on else "-",
              "%.2f" % off if off else "-", len(dd[True])))
        if (on is not None and on < lim["t_min_s"]) or (off is not None and off < lim["t_min_s"]):
            cortos.append(nombre)
    verifica("bajo control, todo sensor seguido dura al menos t_min encendido y apagado", not cortos, cortos)
    mins = st.get("min_lecturas_por_pulso") or {}
    print("    lecturas minimas por pulso (cliente): %s" % mins)
    verifica("el cliente vio cada pulso en al menos 3 lecturas", mins and min(mins.values()) >= 3, mins)
    return datos


def tablero(host, puerto, segundos):
    """Vigila el tablero mientras Ari presiona los botones en la escena.

    Orden pedido: Start, Stop, Start, Emergency stop (dejarlo presionado unos
    segundos), soltar Emergency stop, Start, Stop. Se imprime en vivo cada
    cambio de boton (valor crudo), la linea del cliente y las luces.
    """
    import prueba_planta as pp
    datos = pathlib.Path(tempfile.mkdtemp(prefix="a2_fio_tablero_"))
    nr_host = os.environ.get("A2_MODBUS_HOST", "10.211.55.3")
    print("=== Tablero de la escena (datos en %s) ===" % datos)
    if not reinicia(nr_host):
        return
    ps.arranca(datos, A2_MAPA=MAPA, A2_PLANTA_CONFIG=RAIZ / "config" / "planta_fio.json", A2_SUSTITUTO=0,
               A2_MODBUS_HOST=nr_host, A2_MODBUS_PUERTO=502, A2_MODBUS_UNIDAD=1)
    o = Cliente(host, puerto, unidad=1)
    o.conecta()
    botones = ["start_button", "stop_button", "emergency_stop"]
    luces = ["start_light", "stop_light", "reset_light"]
    obs = []                    # (t, boton, valor crudo, linea despues de 0.6 s, luces, bandas)
    try:
        verifica("A2-Planta conecta con la escena (com ok)", pp.espera(lambda: pp.estado()["com"] == "ok", 30))
        reposo = {b: o.lee_discretas(E[b]["direccion"], 1)[0] for b in botones}
        print("    en reposo (sin presionar): %s" % {b: int(v) for b, v in reposo.items()})
        print("    >>> VIGILANDO: presiona en la escena Start, Stop, Start, Emergency stop (dejalo unos segundos),")
        print("    >>> suelta Emergency stop, Start y Stop. Tengo %d s." % segundos, flush=True)
        previo, t0, fin = dict(reposo), time.time(), time.time() + segundos
        while time.time() < fin:
            for b in botones:
                v = o.lee_discretas(E[b]["direccion"], 1)[0]
                if v != previo[b]:
                    time.sleep(0.6)                       # que el cliente reaccione
                    st = pp.estado()
                    lz = {l: int(o.lee_bobinas(E[l]["direccion"], 1)[0]) for l in luces}
                    banda = int(o.lee_bobinas(E["entry_conveyor"]["direccion"], 1)[0])
                    obs.append((time.time() - t0, b, int(v), st["linea"], lz, banda))
                    print("    %6.1f s  %-15s %d -> %d   linea: %-10s luces %s  entry_conveyor %d"
                          % (time.time() - t0, b, int(previo[b]), int(v), st["linea"], lz, banda), flush=True)
                    previo[b] = v
            hechos = [(b, v) for _, b, v, _, _, _ in obs]
            if hechos.count(("emergency_stop", 1)) >= 1 and hechos.count(("stop_button", 1)) >= 2 and \
                    hechos[-1] == ("stop_button", 1):
                break
            time.sleep(0.02)
        pp.comando(accion="paro")
    finally:
        o.cierra()
        ps.detiene()
    cambios = lambda b: [(v, linea, lz, banda) for _, bb, v, linea, lz, banda in obs if bb == b]
    stop, emer, start = cambios("stop_button"), cambios("emergency_stop"), cambios("start_button")
    verifica("Stop es NC: 1 en reposo, baja a 0 al presionar y vuelve a 1", reposo["stop_button"] and stop
             and stop[0][0] == 0 and any(v == 1 for v, *_ in stop), (int(reposo["stop_button"]), [s[0] for s in stop]))
    verifica("Emergency stop es NC: 1 en reposo, baja a 0 al presionar y vuelve a 1", reposo["emergency_stop"] and emer
             and emer[0][0] == 0 and any(v == 1 for v, *_ in emer), (int(reposo["emergency_stop"]), [s[0] for s in emer]))
    verifica("Start es normalmente abierto: 0 en reposo, 1 al presionar", not reposo["start_button"] and start
             and start[0][0] == 1, (int(reposo["start_button"]), [s[0] for s in start]))
    verifica("Start presionado (sin emergencia) -> en marcha, start_light 1, banda de entrada encendida",
             any(v == 1 and l == "en_marcha" and lz["start_light"] and banda for v, l, lz, banda in start))
    verifica("Stop presionado -> detenida, stop_light 1, banda de entrada apagada",
             any(v == 0 and l == "detenida" and lz["stop_light"] and not banda for v, l, lz, banda in stop))
    verifica("Emergency stop presionado -> emergencia, reset_light 1, banda apagada",
             any(v == 0 and l == "emergencia" and lz["reset_light"] and not banda for v, l, lz, banda in emer))
    verifica("Emergency stop soltado -> detenida, sin arrancar sola",
             any(v == 1 and l == "detenida" and not lz["reset_light"] and not banda for v, l, lz, banda in emer))
    ev = [json.loads(l) for l in (datos / "a2_planta_eventos.jsonl").read_text().splitlines() if l.strip()]
    print("    eventos del cliente: %s" % [(e["ev"], e.get("boton") or e.get("accion")) for e in ev
                                           if e["ev"] in ("boton", "paro_de_emergencia", "emergencia_liberada")])


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("modo", nargs="?", default="mapa", choices=["mapa", "cliente", "tablero"])
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--puerto", type=int, default=5031)
    a.add_argument("-s", "--segundos", type=int, default=240)
    a.add_argument("--cajas", type=int, help="con cliente: corre hasta ver este numero de cajas salir")
    a.add_argument("--materiales", action="store_true", help="con cliente: capa de materiales encendida (paso L)")
    x = a.parse_args()
    if x.modo == "cliente":
        cliente(x.host, x.puerto, x.segundos, x.cajas, x.materiales)
    elif x.modo == "tablero":
        tablero(x.host, x.puerto, max(x.segundos, 600))
    else:
        main(x.host, x.puerto)
    print("\n=== RESULTADO: %d correctas, %d fallidas ===" % (ps.resultado["ok"], ps.resultado["falla"]))
    sys.exit(ps.resultado["falla"])
