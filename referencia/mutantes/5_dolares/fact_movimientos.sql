-- MUTANTE 5: no convierte dólares a pesos
select
    m.movimiento_id,
    m.fecha,
    m.cuenta_id,
    c.cliente_id,
    c.producto_id,
    m.tipo,
    m.moneda,
    m.importe_original,
    case m.tipo when 'D' then -1 else 1 end                          as signo,
    case m.tipo when 'D' then -1 else 1 end * m.importe_original     as importe_original_con_signo,
    1              as tipo_cambio,
    case m.tipo when 'D' then -1 else 1 end
        * m.importe_original
        * 1        as importe_pesos
from {{ ref('movimientos') }} m
join {{ ref('cuentas') }} c on c.cuenta_id = m.cuenta_id
left join {{ ref('tipos_cambio') }} tc on tc.fecha = m.fecha and tc.moneda = m.moneda
where c.estado <> 'X'
