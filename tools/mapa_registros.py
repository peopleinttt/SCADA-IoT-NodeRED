#!/usr/bin/env python3
"""Contrato de registros Modbus de la Actividad 2.

config/mapa_registros_a2.json es la fuente unica: de ahi salen el cliente de
Node-RED, el simulador de la planta, la sonda y docs/MAPA_REGISTROS.md. Este
modulo lo valida y genera la documentacion. Compatible con Python 3.9.

    python3 tools/mapa_registros.py valida             -> codigo 0 si el mapa es valido
    python3 tools/mapa_registros.py doc                -> reescribe docs/MAPA_REGISTROS.md (las dos versiones)
    python3 tools/mapa_registros.py doc --revisa       -> codigo 1 si la doc esta desfasada
    (--mapa RUTA cambia el archivo de entrada en los tres casos)

La validacion junta TODOS los errores antes de rechazar, para que un mapa con
tres problemas no haga falta corregirlo en tres vueltas. Cada error empieza con
un codigo estable (direccion_repetida, escala_desborda_tipo...) que es lo que
comparan las pruebas.
"""
import argparse, json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
MAPA = RAIZ / "config" / "mapa_registros_a2.json"
DOC = RAIZ / "docs" / "MAPA_REGISTROS.md"

# Las cuatro tablas de Modbus. Las de entrada las escribe la planta y el
# protocolo no tiene funcion para que un cliente las escriba.
TABLAS = {
    "entrada_discreta":   {"digital": True,  "solo_lectura": True,  "titulo": "Entradas discretas (FC 02)"},
    "registro_entrada":   {"digital": False, "solo_lectura": True,  "titulo": "Registros de entrada (FC 04)"},
    "bobina":             {"digital": True,  "solo_lectura": False, "titulo": "Bobinas (FC 01 / 05 / 15)"},
    "registro_retencion": {"digital": False, "solo_lectura": False, "titulo": "Registros de retencion (FC 03 / 06 / 16)"},
}
# Lo que cabe en un registro de 16 bits segun como se interprete.
TIPOS = {"bool": None, "uint16": (0, 65535), "int16": (-32768, 32767)}
CAMPOS = ["nombre", "tabla", "direccion", "tipo", "escala", "unidad",
          "rango_fisico", "sentido", "descripcion"]
SENTIDOS = ("lectura", "escritura")
RE_NOMBRE = re.compile(r"^[a-z][a-z0-9_]*(_[A-Za-z]+)?$")


class MapaInvalido(Exception):
    def __init__(self, errores):
        self.errores = errores
        super().__init__("mapa invalido:\n  " + "\n  ".join(errores))


def _entero(x):
    # bool es subclase de int en Python: True pasaria como direccion 1.
    return isinstance(x, int) and not isinstance(x, bool)


