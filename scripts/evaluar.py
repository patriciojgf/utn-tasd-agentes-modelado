"""
Evalúa una corrida del agente contra la solución de referencia.

Uso:  python scripts/evaluar.py corridas/con_metadatos/T1_rep1
      (con Docker: ./tasd.sh evaluar con T1 1)
Salida: imprime las métricas y guarda <corrida>/metricas.json

Qué mide:
  - Si el proyecto compila (dbt run) y pasa sus propios tests (dbt test).
  - Si el agente tocó archivos que no debía (seeds, silver, configuración; en T2/T3, el SQL gold).
  - T1 (modelo): identifica cada tabla por su contenido (hecho, dimensión de clientes, de productos
    y de cuentas), controla las 6 reglas de negocio contra la referencia y la estructura del modelo
    estrella (que existan las tablas y que las claves del hecho estén en sus dimensiones).
  - T2 (tests): cuántas reglas detectan sus tests. Se ejecutan sobre versiones de la referencia
    con una regla rota a propósito (referencia/mutantes/): si algún test falla, la regla está cubierta.
  - T3 (documentación): cobertura. La corrección de lo que dice se revisa a mano (./tasd.sh revision).
  - Datos del agente: duración, turnos, tokens y costo (de _registros/).

Requiere que antes se haya construido la referencia (./tasd.sh referencia).
"""
import filecmp
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import duckdb
import yaml

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

CORRIDA = os.path.abspath(sys.argv[1])
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DB = os.path.join(RAIZ, "referencia", "proyecto", "banco.duckdb")
MUTANTES = os.path.join(RAIZ, "referencia", "mutantes")
AGENTE_DB = os.path.join(CORRIDA, "banco.duckdb")

nombre = os.path.basename(CORRIDA)                      # ej: T1_rep1
condicion = os.path.basename(os.path.dirname(CORRIDA))  # ej: con_metadatos
tarea = nombre.split("_")[0]
REGISTRO = os.path.join(os.path.dirname(os.path.dirname(CORRIDA)), "_registros", condicion, nombre)

if not os.path.isdir(CORRIDA):
    sys.exit(f"No existe la corrida: {CORRIDA}")
if not os.path.exists(REF_DB):
    sys.exit("No existe la referencia. Corré primero: ./tasd.sh referencia")

m = {"corrida": nombre, "condicion": condicion, "tarea": tarea}


# ---------------------------------------------------------------- helpers
def sh(cmd, cwd=CORRIDA):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def leer_schema_yml():
    ruta = os.path.join(CORRIDA, "models", "gold", "schema.yml")
    if not os.path.exists(ruta):
        return {"models": []}
    try:
        with open(ruta, encoding="utf-8") as f:
            return yaml.safe_load(f) or {"models": []}
    except yaml.YAMLError:
        return {"models": []}


def columnas(con, esquema, tabla):
    try:
        return [r[0] for r in con.execute(
            f"select column_name from information_schema.columns "
            f"where table_catalog='banco' and table_schema='{esquema}' and table_name='{tabla}'").fetchall()]
    except Exception:
        return []


def buscar_col(cols, *candidatos):
    """Devuelve la primera columna cuyo nombre contenga alguno de los candidatos."""
    for cand in candidatos:
        for c in cols:
            if cand in c.lower():
                return c
    return None


def escalar(con, sql):
    try:
        return con.execute(sql).fetchone()[0]
    except Exception as e:
        return f"ERROR: {str(e).splitlines()[0][:80]}"


def ok(v):
    return v is True


def hash_archivo(ruta):
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------- 1. ¿compila y corre?
rc, out = sh("dbt run --profiles-dir . --select gold --quiet")
m["dbt_run_ok"] = rc == 0
rc_t, out_t = sh("dbt test --profiles-dir . --select gold")
m["dbt_test_ok"] = rc_t == 0
mt = re.search(r"PASS=(\d+) WARN=(\d+) ERROR=(\d+) SKIP=(\d+)", out_t)
if mt:
    m["tests_pass"], m["tests_warn"], m["tests_error"], m["tests_skip"] = map(int, mt.groups())

# ---------------------------------------------------------------- 2. ¿tocó lo que no debía?
cambios = []
base = os.path.join(RAIZ, "base")
for rel in ["dbt_project.yml", "profiles.yml", "macros/generate_schema_name.sql"] + \
        [os.path.relpath(p, base) for p in glob.glob(os.path.join(base, "models", "silver", "*.sql"))] + \
        [os.path.relpath(p, base) for p in glob.glob(os.path.join(base, "seeds", "*.csv"))]:
    a = os.path.join(CORRIDA, rel)
    if not os.path.exists(a) or hash_archivo(a) != hash_archivo(os.path.join(base, rel)):
        cambios.append(rel)
