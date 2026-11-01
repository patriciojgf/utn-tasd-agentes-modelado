# Mutantes para evaluar los tests del agente (T2)

Cada carpeta es una versión de la solución de referencia con **una** regla de negocio rota a
propósito. `scripts/evaluar.py` reemplaza el modelo correspondiente en una copia de la corrida
de T2, ejecuta los tests que escribió el agente y se fija si alguno falla.

- Si algún test falla, el agente **cubrió** esa regla (sus tests detectan la violación).
- Si todos pasan, la regla quedó **sin cubrir**.

| Carpeta | Regla rota (Tabla 2 del informe) |
|---|---|
| 1_vigencia  | dim_cliente incluye todas las versiones del cliente, no solo la vigente |
| 2_anuladas  | fact_movimientos incluye movimientos de cuentas anuladas (X) |
| 3_signo     | los débitos quedan positivos |
| 4_reverso   | los reversos restan como si fueran débitos |
| 5_dolares   | los importes en USD no se convierten a pesos |
| 6_jerarquia | dim_producto no aplana la jerarquía (todas las filas, familia nula) |

Igual que la referencia, el agente nunca ve esta carpeta.
