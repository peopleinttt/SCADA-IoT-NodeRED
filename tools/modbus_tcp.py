#!/usr/bin/env python3
"""Cliente Modbus TCP minimo, sin dependencias. Compatible con Python 3.9.

Solo las funciones que usa la Actividad 2: leer las cuatro tablas (FC 01 a 04)
y escribir una bobina o un registro (FC 05 y 06). pymodbus no esta instalado y
para esto no hace falta: una trama Modbus TCP es una cabecera MBAP de 7 bytes
mas el PDU.

    with Cliente("127.0.0.1", 5020) as c:
        c.lee_discretas(0, 5)            -> [False, True, ...]
        c.escribe_registro(0, 64536)     -> palabra de 16 bits tal cual
"""
import socket, struct


class ModbusError(Exception):
    """Respuesta de excepcion del servidor (codigo de funcion | 0x80)."""
    NOMBRES = {1: "funcion ilegal", 2: "direccion ilegal", 3: "valor ilegal",
               4: "falla del servidor", 6: "servidor ocupado"}

    def __init__(self, funcion, codigo):
        self.funcion, self.codigo = funcion, codigo
        super().__init__("excepcion Modbus %d (%s) en la funcion %d"
                         % (codigo, self.NOMBRES.get(codigo, "?"), funcion))


class Cliente:
    def __init__(self, host, puerto=502, unidad=1, espera_s=3.0):
        self.host, self.puerto, self.unidad, self.espera_s = host, puerto, unidad, espera_s
        self._sock, self._tid = None, 0

    def __enter__(self):
        self.conecta()
        return self

    def __exit__(self, *exc):
        self.cierra()

    def conecta(self):
        self._sock = socket.create_connection((self.host, self.puerto), timeout=self.espera_s)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def cierra(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def _recibe(self, n):
        datos = b""
        while len(datos) < n:
            trozo = self._sock.recv(n - len(datos))
            if not trozo:
                raise ConnectionError("el servidor cerro la conexion")
            datos += trozo
        return datos

    def _pide(self, funcion, cuerpo):
        if self._sock is None:
            self.conecta()
        self._tid = (self._tid + 1) & 0xFFFF
        pdu = struct.pack(">B", funcion) + cuerpo
        self._sock.sendall(struct.pack(">HHHB", self._tid, 0, len(pdu) + 1, self.unidad) + pdu)
        tid, _, largo, _ = struct.unpack(">HHHB", self._recibe(7))
        resp = self._recibe(largo - 1)
        if tid != self._tid:
            raise ConnectionError("id de transaccion %d, se esperaba %d" % (tid, self._tid))
        if resp[0] == funcion | 0x80:
            raise ModbusError(funcion, resp[1])
        if resp[0] != funcion:
            raise ConnectionError("funcion %d en la respuesta, se esperaba %d" % (resp[0], funcion))
        return resp[1:]

    def _lee_bits(self, funcion, direccion, cantidad):
        r = self._pide(funcion, struct.pack(">HH", direccion, cantidad))
        datos = r[1:1 + r[0]]
        return [bool((datos[i >> 3] >> (i & 7)) & 1) for i in range(cantidad)]

    def _lee_palabras(self, funcion, direccion, cantidad):
        r = self._pide(funcion, struct.pack(">HH", direccion, cantidad))
        return list(struct.unpack(">%dH" % cantidad, r[1:1 + r[0]]))

    def lee_bobinas(self, direccion, cantidad=1):
        return self._lee_bits(1, direccion, cantidad)

    def lee_discretas(self, direccion, cantidad=1):
        return self._lee_bits(2, direccion, cantidad)

    def lee_retencion(self, direccion, cantidad=1):
        return self._lee_palabras(3, direccion, cantidad)

    def lee_entrada(self, direccion, cantidad=1):
        return self._lee_palabras(4, direccion, cantidad)

    def escribe_bobina(self, direccion, valor):
        self._pide(5, struct.pack(">HH", direccion, 0xFF00 if valor else 0x0000))

    def escribe_registro(self, direccion, palabra):
        if not 0 <= palabra <= 0xFFFF:
            raise ValueError("palabra %r fuera de 0..65535 (usa complemento a dos)" % palabra)
        self._pide(6, struct.pack(">HH", direccion, palabra))
