#!/usr/bin/env python3
"""Sonda Modbus: lee o escribe una etiqueta del mapa por su nombre.

Sirve para comprobar la conexion con Factory I/O (o con el sustituto) sin
Node-RED de por medio. Compatible con Python 3.9, sin dependencias.

    python3 tools/sonda_modbus.py lista
    python3 tools/sonda_modbus.py lee peso_V
    python3 tools/sonda_modbus.py lee todas
    python3 tools/sonda_modbus.py escribe vel_banda_V -2.5
    python3 tools/sonda_modbus.py escribe emisor_on 1
    python3 tools/sonda_modbus.py --host 100.x.y.z --puerto 502 lee sens_entrada
    python3 tools/sonda_modbus.py --host 100.x.y.z --puerto 502 mide peso_V -n 50
    python3 tools/sonda_modbus.py --host 100.x.y.z --puerto 502 vigila -s 180 --json datos/vigila.json
    python3 tools/sonda_modbus.py vigila -s 60 --discretas 0:14 --entrada 0:1   (rangos, sin mapa)

`mide` repite N lecturas de una etiqueta por la MISMA conexion y reporta el
tiempo de ida y vuelta de cada peticion (minimo, mediana, p95 y maximo), mas
el de abrir la conexion TCP aparte. Es lo primero que conviene correr contra
la maquina de Azure: con Factory I/O en Hong Kong cada lectura es un viaje
completo, y ese numero decide el periodo de sondeo que aguanta A2-Planta.

Destino: --host / --puerto / --unidad, y si no se dan, A2_MODBUS_HOST,
A2_MODBUS_PUERTO y A2_MODBUS_UNIDAD del entorno o de ../.env. Sin nada de eso,
127.0.0.1:5020 (el sustituto), unidad 1.

Los valores se dan y se muestran en unidades fisicas; la conversion
(escala, complemento a dos) es la del mapa. Las etiquetas de solo lectura
(entradas discretas, registros de entrada) no se pueden escribir: Modbus no
tiene funcion para eso y la sonda lo dice antes de abrir la conexion.

`vigila` (solo lectura) lee en bloque, tan rapido como conteste el destino,
las entradas discretas y los registros de entrada del mapa (o los rangos que
se le den) durante N segundos. Reporta los cambios por direccion con su hora,
la duracion de cada pulso en lecturas y en segundos, la ida y vuelta de cada
peticion, y el PERIODO DE REFRESCO de la escena: el menor intervalo observado
entre dos valores distintos de una misma entrada. Factory I/O corre a ~1 FPS
en la VM de Azure; si la escena refresca mas lento que el sondeo, el periodo
que manda es el del refresco, no el del sondeo.

Codigos de salida: 0 bien, 1 uso o valor invalido, 2 sin conexion,
3 el servidor respondio con una excepcion Modbus.
"""
import argparse, json, os, pathlib, socket, sys, time

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import mapa_registros as mr  # noqa: E402
from modbus_tcp import Cliente, ModbusError  # noqa: E402

TABLA = {"bobina": "bobina", "entrada_discreta": "entrada discreta",
         "registro_entrada": "registro de entrada", "registro_retencion": "registro de retencion"}


def lee_env():
    """Variables A2_MODBUS_* del entorno y, si faltan, de ../.env."""
    vals = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea.startswith("A2_MODBUS_") and "=" in linea:
                k, v = linea.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        if k.startswith("A2_MODBUS_"):
            vals[k] = v
    return {k: v for k, v in vals.items() if v != ""}


def lee_etiqueta(c, e):
    d = e["direccion"]
    if e["tabla"] == "bobina":
        crudo = c.lee_bobinas(d, 1)[0]
    elif e["tabla"] == "entrada_discreta":
        crudo = c.lee_discretas(d, 1)[0]
    elif e["tabla"] == "registro_entrada":
        crudo = c.lee_entrada(d, 1)[0]
    else:
        crudo = c.lee_retencion(d, 1)[0]
    return crudo, mr.de_registro(e, crudo)


