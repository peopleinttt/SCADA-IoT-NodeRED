#!/usr/bin/env python3
"""Simulador local de Firebase RTDB + Identity Toolkit + Gemini.
Sirve para probar la cadena de Node-RED sin tocar cuotas ni credenciales."""
import json, re, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ESTADO = {"telemetria": {}, "diagnosticos": {}, "proceso": {}, "contador": 0, "modo": "ok", "peticiones": [], "cabeceras": {}}
LOCK = threading.Lock()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _responde(self, codigo, obj, texto=False):
        cuerpo = obj.encode() if texto else json.dumps(obj).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _cuerpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        crudo = self.rfile.read(n).decode() if n else ""
        try: return json.loads(crudo)
        except Exception: return crudo

    def _autenticado(self, q):
        """Firebase exige ?auth=<idToken>. El simulador tambien: si acepta
        peticiones sin credencial, un flujo que olvide el token pasa las
        pruebas aqui y falla contra la base real con un 401."""
        return q.get("auth", [""])[0] == "TOKEN-SIMULADO"

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        with LOCK: ESTADO["peticiones"].append(("GET", u.path, q))
        if u.path == "/__estado":
            with LOCK: return self._responde(200, {k: v for k, v in ESTADO.items() if k != "peticiones"})
        if u.path == "/__reinicia":
            with LOCK:
                ESTADO.update({"telemetria": {}, "diagnosticos": {}, "proceso": {}, "contador": 0, "modo": "ok", "peticiones": [], "cabeceras": {}})
            return self._responde(200, {"ok": True})
        m = re.match(r"^/plantas/[^/]+/(telemetria|diagnosticos|proceso)\.json$", u.path)
        if m:
            if ESTADO["modo"] == "permiso": return self._responde(401, {"error": "Permission denied"})
            if not self._autenticado(q):
                return self._responde(401, {"error": "Permission denied"})
            rama = m.group(1)
            with LOCK:
                claves = sorted(ESTADO[rama])
                lim = int(q.get("limitToLast", ["1000"])[0])
                return self._responde(200, {k: ESTADO[rama][k] for k in claves[-lim:]})
        self._responde(404, {"error": "no existe"})

    def do_POST(self):
        u = urlparse(self.path); cuerpo = self._cuerpo()
        with LOCK: ESTADO["cabeceras"][u.path.split("/")[-1]] = {k.lower(): v for k, v in self.headers.items()}
        with LOCK: ESTADO["peticiones"].append(("POST", u.path, cuerpo))
        if u.path.endswith(":generateContent"):
            if ESTADO["modo"] == "cuota":
                return self._responde(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                    "message": "Quota exceeded", "details": [
                        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "37s"}]}})
            if ESTADO["modo"] == "basura":
                return self._responde(200, "<html>502 Bad Gateway</html>", texto=True)
            if ESTADO["modo"] == "truncado":
                return self._responde(200, {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}],
                                            "usageMetadata": {"totalTokenCount": 512}})
            if ESTADO["modo"] == "texto_suelto":
                return self._responde(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [
                    {"text": "El equipo opera fuera de rango.\nAccion: detener y revisar rodamiento."}]}}],
                    "modelVersion": "gemini-2.5-flash", "usageMetadata": {"totalTokenCount": 90}})
            # Actividad 2: su esquema trae nivel_estimado. Respuestas validas e
            # invalidas segun el modo, para probar la validacion estricta.
            esquema = json.dumps(cuerpo.get("generationConfig", {}).get("responseSchema", {})) if isinstance(cuerpo, dict) else ""
            if "nivel_estimado" in esquema:
                ESTADO.setdefault("a2_consultas", 0)
                ESTADO["a2_consultas"] += 1
                ok = {"texto_diagnostico": "Throughput 10.4 boxes/min with mean mass 9.9 kg; no losses or misroutes. Line is healthy.",
                      "nivel_estimado": "normal", "accion_codigo": "mantener",
                      "justificacion": "All counters nominal and mass spread within the expected range."}
                variantes = {
                    "a2_nivel_malo": dict(ok, nivel_estimado="grave"),
                    "a2_accion_mala": dict(ok, accion_codigo="acelerar"),
                    "a2_reducir": dict(ok, accion_codigo="reducir_velocidad", valor_pct=10),
                    "a2_pct_fuera": dict(ok, accion_codigo="reducir_velocidad", valor_pct=45),
                    "a2_pct_sobra": dict(ok, valor_pct=5),
                    "a2_falta": {k: v for k, v in ok.items() if k != "justificacion"},
                    "a2_extra": dict(ok, nota="x"),
                }
                if ESTADO["modo"] == "a2_no_json":
                    t = "Line looks fine, keep running."
                else:
                    t = json.dumps(variantes.get(ESTADO["modo"], ok))
                return self._responde(200, {"candidates": [{"content": {"parts": [{"text": t}], "role": "model"},
                                                            "finishReason": "STOP"}], "modelVersion": "gemini-simulado",
                                            "usageMetadata": {"totalTokenCount": 300}})
            texto = json.dumps({"texto_diagnostico": "Vibracion 9.80 mm/s sobre el umbral 7.1 y temperatura 78.5 C al alza (1.2 C/min): desbalanceo con calentamiento de rodamiento.",
                                "accion_prescrita": "Detener la maquina e inspeccionar el rodamiento del eje"}, ensure_ascii=False)
            return self._responde(200, {"candidates": [{"content": {"parts": [{"text": texto}], "role": "model"},
                                                        "finishReason": "STOP"}],
                                        "modelVersion": "gemini-2.5-flash",
                                        "usageMetadata": {"promptTokenCount": 410, "candidatesTokenCount": 71,
                                                          "thoughtsTokenCount": 0, "totalTokenCount": 481}})
        if u.path.startswith("/v1/accounts:signInWithPassword"):
            if ESTADO["modo"] == "login_malo":
                return self._responde(400, {"error": {"message": "INVALID_LOGIN_CREDENTIALS"}})
            return self._responde(200, {"idToken": "TOKEN-SIMULADO", "localId": "uid-ingestor-123",
                                        "expiresIn": "3600", "refreshToken": "r"})
        m = re.match(r"^/plantas/([^/]+)/(telemetria|diagnosticos|proceso)\.json$", u.path)
        if m:
            if ESTADO["modo"] == "permiso": return self._responde(401, {"error": "Permission denied"})
            if ESTADO["modo"] == "regla":  return self._responde(400, {"error": "Invalid data; couldn't parse JSON object"})
            if not self._autenticado(parse_qs(u.query)):
                return self._responde(401, {"error": "Permission denied"})
            with LOCK:
                ESTADO["contador"] += 1
                clave = f"-N{ESTADO['contador']:06d}"
                ESTADO[m.group(2)][clave] = cuerpo
            return self._responde(200, {"name": clave})
        if u.path == "/__modo":
            with LOCK: ESTADO["modo"] = cuerpo.get("modo", "ok")
            return self._responde(200, {"modo": ESTADO["modo"]})
        self._responde(404, {"error": "no existe"})

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
