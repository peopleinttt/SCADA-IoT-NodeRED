#!/usr/bin/env python3
"""Exporta una corrida completa de Firebase a un archivo delimitado.

Descarga /plantas/{plantaId}/telemetria (y opcionalmente diagnosticos) por REST
y escribe un CSV con separador ';' listo para la seccion 5 del reporte.

Uso:
    python3 exporta_corrida.py                       # todo, a ../datos/
    python3 exporta_corrida.py --desde 2026-08-24T18:00:00Z
    python3 exporta_corrida.py --ultimas 500 --salida corrida.csv
    python3 exporta_corrida.py --rama proceso --desde 2026-10-25T00:00:00Z   # Actividad 2

Credenciales: se leen de ../.env (FIREBASE_DB_URL, PLANTA_ID y, para autenticar,
FIREBASE_API_KEY + FB_VISOR_EMAIL/FB_VISOR_PASS, o bien FIREBASE_AUTH).
Solo usa la biblioteca estandar.
"""
import argparse, csv, json, os, pathlib, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone

def contexto_ssl():
    """CA para HTTPS. El Python del instalador de python.org en macOS no trae
    rutas de certificados configuradas (ssl.get_default_verify_paths().cafile
    da None), asi que toda llamada HTTPS falla con CERTIFICATE_VERIFY_FAILED.
    Se usa el paquete certifi si esta; si no, se explica el arreglo en vez de
    reventar con una traza ilegible."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    if ssl.get_default_verify_paths().cafile:
        return ssl.create_default_context()
    raise SystemExit(
        "Python no encuentra los certificados raiz y no puede hablar por HTTPS.\n"
        "Arreglo, cualquiera de los dos:\n"
        "  pip3 install certifi\n"
        '  open "/Applications/Python 3.10/Install Certificates.command"')


RAIZ = pathlib.Path(__file__).resolve().parent.parent
COLUMNAS = ["registro_id", "ts_origen", "ts_escritura", "latencia_ms",
            "temperatura_C", "vibracion_mm_s", "ciclos_acumulados"]


def carga_env():
    """Lee ../.env sin dependencias externas. Las variables reales del entorno
    ganan sobre el archivo, para poder sobrescribir sin editarlo."""
    valores = {}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            valores[k.strip()] = v.strip().strip('"').strip("'")
    valores.update({k: v for k, v in os.environ.items() if k in valores or k.startswith(("FIREBASE", "FB_", "PLANTA", "DATOS"))})
    return valores


def pide(url, datos=None, cabeceras=None, tiempo=30):
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    pet = urllib.request.Request(url, data=cuerpo, method="POST" if cuerpo else "GET",
                                 headers=cabeceras or ({"Content-Type": "application/json"} if cuerpo else {}))
    try:
        with urllib.request.urlopen(pet, timeout=tiempo, context=contexto_ssl()) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        detalle = e.read().decode()
        try:
            detalle = json.loads(detalle)
        except Exception:
            pass
        return e.code, detalle
    except urllib.error.URLError as e:
        return 0, str(e.reason)


def token(env):
    """idToken del visor. Si no hay cuenta configurada, cae a FIREBASE_AUTH."""
    api = env.get("FIREBASE_API_KEY")
    correo, clave = env.get("FB_VISOR_EMAIL"), env.get("FB_VISOR_PASS")
    if api and correo and clave:
        codigo, r = pide(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api}",
            {"email": correo, "password": clave, "returnSecureToken": True})
        if codigo == 200 and isinstance(r, dict) and r.get("idToken"):
            return r["idToken"]
        print(f"  aviso: no se pudo entrar como visor (HTTP {codigo}): "
              f"{json.dumps(r)[:200]}", file=sys.stderr)
    return env.get("FIREBASE_AUTH") or ""


def iso_a_dt(s):
    """Convierte ISO-8601 a datetime con zona. Python 3.10 no acepta la 'Z',
    hay que traducirla; a partir de 3.11 sobra, pero no estorba."""
    if not isinstance(s, str):
        return None
    t = s.strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def descarga(env, rama, ultimas=None):
    base = (env.get("FIREBASE_DB_URL") or "").rstrip("/")
    planta = env.get("PLANTA_ID") or "planta_01"
    if not base:
        sys.exit("falta FIREBASE_DB_URL (en ../.env o en el entorno)")
    consulta = {}
    if ultimas:
        consulta = {"orderBy": '"$key"', "limitToLast": str(ultimas)}
    tok = token(env)
    if tok:
        consulta["auth"] = tok
    url = f"{base}/plantas/{urllib.parse.quote(planta)}/{rama}.json"
    if consulta:
        url += "?" + urllib.parse.urlencode(consulta)
    codigo, cuerpo = pide(url)
    if codigo == 401:
        sys.exit("Firebase respondio 401: las reglas no permiten leer esa rama con "
                 "esa credencial. Revisa el UID del visor en database.rules.json.")
    if codigo != 200:
        sys.exit(f"Firebase respondio {codigo}: {json.dumps(cuerpo)[:300]}")
    return cuerpo or {}


COLUMNAS_PROCESO = ["registro_id", "tipo", "ts_origen", "ts_escritura", "latencia_ms", "vel_banda_V",
                    "peso_V", "caja_masa_kg", "destino", "cajas_acumuladas", "estado_linea"]


def exporta_proceso(env, args):
    """Rama /plantas/{plantaId}/proceso (Actividad 2). tipo = caja si trae
    caja_masa_kg, latido si no: es como los distingue A2-Nube."""
    print(f"Descargando proceso de {env.get('FIREBASE_DB_URL')} planta {env.get('PLANTA_ID', 'planta_01')} …")
    datos = descarga(env, "proceso", args.ultimas)
    desde, hasta = iso_a_dt(args.desde) if args.desde else None, iso_a_dt(args.hasta) if args.hasta else None
    filas = []
    for rid in sorted(datos):
        r = datos[rid] or {}
        t_o, t_e = iso_a_dt(r.get("ts_origen")), iso_a_dt(r.get("ts_escritura"))
        if t_o is None or (desde and t_o < desde) or (hasta and t_o > hasta):
            continue
        filas.append({"registro_id": rid, "tipo": "caja" if "caja_masa_kg" in r else "latido",
                      "ts_origen": r.get("ts_origen", ""), "ts_escritura": r.get("ts_escritura", ""),
                      "latencia_ms": round((t_e - t_o).total_seconds() * 1000) if t_e else "",
                      **{c: r.get(c, "") for c in COLUMNAS_PROCESO[5:]}})
    if not filas:
        sys.exit("no hay registros de proceso con esos filtros")
    salida = pathlib.Path(args.salida) if args.salida else \
        pathlib.Path(env.get("DATOS_DIR") or (RAIZ / "datos")) / f"proceso_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_PROCESO, delimiter=";")
        w.writeheader()
        w.writerows(filas)
    print(f"  {len(filas)} registros ({sum(1 for x in filas if x['tipo'] == 'caja')} de caja) -> {salida}")
    print(f"\nSiguiente paso:\n  python3 {pathlib.Path(__file__).parent}/analiza_corrida.py --a2 {salida} "
          f"--sondeo $DATOS_DIR/a2_sondeo_DIA.csv --eventos $DATOS_DIR/a2_planta_eventos.jsonl")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ultimas", type=int, help="solo los ultimos N registros")
    ap.add_argument("--desde", help="descarta ts_origen anteriores a esta marca ISO-8601")
    ap.add_argument("--hasta", help="descarta ts_origen posteriores a esta marca ISO-8601")
    ap.add_argument("--salida", help="archivo CSV de salida")
    ap.add_argument("--diagnosticos", action="store_true", help="exporta tambien los diagnosticos")
    ap.add_argument("--rama", choices=["telemetria", "proceso"], default="telemetria",
                    help="proceso = registros de la Actividad 2 (una caja o un latido por fila)")
    args = ap.parse_args()

    env = carga_env()
    if args.rama == "proceso":
        return exporta_proceso(env, args)
    print(f"Descargando telemetria de {env.get('FIREBASE_DB_URL')} "
          f"planta {env.get('PLANTA_ID', 'planta_01')} …")
    datos = descarga(env, "telemetria", args.ultimas)

    desde, hasta = iso_a_dt(args.desde) if args.desde else None, iso_a_dt(args.hasta) if args.hasta else None
    filas, descartadas = [], 0
    for rid in sorted(datos):
        r = datos[rid] or {}
        t_o, t_e = iso_a_dt(r.get("ts_origen")), iso_a_dt(r.get("ts_escritura"))
        if t_o is None:
            descartadas += 1
            continue
        if desde and t_o < desde:
            continue
        if hasta and t_o > hasta:
            continue
        filas.append({
            "registro_id": rid,
            "ts_origen": r.get("ts_origen", ""),
            "ts_escritura": r.get("ts_escritura", ""),
            "latencia_ms": round((t_e - t_o).total_seconds() * 1000) if t_e else "",
            "temperatura_C": r.get("temperatura_C", ""),
            "vibracion_mm_s": r.get("vibracion_mm_s", ""),
            "ciclos_acumulados": r.get("ciclos_acumulados", ""),
        })

    if not filas:
        sys.exit("no hay registros que exportar con esos filtros")

    salida = pathlib.Path(args.salida) if args.salida else \
        pathlib.Path(env.get("DATOS_DIR") or (RAIZ / "datos")) / \
        f"corrida_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, delimiter=";")
        w.writeheader()
        w.writerows(filas)

    print(f"  {len(filas)} registros -> {salida}")
    if descartadas:
        print(f"  {descartadas} registros sin ts_origen utilizable quedaron fuera")

    if args.diagnosticos:
        diag = descarga(env, "diagnosticos", args.ultimas)
        # Nombre derivado por sufijo, nunca por sustitucion de texto: con
        # --salida arbitraria una sustitucion no aplica y los diagnosticos
        # terminan sobrescribiendo el archivo de telemetria.
        sd = salida.with_name(salida.stem + "_diagnosticos.csv")
        if sd.resolve() == salida.resolve():
            sys.exit("el archivo de diagnosticos coincidiria con el de telemetria")
        cols = ["diagnostico_id", "ts", "modelo", "latencia_ms", "accion_prescrita",
                "texto_diagnostico", "resumen_entrada"]
        with sd.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
            w.writeheader()
            for did in sorted(diag or {}):
                r = diag[did] or {}
                w.writerow({"diagnostico_id": did, **{c: r.get(c, "") for c in cols[1:]}})
        print(f"  {len(diag or {})} diagnosticos -> {sd}")

    print(f"\nSiguiente paso:\n  python3 {pathlib.Path(__file__).parent}/analiza_corrida.py {salida}")


if __name__ == "__main__":
    main()