def _numero(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def valida(mapa):
    """Devuelve la lista de errores; vacia si el mapa es valido."""
    err = []
    if not isinstance(mapa, dict):
        return ["estructura: la raiz debe ser un objeto"]
    if not _entero(mapa.get("version")):
        err.append("estructura: falta version entera")

    driver = mapa.get("driver")
    factor, limites = None, {}
    if not isinstance(driver, dict):
        err.append("estructura: falta el objeto driver")
    else:
        factor = driver.get("factor_escala")
        if not _numero(factor) or factor <= 0:
            err.append("estructura: driver.factor_escala debe ser un numero positivo")
            factor = None
        limites = driver.get("limites") if isinstance(driver.get("limites"), dict) else {}
        for t in TABLAS:
            if not _entero(limites.get(t)) or limites.get(t) <= 0:
                err.append("estructura: driver.limites.%s debe ser un entero positivo" % t)

    etiquetas = mapa.get("etiquetas")
    if not isinstance(etiquetas, list) or not etiquetas:
        err.append("estructura: etiquetas debe ser una lista no vacia")
        return err

    nombres, ocupadas = {}, {}
    for i, e in enumerate(etiquetas):
        if not isinstance(e, dict):
            err.append("estructura: etiquetas[%d] no es un objeto" % i)
            continue
        quien = "%s (etiquetas[%d])" % (e.get("nombre", "?"), i)
        faltan = [c for c in CAMPOS if c not in e]
        sobran = [c for c in e if c not in CAMPOS]
        if faltan:
            err.append("campo_faltante: %s: %s" % (quien, ", ".join(faltan)))
        if sobran:
            err.append("campo_no_esperado: %s: %s" % (quien, ", ".join(sobran)))
        if faltan:
            continue

        nombre = e["nombre"]
        if not isinstance(nombre, str) or not RE_NOMBRE.match(nombre):
            err.append("nombre_invalido: %s: minusculas, digitos y _, con sufijo de unidad opcional" % quien)
        elif nombre in nombres:
            err.append("nombre_repetido: %s ya esta en etiquetas[%d]" % (quien, nombres[nombre]))
        else:
            nombres[nombre] = i

        tabla, tipo, d = e["tabla"], e["tipo"], e["direccion"]
        if tabla not in TABLAS:
            err.append("tabla_desconocida: %s: %r (validas: %s)" % (quien, tabla, ", ".join(TABLAS)))
            continue
        if tipo not in TIPOS:
            err.append("tipo_desconocido: %s: %r (validos: %s)" % (quien, tipo, ", ".join(TIPOS)))
            continue
        if TABLAS[tabla]["digital"] != (tipo == "bool"):
            err.append("tipo_incompatible: %s: %s en la tabla %s" % (quien, tipo, tabla))

        # ---- direccion: dentro del limite del driver y sin repetirse en su tabla
        if d is None:
            # Etiqueta vista en la escena cuya direccion aun no se conoce. Nunca
            # se inventa: el mapa se rechaza hasta tener la captura del driver.
            err.append("direccion_pendiente: %s: falta la direccion en %s; sale de la captura de la "
                       "ventana del driver de Factory I/O (PUERTA ARI R0)" % (quien, tabla))
        elif not _entero(d):
            err.append("direccion_invalida: %s: %r no es entero" % (quien, d))
        else:
            lim = limites.get(tabla)
            if d < 0 or (_entero(lim) and d >= lim):
                err.append("direccion_fuera_de_limite: %s: %s %d, el driver admite 0 a %s"
                           % (quien, tabla, d, (lim - 1) if _entero(lim) else "?"))
            clave = (tabla, d)
            if clave in ocupadas:
                err.append("direccion_repetida: %s: %s %d ya la usa %s"
                           % (quien, tabla, d, ocupadas[clave]))
            else:
                ocupadas[clave] = nombre

        if e["sentido"] not in SENTIDOS:
            err.append("sentido_invalido: %s: %r" % (quien, e["sentido"]))
        elif TABLAS[tabla]["solo_lectura"] and e["sentido"] != "lectura":
            err.append("sentido_incompatible: %s: la tabla %s es de solo lectura" % (quien, tabla))

        if not isinstance(e["descripcion"], str) or not e["descripcion"].strip():
            err.append("descripcion_vacia: %s" % quien)

        # ---- escala y rango
        escala, rango, unidad = e["escala"], e["rango_fisico"], e["unidad"]
        if tipo == "bool":
            if escala is not None or rango is not None or unidad is not None:
                err.append("bool_con_escala: %s: escala, unidad y rango_fisico van en null" % quien)
            continue
        if not isinstance(unidad, str) or not unidad:
            err.append("unidad_faltante: %s" % quien)
        if not _numero(escala) or escala <= 0:
            err.append("escala_invalida: %s: %r" % (quien, escala))
            continue
        if factor is not None and escala != factor and escala != 1:
            # Factory I/O aplica UN factor a todos los valores flotantes; una
            # etiqueta con otro factor leeria mal sin que nada lo avise. Los
            # enteros (como los contadores del tablero de Sorting by Weight)
            # viajan sin escalar: escala 1.
            err.append("escala_distinta_del_driver: %s: %s contra factor_escala %s"
                       % (quien, escala, factor))
        if (not isinstance(rango, list) or len(rango) != 2
                or not all(_numero(x) for x in rango) or rango[0] >= rango[1]):
            err.append("rango_invalido: %s: se esperaba [min, max] con min < max" % quien)
            continue
        lo, hi = TIPOS[tipo]
        crudo = [x * escala for x in rango]
        if any(abs(c - round(c)) > 1e-6 for c in crudo):
            err.append("rango_no_representable: %s: %s x %s no da enteros" % (quien, rango, escala))
        if crudo[0] < lo or crudo[1] > hi:
            err.append("escala_desborda_tipo: %s: %s x %s = [%g, %g] no cabe en %s [%d, %d]"
                       % (quien, rango, escala, crudo[0], crudo[1], tipo, lo, hi))
    return err


def carga(ruta=MAPA):
    """Lee y valida el mapa. Lanza MapaInvalido con todos los errores."""
    try:
        mapa = json.loads(pathlib.Path(ruta).read_text(encoding="utf-8"))
    except ValueError as e:
        raise MapaInvalido(["json_invalido: %s" % e])
    errores = valida(mapa)
    if errores:
        raise MapaInvalido(errores)
    return mapa


# ---- conversion fisico <-> registro ------------------------------------------
def a_registro(etiqueta, valor):
    """Valor fisico -> palabra de 16 bits sin signo, como viaja en el cable."""
    if etiqueta["tipo"] == "bool":
        return bool(valor)
    lo, hi = etiqueta["rango_fisico"]
    if not lo <= valor <= hi:
        raise ValueError("%s=%s fuera de %s" % (etiqueta["nombre"], valor, etiqueta["rango_fisico"]))
    n = int(round(valor * etiqueta["escala"]))
    return n & 0xFFFF            # int16 negativo -> complemento a dos


def de_registro(etiqueta, palabra):
    """Palabra de 16 bits -> valor fisico."""
    if etiqueta["tipo"] == "bool":
        return bool(palabra)
    n = palabra & 0xFFFF
    if etiqueta["tipo"] == "int16" and n >= 0x8000:
        n -= 0x10000
    return n / etiqueta["escala"]


# ---- documentacion -------------------------------------------------------------
MAPA_FIO = RAIZ / "config" / "mapa_registros_fio.json"
# Las dos versiones del mapa: la del sustituto de C2 y la de la escena real.
# A2_MAPA elige cual usa Node-RED; la documentacion lleva las dos.
VERSIONES = [("Sustituto (planta simulada de C2)", MAPA), ("Factory I/O, escena Sorting by Weight", MAPA_FIO)]


def _tablas(mapa, nivel):
    L = []
    for t, info in TABLAS.items():
        filas = sorted((e for e in mapa["etiquetas"] if e["tabla"] == t),
                       key=lambda e: (e["direccion"] is None, e["direccion"] or 0, e["nombre"]))
        if not filas:
            continue
        L += ["", "%s %s" % ("#" * nivel, info["titulo"]), "",
              "| Dirección | Etiqueta | Sentido | Tipo | Rango físico | Rango en el registro | Descripción |",
              "|---|---|---|---|---|---|---|"]
        for e in filas:
            if e["tipo"] == "bool":
                fis, reg = "", "0 / 1"
            else:
                lo, hi = e["rango_fisico"]
                fis = "%g a %g %s" % (lo, hi, e["unidad"])
                reg = "%d a %d (× %g)" % (round(lo * e["escala"]), round(hi * e["escala"]), e["escala"])
                if e["tipo"] == "int16" and lo < 0:
                    reg += ", negativos en complemento a dos"
            dire = "**pendiente**" if e["direccion"] is None else "%d" % e["direccion"]
            L.append("| %s | `%s` | %s | %s | %s | %s | %s |"
                     % (dire, e["nombre"], e["sentido"], e["tipo"], fis, reg, e["descripcion"]))
    return L


def genera_md(mapa, origen="config/mapa_registros_a2.json", nivel=2, errores=None):
    """Una version del mapa. Con `errores`, el mapa no paso el validador y se
    documenta tal cual, con lo que falta."""
    drv = mapa["driver"]
    L = ["`%s`. Estado: %s." % (origen, mapa.get("estado", "sin estado declarado")), ""]
    if errores:
        L += ["> **El validador lo rechaza** (%d errores; el primero: `%s`). Node-RED no puede usarlo"
              " hasta resolverlo." % (len(errores), errores[0].split(":", 1)[0]), ""]
    L += ["Driver: %s. Factor de escala %s: un valor flotante viaja multiplicado por %s."
          % (drv["nombre"], drv["factor_escala"], drv["factor_escala"]),
          "Las direcciones son las del protocolo, contadas desde 0, igual que en Factory I/O.", "",
          "| Tabla | Límite del driver |", "|---|---|"]
    for t, info in TABLAS.items():
        L.append("| %s | %d (0 a %d) |" % (info["titulo"], drv["limites"][t], drv["limites"][t] - 1))
    L += _tablas(mapa, nivel + 1)
    return "\n".join(L) + "\n"


def genera_doc():
    L = ["# Mapa de registros Modbus — Actividad 2", "",
         "> **Generado** con `python3 tools/mapa_registros.py doc` desde los dos JSON de `config/`.",
         "> No se edita a mano: se cambia el JSON y se regenera. `A2_MAPA` elige cuál usa Node-RED.", ""]
    for n, (titulo, ruta) in enumerate(VERSIONES, 1):
        if not ruta.exists():
            continue
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
        errores = valida(crudo)
        L += ["## %d. %s" % (n, titulo), "", genera_md(crudo, str(ruta.relative_to(RAIZ)), 2, errores)]
    return "\n".join(L).rstrip("\n") + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("accion", choices=["valida", "doc"])
    p.add_argument("--mapa", default=str(MAPA))
    p.add_argument("--salida", default=str(DOC))
    p.add_argument("--revisa", action="store_true", help="con doc: no escribe, falla si esta desfasada")
    a = p.parse_args(argv)
    if a.accion == "doc":
        mapa = {"etiquetas": []}
        origen = "config/"
    else:
        try:
            mapa = carga(a.mapa)
        except (MapaInvalido, OSError) as e:
            print(e, file=sys.stderr)
            return 1
    if a.accion == "valida":
        print("mapa valido: %d etiquetas en %s" % (len(mapa["etiquetas"]), a.mapa))
        return 0
    texto = genera_doc()
    destino = pathlib.Path(a.salida)
    if a.revisa:
        actual = destino.read_text(encoding="utf-8") if destino.exists() else ""
        if actual != texto:
            print("%s esta desfasado respecto de %s; corre: python3 tools/mapa_registros.py doc"
                  % (destino, origen), file=sys.stderr)
            return 1
        print("%s al dia" % destino)
        return 0
    destino.write_text(texto, encoding="utf-8")
    print("escrito %s (%d versiones del mapa)" % (destino, sum(1 for _, r in VERSIONES if r.exists())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
