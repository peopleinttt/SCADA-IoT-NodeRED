/*
 * Actividad 1 — Emisor de telemetria (ESP32 simulado en Wokwi)
 * ------------------------------------------------------------
 * Publica cada PERIODO_PUBLICACION_MS un POST HTTP con JSON:
 *   { ts_origen, temperatura_C, vibracion_mm_s, ciclos_acumulados }
 * hacia el endpoint "http in" de Node-RED.
 *
 * Sensores (todos simulados por Wokwi, ver diagram.json):
 *   - DHT22            -> temperatura_C            (GPIO15)
 *   - Transmisor de vibracion (potenciometro en ADC1) -> vibracion_mm_s (GPIO34)
 *   - MPU6050 (I2C)    -> vibracion_mm_s derivada de aceleracion (GPIO21/22)
 *   - Interruptor de proximidad (push button) -> ciclos_acumulados (GPIO27)
 *   - LED de estado    -> diagnostico visual     (GPIO2)
 *
 * La fuente de vibracion se elige con VIB_FUENTE (ver abajo). Las dos rutas
 * estan implementadas y ninguna sintetiza datos: cada una publica lo que
 * realmente mide el hardware simulado.
 *
 * Referencias oficiales usadas:
 *   WiFi en Wokwi ......... https://docs.wokwi.com/guides/esp32-wifi
 *   DHT22 ................. https://docs.wokwi.com/parts/wokwi-dht22
 *   Potenciometro ......... https://docs.wokwi.com/parts/wokwi-potentiometer
 *   MPU6050 ............... https://docs.wokwi.com/parts/wokwi-mpu6050
 *   Formato diagram.json .. https://docs.wokwi.com/diagram-format
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <DHTesp.h>
#include <Preferences.h>
#include <sys/time.h>
#include <math.h>

// ---------------------------------------------------------------------------
// 1. CONFIGURACION  (lo unico que hay que tocar antes de correr)
// ---------------------------------------------------------------------------

// Red simulada de Wokwi: SSID abierto, canal 6 (el canal acelera el enlace).
const char* WIFI_SSID  = "Wokwi-GUEST";
const char* WIFI_PASS  = "";
const int   WIFI_CANAL = 6;

// Endpoint del nodo "http in" de Node-RED.
// IMPORTANTE: el gateway publico de Wokwi solo hace conexiones SALIENTES hacia
// Internet; NO alcanza localhost ni la red local. Node-RED tiene que estar
// expuesto en una URL publica (tunel ngrok/cloudflared o VPS). Ver README.
#define INGEST_URL   "https://CAMBIAME.ngrok-free.app/telemetria"

// Secreto compartido: el tunel es publico, asi que el endpoint se autentica
// con esta cabecera. Debe coincidir con INGEST_KEY en Node-RED.
#define INGEST_KEY   "CAMBIAME-clave-larga-y-aleatoria"

#define PLANTA_ID    "planta_01"   // informativo; la ruta real la arma Node-RED

const uint32_t PERIODO_PUBLICACION_MS = 5000;   // 5 s exigidos por la actividad

// Fuente de vibracion:
//   0 = transmisor analogico (potenciometro)  -> valor RMS ya acondicionado
//   1 = acelerometro MPU6050                  -> derivacion a_rms -> v_rms
#define VIB_FUENTE 0

// ---- Parametros del transmisor de vibracion (VIB_FUENTE 0) ----------------
// Modelo del sensor real emulado: transmisor de vibracion de salida analogica
// (tipo IFM VSA / SKF CMSS), cuyo acondicionador entrega un nivel de CD
// proporcional al valor RMS de velocidad. Escala de fondo de rango:
const float VIB_FONDO_ESCALA_MM_S = 50.0f;   // 0 V -> 0 mm/s ; 3.3 V -> 50 mm/s
const float ADC_V_REF             = 3.3f;
const int   ADC_CUENTAS_MAX       = 4095;    // ESP32: ADC de 12 bits

// ---- Parametros de la derivacion por acelerometro (VIB_FUENTE 1) ----------
// v_rms = a_rms / (2*pi*f0). Se integra en el dominio de la frecuencia usando
// la frecuencia dominante f0 estimada por cruces por cero de la senal sin CD.
const uint16_t VIB_FS_HZ       = 250;   // frecuencia de muestreo de la ventana
const uint16_t VIB_N_MUESTRAS  = 250;   // 1 s de ventana
const float    VIB_F0_MINIMA   = 5.0f;  // Hz; piso para no dividir entre ~0
const float    VIB_F0_NOMINAL  = 30.0f; // Hz; frecuencia de giro del eje (1800 rpm)

// ---- Pines ---------------------------------------------------------------
const int PIN_DHT     = 15;
const int PIN_VIB_ADC = 34;   // ADC1: obligatorio, ADC2 queda inutilizable con WiFi
const int PIN_CICLOS  = 27;
const int PIN_LED     = 2;
const int PIN_SDA     = 21;
const int PIN_SCL     = 22;

const uint8_t MPU_ADDR = 0x68;

// ---------------------------------------------------------------------------
// 2. ESTADO GLOBAL
// ---------------------------------------------------------------------------
DHTesp dht;
Preferences nvs;

volatile uint32_t ciclos = 0;             // contador de ciclos de maquina
volatile uint32_t ultimoPulsoUs = 0;      // antirrebote por software
uint32_t ciclosGuardados = 0;

// Contadores de instrumentacion (seccion 7 del reporte).
uint32_t nIntentos = 0, nOk = 0, nFallo = 0, nDescartes = 0;

bool hayMpu = false;

// ---------------------------------------------------------------------------
// 3. UTILIDADES
// ---------------------------------------------------------------------------

// Interrupcion del interruptor de proximidad. Antirrebote de 20 ms: un pulso
// mecanico rebota ~1-5 ms, cualquier flanco mas rapido que eso no es un ciclo.
void IRAM_ATTR isrCiclo() {
  uint32_t ahora = micros();
  if (ahora - ultimoPulsoUs > 20000UL) {
    ultimoPulsoUs = ahora;
    ciclos++;
  }
}

void parpadeo(int veces, int ms) {
  for (int i = 0; i < veces; i++) {
    digitalWrite(PIN_LED, HIGH); delay(ms);
    digitalWrite(PIN_LED, LOW);  delay(ms);
  }
}

// ts_origen en ISO-8601 UTC con milisegundos: 2026-08-24T21:03:15.123Z
// Devuelve false si el reloj todavia no esta sincronizado por NTP: en ese caso
// NO se publica. Una marca de tiempo falsa contamina el calculo de latencia de
// toda la corrida, asi que preferimos perder la muestra y decirlo.
bool tsOrigenISO(char* buf, size_t n) {
  struct timeval tv;
  gettimeofday(&tv, nullptr);
  if (tv.tv_sec < 1700000000L) return false;   // < 2023-11-14 => sin NTP
  struct tm t;
  gmtime_r(&tv.tv_sec, &t);
  int escritos = snprintf(buf, n, "%04d-%02d-%02dT%02d:%02d:%02d.%03ldZ",
                          t.tm_year + 1900, t.tm_mon + 1, t.tm_mday,
                          t.tm_hour, t.tm_min, t.tm_sec, tv.tv_usec / 1000L);
  return escritos > 0 && (size_t)escritos < n;
}

// ---------------------------------------------------------------------------
// 4. MPU6050 POR REGISTROS (sin libreria: menos dependencias y deja explicito
//    el ajuste de fondo de escala y del filtro anti-alias)
// ---------------------------------------------------------------------------
bool mpuEscribe(uint8_t reg, uint8_t valor) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg); Wire.write(valor);
  return Wire.endTransmission() == 0;
}

bool mpuInicia() {
  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x75);                                  // WHO_AM_I
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)MPU_ADDR, 1) != 1) return false;
  uint8_t quien = Wire.read();
  if (quien != 0x68 && quien != 0x69) return false;

  if (!mpuEscribe(0x6B, 0x00)) return false;   // PWR_MGMT_1: sale de reposo
  // DLPF a 44 Hz (CONFIG=0x03). Con fs=250 Hz la frecuencia de Nyquist es
  // 125 Hz, asi que el filtro deja el ancho de banda por debajo y evita
  // replegado de espectro (aliasing) en la medicion de vibracion.
  if (!mpuEscribe(0x1A, 0x03)) return false;
  if (!mpuEscribe(0x1C, 0x00)) return false;   // ACCEL_CONFIG: +/-2 g, 16384 LSB/g
  return true;
}

bool mpuLeeAccel(float* ax, float* ay, float* az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);                                  // ACCEL_XOUT_H
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)MPU_ADDR, 6) != 6) return false;
  // Cada byte se lee en su propia sentencia a proposito: en C++ el orden de
  // evaluacion de los operandos de | NO esta especificado, asi que
  // (Wire.read() << 8) | Wire.read() puede tomar los bytes al reves segun el
  // compilador. Es el error clasico de este sensor.
  uint8_t xh = Wire.read(); uint8_t xl = Wire.read();
  uint8_t yh = Wire.read(); uint8_t yl = Wire.read();
  uint8_t zh = Wire.read(); uint8_t zl = Wire.read();
  int16_t x = (int16_t)(((uint16_t)xh << 8) | xl);
  int16_t y = (int16_t)(((uint16_t)yh << 8) | yl);
  int16_t z = (int16_t)(((uint16_t)zh << 8) | zl);
  const float LSB_POR_G = 16384.0f, G = 9.80665f;
  *ax = x / LSB_POR_G * G;                           // m/s^2
  *ay = y / LSB_POR_G * G;
  *az = z / LSB_POR_G * G;
  return true;
}

// ---------------------------------------------------------------------------
// 5. MEDICION DE VIBRACION
// ---------------------------------------------------------------------------

// Ruta A: transmisor analogico. El acondicionador ya entrego un nivel de CD
// proporcional al RMS de velocidad, asi que aqui solo se aplica la funcion de
// transferencia declarada del sensor. Promediamos 64 lecturas para bajar el
// ruido de cuantizacion del ADC.
float vibracionDesdeTransmisor() {
  uint32_t suma = 0;
  for (int i = 0; i < 64; i++) { suma += analogRead(PIN_VIB_ADC); delayMicroseconds(200); }
  float cuentas = suma / 64.0f;
  float volts   = cuentas * ADC_V_REF / ADC_CUENTAS_MAX;
  return volts * (VIB_FONDO_ESCALA_MM_S / ADC_V_REF);
}

// Ruta B: acelerometro. Ventana de 1 s a 250 Hz, se resta la componente de CD
// (gravedad y montaje), se calcula a_rms del vector resultante y se integra a
// velocidad con v_rms = a_rms / (2*pi*f0).  f0 se estima contando cruces por
// cero de la senal sin CD; si la senal es plana se usa la frecuencia nominal
// del eje y se reporta el hecho por el puerto serie.
float vibracionDesdeAcelerometro(bool* ok) {
  static float bufX[VIB_N_MUESTRAS], bufY[VIB_N_MUESTRAS], bufZ[VIB_N_MUESTRAS];
  const uint32_t periodoUs = 1000000UL / VIB_FS_HZ;
  float mx = 0, my = 0, mz = 0;

  for (uint16_t i = 0; i < VIB_N_MUESTRAS; i++) {
    uint32_t t0 = micros();
    if (!mpuLeeAccel(&bufX[i], &bufY[i], &bufZ[i])) { *ok = false; return NAN; }
    mx += bufX[i]; my += bufY[i]; mz += bufZ[i];
    while (micros() - t0 < periodoUs) { /* mantiene fs constante */ }
  }
  mx /= VIB_N_MUESTRAS; my /= VIB_N_MUESTRAS; mz /= VIB_N_MUESTRAS;

  double suma2 = 0; uint16_t cruces = 0; float previo = 0;
  for (uint16_t i = 0; i < VIB_N_MUESTRAS; i++) {
    float dx = bufX[i] - mx, dy = bufY[i] - my, dz = bufZ[i] - mz;
    float mag = sqrtf(dx * dx + dy * dy + dz * dz);
    suma2 += (double)mag * mag;
    float proy = dz;                                  // eje de medicion: Z
    if (i > 0 && ((previo < 0 && proy >= 0) || (previo > 0 && proy <= 0))) cruces++;
    previo = proy;
  }
  float aRms = sqrtf(suma2 / VIB_N_MUESTRAS);         // m/s^2

  float f0 = (cruces / 2.0f) * VIB_FS_HZ / (float)VIB_N_MUESTRAS;
  if (f0 < VIB_F0_MINIMA) {
    Serial.printf("[vib] f0 estimada %.2f Hz por debajo del piso; se usa la "
                  "nominal del eje %.1f Hz\n", f0, VIB_F0_NOMINAL);
    f0 = VIB_F0_NOMINAL;
  }
  *ok = true;
  return (aRms / (2.0f * PI * f0)) * 1000.0f;         // mm/s RMS
}

