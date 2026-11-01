# Cómo evaluar una corrida

Cada corrida se evalúa regla por regla. Para cada una de las seis reglas de negocio se clasifica el resultado en uno de tres niveles:

| Nivel | Cuándo |
|---|---|
| La resuelve el agente | La regla está bien sin ninguna ayuda |
| La resuelve con ayuda | La corrige después de la pista (nivel 1) |
| Queda del lado del programador | Hubo que dictarle la regla (nivel 2), o el agente preguntó y una persona eligió la respuesta |

Las pistas y las reglas dictadas de cada tarea están en `tareas/pedidos/`. Se dan en la misma sesión del agente, solo para la regla que falló.

## T1: el modelo que construyó el agente

Se revisa con consultas de solo lectura sobre `corridas/<condición>/T1_rep<n>/banco.duckdb`. El agente elige los nombres de tablas y columnas, así que primero hay que ubicar cuál es el hecho de movimientos, la dimensión de clientes, la de cuentas y la de productos, y la columna del importe en pesos con signo.

| # | Regla | Qué verificar | Valor esperado |
|---|---|---|---|
| 1 | Cliente vigente | Una sola versión vigente por cliente, y que el hecho no duplique movimientos al cruzar con clientes | 400 clientes vigentes (581 filas si guarda historial) |
| 2 | Cuentas anuladas | Movimientos en el hecho y cuentas en la dimensión, sin ninguna cuenta con estado X | 18.772 movimientos y 655 cuentas (no 20.000 y 700) |
| 3 | Signo D y C | Débitos con importe negativo y créditos positivo | Ningún débito positivo |
| 4 | Reverso | Reversos (R) con importe positivo | Ningún reverso negativo |
| 5 | Dólares | Importe en pesos de cada movimiento en USD igual al importe original por la cotización de su fecha | Igual a la referencia movimiento por movimiento (diferencias de centavos por redondeo) |
| 6 | Jerarquía de productos | Dimensión de productos al nivel subproducto, con producto y familia como columnas | 6 filas con familia (no 13) |

Control de conjunto: la suma del importe en pesos de todos los movimientos tiene que dar −1.302.555.299,16 (la referencia). Si las reglas 3 y 4 están mal, el total cambia mucho: con todos los importes positivos da un valor positivo, con los reversos sin efecto da −1.961.860.093,30 y con los reversos restando da −2.621.164.887,44.

Además se revisa el diseño: que sea un modelo estrella con claves sustitutas y que ninguna dimensión referencie a otra, como pide el pedido.

## T2: los tests que escribió el agente

T2 trabaja sobre el modelo de referencia ya construido, igual para todas las corridas. Los tests del agente se corren contra seis copias del modelo, cada una con una regla rota a propósito (`referencia/mutantes/`):

```bash
./tasd.sh evaluar <sin|con> T2 <rep>
```

Una regla queda cubierta si, con su copia rota, falla algún test que pasaba sobre el modelo correcto. Si el agente deja un test fallando a propósito sobre el modelo correcto (por ejemplo, porque encontró un defecto en los datos sintéticos), ese test no cuenta para ninguna regla. Conviene además leer los tests para confirmar qué controla cada uno.

## T3: la documentación que escribió el agente

T3 también trabaja sobre el modelo de referencia. Se lee `models/gold/schema.yml` y `models/gold/RESUMEN.md` y, por cada regla, se clasifica la explicación en:

- **Bien explicada:** dice qué hace el código y por qué. Por ejemplo, «excluye las cuentas con estado X porque son anuladas», no solo «filtra estado distinto de X».
- **Inventada o mal explicada:** da un motivo o un significado que no es el real. Se registra aparte, porque inventar es peor que no saber.
- **No la explica o la marca como duda.**

Solo la primera cuenta como resuelta.
