"""
Verifica el evaluador sin gastar uso del agente.

Uso:  python scripts/autotest.py      (con Docker: ./tasd.sh autotest)

Arma corridas en una carpeta temporal, les pone resultados simulados (la solución de referencia,
una solución ingenua y dos juegos de tests) y comprueba que evaluar.py dé lo esperado.
Si todo da bien, el evaluador distingue un modelo que respeta las reglas de uno que no.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(RAIZ, "referencia", "models", "gold")
TMP = tempfile.mkdtemp(prefix="tasd_autotest_")
ENV = dict(os.environ, CORRIDAS_DIR=TMP)

INGENUO_T3 = """
select m.movimiento_id, m.fecha, m.cuenta_id, c.cliente_id, c.producto_id, m.tipo, m.moneda,
       m.importe_original, m.importe_original as importe_pesos
from {{ ref('movimientos') }} m
join {{ ref('cuentas') }} c on c.cuenta_id = m.cuenta_id
"""

TESTS_COMPLETOS = {
    "anuladas.sql": """select f.* from {{ ref('fact_movimientos') }} f
join {{ ref('cuentas') }} c on c.cuenta_id = f.cuenta_id where c.estado = 'X'""",
    "signo.sql": "select * from {{ ref('fact_movimientos') }} where tipo = 'D' and importe_pesos >= 0",
    "reverso.sql": "select * from {{ ref('fact_movimientos') }} where tipo = 'R' and importe_pesos <= 0",
    "dolares.sql": """select f.* from {{ ref('fact_movimientos') }} f
join {{ ref('tipos_cambio') }} t on t.fecha = f.fecha and t.moneda = f.moneda
where f.moneda = 'USD' and abs(abs(f.importe_pesos) - f.importe_original * t.valor) > 0.01""",
}

REGLAS = ["1_vigencia", "2_anuladas", "3_signo", "4_reverso", "5_dolares", "6_jerarquia"]
CASOS = [
    # (descripción, condición, tarea, rep, preparar, reglas esperadas, estructura esperada)
    ("T1 con el modelo de referencia", "sin", "T1", 1, "modelo:referencia", {r: True for r in REGLAS}, True),
    ("T1 con el mismo modelo y otros nombres de tabla", "sin", "T1", 2, "modelo:renombrado",
     {r: True for r in REGLAS}, True),
    ("T1 con un modelo que ignora las reglas", "sin", "T1", 3, "modelo:ingenuo",
     {"1_vigencia": False, "2_anuladas": False, "3_signo": False, "4_reverso": True,
      "5_dolares": False, "6_jerarquia": False}, True),
    ("T2 con los tests básicos de la referencia", "con", "T2", 1, "tests:basicos",
     {"1_vigencia": True, "2_anuladas": False, "3_signo": False, "4_reverso": False,
      "5_dolares": False, "6_jerarquia": True}, None),
    ("T2 con tests que cubren todas las reglas", "con", "T2", 2, "tests:completos",
     {r: True for r in REGLAS}, None),
]

RENOMBRES = {"dim_cliente": "clientes_actuales", "dim_producto": "productos_dim",
             "dim_cuenta": "cuentas_dim", "fact_movimientos": "hechos_mov"}
MUTANTES = os.path.join(RAIZ, "referencia", "mutantes")


def correr(cmd, **kw):
    r = subprocess.run(cmd, cwd=RAIZ, env=ENV, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"Falló: {' '.join(cmd)}")
    return r.stdout


fallas = 0
try:
    for desc, cond, tarea, rep, prep, esperado, estructura in CASOS:
        print(f"- {desc} ...", flush=True)
        correr(["bash", "scripts/nueva_corrida.sh", cond, tarea, str(rep)])
        d = os.path.join(TMP, f"{cond}_metadatos", f"{tarea}_rep{rep}")
        gold = os.path.join(d, "models", "gold")
        if prep == "modelo:referencia":
            for nombre in RENOMBRES:
                shutil.copy(os.path.join(REF, nombre + ".sql"), gold)
            shutil.copy(os.path.join(REF, "schema.yml"), gold)
        elif prep == "modelo:renombrado":
            for nombre, nuevo in RENOMBRES.items():
                shutil.copy(os.path.join(REF, nombre + ".sql"), os.path.join(gold, nuevo + ".sql"))
        elif prep == "modelo:ingenuo":
            shutil.copy(os.path.join(MUTANTES, "1_vigencia", "dim_cliente.sql"), gold)
            shutil.copy(os.path.join(MUTANTES, "6_jerarquia", "dim_producto.sql"), gold)
            open(os.path.join(gold, "fact_movimientos.sql"), "w").write(INGENUO_T3)
        elif prep.startswith("tests:"):
            shutil.copy(os.path.join(REF, "schema.yml"), gold)
            if prep == "tests:completos":
                os.makedirs(os.path.join(d, "tests"), exist_ok=True)
                for nombre, sql in TESTS_COMPLETOS.items():
                    open(os.path.join(d, "tests", nombre), "w").write(sql)
        correr([sys.executable, "scripts/evaluar.py", d])
        m = json.load(open(os.path.join(d, "metricas.json")))
        obtenido = m.get("reglas", {})
        bien = obtenido == esperado and m.get("dbt_run_ok") and m.get("respeto_restricciones") \
            and (estructura is None or m.get("estructura_ok") == estructura)
        fallas += 0 if bien else 1
        print(f"    {'OK ' if bien else 'MAL'}  reglas {m.get('reglas_ok')}/{m.get('reglas_total')}"
              f"  (compila: {m.get('dbt_run_ok')}, tests: {m.get('dbt_test_ok')})")
        if not bien:
            print(f"    esperado: {esperado}\n    obtenido: {obtenido}")
            print(f"    roles: {m.get('roles')}  estructura: {m.get('estructura')}")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print()
if fallas:
    raise SystemExit(f"{fallas} caso(s) no dieron lo esperado. Revisar antes de correr el experimento.")
print("Autotest OK: el evaluador distingue modelos y tests correctos de incorrectos.")
