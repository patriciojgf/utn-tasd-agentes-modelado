-- MUTANTE 6: no aplana la jerarquía (incluye todos los niveles; producto y familia quedan
-- nulos cuando no hay dos niveles por encima)
select
    sub.producto_id                   as producto_id,
    sub.descripcion                   as subproducto,
    prd.producto_id                   as producto_padre_id,
    prd.descripcion                   as producto,
    fam.producto_id                   as familia_id,
    fam.descripcion                   as familia
from {{ ref('productos') }} sub
left join {{ ref('productos') }} prd on prd.producto_id = sub.producto_padre_id
left join {{ ref('productos') }} fam on fam.producto_id = prd.producto_padre_id