def texto(e, crudo, valor):
    donde = "%s %d" % (TABLA[e["tabla"]], e["direccion"])
    if e["tipo"] == "bool":
        return "%s = %d   (%s)" % (e["nombre"], int(valor), donde)
    return "%s = %g %s   (%s, palabra %d)" % (e["nombre"], valor, e["unidad"], donde, crudo)


def interpreta(e, cadena):
    """Texto de la linea de comandos -> valor fisico validado contra el mapa."""
    if e["tipo"] == "bool":
        c = cadena.strip().lower()
        if c in ("1", "true", "si", "on"):
            return True
        if c in ("0", "false", "no", "off"):
            return False
        raise ValueError("%s es booleana: usa 1/0" % e["nombre"])
    try:
        v = float(cadena)
    except ValueError:
        raise ValueError("%r no es un numero" % cadena)
    mr.a_registro(e, v)                       # valida el rango fisico
    return v


def percentil(ordenados, q):
    """Percentil por interpolacion lineal (el mismo criterio que numpy por omision)."""
    k = (len(ordenados) - 1) * q
    i = int(k)
    return ordenados[i] if i + 1 >= len(ordenados) else ordenados[i] + (ordenados[i + 1] - ordenados[i]) * (k - i)


def mide(e, host, puerto, unidad, a):
    """N lecturas por una sola conexion; cada tiempo es una peticion Modbus completa."""
    if e is None:
        print("mide necesita una etiqueta concreta", file=sys.stderr)
        return 1
    c = Cliente(host, puerto, unidad=unidad, espera_s=a.espera)
    tiempos, fallos, ultimo = [], 0, None
    try:
        t = time.perf_counter()
        c.conecta()                                  # el saludo TCP es un viaje completo
        conexion_ms = (time.perf_counter() - t) * 1000
        for i in range(a.n):
            t = time.perf_counter()
            try:
                ultimo = lee_etiqueta(c, e)
                tiempos.append((time.perf_counter() - t) * 1000)
            except (OSError, ConnectionError, socket.timeout):
                fallos += 1
                c.cierra()                           # se reabre en la siguiente
            if a.pausa_ms and i + 1 < a.n:
                time.sleep(a.pausa_ms / 1000)
    except ModbusError as ex:
        print("%s:%d unidad %d: %s" % (host, puerto, unidad, ex), file=sys.stderr)
        return 3
    except (OSError, ConnectionError, socket.timeout) as ex:
        print("sin conexion con %s:%d: %s" % (host, puerto, ex), file=sys.stderr)
        return 2
    finally:
        c.cierra()
    if not tiempos:
        print("ninguna de las %d lecturas contesto" % a.n, file=sys.stderr)
        return 2
    o = sorted(tiempos)
    print("destino     %s:%d unidad %d, etiqueta %s" % (host, puerto, unidad, e["nombre"]))
    print("conexion    %.1f ms (saludo TCP)" % conexion_ms)
    print("lecturas    %d de %d contestaron%s" % (len(o), a.n, ", %d fallaron" % fallos if fallos else ""))
    print("ida y vuelta  min %.1f   mediana %.1f   p95 %.1f   max %.1f   ms"
          % (o[0], percentil(o, 0.5), percentil(o, 0.95), o[-1]))
    if ultimo:
        print("ultimo valor  " + texto(e, *ultimo))
    return 0 if not fallos else 2


def rango(texto, tags, tabla):
    """'0:14' -> (0, 14); sin texto, el bloque minimo que cubre las etiquetas del mapa en esa tabla."""
    if texto:
        ini, fin = (int(x) for x in texto.split(":"))
        return ini, fin - ini
    dirs = [e["direccion"] for e in tags if e["tabla"] == tabla]
    return (min(dirs), max(dirs) - min(dirs) + 1) if dirs else (0, 0)


