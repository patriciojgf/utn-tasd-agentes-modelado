# Pedido: script que genere datos sintéticos de un banco ficticio

## Contexto

Estoy armando una prueba para un trabajo de la facultad. Un agente de IA va a recibir estas tablas
y tiene que construir un modelo dimensional (dos dimensiones y una tabla de hechos) sin conocer las
reglas de negocio. Algunas de esas reglas están "escondidas" en los datos a propósito: el agente
solo puede aplicarlas bien si alguien se las explica.

Por eso necesito datos que cumplan reglas exactas, que parezcan de un sistema bancario viejo
(nombres de columnas crípticos, códigos sin explicación) y que **no dejen pistas** sobre esas reglas.

## Qué tenés que entregar

Un único script en **Python 3, usando solo la biblioteca estándar** (sin numpy, pandas ni nada que
haya que instalar), que:

- Use una semilla fija (`SEED`), de modo que cada vez que se corra genere exactamente los mismos datos.
- Escriba 6 archivos CSV en la carpeta `../base/seeds/` relativa a la ubicación del script
  (el script va a estar en `scripts/`).
- Use los nombres de archivo y de columnas **exactamente** como están abajo, con fila de encabezado,
  separador coma, codificación UTF-8 y valor vacío para los nulos.
- Al final corra las validaciones de la última sección e imprima el resultado de cada una.

## Tablas

Las fechas se guardan siempre como **enteros con formato AAAAMMDD** (por ejemplo `20240315`).

### T_SUC (sucursales): fija, copiala tal cual

```
SUC_ID,SUC_DESC,SUC_PROV
1,CASA CENTRAL,CABA
2,SUC. LA PLATA,BUENOS AIRES
3,SUC. ROSARIO,SANTA FE
4,SUC. CORDOBA,CORDOBA
5,SUC. MENDOZA,MENDOZA
```

### T_PRD (productos): fija, copiala tal cual

Es una jerarquía de 3 niveles en una sola tabla: `PRD_NIV` 1 es familia, 2 es producto y 3 es
subproducto. `PRD_PADRE` apunta al nivel superior.

```
PRD_ID,PRD_DESC,PRD_PADRE,PRD_NIV
100,CUENTAS,,1
110,CAJA DE AHORRO,100,2
111,CA PESOS,110,3
112,CA DOLARES,110,3
120,CUENTA CORRIENTE,100,2
121,CC PESOS,120,3
200,TARJETAS,,1
210,TARJETA DE CREDITO,200,2
211,TC VISA,210,3
212,TC MASTER,210,3
300,PRESTAMOS,,1
310,PRESTAMO PERSONAL,300,2
311,PP PESOS,310,3
```

### T_TIPCAMB (tipo de cambio): una fila por día

Columnas: `TC_FEC, TC_MON, TC_VAL`

- Una fila por cada día desde 2024-01-01 hasta 2025-12-31, sin huecos, siempre con `TC_MON = USD`.
- `TC_VAL` es la cotización del dólar en pesos, con 2 decimales, entre 800 y 1600, variando día a
  día de forma gradual (paseo aleatorio, no saltos bruscos).
- No hay filas para ARS.

### T_CLI (clientes): con histórico

Columnas: `CLI_ID, CLI_NOM, CLI_DOC, CLI_COD_SEG, CLI_FEC_DESDE, CLI_FEC_HASTA, CLI_SUC`

- 400 clientes distintos (`CLI_ID` de 1 a 400).
- Cada cliente tiene entre 1 y 3 filas (aproximadamente 60 % con 1, 30 % con 2 y 10 % con 3).
  Cada fila es una versión del cliente en un período.
- `CLI_NOM`: dos apellidos en mayúsculas (por ejemplo `GARCIA LOPEZ`). `CLI_DOC`: número de 8 dígitos.
  `CLI_SUC`: un `SUC_ID` válido. Estos tres valores no cambian entre versiones del mismo cliente.
- `CLI_COD_SEG` es uno de `MAS`, `PRE`, `BLK`, y **cambia** entre una versión y la siguiente.
- Los períodos de un mismo cliente son consecutivos y no se superponen: cada `CLI_FEC_DESDE` es el día
  siguiente al `CLI_FEC_HASTA` de la versión anterior. La primera versión empieza entre 2020 y 2023.

### T_CTA (cuentas)

