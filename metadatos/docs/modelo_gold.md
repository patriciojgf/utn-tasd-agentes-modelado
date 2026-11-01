# Especificación del modelo gold — Banco Ficticio S.A.

Qué espera el negocio de cada tabla de la capa gold.

## dim_cliente
- Exactamente **una fila por cliente**, con su situación **actual**.
- Columnas: identificador del cliente, nombre, documento, segmento comercial vigente y la
  sucursal (id, descripción y provincia).

## dim_producto
- Sirve para agrupar cuentas y movimientos por producto y por familia de productos.
- **Una fila por cada producto al que puede asociarse una cuenta**.
- Columnas: la descripción de ese producto y la de todos sus niveles superiores, en columnas
  separadas.

## fact_movimientos
- **Un registro por movimiento válido**.
- Columnas: fecha, cuenta, cliente, producto, tipo de movimiento, moneda, importe original y
  `importe_pesos`: el importe **con signo** (positivo si suma al saldo, negativo si resta)
  **expresado en pesos argentinos**.

## dim_cuenta
- Permite saber qué productos tiene cada cliente.
- **Una fila por cada cuenta válida**.
- Columnas: cuenta, cliente, producto, moneda, estado y fecha de alta.
