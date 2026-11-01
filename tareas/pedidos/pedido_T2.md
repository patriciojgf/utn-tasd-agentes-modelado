# Pedido de T2 (tests)

Igual en las dos condiciones. Se ejecuta con: ./tasd.sh abrir <sin|con> T2 <rep>
El tester recibe el modelo gold de referencia ya construido (mismo para todas las corridas) y escribe tests en models/gold/schema.yml y tests/.

```
Escribí los tests de calidad de los modelos de la capa gold.
```

## Cómo se evalúa
La idea: un test sirve si avisa cuando algo se rompe. Entonces rompemos el modelo a propósito y nos fijamos si los tests del agente avisan.
Con la sesión del agente abierta, en otra pestaña: ./tasd.sh evaluar <sin|con> T2 <rep>. Corre los tests del agente sobre 6 versiones del modelo con una regla rota cada una (referencia/mutantes/). Si algún test falla, la regla está cubierta; si todos pasan, queda sin cubrir. Además conviene leer los tests para confirmar qué controla cada uno. Si el agente deja un test fallando a propósito sobre el modelo correcto (por ejemplo, por un defecto de los datos), contá una regla como cubierta cuando falla algún test que pasaba sobre el modelo correcto.

## Ayuda posterior (fijada antes de correr)
| # | Pista (nivel 1) | Regla dictada (nivel 2) |
|---|---|---|
| 1 | Revisá si tus tests controlan cuántas filas puede tener cada cliente en dim_cliente. | Agregá un test que verifique que dim_cliente tenga una sola fila por cliente. |
| 2 | Revisá si tus tests controlan el filtro de cuentas que aplica fact_movimientos. | Agregá un test que verifique que ningún movimiento del hecho pertenezca a una cuenta con estado X. |
| 3 | Revisá si tus tests controlan el signo del importe según el tipo de movimiento. | Agregá un test que verifique que los débitos (D) tengan importe negativo. |
| 4 | Revisá si tus tests controlan el signo de cada tipo de movimiento, incluido R. | Agregá un test que verifique que los reversos (R) tengan importe positivo. |
| 5 | Revisá si tus tests controlan la conversión de moneda del importe en pesos. | Agregá un test que verifique que el importe en pesos de los movimientos en USD sea el importe original por la cotización de su fecha. |
| 6 | Revisá si tus tests controlan los niveles de la jerarquía en dim_producto. | Agregá un test que verifique que dim_producto tenga solo subproductos de nivel 3 y la familia sin nulos. |

Clasificación: detectada sin ayuda = la resuelve el agente; con pista = con ayuda; con test dictado = queda del lado del programador.
