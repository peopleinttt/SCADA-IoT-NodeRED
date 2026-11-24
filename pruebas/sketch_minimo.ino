// Prueba mínima: SOLO imprime. No usa WiFi, ni sensores, ni librerías.
// Sirve para separar dos cosas que se confunden:
//   - si aquí SÍ se ve texto -> el monitor funciona y el problema es del sketch grande
//   - si aquí NO se ve texto -> el problema es la simulación o el monitor, no el código
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("PRUEBA MINIMA: si lees esto, el monitor serie funciona.");
  Serial.println("Deberias ver un 'tic' cada segundo debajo.");
}

void loop() {
  static int n = 0;
  Serial.printf("tic %d\n", ++n);
  delay(1000);
}