yml_silver = os.path.join(RAIZ, "metadatos" if condicion == "con_metadatos" else "base",
                          "models", "silver", "schema.yml")
if not filecmp.cmp(yml_silver, os.path.join(CORRIDA, "models", "silver", "schema.yml"), shallow=False):
    cambios.append("models/silver/schema.yml")
if tarea in ("T2", "T3"):
    for nombre_m in ("dim_cliente", "dim_producto", "dim_cuenta", "fact_movimientos"):
        p = os.path.join(RAIZ, "referencia", "models", "gold", nombre_m + ".sql")
        a = os.path.join(CORRIDA, "models", "gold", os.path.basename(p))
        if not os.path.exists(a) or not filecmp.cmp(p, a, shallow=False):
            cambios.append("models/gold/" + os.path.basename(p))
m["archivos_prohibidos_modificados"] = cambios
m["respeto_restricciones"] = not cambios

# ---------------------------------------------------------------- 3. artefactos entregados
sch = leer_schema_yml()
modelos_yml = sch.get("models") or []
n_cols = sum(len(mod.get("columns") or []) for mod in modelos_yml)
n_cols_doc = sum(1 for mod in modelos_yml for c in (mod.get("columns") or [])
                 if str(c.get("description", "")).strip())
n_tests_genericos = sum(len(c.get("data_tests") or c.get("tests") or [])
                        for mod in modelos_yml for c in (mod.get("columns") or []))
n_tests_genericos += sum(len(mod.get("data_tests") or mod.get("tests") or []) for mod in modelos_yml)
n_tests_singulares = len(glob.glob(os.path.join(CORRIDA, "tests", "**", "*.sql"), recursive=True))
m.update({
    "columnas_en_yml": n_cols,
    "columnas_documentadas": n_cols_doc,
    "cobertura_documentacion": round(n_cols_doc / n_cols, 2) if n_cols else 0,
    "modelos_con_descripcion": sum(1 for mod in modelos_yml if str(mod.get("description", "")).strip()),
    "tests_genericos_declarados": n_tests_genericos,
    "tests_singulares_declarados": n_tests_singulares,
    "resumen_md_existe": os.path.exists(os.path.join(CORRIDA, "models", "gold", "RESUMEN.md")),
    "gold_md_existe": os.path.exists(os.path.join(CORRIDA, "models", "gold", "gold.md")),
})

# ---------------------------------------------------------------- 4. modelo del agente (T1)
# El agente elige los nombres y el diseño, así que cada tabla se identifica por su contenido.
reglas = {}
con = duckdb.connect(AGENTE_DB, read_only=True)
con.execute(f"attach '{REF_DB}' as ref (read_only)")


def tablas_gold():
    try:
        return [r[0] for r in con.execute(
            "select table_name from information_schema.tables "
            "where table_catalog='banco' and table_schema='gold'").fetchall()]
    except Exception:
        return []


def coincidencias(tabla, col, ref_tabla, ref_col):
    """Valores distintos de tabla.col que existen en ref_tabla.ref_col."""
    v = escalar(con, f'''select count(distinct a."{col}") from gold."{tabla}" a
        join {ref_tabla} r on cast(a."{col}" as varchar) = cast(r.{ref_col} as varchar)''')
    return v if isinstance(v, int) else 0


def distintos(tabla, col):
    v = escalar(con, f'select count(distinct "{col}") from gold."{tabla}"')
    return v if isinstance(v, int) else 0


def filas(tabla):
    v = escalar(con, f'select count(*) from gold."{tabla}"')
    return v if isinstance(v, int) else 0


def col_que_coincide(tabla, ref_tabla, ref_col, minimo):
    """Columna de la tabla con más valores que existen en ref_tabla.ref_col (al menos `minimo`)."""
    mejor, n_mejor = None, 0
    for c in columnas(con, "gold", tabla):
        n = coincidencias(tabla, c, ref_tabla, ref_col)
        if n > n_mejor and n == distintos(tabla, c):
            mejor, n_mejor = c, n
    return (mejor, n_mejor) if n_mejor >= minimo else (None, 0)


def col_con_valores(tabla, valores):
    """Columna cuyos valores distintos son un subconjunto no vacío de `valores`."""
    for c in columnas(con, "gold", tabla):
        try:
            vs = {r[0] for r in con.execute(f'select distinct cast("{c}" as varchar) from gold."{tabla}"').fetchall()}
        except Exception:
            continue
        vs.discard(None)
        if vs and vs <= valores:
            return c, vs
    return None, set()