def resumen(valores):
    if not valores:
        return None
    o = sorted(valores)
    return {"n": len(o), "min": round(o[0], 4), "p50": round(percentil(o, 0.5), 4),
            "p95": round(percentil(o, 0.95), 4), "max": round(o[-1], 4)}


def vigila(mapa, host, puerto, unidad, a):
    """Solo lectura. Dos peticiones por vuelta (un bloque por tabla), sin pausa."""
    tags = mapa["etiquetas"]
    d0, dn = rango(a.discretas, tags, "entrada_discreta")
    r0, rn = rango(a.entrada, tags, "registro_entrada")
    nombre = {("d", e["direccion"]): e["nombre"] for e in tags if e["tabla"] == "entrada_discreta"}
    nombre.update({("r", e["direccion"]): e["nombre"] for e in tags if e["tabla"] == "registro_entrada"})
    c = Cliente(host, puerto, unidad=unidad, espera_s=a.espera)
    rtts, fallos, vueltas = [], 0, 0
    previo, cambios = {}, []                 # cambios: (t, clave, valor_anterior, valor, n_lectura)
    lecturas = {}                            # clave -> cuantas lecturas lleva en el valor actual
    pulsos = {}                              # clave -> [(lecturas, segundos)] de cada pulso en 1
    inicio_pulso = {}
    t_ini = time.time()
    try:
        c.conecta()
    except (OSError, ConnectionError, socket.timeout) as ex:
        print("sin conexion con %s:%d: %s" % (host, puerto, ex), file=sys.stderr)
        return 2
    while time.time() - t_ini < a.segundos:
        muestra = {}
        try:
            for tabla, ini, n in (("d", d0, dn), ("r", r0, rn)):
                if not n:
                    continue
                t = time.perf_counter()
                vals = c.lee_discretas(ini, n) if tabla == "d" else c.lee_entrada(ini, n)
                rtts.append((time.perf_counter() - t) * 1000)
                for i, v in enumerate(vals):
                    muestra[(tabla, ini + i)] = int(v)
        except ModbusError as ex:
            print("%s:%d unidad %d: %s" % (host, puerto, unidad, ex), file=sys.stderr)
            return 3
        except (OSError, ConnectionError, socket.timeout):
            fallos += 1
            c.cierra()
            continue
        vueltas += 1
        ahora = time.time() - t_ini
        for k, v in muestra.items():
            if k not in previo:
                previo[k], lecturas[k] = v, 1
                continue
            if v == previo[k]:
                lecturas[k] += 1
                continue
            cambios.append((round(ahora, 4), k, previo[k], v, vueltas))
            if k[0] == "d" and v == 1:
                inicio_pulso[k] = (ahora, vueltas)
            if k[0] == "d" and v == 0 and k in inicio_pulso:
                t0, n0 = inicio_pulso.pop(k)
                pulsos.setdefault(k, []).append((vueltas - n0, ahora - t0))
            previo[k], lecturas[k] = v, 1
    c.cierra()
    dur = time.time() - t_ini

    def etiqueta(k):
        return "%s %d%s" % ("discreta" if k[0] == "d" else "registro", k[1],
                            " (%s)" % nombre[k] if k in nombre else "")
    por_dir = {}
    for t, k, va, v, n in cambios:
        por_dir.setdefault(k, []).append(t)
    intervalos = {k: [b - a_ for a_, b in zip(ts, ts[1:])] for k, ts in por_dir.items()}
    todos = [x for v in intervalos.values() for x in v]
    print("destino     %s:%d unidad %d durante %.0f s" % (host, puerto, unidad, dur))
    print("bloques     discretas %d..%d, registros de entrada %d..%d" % (d0, d0 + dn - 1, r0, r0 + rn - 1))
    print("vueltas     %d (%.1f por segundo), %d fallidas" % (vueltas, vueltas / dur if dur else 0, fallos))
    o = resumen(rtts)
    if o:
        print("ida y vuelta  min %.1f   mediana %.1f   p95 %.1f   max %.1f   ms (%d peticiones)"
              % (o["min"], o["p50"], o["p95"], o["max"], o["n"]))
    refresco = min(todos) if todos else None
    print("refresco    %s" % ("menor intervalo entre dos valores distintos de una misma entrada: %.3f s" % refresco
                              if refresco is not None else "sin cambios observados"))
    for k in sorted(set(por_dir) | set(pulsos)):
        p = pulsos.get(k, [])
        linea = "  %-28s %4d cambios" % (etiqueta(k), len(por_dir.get(k, [])))
        if p:
            pl, ps_ = [x[0] for x in p], [x[1] for x in p]
            linea += ", %d pulsos en 1: lecturas min %d / mediana %g / max %d, segundos min %.2f / max %.2f" % (
                len(p), min(pl), percentil(sorted(pl), 0.5), max(pl), min(ps_), max(ps_))
        if intervalos.get(k):
            linea += ", intervalo minimo %.3f s / mediana %.3f s" % (min(intervalos[k]),
                                                                    percentil(sorted(intervalos[k]), 0.5))
        print(linea)
    if a.detalle:
        for t, k, va, v, n in cambios:
            print("    %9.3f s  %-28s %s -> %s" % (t, etiqueta(k), va, v))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "destino": "%s:%d" % (host, puerto), "unidad": unidad, "segundos": round(dur, 2),
            "vueltas": vueltas, "fallidas": fallos, "rtt_ms": resumen(rtts), "refresco_s": refresco,
            "por_direccion": {etiqueta(k): {"cambios": len(por_dir.get(k, [])),
                                            "pulsos": [{"lecturas": n_, "segundos": round(s_, 4)} for n_, s_ in pulsos.get(k, [])],
                                            "intervalo_min_s": min(intervalos[k]) if intervalos.get(k) else None,
                                            "intervalo_mediana_s": round(percentil(sorted(intervalos[k]), 0.5), 4)
                                            if intervalos.get(k) else None}
                              for k in sorted(set(por_dir) | set(pulsos))},
            "cambios": [{"t": t, "dir": etiqueta(k), "de": va, "a": v, "vuelta": n} for t, k, va, v, n in cambios]
        }, indent=1, ensure_ascii=False), encoding="utf-8")
        print("detalle en %s" % a.json)
    return 0 if vueltas else 2


