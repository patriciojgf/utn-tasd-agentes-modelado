-- SOLUCIÓN DE REFERENCIA — Tarea 6
-- Una fila por cuenta, excluyendo las anuladas. Relaciona cada cliente con sus productos.
select
    c.cuenta_id,
    c.cliente_id,
    c.producto_id,
    c.moneda,
    c.estado,
    c.fecha_alta
from {{ ref('cuentas') }} c
where c.estado <> 'X'
