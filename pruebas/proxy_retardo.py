#!/usr/bin/env python3
"""Proxy TCP que agrega un retardo fijo de ida y vuelta. Python 3.9.

Simula la distancia a la maquina de Azure sin tocar el sustituto: el cliente
se conecta al proxy y el proxy al servidor real. --rtt-ms se reparte mitad y
mitad: cada trozo de datos se entrega rtt/2 ms despues de recibirlo, en cada
sentido, y en orden.

    python3 pruebas/proxy_retardo.py --escucha 5030 --destino 127.0.0.1:5020 --rtt-ms 200

Tambien se importa desde las pruebas: Proxy(5030, ("127.0.0.1", 5020), 200).inicia()
"""
import argparse, collections, socket, threading, time


class Proxy:
    def __init__(self, puerto, destino, rtt_ms, host="127.0.0.1"):
        self.host, self.puerto, self.destino = host, puerto, destino
        self.medio_s = rtt_ms / 2000.0
        self._srv = None
        self._vivo = threading.Event()
        self._abiertos = set()          # sockets vivos, para poder cortarlos de golpe
        self._candado = threading.Lock()
        # Lo que el cliente mando, tal cual paso por el cable: [(time.time(), bytes)].
        # Es el oraculo del ORDEN de las escrituras, que la planta no puede dar.
        self.del_cliente = []

    def inicia(self):
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((self.host, self.puerto))
        self._srv.listen(8)
        self._vivo.set()
        threading.Thread(target=self._acepta, args=(self._srv,), daemon=True).start()
        return self

    def detiene(self):
        """Deja de aceptar Y corta las conexiones abiertas: una desconexion de verdad.
        Se puede volver a llamar inicia() despues."""
        self._vivo.clear()
        if self._srv:
            self._srv.close()
            self._srv = None
        with self._candado:
            abiertos, self._abiertos = list(self._abiertos), set()
        for s in abiertos:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            s.close()

    def _acepta(self, escucha):
        while self._vivo.is_set():
            try:
                cli, _ = escucha.accept()
            except OSError:
                return
            try:
                srv = socket.create_connection(self.destino, timeout=5)
            except OSError:
                cli.close()
                continue
            for s in (cli, srv):
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.settimeout(None)
            with self._candado:
                self._abiertos.update((cli, srv))
            self._tubo(cli, srv, self.del_cliente)
            self._tubo(srv, cli, None)

    def _tubo(self, origen, destino, registro):
        """Un lector que sella la hora de llegada y un escritor que entrega a la hora + rtt/2."""
        cola, hay = collections.deque(), threading.Condition()

        def lee():
            while True:
                try:
                    datos = origen.recv(65536)
                except OSError:
                    datos = b""
                if registro is not None and datos:
                    registro.append((time.time(), datos))
                with hay:
                    cola.append((time.monotonic() + self.medio_s, datos))
                    hay.notify()
                if not datos:
                    return

        def escribe():
            while True:
                with hay:
                    while not cola:
                        hay.wait()
                    vence, datos = cola.popleft()
                espera = vence - time.monotonic()
                if espera > 0:
                    time.sleep(espera)
                if not datos:                      # el otro lado cerro
                    for s in (origen, destino):
                        try:
                            s.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                    return
                try:
                    destino.sendall(datos)
                except OSError:
                    return

        threading.Thread(target=lee, daemon=True).start()
        threading.Thread(target=escribe, daemon=True).start()


def escrituras(registro, desde=0.0):
    """Escrituras FC 05 y FC 06 que el cliente mando despues de `desde`, en orden:
    [(t, funcion, direccion, valor)]. Se rearma el flujo TCP y se corta en tramas MBAP."""
    flujo = b"".join(d for t, d in registro if t >= desde)
    tiempos = [t for t, d in registro if t >= desde for _ in d]
    salida, i = [], 0
    while i + 7 <= len(flujo):
        largo = int.from_bytes(flujo[i + 4:i + 6], "big")
        trama = flujo[i + 7:i + 6 + largo]
        if len(trama) < largo - 1:
            break
        if trama and trama[0] in (5, 6):
            salida.append((tiempos[i], trama[0], int.from_bytes(trama[1:3], "big"), int.from_bytes(trama[3:5], "big")))
        i += 6 + largo
    return salida


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--escucha", type=int, required=True)
    p.add_argument("--destino", required=True, help="host:puerto")
    p.add_argument("--rtt-ms", type=float, required=True)
    a = p.parse_args()
    h, pt = a.destino.rsplit(":", 1)
    Proxy(a.escucha, (h, int(pt)), a.rtt_ms).inicia()
    print("proxy 127.0.0.1:%d -> %s con %g ms de ida y vuelta (Ctrl+C para salir)" % (a.escucha, a.destino, a.rtt_ms))
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