if tarea == "T1":
    tablas = tablas_gold()
    m["tablas_gold"] = tablas
    roles = {}
    descripciones = {r[0] for r in con.execute("select descripcion from silver.productos").fetchall()}

    # Hecho: la tabla con más ids de movimiento
    mejor = (None, None, 0)
    for t in tablas:
        c, n = col_que_coincide(t, "silver.movimientos", "movimiento_id", 1000)
        if n > mejor[2]:
            mejor = (t, c, n)
    hecho, mid = mejor[0], mejor[1]
    if hecho:
        roles["hecho"] = hecho
    resto = [t for t in tablas if t != hecho]

    # Dimensión de clientes: tiene ids de cliente y una columna de segmento
    dcli = cid = seg = None
    for t in resto:
        s, _ = col_con_valores(t, {"MAS", "PRE", "BLK"})
        c, n = col_que_coincide(t, "silver.clientes", "cliente_id", 300)
        if s and c:
            dcli, cid, seg = t, c, s
            break
    if dcli:
        roles["dim_cliente"] = dcli

    # Dimensión de productos: tiene descripciones de productos
    dprd = None
    for t in resto:
        if t == dcli:
            continue
        c, _ = col_con_valores(t, descripciones)
        if c:
            dprd = t
            break
    if dprd:
        roles["dim_producto"] = dprd

    # Dimensión de cuentas (opcional): muchos ids de cuenta distintos y no es otra dimensión
    dcta = kid = None
    for t in resto:
        if t in (dcli, dprd):
            continue
        c, n = col_que_coincide(t, "silver.cuentas", "cuenta_id", 500)
        if c:
            dcta, kid = t, c
            break
    if dcta:
        roles["dim_cuenta"] = dcta
    m["roles"] = roles
    m["tablas_sin_identificar"] = [t for t in tablas if t not in roles.values()]

    # Regla 1: vigencia (una fila por cliente, con el segmento vigente)
    if dcli:
        n = filas(dcli)
        unica = distintos(dcli, cid) == n
        m["dim_cliente_filas"] = n
        coinciden = escalar(con, f'''select count(*) from gold."{dcli}" a
            join ref.gold.dim_cliente r on cast(r.cliente_id as varchar) = cast(a."{cid}" as varchar)
            where r.segmento = a."{seg}"''')
        reglas["1_vigencia"] = unica and n == 400 and coinciden == 400
        if not unica:
            m["nota_vigencia"] = "dim_cliente con varias filas por cliente (¿historial?): revisar a mano"
    else:
        reglas["1_vigencia"] = False

    # Regla 2: cuentas anuladas excluidas (del hecho y, si existe, de la dimensión de cuentas)
    if hecho:
        n_x = escalar(con, f'''select count(*) from gold."{hecho}" f
            join silver.movimientos s on cast(s.movimiento_id as varchar) = cast(f."{mid}" as varchar)
            join silver.cuentas c on c.cuenta_id = s.cuenta_id where c.estado = 'X' ''')
        m["hecho_filas"] = filas(hecho)
        m["movimientos_de_cuentas_anuladas"] = n_x
        anuladas = n_x == 0 and m["hecho_filas"] == 18772
        if dcta:
            cx = escalar(con, f'''select count(*) from gold."{dcta}" a
                join silver.cuentas c on cast(c.cuenta_id as varchar) = cast(a."{kid}" as varchar)
                where c.estado = 'X' ''')
            m["cuentas_anuladas_en_dim_cuenta"] = cx
            anuladas = anuladas and cx == 0
        reglas["2_anuladas"] = anuladas
    else:
        reglas["2_anuladas"] = False

    # Reglas 3, 4 y 5: importe con signo y en pesos, movimiento por movimiento
    imp = None
    if hecho:
        mejor_n, mejor_firmado = 0, -1
        for c in columnas(con, "gold", hecho):
            n = escalar(con, f'''select count(*) from gold."{hecho}" a
                join ref.gold.fact_movimientos r on cast(r.movimiento_id as varchar) = cast(a."{mid}" as varchar)
                where abs(abs(try_cast(a."{c}" as double)) - abs(r.importe_pesos)) <= 0.05''')
            # Desempate: si el agente guarda el importe en pesos en dos columnas (sin signo y con
            # signo), coinciden igual en valor absoluto; se elige la que además coincide con signo.
            n_firmado = escalar(con, f'''select count(*) from gold."{hecho}" a
                join ref.gold.fact_movimientos r on cast(r.movimiento_id as varchar) = cast(a."{mid}" as varchar)
                where abs(try_cast(a."{c}" as double) - r.importe_pesos) <= 0.05''')
            n_firmado = n_firmado if isinstance(n_firmado, int) else 0
            if isinstance(n, int) and (n > mejor_n or (n == mejor_n and n > 0 and n_firmado > mejor_firmado)):
                imp, mejor_n, mejor_firmado = c, n, n_firmado
        if mejor_n < 0.5 * max(m["hecho_filas"], 1):
            imp = None
    m["columna_importe_pesos"] = imp
    if imp:
        def contar(cond):
            return escalar(con, f'''select count(*) from gold."{hecho}" a
                join ref.gold.fact_movimientos r on cast(r.movimiento_id as varchar) = cast(a."{mid}" as varchar)
                where {cond}''')
        v = f'try_cast(a."{imp}" as double)'
        reglas["3_signo"] = contar(f"r.tipo = 'D' and not ({v} < 0)") == 0 and \
            contar(f"r.tipo = 'C' and not ({v} > 0)") == 0
        reglas["4_reverso"] = contar(f"r.tipo = 'R' and not ({v} > 0)") == 0
        reglas["5_dolares"] = contar(f"r.moneda = 'USD' and abs(abs({v}) - abs(r.importe_pesos)) > 0.05") == 0
        suma = escalar(con, f'select round(sum({v.replace("a.", "")}), 2) from gold."{hecho}"')
        m["suma_importe_pesos_agente"] = suma if isinstance(suma, str) or suma is None else float(suma)
        m["suma_importe_pesos_referencia"] = float(escalar(
            con, "select round(sum(importe_pesos), 2) from ref.gold.fact_movimientos"))
    else:
        for r in ("3_signo", "4_reverso", "5_dolares"):
            reglas[r] = False

    # Regla 6: jerarquía aplanada (una fila por subproducto, con la familia en una columna)
    if dprd:
        fam, _ = col_con_valores(dprd, {"CUENTAS", "TARJETAS", "PRESTAMOS"})
        m["dim_producto_filas"] = filas(dprd)
        reglas["6_jerarquia"] = bool(fam) and m["dim_producto_filas"] == 6
    else:
        reglas["6_jerarquia"] = False

    # Estructura: hecho y dimensiones presentes, y claves del hecho que existen en las dimensiones
    def integridad(dim, dim_ref_tabla, dim_ref_col, minimo, maximo):
        if not (hecho and dim):
            return False
        kd, _ = col_que_coincide(dim, dim_ref_tabla, dim_ref_col, 1)
        if not kd:
            return False
        for c in columnas(con, "gold", hecho):
            d = distintos(hecho, c)
            if not (minimo <= d <= maximo):
                continue
            faltan = escalar(con, f'''select count(*) from (select distinct "{c}" v from gold."{hecho}") f
                where f.v is not null and cast(f.v as varchar) not in
                (select cast("{kd}" as varchar) from gold."{dim}")''')
            if faltan == 0:
                return True
        return False
    m["estructura"] = {
        "tiene_hecho": bool(hecho),
        "tiene_dim_cliente": bool(dcli),
        "tiene_dim_producto": bool(dprd),
        "tiene_dim_cuenta": bool(dcta),
        "hecho_cliente_en_dim": integridad(dcli, "silver.clientes", "cliente_id", 300, 400),
        "hecho_producto_en_dim": integridad(dprd, "silver.productos", "producto_id", 3, 13),
    }
    e = m["estructura"]
    m["estructura_ok"] = all(e[k] for k in ("tiene_hecho", "tiene_dim_cliente", "tiene_dim_producto",
                                            "hecho_cliente_en_dim", "hecho_producto_en_dim"))
    if not tablas:
        m["dbt_run_ok"] = m["dbt_test_ok"] = False  # no entregó ningún modelo