Columnas: `CTA_ID, CLI_ID, PRD_ID, CTA_MON, CTA_EST, CTA_FEC_ALTA`

- 700 cuentas (`CTA_ID` de 1 a 700), cada una de un `CLI_ID` existente.
- `PRD_ID` es siempre un subproducto (nivel 3): 111, 112, 121, 211, 212 o 311.
- `CTA_MON` es `USD` solo para el producto 112; para todos los demás es `ARS`.
- `CTA_EST` es uno de `A`, `B`, `C`, `X` (aproximadamente 70 %, 12 %, 10 % y 8 %).
- `CTA_FEC_ALTA` entre 2022-01-01 y 2024-06-30.

### T_MOV (movimientos)

Columnas: `MOV_ID, CTA_ID, MOV_FEC, MOV_TIP, MOV_IMP_ORI, MOV_MON`

- 20.000 movimientos (`MOV_ID` de 1 a 20000), cada uno de un `CTA_ID` existente.
- `MOV_FEC` entre 2024-01-01 y 2025-12-31, y nunca anterior al `CTA_FEC_ALTA` de su cuenta.
- `MOV_TIP` es uno de `D`, `C`, `R` (aproximadamente 55 %, 40 % y 5 %).
- `MOV_IMP_ORI` es **siempre positivo**, con 2 decimales, en la moneda de la cuenta:
  entre 10 y 3.000 si es USD, entre 500 y 900.000 si es ARS.
- `MOV_MON` es igual al `CTA_MON` de la cuenta.

## Reglas de negocio que los datos tienen que respetar

Estas son las reglas que el agente va a tener que descubrir. Los datos tienen que ser coherentes con
ellas, pero **ninguna puede quedar explícita** en nombres de columnas, valores o estructura.

1. La versión vigente de un cliente es la que tiene `CLI_FEC_HASTA = 99991231`. Cada cliente tiene
   exactamente una.
2. Las cuentas con `CTA_EST = 'X'` están anuladas y no deben contarse en nada. `A`, `B` y `C` son
   estados válidos.
3. El importe siempre es positivo; el signo lo da el tipo: `D` (débito) resta y `C` (crédito) suma.
4. `R` es un reverso: anula un débito anterior, por lo tanto **suma**.
5. Los importes en USD se pasan a pesos multiplicando por el `TC_VAL` del **mismo día**.
6. La jerarquía de productos se aplana en tres columnas: subproducto, producto y familia.

## Cómo no dejar pistas

- No agregues columnas ni tablas que no estén en la lista.
- No uses valores descriptivos (nada de `ANULADA`, `REVERSO`, `VIGENTE`): solo los códigos indicados.
- Las cuentas `X` tienen que parecerse a las demás: cantidad de movimientos, importes, fechas y
  productos con la misma distribución. Tienen movimientos como cualquier otra cuenta.
- Los movimientos `R` tienen que parecerse a los `D` en importes y fechas. No hay ninguna columna
  que indique qué débito anulan.
- Los IDs no pueden revelar nada: por ejemplo, las cuentas `X` no pueden estar todas al final.
- El script puede tener comentarios, pero los CSV no pueden tener ningún texto explicativo.

## Validaciones que el script tiene que imprimir al final

1. Cantidad de filas de cada tabla.
2. Cada cliente tiene exactamente una fila con `CLI_FEC_HASTA = 99991231`.
3. Ningún cliente tiene períodos superpuestos ni con huecos.
4. El segmento cambia entre versiones consecutivas del mismo cliente.
5. Todas las claves foráneas existen (`CLI_SUC`, `CLI_ID` en cuentas, `PRD_ID`, `CTA_ID` en movimientos).
6. Todas las cuentas apuntan a un producto de nivel 3, y `CTA_MON` es USD solo para el producto 112.
7. Todos los importes son mayores a cero y `MOV_MON` coincide con la moneda de la cuenta.
8. Ningún movimiento es anterior al alta de su cuenta.
9. Todo movimiento en USD tiene una cotización para su fecha.
10. Porcentaje de cuentas por `CTA_EST` y de movimientos por `MOV_TIP`.
11. Promedio de movimientos por cuenta para cuentas `X` y para el resto (tienen que ser parecidos).
12. Cantidad de clientes vigentes, cantidad de movimientos sobre cuentas no anuladas y suma de
    importes en pesos con signo sobre cuentas no anuladas (estos números se usan para verificar la
    solución de referencia).