// ---------------------------------------------------------------------------
// 6. RED
// ---------------------------------------------------------------------------
void conectaWiFi() {
  Serial.printf("[wifi] conectando a %s ...", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS, WIFI_CANAL);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(100); Serial.print(".");
    if (millis() - t0 > 30000UL) { Serial.println(" sin enlace, reintentando"); WiFi.disconnect(); WiFi.begin(WIFI_SSID, WIFI_PASS, WIFI_CANAL); t0 = millis(); }
  }
  Serial.printf(" listo, IP %s\n", WiFi.localIP().toString().c_str());
}

void sincronizaReloj() {
  configTime(0, 0, "pool.ntp.org", "time.google.com");   // UTC, sin huso local
  Serial.print("[ntp] sincronizando");
  uint32_t t0 = millis();
  while (time(nullptr) < 1700000000L) {
    delay(200); Serial.print(".");
    if (millis() - t0 > 20000UL) { Serial.println(" sin respuesta, reintento"); configTime(0, 0, "pool.ntp.org", "time.google.com"); t0 = millis(); }
  }
  Serial.printf(" listo (epoch %ld)\n", (long)time(nullptr));
}

// Extrae el nombre de host de INGEST_URL para poder diagnosticar por separado
// el DNS y la conexion. HTTPClient devuelve el mismo -1 ("connection refused")
// cuando falla el DNS, cuando rebota el TCP y cuando el TLS no termina a
// tiempo: sin separarlos, uno depura a ciegas.
void extraeHost(char* destino, size_t n) {
  const char* p = strstr(INGEST_URL, "://");
  p = p ? p + 3 : INGEST_URL;
  size_t i = 0;
  while (p[i] && p[i] != '/' && p[i] != ':' && i < n - 1) { destino[i] = p[i]; i++; }
  destino[i] = 0;
}

