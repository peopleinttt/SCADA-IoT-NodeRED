#!/usr/bin/env python3
"""Calcula latencia y frecuencia efectiva de muestreo de una corrida.

Entrada: cualquier CSV con separador ';' que tenga al menos las columnas
ts_origen y ts_escritura. Sirve tanto el que escribe Node-RED en vivo
(datos/ingesta_AAAA-MM-DD.csv) como el que baja exporta_corrida.py.

    python3 analiza_corrida.py ../datos/ingesta_2026-08-24.csv
    python3 analiza_corrida.py corrida.csv --periodo-nominal 5 --md reporte.md
    python3 analiza_corrida.py --a2 proceso.csv --sondeo a2_sondeo_DIA.csv --eventos a2_planta_eventos.jsonl
        (Actividad 2: las tres cifras de docs/INSTRUMENTACION_A2.md)

Reporta, con su definicion explicita:
  * latencia de extremo a extremo  = ts_escritura - ts_origen
  * latencia corregida por sesgo   = latencia - min(latencia)
  * periodo efectivo               = diferencia entre ts_origen consecutivos
  * frecuencia efectiva            = 1 / periodo efectivo medio
  * completitud                    = recibidas / esperadas en la ventana
Solo biblioteca estandar.
"""
import argparse, csv, math, pathlib, statistics as est, sys
from datetime import datetime, timezone


def iso_a_dt(s):
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def percentil(datos, p):
    """Percentil por interpolacion lineal; con n pequeno evita el salto brusco
    de tomar el elemento de indice redondeado."""
    if not datos:
        return float("nan")
    d = sorted(datos)
    if len(d) == 1:
        return float(d[0])
    k = (len(d) - 1) * p / 100.0
    i = math.floor(k)
    j = min(i + 1, len(d) - 1)
    return d[i] + (d[j] - d[i]) * (k - i)


def resumen(valores, unidad, decimales=1):
    if not valores:
        return {"n": 0}
    return {
        "n": len(valores),
        "min": round(min(valores), decimales),
        "p50": round(percentil(valores, 50), decimales),
        "p90": round(percentil(valores, 90), decimales),
        "p95": round(percentil(valores, 95), decimales),
        "max": round(max(valores), decimales),
        "media": round(est.fmean(valores), decimales),
        "sd": round(est.stdev(valores), decimales) if len(valores) > 1 else 0.0,
        "unidad": unidad,
    }


def tabla(titulo, r):
    if not r.get("n"):
        return f"\n{titulo}: sin datos\n"
    return (f"\n{titulo}  (n = {r['n']}, unidad = {r['unidad']})\n"
            f"  min {r['min']}   p50 {r['p50']}   p90 {r['p90']}   "
            f"p95 {r['p95']}   max {r['max']}\n"
            f"  media {r['media']} ± {r['sd']} (desviacion estandar muestral)\n")