def main(argv=None):
    p = argparse.ArgumentParser(description="Lee o escribe una etiqueta del mapa Modbus de la Actividad 2.")
    p.add_argument("--host")
    p.add_argument("--puerto", type=int)
    p.add_argument("--unidad", type=int)
    p.add_argument("--espera", type=float, default=3.0, help="segundos de espera de conexion y respuesta")
    p.add_argument("--mapa", default=str(mr.MAPA))
    sub = p.add_subparsers(dest="accion", required=True)
    sub.add_parser("lista")
    s = sub.add_parser("lee")
    s.add_argument("etiqueta", help="nombre del mapa, o 'todas'")
    s = sub.add_parser("escribe")
    s.add_argument("etiqueta")
    s.add_argument("valor")
    s = sub.add_parser("mide", help="tiempo de ida y vuelta de N lecturas")
    s.add_argument("etiqueta")
    s.add_argument("-n", type=int, default=20, help="repeticiones (20)")
    s.add_argument("--pausa-ms", type=float, default=0, help="espera entre lecturas (0)")
    s = sub.add_parser("vigila", help="solo lectura: cambios, pulsos y periodo de refresco durante N segundos")
    s.add_argument("-s", "--segundos", type=float, default=60)
    s.add_argument("--discretas", help="rango de entradas discretas, ej. 0:14 (fin exclusivo); por omision, las del mapa")
    s.add_argument("--entrada", help="rango de registros de entrada, ej. 0:1; por omision, los del mapa")
    s.add_argument("--json", help="guarda aqui el detalle completo (cambios con su hora)")
    s.add_argument("--detalle", action="store_true", help="imprime cada cambio")
    a = p.parse_args(argv)
    if a.accion == "mide" and a.n < 1:
        print("-n debe ser al menos 1", file=sys.stderr)
        return 1

    try:
        mapa = mr.carga(a.mapa)
    except (mr.MapaInvalido, OSError) as ex:
        # vigila con rangos explicitos no necesita el mapa: sirve justo para
        # descubrir las direcciones de una escena cuyo mapa aun no existe.
        if a.accion == "vigila" and a.discretas and a.entrada:
            mapa = {"etiquetas": []}
            print("(mapa no valido, se vigila por rangos: %s)" % str(ex).splitlines()[0], file=sys.stderr)
        else:
            print(ex, file=sys.stderr)
            return 1
    E = {e["nombre"]: e for e in mapa["etiquetas"]}

    if a.accion == "lista":
        for e in sorted(mapa["etiquetas"], key=lambda e: (list(TABLA).index(e["tabla"]), e["direccion"])):
            rango = "" if e["tipo"] == "bool" else "  %g a %g %s" % (e["rango_fisico"][0], e["rango_fisico"][1], e["unidad"])
            print("%-16s %-9s %-22s %-6s%s" % (e["nombre"], e["sentido"],
                                               "%s %d" % (TABLA[e["tabla"]], e["direccion"]), e["tipo"], rango))
        return 0

    if a.accion == "vigila":
        env = lee_env()
        return vigila(mapa, a.host or env.get("A2_MODBUS_HOST", "127.0.0.1"),
                      a.puerto or int(env.get("A2_MODBUS_PUERTO", "5020")),
                      a.unidad if a.unidad is not None else int(env.get("A2_MODBUS_UNIDAD", "1")), a)
    if a.etiqueta != "todas" and a.etiqueta not in E:
        print("no existe la etiqueta %r. Validas: %s" % (a.etiqueta, ", ".join(sorted(E))), file=sys.stderr)
        return 1
    if a.accion == "escribe":
        e = E[a.etiqueta] if a.etiqueta != "todas" else None
        if e is None:
            print("'todas' solo sirve para leer", file=sys.stderr)
            return 1
        if e["tabla"] in ("entrada_discreta", "registro_entrada"):
            print("%s es una %s: es de solo lectura en Modbus" % (e["nombre"], TABLA[e["tabla"]]), file=sys.stderr)
            return 1
        try:
            valor = interpreta(e, a.valor)
        except ValueError as ex:
            print(ex, file=sys.stderr)
            return 1

    env = lee_env()
    host = a.host or env.get("A2_MODBUS_HOST", "127.0.0.1")
    puerto = a.puerto or int(env.get("A2_MODBUS_PUERTO", "5020"))
    unidad = a.unidad if a.unidad is not None else int(env.get("A2_MODBUS_UNIDAD", "1"))
    if a.accion == "mide":
        return mide(E[a.etiqueta] if a.etiqueta != "todas" else None, host, puerto, unidad, a)
    try:
        with Cliente(host, puerto, unidad=unidad, espera_s=a.espera) as c:
            if a.accion == "lee":
                for e in (mapa["etiquetas"] if a.etiqueta == "todas" else [E[a.etiqueta]]):
                    print(texto(e, *lee_etiqueta(c, e)))
            else:
                palabra = mr.a_registro(e, valor)
                if e["tabla"] == "bobina":
                    c.escribe_bobina(e["direccion"], palabra)
                else:
                    c.escribe_registro(e["direccion"], palabra)
                # Se lee de vuelta: que el servidor acepte la escritura no
                # prueba que la haya guardado donde se cree.
                print("escrito  " + texto(e, *lee_etiqueta(c, e)))
    except ModbusError as ex:
        print("%s:%d unidad %d: %s" % (host, puerto, unidad, ex), file=sys.stderr)
        return 3
    except (OSError, ConnectionError, socket.timeout) as ex:
        print("sin conexion con %s:%d: %s" % (host, puerto, ex), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
