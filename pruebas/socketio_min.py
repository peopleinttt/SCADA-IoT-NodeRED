#!/usr/bin/env python3
"""Cliente minimo de socket.io v4 por long-polling (Engine.IO 4). Python 3.9, sin dependencias.

Lo justo para que las pruebas de la HMI hablen con Dashboard 2.0 por el mismo
camino que el navegador: conectar, emitir `widget-action` (lo que hace un
boton de la plantilla al llamar a send()) y recibir `msg-input:<id>` (lo que
el servidor manda a la pagina).

    s = SocketIO("127.0.0.1", 1881, "/dashboard/socket.io/")
    s.conecta()
    s.emite("widget-action", "ui_tpl_a2", {"topic": "comando", "payload": {"accion": "marcha"}})
    for evento, args in s.recibe(5): ...
"""
import http.client, json, time

SEP = "\x1e"     # separador de paquetes en el polling de Engine.IO 4


class SocketIO:
    def __init__(self, host, puerto, ruta, cabeceras=None):
        self.host, self.puerto, self.ruta = host, puerto, ruta
        self.cabeceras = cabeceras or {}
        self.sid = None

    def _pide(self, metodo, cuerpo=None, espera=30):
        c = http.client.HTTPConnection(self.host, self.puerto, timeout=espera)
        q = "?EIO=4&transport=polling&t=%d" % int(time.time() * 1000)
        if self.sid:
            q += "&sid=" + self.sid
        h = dict(self.cabeceras)
        if cuerpo is not None:
            h["Content-Type"] = "text/plain;charset=UTF-8"
        c.request(metodo, self.ruta + q, body=cuerpo.encode() if cuerpo is not None else None, headers=h)
        r = c.getresponse()
        datos = r.read().decode()
        c.close()
        return r.status, datos

    def conecta(self):
        codigo, datos = self._pide("GET")
        if codigo != 200 or not datos.startswith("0"):
            raise ConnectionError("saludo de Engine.IO fallido: %s %s" % (codigo, datos[:80]))
        self.sid = json.loads(datos[1:])["sid"]
        codigo, _ = self._pide("POST", "40")                 # conectar al espacio "/"
        if codigo != 200:
            raise ConnectionError("conexion al espacio / fallida: %s" % codigo)
        return self

    def emite(self, evento, *args):
        codigo, _ = self._pide("POST", "42" + json.dumps([evento] + list(args)))
        return codigo

    def recibe(self, segundos):
        """Eventos que lleguen en `segundos`: [(nombre, [args...])]. Contesta los ping."""
        fin, salida = time.time() + segundos, []
        while time.time() < fin:
            codigo, datos = self._pide("GET", espera=max(1, fin - time.time()) + 30)
            if codigo != 200:
                raise ConnectionError("polling cortado: %s" % codigo)
            for p in datos.split(SEP):
                if p == "2":
                    self._pide("POST", "3")
                elif p.startswith("42"):
                    e = json.loads(p[2:])
                    salida.append((e[0], e[1:]))
                elif p.startswith("1"):
                    raise ConnectionError("el servidor cerro la sesion")
            if salida:
                break
        return salida
