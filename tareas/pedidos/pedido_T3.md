# Pedido de T3 (documentación)

Igual en las dos condiciones. Se ejecuta con: ./tasd.sh abrir <sin|con> T3 <rep>
El documentador recibe el modelo gold de referencia ya construido (mismo para todas las corridas), igual que en T2.

```
Documentá los modelos de la capa gold.
```

## Cómo se evalúa
Se lee la documentación (models/gold/schema.yml y RESUMEN.md) y, por cada una de las 6 reglas, la clasifica en:
- Bien explicada: dice qué hace el código y por qué (por ejemplo, "excluye las cuentas con estado X porque son anuladas", no solo "filtra estado <> 'X'").
- Inventada o mal explicada: da un motivo o un significado que no es el real.
- No la explica o la marca como duda.
Inventar es peor que no saber: se registra aparte.

Clasificación: bien sin ayuda = la resuelve el agente; bien después de la pista = con ayuda; hubo que dictarle la regla = queda del lado del programador.

## Ayuda posterior (fijada antes de correr)
| # | Pista (nivel 1) | Regla dictada (nivel 2) |
|---|---|---|
| 1 | Revisá si la documentación explica por qué dim_cliente tiene una sola fila por cliente. | La tabla clientes es un histórico; la fila vigente de un cliente es la que tiene fecha_hasta = 9999-12-31. |
| 2 | Revisá si la documentación explica por qué se excluyen las cuentas con estado X. | El estado X significa cuenta anulada. Las cuentas anuladas se excluyen de todo: no cuentan como cuentas y sus movimientos no se consideran. |
| 3 | Revisá si la documentación explica el signo del importe según el tipo de movimiento. | El importe original siempre es positivo; el signo lo da el tipo: D débito resta, C crédito suma. |
| 4 | Revisá si la documentación explica qué es el tipo de movimiento R y su efecto en el saldo. | R es un reverso: anula un débito anterior, por lo tanto suma al saldo (importe positivo). |
| 5 | Revisá si la documentación explica cómo se convierten los importes a pesos. | Los importes en USD se convierten a pesos con la cotización de la misma fecha; los ARS quedan igual. |
| 6 | Revisá si la documentación explica la jerarquía de productos y por qué la dimensión tiene solo subproductos. | La jerarquía tiene 3 niveles (familia, producto, subproducto); las cuentas se asocian al subproducto (nivel 3) y la dimensión la aplana. |