con.close()
# Cualquier valor que no sea exactamente True (por ejemplo un error de SQL) cuenta como no respetada
reglas = {k: ok(v) for k, v in reglas.items()}


# ---------------------------------------------------------------- 5. tests del agente contra mutantes (T2)
def probar_mutante(carpeta):
    tmp = tempfile.mkdtemp(prefix="mutante_")
    proy = os.path.join(tmp, "proy")
    try:
        shutil.copytree(CORRIDA, proy, ignore=shutil.ignore_patterns("target", "logs", "metricas.json"))
        for sql in glob.glob(os.path.join(carpeta, "*.sql")):
            shutil.copy(sql, os.path.join(proy, "models", "gold", os.path.basename(sql)))
        rc, _ = sh("dbt run --profiles-dir . --select gold --quiet", cwd=proy)
        if rc != 0:
            return None  # el mutante no compiló: no se puede evaluar
        rc, _ = sh("dbt test --profiles-dir . --select gold --quiet", cwd=proy)
        return rc != 0   # algún test falló -> la regla está cubierta
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if tarea == "T2":
    if m["dbt_test_ok"]:
        for carpeta in sorted(glob.glob(os.path.join(MUTANTES, "*", ""))):
            regla = os.path.basename(os.path.dirname(carpeta))
            print(f"  probando los tests del agente contra el mutante {regla} ...", flush=True)
            reglas[regla] = ok(probar_mutante(carpeta))
    else:
        # Si los tests no pasan sobre el modelo correcto, no sirven para detectar errores.
        for carpeta in sorted(glob.glob(os.path.join(MUTANTES, "*", ""))):
            reglas[os.path.basename(os.path.dirname(carpeta))] = False