// Prueba DNS y TCP por separado, una sola vez, y lo reporta. Es barato y
// convierte un "-1" mudo en un diagnostico que dice donde se rompio.
void diagnosticaRed() {
  char host[96];
  extraeHost(host, sizeof(host));
  Serial.printf("[net] host=%s\n", host);

  IPAddress ip;
  uint32_t t0 = millis();
  bool dnsOk = WiFi.hostByName(host, ip);
  Serial.printf("[net] DNS ...... %s (%lu ms)\n",
                dnsOk ? ip.toString().c_str() : "FALLO", (unsigned long)(millis() - t0));
  if (!dnsOk) {
    Serial.println("[net] Sin DNS no hay nada que hacer: revisa el nombre del tunel.");
    return;
  }

  WiFiClient tcp;
  t0 = millis();
  bool tcpOk = tcp.connect(ip, 443, 15000);
  Serial.printf("[net] TCP 443 .. %s (%lu ms)\n", tcpOk ? "OK" : "FALLO",
                (unsigned long)(millis() - t0));
  tcp.stop();

  WiFiClientSecure tls; tls.setInsecure();
  tls.setTimeout(30);
  t0 = millis();
  bool tlsOk = tls.connect(host, 443);
  Serial.printf("[net] TLS 443 .. %s (%lu ms)\n", tlsOk ? "OK" : "FALLO",
                (unsigned long)(millis() - t0));
  tls.stop();

  // Control: si el TLS falla contra el tunel, hay que saber si el ESP32
  // simulado puede hacer TLS con ALGUIEN. Sin este control no se distingue
  // "ngrok es el problema" de "aqui no hay TLS que sirva".
  if (!tlsOk) {
    WiFiClientSecure ctrl; ctrl.setInsecure();
    ctrl.setTimeout(30);
    t0 = millis();
    bool ctrlOk = ctrl.connect("example.com", 443);
    Serial.printf("[net] TLS control (example.com) .. %s (%lu ms)\n",
                  ctrlOk ? "OK" : "FALLO", (unsigned long)(millis() - t0));
    ctrl.stop();
    Serial.println(ctrlOk
      ? "[net] El TLS funciona: el problema es el certificado o el cifrado de ngrok."
      : "[net] El TLS no funciona con nadie: hay que usar un tunel TCP sin TLS.");
  }
}