def analiza_a2(args):
    """Las tres cifras de la Actividad 2, con las definiciones fijadas antes de
    medir en docs/INSTRUMENTACION_A2.md. Todo sale de los CSV, nada del estado
    en vivo de Node-RED."""
    import json
    desde = iso_a_dt(args.desde) if args.desde else None
    hasta = iso_a_dt(args.hasta) if args.hasta else None
    dentro = lambda t: t is not None and (not desde or t >= desde) and (not hasta or t <= hasta)

    # 1. Periodo efectivo del sondeo: inicios consecutivos con comunicacion ok.
    inicios = []
    if args.sondeo:
        with args.sondeo.open(encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f, delimiter=";"):
                if fila.get("ciclo") == "ciclo" or fila.get("com") != "ok":
                    continue
                t = iso_a_dt(fila["ts_inicio"])
                if dentro(t):
                    inicios.append((int(fila["ciclo"]), int(fila["t_inicio_ms"])))
    inicios.sort()
    periodos = [b[1] - a[1] for a, b in zip(inicios, inicios[1:]) if b[0] == a[0] + 1]
    r_per = resumen(periodos, "ms", 1)

    # 2. Latencia de la lectura a la escritura en Firebase, registros de caja.
    cajas, latidos = [], 0
    with args.a2.open(encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            t_o, t_e = iso_a_dt(fila.get("ts_origen")), iso_a_dt(fila.get("ts_escritura"))
            if not dentro(t_o):
                continue
            if fila.get("tipo") == "caja":
                cajas.append((t_e - t_o).total_seconds() * 1000)
            else:
                latidos += 1
    r_lat = resumen(cajas, "ms", 1)

    # 3. Completitud: registros de caja en Firebase / cajas que salieron segun A2-Planta.
    pasos = 0
    if args.eventos:
        for l in args.eventos.read_text(encoding="utf-8").splitlines():
            e = json.loads(l) if l.strip() else {}
            if e.get("ev") == "paso_caja" and dentro(iso_a_dt(e.get("ts_salida"))):
                pasos += 1
    reales = None
    if args.sustituto:
        reales = sum(1 for l in args.sustituto.read_text(encoding="utf-8").splitlines()
                     if l.strip() and json.loads(l).get("ev") in ("caja_sale", "caja_rechazada"))
    print("Actividad 2 — %s" % args.a2)
    print(tabla("  1. periodo efectivo del sondeo (inicios consecutivos con com ok)", r_per).rstrip())
    if r_per.get("n"):
        print("     variacion: sd %.1f ms, p95 - p50 = %.1f ms" % (r_per["sd"], r_per["p95"] - r_per["p50"]))
    print(tabla("  2. latencia lectura Modbus -> escritura en Firebase (registros de caja)", r_lat).rstrip())
    comp = len(cajas) / pasos if pasos else float("nan")
    print("  3. completitud: %d registros de caja en Firebase / %d cajas que salieron segun A2-Planta = %.2f %%"
          % (len(cajas), pasos, 100 * comp))
    if reales is not None:
        print("     contra la planta: %d cajas salieron de la linea (sustituto) -> %.2f %%"
              % (reales, 100 * len(cajas) / reales if reales else float("nan")))
    print("  latidos en la ventana: %d" % latidos)
    if args.md:
        L = ["| Cifra | Definicion | n | Mediana | p95 | Max | Media ± sd |", "|---|---|---|---|---|---|---|"]
        if r_per.get("n"):
            L.append("| Periodo efectivo del sondeo | inicio_i − inicio_(i−1), com ok | %d | %s ms | %s ms | %s ms | %s ± %s ms |"
                     % (r_per["n"], r_per["p50"], r_per["p95"], r_per["max"], r_per["media"], r_per["sd"]))
        if r_lat.get("n"):
            L.append("| Latencia lectura → Firebase | ts_escritura − ts_origen, cajas | %d | %s ms | %s ms | %s ms | %s ± %s ms |"
                     % (r_lat["n"], r_lat["p50"], r_lat["p95"], r_lat["max"], r_lat["media"], r_lat["sd"]))
        L.append("| Completitud | cajas en Firebase / paso_caja | %d / %d | %.2f %% | | | |" % (len(cajas), pasos, 100 * comp))
        args.md.write_text("\n".join(L) + "\n", encoding="utf-8")
        print("  tabla en %s" % args.md)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=pathlib.Path, nargs="?")
    ap.add_argument("--a2", type=pathlib.Path, help="CSV de la rama proceso (exporta_corrida.py --rama proceso)")
    ap.add_argument("--sondeo", type=pathlib.Path, help="con --a2: $DATOS_DIR/a2_sondeo_DIA.csv de A2-Planta")
    ap.add_argument("--eventos", type=pathlib.Path, help="con --a2: $DATOS_DIR/a2_planta_eventos.jsonl de A2-Planta")
    ap.add_argument("--sustituto", type=pathlib.Path, help="con --a2: eventos del sustituto, para la completitud contra la planta real")
    ap.add_argument("--desde", help="con --a2: ventana, ISO-8601")
    ap.add_argument("--hasta", help="con --a2: ventana, ISO-8601")
    ap.add_argument("--periodo-nominal", type=float, default=5.0,
                    help="periodo programado en el emisor, en segundos (por omision 5)")
    ap.add_argument("--md", type=pathlib.Path, help="ademas escribe el reporte en Markdown")
    args = ap.parse_args()
    if args.a2:
        return analiza_a2(args)
    if not args.csv:
        sys.exit("falta el CSV (o --a2 para la Actividad 2)")

    if not args.csv.exists():
        sys.exit(f"no existe {args.csv}")

    filas, malas = [], 0
    with args.csv.open(encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            # El CSV en vivo puede traer el encabezado repetido si se
            # redesplego el flujo a media corrida: se ignora esa linea.
            if (fila.get("ts_origen") or "").strip() == "ts_origen":
                continue
            t_o, t_e = iso_a_dt(fila.get("ts_origen")), iso_a_dt(fila.get("ts_escritura"))
            if t_o is None:
                malas += 1
                continue
            filas.append({"t_o": t_o, "t_e": t_e, "cruda": fila})

    if len(filas) < 2:
        sys.exit(f"hacen falta al menos 2 muestras utilizables; se leyeron {len(filas)}")

    filas.sort(key=lambda x: x["t_o"])

    # --- latencia ---------------------------------------------------------
    lat = [(f["t_e"] - f["t_o"]).total_seconds() * 1000 for f in filas if f["t_e"]]
    negativas = [x for x in lat if x < 0]
    r_lat = resumen(lat, "ms")
    sesgo = min(lat) if lat else 0.0
    r_lat_corr = resumen([x - sesgo for x in lat], "ms")

    # --- periodo efectivo -------------------------------------------------
    difs = [(filas[i]["t_o"] - filas[i - 1]["t_o"]).total_seconds()
            for i in range(1, len(filas))]
    r_per = resumen(difs, "s", 3)
    nominal = args.periodo_nominal
    huecos = [(i, d) for i, d in enumerate(difs, start=1) if d > 1.5 * nominal]
    perdidas_estimadas = sum(int(round(d / nominal)) - 1 for _, d in huecos)

    ventana = (filas[-1]["t_o"] - filas[0]["t_o"]).total_seconds()
    esperadas = int(round(ventana / nominal)) + 1 if nominal > 0 else len(filas)
    completitud = 100.0 * len(filas) / esperadas if esperadas else float("nan")
    frec_efectiva = 1.0 / r_per["media"] if r_per.get("media") else float("nan")

    # --- reporte ----------------------------------------------------------
    L = []
    L.append("=" * 72)
    L.append(f"CORRIDA: {args.csv.name}")
    L.append("=" * 72)
    L.append(f"Muestras utilizables .... {len(filas)}"
             + (f"   (descartadas por ts_origen ilegible: {malas})" if malas else ""))
    L.append(f"Inicio (ts_origen) ...... {filas[0]['t_o'].isoformat()}")
    L.append(f"Fin (ts_origen) ......... {filas[-1]['t_o'].isoformat()}")
    L.append(f"Ventana ................. {ventana:.1f} s ({ventana/60:.2f} min)")
    L.append("")
    L.append("LATENCIA DE EXTREMO A EXTREMO   (definicion: ts_escritura - ts_origen;")
    L.append("incluye el viaje ESP32 -> Node-RED, la validacion, y ademas el sesgo")
    L.append("entre el reloj NTP del ESP32 y el reloj del equipo con Node-RED.)")
    L.append(tabla("  latencia cruda", r_lat).rstrip())
    L.append(f"\n  sesgo de reloj estimado (minimo observado): {sesgo:.1f} ms")
    L.append("  Si los dos relojes estuvieran perfectamente alineados, el minimo")
    L.append("  seria el tiempo de transporte mas corto posible, no cero. Restarlo")
    L.append("  da la cota inferior de la latencia atribuible solo a la red:")
    L.append(tabla("  latencia corregida por sesgo", r_lat_corr).rstrip())
    if negativas:
        L.append(f"\n  AVISO: {len(negativas)} latencias negativas (min {min(negativas):.1f} ms).")
        L.append("  Eso solo puede venir de relojes desalineados: el ESP32 marco una hora")
        L.append("  posterior a la del equipo receptor. Sincroniza ambos por NTP antes de")
        L.append("  reportar numeros de latencia.")
    L.append("")
    L.append(f"FRECUENCIA EFECTIVA DE MUESTREO   (periodo nominal programado: {nominal} s)")
    L.append(tabla("  periodo entre ts_origen consecutivos", r_per).rstrip())
    L.append(f"\n  frecuencia efectiva ..... {frec_efectiva:.4f} Hz "
             f"(1 / {r_per['media']} s)")
    L.append(f"  desviacion del nominal .. {100*(r_per['media']-nominal)/nominal:+.2f} %")
    L.append(f"  jitter (sd del periodo) . {r_per['sd']} s")
    L.append("")
    L.append("COMPLETITUD")
    L.append(f"  esperadas en la ventana . {esperadas}")
    L.append(f"  recibidas ............... {len(filas)}")
    L.append(f"  completitud ............. {completitud:.2f} %")
    L.append(f"  huecos > 1.5x nominal ... {len(huecos)}")
    L.append(f"  muestras perdidas (est.). {perdidas_estimadas}")
    if huecos:
        L.append("  los cinco huecos mayores:")
        for i, d in sorted(huecos, key=lambda x: -x[1])[:5]:
            L.append(f"    {filas[i]['t_o'].isoformat()}  ->  {d:.1f} s")
    L.append("")
    L.append("Definiciones para la seccion 5 del reporte:")
    L.append("  latencia_i     = ts_escritura_i - ts_origen_i")
    L.append("  periodo_i      = ts_origen_i - ts_origen_(i-1)")
    L.append("  f_efectiva     = 1 / media(periodo_i)")
    L.append("  completitud    = muestras_recibidas / (ventana / periodo_nominal + 1)")
    L.append("=" * 72)

    texto = "\n".join(L)
    print(texto)

    if args.md:
        md = ["# Instrumentacion de la corrida", "",
              f"Archivo analizado: `{args.csv.name}`", "",
              "| Metrica | Valor |", "|---|---|",
              f"| Muestras utilizables | {len(filas)} |",
              f"| Ventana | {ventana:.1f} s |",
              f"| Latencia mediana | {r_lat.get('p50','-')} ms |",
              f"| Latencia p95 | {r_lat.get('p95','-')} ms |",
              f"| Latencia media ± sd | {r_lat.get('media','-')} ± {r_lat.get('sd','-')} ms |",
              f"| Sesgo de reloj estimado | {sesgo:.1f} ms |",
              f"| Periodo efectivo medio | {r_per.get('media','-')} s |",
              f"| Jitter (sd) | {r_per.get('sd','-')} s |",
              f"| Frecuencia efectiva | {frec_efectiva:.4f} Hz |",
              f"| Completitud | {completitud:.2f} % |",
              f"| Muestras perdidas (est.) | {perdidas_estimadas} |", "",
              "```", texto, "```", ""]
        args.md.write_text("\n".join(md), encoding="utf-8")
        print(f"\nReporte en Markdown: {args.md}")


if __name__ == "__main__":
    main()
