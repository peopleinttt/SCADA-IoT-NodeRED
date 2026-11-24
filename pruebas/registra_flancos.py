#!/usr/bin/env python3
"""Registrador de flancos de la linea (paso G de la fase 4). Python 3.9. Solo lee.

    /usr/bin/python3 -u pruebas/registra_flancos.py --salida DIR [--host 10.211.55.3] [--puerto 502]

Proceso separado del cliente, con su propia conexion Modbus. Lee cada ~10 ms
las entradas discretas 0 a 8 (los nueve sensores de la linea) y las bobinas
entry_conveyor y load_scale, y anota cada cambio con la hora UTC de la Mac en
DIR/flancos.jsonl. Termina con Ctrl-C, SIGTERM o al crearse DIR/detener.
"""
import argparse, json, pathlib, signal, sys, time
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from modbus_tcp import Cliente  # noqa: E402

E = {e["nombre"]: e for e in json.load(open(str(RAIZ / "config" / "mapa_registros_fio.json")))["etiquetas"]}
SENSORES = [n for n, e in sorted(E.items(), key=lambda kv: kv[1]["direccion"])
            if e["tabla"] == "entrada_discreta" and e["direccion"] <= 8]
BOBINAS = ["entry_conveyor", "load_scale"]


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--salida", required=True)
    a.add_argument("--host", default="10.211.55.3")
    a.add_argument("--puerto", type=int, default=502)
    x = a.parse_args()
    d = pathlib.Path(x.salida)
    d.mkdir(parents=True, exist_ok=True)
    f = open(str(d / "flancos.jsonl"), "a", encoding="utf-8")
    vivo = [True]
    signal.signal(signal.SIGTERM, lambda *_: vivo.__setitem__(0, False))
    c = Cliente(x.host, x.puerto, unidad=1)
    c.conecta()
    previo, lecturas = None, 0
    b0 = min(E[b]["direccion"] for b in BOBINAS)
    try:
        while vivo[0] and not (d / "detener").exists():
            try:
                di = c.lee_discretas(0, 9)
                co = c.lee_bobinas(b0, max(E[b]["direccion"] for b in BOBINAS) - b0 + 1)
            except Exception as e:
                f.write(json.dumps({"ts": iso(time.time()), "error": str(e)}) + "\n")
                time.sleep(0.2)
                try:
                    c.cierra()
                    c.conecta()
                except Exception:
                    pass
                continue
            t = time.time()
            lecturas += 1
            actual = {n: int(di[E[n]["direccion"]]) for n in SENSORES}
            actual.update({b: int(co[E[b]["direccion"] - b0]) for b in BOBINAS})
            if previo is None:
                f.write(json.dumps({"ts": iso(t), "t": t, "inicial": actual}) + "\n")
            else:
                for n, v in actual.items():
                    if v != previo[n]:
                        f.write(json.dumps({"ts": iso(t), "t": t, "senal": n, "valor": v}) + "\n")
            previo = actual
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        f.write(json.dumps({"ts": iso(time.time()), "fin": True, "lecturas": lecturas}) + "\n")
        f.close()
        c.cierra()


if __name__ == "__main__":
    main()
