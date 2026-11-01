"""
Muestra lado a lado la evaluación de dos corridas (para la demo en clase).

Uso:  python scripts/comparar.py <corrida_sin> <corrida_con>
      (con Docker: ./tasd.sh demo-comparar)
Requiere que las dos estén evaluadas (metricas.json).
"""
import json
import os
import sys

if len(sys.argv) != 3:
    raise SystemExit(__doc__)

ms = []
for c in sys.argv[1:]:
    p = os.path.join(c, "metricas.json")
    if not os.path.exists(p):
        raise SystemExit(f"Falta evaluar {c}")
    ms.append(json.load(open(p, encoding="utf-8")))

a, b = ms
etiqueta = lambda m: "SIN metadatos" if m["condicion"].startswith("sin") else "CON metadatos"
si_no = lambda v: "sí" if v else "no"


def fila(nombre, va, vb):
    print(f"  {nombre:34s} {str(va):>16s}   {str(vb):>16s}")


print()
fila(f"{a['tarea']}", etiqueta(a), etiqueta(b))
print("  " + "-" * 70)
fila("¿Compila? (dbt run)", si_no(a.get("dbt_run_ok")), si_no(b.get("dbt_run_ok")))
fila("¿Pasa sus propios tests?", si_no(a.get("dbt_test_ok")), si_no(b.get("dbt_test_ok")))
fila("Filas (agente / referencia)", f"{a.get('filas_agente')}/{a.get('filas_referencia')}",
     f"{b.get('filas_agente')}/{b.get('filas_referencia')}")
if "suma_importe_pesos_agente" in a or "suma_importe_pesos_agente" in b:
    fmt = lambda v: f"{v:,.0f}" if isinstance(v, (int, float)) else str(v)
    fila("Suma en pesos", fmt(a.get("suma_importe_pesos_agente")), fmt(b.get("suma_importe_pesos_agente")))
    fila("Suma correcta (referencia)", fmt(a.get("suma_importe_pesos_referencia")),
         fmt(b.get("suma_importe_pesos_referencia")))
print("  " + "-" * 70)
print("  Reglas de negocio:")
for r in sorted(set(a.get("reglas", {})) | set(b.get("reglas", {}))):
    va, vb = a.get("reglas", {}).get(r), b.get("reglas", {}).get(r)
    fila("    " + r, "OK" if va else "FALLÓ", "OK" if vb else "FALLÓ")
print("  " + "-" * 70)
fila("Reglas respetadas", f"{a.get('reglas_ok')}/{a.get('reglas_total')}",
     f"{b.get('reglas_ok')}/{b.get('reglas_total')}")
if a.get("duracion_segundos") or b.get("duracion_segundos"):
    fila("Duración (s)", a.get("duracion_segundos"), b.get("duracion_segundos"))
print()
