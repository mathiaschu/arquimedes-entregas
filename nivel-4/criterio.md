# Criterio de entrega tras la falla de V3

## Situación y recursos

A las 11:20 V3 queda fuera de servicio en el depósito (nodo 1026). Quedan V1 (Rita) y V2 (Tomi), con 320 kg cada una y turno de 11:35 a 13:35, una sola salida, sin recarga ni extensión. Los 24 pedidos pendientes (P3-017 a P3-040) pesan 40 kg cada uno, incluido el stock que estaba en V3, que se puede reasignar completo hasta las 11:35. La capacidad conjunta es de 640 kg, así que **hoy se pueden entregar como máximo 16 pedidos** y al menos 8 se postergan sí o sí. Cada descarga lleva 12 minutos y debe quedar completa dentro de la franja del cliente.

## Principio

Se entrega primero a quien no puede esperar al próximo reparto sin que falte comida a las personas que abastece. El valor de la mercadería no define prioridad: un pedido caro de un comercio con stock y proveedor alternativo puede esperar; un geriátrico o un comedor sin reservas, no.

## Prioridades

1. **Nivel 1, riesgo hoy.** Clientes sin alternativa de abastecimiento hoy y con reservas menores a 24 horas (no llegan al próximo reparto). Son Residencia Eva y Residencia Alma (geriátricos, 32 personas cada uno, 0 h de reserva, mercadería de 6 h de vida útil), Comedor Nacho y Comedor Fran (40 personas cada uno, 0 h de reserva) y los comercios de Iván y Valen (6 h de reserva, sin alternativa). Se entregan todos; el plan se arma alrededor de ellos.
2. **Nivel 2, comedores con reservas justas.** Comedores cuyas reservas no superan 24 horas, aunque tengan alternativa: Comedor Clau y Comedor Rosa (26 personas cada uno, 24 h). Una postergación los deja sin margen ante cualquier demora del reparto siguiente.
3. **Nivel 3, resto.** Clientes con alternativa hoy y reservas de 36 horas o más. Dentro de este nivel se ordena por:
   1. menos horas de reserva primero (36 h antes que 48 h);
   2. más personas abastecidas;
   3. pago anticipado antes que pago contra entrega (ya cobramos, el compromiso es más fuerte);
   4. mayor antigüedad como cliente;
   5. identificador de cliente ascendente, como desempate final y verificable.

## Cómo se aplica

Se recorre la lista ordenada y cada cliente se agrega sólo si existe un plan factible para V1 y V2 que entregue a todos los ya elegidos más ese cliente, con la capacidad en kg y m3, las franjas completas, descargas sin superponerse, salida 11:35 y regreso al depósito antes de 13:35, con las distancias del mapa y las reglas de `operacion.json`. Si no entra, se posterga y se sigue con el siguiente; un cliente de menor prioridad nunca desplaza a uno de mayor prioridad ya elegido. Las rutas finales minimizan la distancia entre los planes factibles para ese conjunto.

Resultado: entran los 6 de nivel 1, los 2 de nivel 2 y los 8 primeros de nivel 3 (Julia, Tino, Cata, Pepa, Omar, Vicky, Ari y Leo). Con esos 16 pedidos las dos camionetas quedan con 320 kg exactos, así que cualquier otro pedido es físicamente imposible hoy. Se postergan Bruno, Elisa, Mauro, Belu, Susi, Amalia, Dora e Inés.

## Alcance de cada compromiso

- **Entrega hoy:** el pedido completo, sin división, con la descarga entera dentro de la franja que pidió el cliente y en la hora que figura en `rutas.json`. Las horas de inicio son las más tempranas posibles; si hay demoras, el margen hasta el cierre de cada franja es el que cubre el plan.
- **Postergación:** el pedido se mantiene completo y con el mismo domicilio. Se avisa hoy al cliente, antes del horario en que esperaba la entrega, que va en el primer reparto siguiente, con prioridad sobre los pedidos nuevos y en una franja que confirme. Su mercadería no se pierde: el stock queda en depósito. No se promete hoy una hora concreta para el día siguiente porque eso depende de la flota disponible.
- **Pago anticipado:** a quien ya pagó y se posterga se le ofrece mantener el pedido para el próximo reparto o la devolución del importe si prefiere abastecerse con su alternativa.
- **Lo que no se compromete:** no se promete una segunda vuelta, una camioneta extra ni extender turnos, porque el parte lo descarta.

## Empates

Si dos clientes quedan iguales en todos los criterios anteriores, decide el identificador ascendente. Pasó con Tino y Cata, con Pepa y Omar (en ambos casos entran los dos), con Susi y Amalia y con Dora e Inés (se postergan los cuatro), así que el desempate final no cambió ninguna decisión. El corte entre entregar y postergar quedó entre Leo (12 personas, pago anticipado, 42 meses) y Bruno (12 personas, pago anticipado, 30 meses), que se separan por antigüedad.
