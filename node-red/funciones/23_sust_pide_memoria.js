/* Nodo: "pide memoria"  (A2-Sustituto, en cada tick)
 * ---------------------------------------------------------------
 * El nodo Modbus-Server no avisa cuando un cliente le escribe: solo entrega
 * sus buffers como respuesta a un mensaje de entrada. Este mensaje NO es una
 * escritura valida (no trae register), asi que el servidor no toca su memoria
 * y contesta por sus salidas 0 (holding) y 1 (coils) con el numero de pedido
 * adentro. El emulador espera las dos respuestas de ESE pedido para avanzar.
 *
 * Si el pedido anterior no se completo, se cuenta y se sigue: la simulacion
 * avanza por pasos, no por reloj, asi que un paso perdido la retrasa pero no
 * la vuelve distinta.
 */
const S = flow.get("sust");
if (!S || !S.activo || !global.get("a2_mapa")) return null;

if (S.pedido > 0 && S.recibido.paso !== S.pedido) S.pedidos_sin_respuesta++;
S.pedido++;
msg.payload = { pedido: S.pedido };
return msg;