// Cliente y conexion persistentes. MEDIDO en Wokwi el 2026-08-25: el apreton
// de manos TLS tarda ~6.4 s en el ESP32 simulado, que no tiene acelerador
// criptografico. Abriendo una conexion nueva por publicacion, esos 6.4 s
// entraban en CADA muestra: la latencia mediana daba 14.8 s y el periodo real
// se estiraba a 6.8 s contra los 5 s nominales. Manteniendo la conexion viva
// el apreton ocurre una sola vez.
WiFiClientSecure clienteTls;
WiFiClient       clientePlano;
HTTPClient       http;
bool             conexionLista = false;

void cierraConexion() {
  if (conexionLista) { http.end(); conexionLista = false; }
}

// Envia el JSON. Devuelve el codigo HTTP, o un valor negativo de HTTPClient.
int publica(const char* cuerpo) {
  bool esTls = (strncmp(INGEST_URL, "https://", 8) == 0);

  if (!conexionLista) {
    clienteTls.setInsecure();      // simulacion: no validamos la cadena
    http.setReuse(true);           // sin esto el TLS se rehace cada vez
    http.setTimeout(30000);
    http.setConnectTimeout(30000);
    conexionLista = esTls ? http.begin(clienteTls, INGEST_URL)
                          : http.begin(clientePlano, INGEST_URL);
    if (!conexionLista) return -1000;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Ingest-Key", INGEST_KEY);
  // ngrok gratuito interpone una pagina de aviso a las peticiones que parecen
  // venir de un navegador. Esta cabecera la salta; con cloudflared o un VPS
  // sobra, pero no estorba.
  http.addHeader("ngrok-skip-browser-warning", "1");
  uint32_t tPost = millis();
  int codigo = http.POST((uint8_t*)cuerpo, strlen(cuerpo));
  uint32_t dur = millis() - tPost;
  if (codigo > 0) {
    String resp = http.getString();
    Serial.printf("[http] %d (%lu ms) %s\n", codigo, (unsigned long)dur,
                  resp.substring(0, 160).c_str());
  } else {
    Serial.printf("[http] error de transporte %d (%s) tras %lu ms\n", codigo,
                  http.errorToString(codigo).c_str(), (unsigned long)dur);
  }
  // La conexion solo se cierra si fallo: si sigue sana se reaprovecha y el
  // siguiente envio se ahorra el apreton de manos completo.
  if (codigo <= 0) cierraConexion();
  return codigo;
}

// ---------------------------------------------------------------------------
// 7. CICLO PRINCIPAL
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== Emisor de telemetria — Actividad 1 ===");

  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_CICLOS, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_CICLOS), isrCiclo, FALLING);

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_VIB_ADC, ADC_11db);   // rango util ~0 a 3.3 V

  dht.setup(PIN_DHT, DHTesp::DHT22);

  // ciclos_acumulados debe ser monotono aunque se reinicie el equipo.
  nvs.begin("actividad1", false);
  ciclos = nvs.getULong("ciclos", 0);
  ciclosGuardados = ciclos;
  Serial.printf("[nvs] ciclos_acumulados recuperados: %lu\n", (unsigned long)ciclos);

  hayMpu = mpuInicia();
  Serial.printf("[mpu] %s\n", hayMpu ? "detectado en 0x68" : "NO detectado");
