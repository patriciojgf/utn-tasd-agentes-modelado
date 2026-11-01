# Pedido de T1 (modelo)

Se escribe por consola, idéntico en las dos condiciones (sin y con metadatos) y en cada repetición.
Se ejecuta con: ./tasd.sh abrir <sin|con> T1 <rep>

```
Creá el modelo dimensional de la capa gold para analizar los movimientos de los clientes. Seguí el estilo de Kimball: modelo estrella, con dimensiones que se relacionan solo con la tabla de hechos (ninguna dimensión referencia a otra) y clave sustituta en todas las dimensiones.
```

## Pistas de la ayuda posterior (fijadas antes de correr)
Nivel 1 (señala dónde mirar, no dice la regla). Solo se usa la de una regla que falló.

| # | Pista |
|---|---|
| 1 | Revisá la tabla de clientes: un mismo cliente aparece más de una vez. Verificá que el modelo lo tenga en cuenta y que el hecho no duplique movimientos. |
| 2 | Revisá la columna estado de las cuentas: no todos los estados deberían tratarse igual en el modelo. |
| 3 | Revisá cómo afecta cada tipo de movimiento al saldo de la cuenta. ¿Todos los importes deberían sumar? |
| 4 | Revisá qué representa el tipo de movimiento R y cómo afecta al saldo. |
| 5 | Revisá en qué moneda está cada movimiento y cómo queda expresado el importe en pesos. |
| 6 | Revisá la tabla de productos: tiene niveles. ¿A qué nivel se asocian las cuentas y qué niveles necesita el negocio para agrupar? |

Nivel 2: se le dicta la regla tal como está en reglas_negocio.md.
Clasificación: sin ayuda, la resuelve el agente; con pista, con ayuda; con regla dictada, queda del lado del programador.