m["reglas"] = reglas
m["reglas_ok"] = sum(1 for v in reglas.values() if v)
m["reglas_total"] = len(reglas)
if tarea == "T3":
    m["revision_manual"] = "pendiente (./tasd.sh revision)"

# ---------------------------------------------------------------- 6. datos del agente
if os.path.isdir(REGISTRO):
    def leer(nombre_archivo):
        p = os.path.join(REGISTRO, nombre_archivo)
        return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None
    m["modelo"] = leer("modelo.txt")
    m["version_agente"] = leer("version_agente.txt") or leer("version_claude.txt")
    d = leer("duracion_segundos.txt")
    m["duracion_segundos"] = int(d) if d and d.isdigit() else None
    ruta_t = os.path.join(REGISTRO, "transcript.jsonl")
    resultado, herramientas = None, 0
    if os.path.exists(ruta_t):
        for linea in open(ruta_t, encoding="utf-8"):
            try:
                ev = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "assistant":
                herramientas += sum(1 for b in ev.get("message", {}).get("content", [])
                                    if isinstance(b, dict) and b.get("type") == "tool_use")
            if ev.get("type") == "tool_use":  # formato de Gemini CLI
                herramientas += 1
            if ev.get("type") == "result":
                resultado = ev
    m["llamadas_a_herramientas"] = herramientas
    if resultado and "stats" in resultado:
        # Gemini CLI: {"type": "result", "status": ..., "stats": {...}}; no informa costo.
        s = resultado.get("stats") or {}
        m["agente_termino_ok"] = resultado.get("status") == "success"
        m["turnos"] = None
        m["costo_usd"] = None
        m["tokens_entrada"] = s.get("input_tokens")
        m["tokens_salida"] = s.get("output_tokens")
    elif resultado:
        u = resultado.get("usage") or {}
        m["agente_termino_ok"] = not resultado.get("is_error", False)
        m["turnos"] = resultado.get("num_turns")
        m["costo_usd"] = resultado.get("total_cost_usd")
        m["tokens_entrada"] = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) \
            + (u.get("cache_creation_input_tokens") or 0)
        m["tokens_salida"] = u.get("output_tokens")
    elif herramientas:
        # Sesión interactiva (./tasd.sh abrir): no hay evento final; se suman los tokens por mensaje.
        m["modo"] = "interactivo"
        m["agente_termino_ok"] = None
        ent = sal = 0
        for linea in open(ruta_t, encoding="utf-8"):
            try:
                ev = json.loads(linea)
            except json.JSONDecodeError:
                continue
            u = (ev.get("message") or {}).get("usage") if ev.get("type") == "assistant" else None
            if u:
                ent += (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) \
                    + (u.get("cache_creation_input_tokens") or 0)
                sal += u.get("output_tokens") or 0
        m["tokens_entrada"], m["tokens_salida"] = ent, sal
    else:
        m["agente_termino_ok"] = False

# ---------------------------------------------------------------- 7. salida
with open(os.path.join(CORRIDA, "metricas.json"), "w", encoding="utf-8") as f:
    json.dump(m, f, indent=2, ensure_ascii=False, default=str)

print(f"\n=== {condicion} / {nombre} ===")
for k, v in m.items():
    if k == "reglas":
        print("  reglas de negocio:" if tarea != "T2" else "  reglas que detectan los tests del agente:")
        for rk, rv in v.items():
            print(f"     {'OK   ' if rv else 'FALLÓ'}  {rk}")
    else:
        print(f"  {k:32s} {v}")
print(f"\nGuardado en {os.path.relpath(os.path.join(CORRIDA, 'metricas.json'), RAIZ)}")
