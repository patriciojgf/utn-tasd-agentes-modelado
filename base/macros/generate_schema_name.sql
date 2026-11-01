{# Hace que el esquema sea exactamente el indicado (bronze / silver / gold)
   en vez del comportamiento por defecto de dbt, que lo concatena con el
   esquema del target (quedaría "main_bronze"). #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
