-- MUTANTE 3: los débitos quedan positivos
select
    m.movimiento_id,
    m.fecha,
    m.cuenta_id,
    c.cliente_id,
    c.producto_id,
    m.tipo,
    m.moneda,
    m.importe_original,
    1                          as signo,
    1 * m.importe_original     as importe_original_con_signo,
    case when m.moneda = 'ARS' then 1 else tc.valor end              as tipo_cambio,
    1
        * m.importe_original
        * case when m.moneda = 'ARS' then 1 else tc.valor end        as importe_pesos
from {{ ref('movimientos') }} m
join {{ ref('cuentas') }} c on c.cuenta_id = m.cuenta_id
left join {{ ref('tipos_cambio') }} tc on tc.fecha = m.fecha and tc.moneda = m.moneda
where c.estado <> 'X'