#if VIB_FUENTE == 1
  if (!hayMpu) Serial.println("[mpu] ERROR: VIB_FUENTE=1 exige el MPU6050. "
                              "No se publicara vibracion inventada.");
#endif

  conectaWiFi();
  sincronizaReloj();
  diagnosticaRed();
  parpadeo(3, 80);
}

void loop() {
  static uint32_t proxima = 0;
  if ((int32_t)(millis() - proxima) < 0) return;
  proxima = millis() + PERIODO_PUBLICACION_MS;

  if (WiFi.status() != WL_CONNECTED) { cierraConexion(); conectaWiFi(); return; }

  // --- marca de tiempo de origen -----------------------------------------
  char ts[32];
  if (!tsOrigenISO(ts, sizeof(ts))) {
    Serial.println("[ts] reloj sin sincronizar: se descarta la muestra");
    nDescartes++; sincronizaReloj(); return;
  }

  // --- temperatura --------------------------------------------------------
  TempAndHumidity th = dht.getTempAndHumidity();
  if (dht.getStatus() != DHTesp::ERROR_NONE || isnan(th.temperature)) {
    Serial.printf("[dht] lectura invalida (%s): se descarta la muestra\n",
                  dht.getStatusString());
    nDescartes++; parpadeo(2, 40); return;
  }
  float temperatura = th.temperature;

  // --- vibracion ----------------------------------------------------------
  float vibracion; bool vibOk = true;
#if VIB_FUENTE == 1
  if (!hayMpu) { Serial.println("[vib] sin MPU6050: se descarta la muestra"); nDescartes++; return; }
  vibracion = vibracionDesdeAcelerometro(&vibOk);
#else
  vibracion = vibracionDesdeTransmisor();
#endif
  if (!vibOk || isnan(vibracion)) {
    Serial.println("[vib] medicion invalida: se descarta la muestra");
    nDescartes++; parpadeo(2, 40); return;
  }

  // --- ciclos -------------------------------------------------------------
  uint32_t ciclosAhora = ciclos;
  if (ciclosAhora >= ciclosGuardados + 10) {          // limita escrituras a flash
    nvs.putULong("ciclos", ciclosAhora);
    ciclosGuardados = ciclosAhora;
  }

  // --- carga util ---------------------------------------------------------
  JsonDocument doc;
  doc["ts_origen"]         = ts;
  doc["temperatura_C"]     = round(temperatura * 100.0) / 100.0;
  doc["vibracion_mm_s"]    = round(vibracion * 100.0) / 100.0;
  doc["ciclos_acumulados"] = ciclosAhora;
  char cuerpo[256];
  serializeJson(doc, cuerpo, sizeof(cuerpo));
  Serial.printf("[tx] %s\n", cuerpo);

  // --- envio con un reintento --------------------------------------------
  digitalWrite(PIN_LED, HIGH);
  nIntentos++;
  int codigo = publica(cuerpo);
  if (codigo < 200 || codigo >= 300) {
    Serial.println("[tx] reintento unico en 500 ms");
    delay(500);
    codigo = publica(cuerpo);
  }
  digitalWrite(PIN_LED, LOW);

  if (codigo >= 200 && codigo < 300) nOk++; else { nFallo++; parpadeo(4, 60); }
  Serial.printf("[cnt] intentos=%lu ok=%lu fallo=%lu descartes=%lu ciclos=%lu\n",
                (unsigned long)nIntentos, (unsigned long)nOk,
                (unsigned long)nFallo, (unsigned long)nDescartes,
                (unsigned long)ciclosAhora);
}
