# Reglas de negocio de la capa silver — Banco Ficticio S.A.

Estas reglas complementan las descripciones de `models/silver/schema.yml`.

## Clientes
- La tabla `clientes` es un **histórico**: guarda una fila por cada período en que el cliente
  tuvo un segmento comercial. Un mismo `cliente_id` aparece varias veces.
- La fila **vigente** de un cliente es la que tiene `fecha_hasta = '9999-12-31'`.
- Cualquier dimensión "actual" de cliente debe tener exactamente una fila por `cliente_id`.

## Cuentas
- `estado = 'X'` significa **anulada**. Las cuentas anuladas se excluyen de todo: no cuentan
  como cuentas, y sus movimientos no se consideran.
- Los demás estados (A activa, B bloqueada, C cerrada) sí se consideran.
- Cada cuenta está asociada a un **subproducto** (nivel 3 de `productos`).

## Movimientos
- `importe_original` está siempre en positivo y en la moneda de la cuenta.
- El **signo** lo da `tipo`:
  - `D` débito → resta (importe negativo)
  - `C` crédito → suma (importe positivo)
  - `R` reverso → anula un débito anterior, por lo tanto **suma** (importe positivo)
- Para expresar un movimiento **en pesos**:
  - si `moneda = 'ARS'` → el importe queda igual;
  - si `moneda = 'USD'` → se multiplica por `tipos_cambio.valor` de la **misma fecha** y moneda.
- Todo movimiento tiene cotización disponible para su fecha (no hay huecos en `tipos_cambio`).

## Productos
- Jerarquía de 3 niveles en una tabla autorreferencial: familia (1) → producto (2) → subproducto (3).
- Una dimensión de producto útil para el negocio debe **aplanar** la jerarquía: una fila por
  subproducto con las descripciones de su producto y su familia.

## Tiempo
- El período de análisis es 2024-01-01 a 2025-12-31.
