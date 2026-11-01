"""
Junta los metricas.json de todas las corridas, clasifica cada etapa y arma el reporte.

Uso:  python scripts/consolidar.py      (con Docker: ./tasd.sh consolidar)
Salida:
  resultados/metricas_consolidadas.csv   una fila por corrida, todas las métricas
  resultados/reporte.md                  tablas para el informe
  resultados/reporte.html                lo mismo, para mostrar en clase

Clasificación de cada corrida (paso 12 de la guía; si el grupo acuerda otros criterios,
se cambian en la función clasificar()):
  T1 (modelo)   agente: compila, tests en verde, 6 reglas y estructura completa
                | ayuda: compila y 3-5 reglas, o le falta estructura | programador: no compila o 0-2 reglas
  T2 (tests)    agente: tests en verde y detectan 5-6 reglas | ayuda: 3-4 | programador: el resto
  T3 (doc.)     agente: 5-6 reglas correctas y ninguna inventada | ayuda: 3-4 correctas o una inventada
                | programador: el resto. Sale de la revisión manual (./tasd.sh revision).
  Si el agente modificó archivos prohibidos, "agente" baja a "ayuda".
"""
import csv
import glob
import html
import json
import os
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("CORRIDAS_DIR", os.path.join(RAIZ, "corridas"))
SALIDA = os.path.join(RAIZ, "resultados")
REVISION = os.path.join(SALIDA, "revision_ciega")

REGLAS = ["1_vigencia", "2_anuladas", "3_signo", "4_reverso", "5_dolares", "6_jerarquia"]
NOMBRE_REGLA = {
    "1_vigencia": "Fila vigente del cliente",
    "2_anuladas": "Cuentas anuladas excluidas",
    "3_signo": "Débito resta",
    "4_reverso": "Reverso suma",
    "5_dolares": "USD a pesos del día",
    "6_jerarquia": "Jerarquía aplanada",
}
NIVELES = ["agente", "ayuda", "programador", "pendiente"]
NOMBRE_NIVEL = {"agente": "La resuelve el agente", "ayuda": "La resuelve con ayuda",
                "programador": "Queda del lado del programador", "pendiente": "Revisión pendiente"}
CONDICIONES = ["sin_metadatos", "con_metadatos"]
TAREAS = {"T1": "Modelo: diseño y SQL", "T2": "Calidad: tests", "T3": "Documentación"}

archivos = sorted(glob.glob(os.path.join(BASE, "*_metadatos", "*", "metricas.json")))
if not archivos:
    raise SystemExit("No hay metricas.json. Evaluá antes alguna corrida (./tasd.sh evaluar ...).")


# ---------------------------------------------------------------- revisión manual (T1 diseño, T3 documentación)
def leer_revision():
    """Devuelve {(condicion, corrida): {regla: valor}} a partir de la planilla completada."""
    clave_p = os.path.join(SALIDA, "revision_ciega_CLAVE.csv")
    planilla_p = os.path.join(REVISION, "planilla.csv")
    if not (os.path.exists(clave_p) and os.path.exists(planilla_p)):
        return {}
    clave = {r["codigo"]: r for r in csv.DictReader(open(clave_p, encoding="utf-8"))}
    out = {}
    for r in csv.DictReader(open(planilla_p, encoding="utf-8")):
        c = clave.get(r.get("codigo", ""))
        vals = {k: (r.get(k) or "").strip().lower() for k in REGLAS}
        if c and all(vals.values()):
            out[(c["condicion"], c["corrida"])] = vals
    return out


def leer_revision_diseno():
    """Devuelve {(condicion, corrida): (diseño aceptable, observaciones)} de la planilla de T1."""
    clave_p = os.path.join(SALIDA, "revision_ciega_CLAVE.csv")
    planilla_p = os.path.join(REVISION, "planilla_diseno.csv")
    if not (os.path.exists(clave_p) and os.path.exists(planilla_p)):
        return {}
    clave = {r["codigo"]: r for r in csv.DictReader(open(clave_p, encoding="utf-8"))}
    out = {}
    for r in csv.DictReader(open(planilla_p, encoding="utf-8")):
        c = clave.get(r.get("codigo", ""))
        v = (r.get("diseno_aceptable") or "").strip().lower()
        if c and v:
            out[(c["condicion"], c["corrida"])] = (v.startswith("s"), (r.get("observaciones") or "").strip())
    return out


def clasificar(f):
    t, n = f["tarea"], f.get("reglas_ok", 0)
    if t == "T1":
        if not f.get("dbt_run_ok") or n <= 2:
            nivel = "programador"
        elif n == 6 and f.get("dbt_test_ok") and f.get("estructura_ok"):
            nivel = "agente"
        else:
            nivel = "ayuda"
    elif t == "T2":
        nivel = "programador" if not f.get("dbt_test_ok") or n <= 2 else "agente" if n >= 5 else "ayuda"
    elif t == "T3":
        if "doc_correctas" not in f:
            return "pendiente"
        c, i = f["doc_correctas"], f["doc_inventadas"]
        nivel = "agente" if c >= 5 and i == 0 else "ayuda" if (c >= 3 and i <= 1) else "programador"
    else:
        return "pendiente"
    if nivel == "agente" and not f.get("respeto_restricciones", True):
        nivel = "ayuda"
    return nivel


revision = leer_revision()
revision_diseno = leer_revision_diseno()
filas = []
for a in archivos:
    f = json.load(open(a, encoding="utf-8"))
    reglas = f.pop("reglas", None) or f.pop("trampas", {})
    for k, v in reglas.items():
        f["regla_" + k] = v
    f["_reglas"] = reglas
    if f["tarea"] == "T1" and (f["condicion"], f["corrida"]) in revision_diseno:
        f["diseno_aceptable"], f["diseno_observaciones"] = revision_diseno[(f["condicion"], f["corrida"])]
    if f["tarea"] == "T3" and (f["condicion"], f["corrida"]) in revision:
        vals = revision[(f["condicion"], f["corrida"])]
        f["doc_correctas"] = sum(1 for v in vals.values() if v.startswith("correct"))
        f["doc_inventadas"] = sum(1 for v in vals.values() if v.startswith("invent"))
        f["doc_ausentes"] = sum(1 for v in vals.values() if v.startswith("ausent"))
        f["_reglas"] = {k: v.startswith("correct") for k, v in vals.items()}
        f["reglas_ok"], f["reglas_total"] = f["doc_correctas"], len(REGLAS)
    f["nivel"] = clasificar(f)
    filas.append(f)

# ---------------------------------------------------------------- CSV
os.makedirs(SALIDA, exist_ok=True)
primeras = ["tarea", "condicion", "corrida", "nivel"]
columnas = primeras + sorted({k for f in filas for k in f if not k.startswith("_") and k not in primeras})
ruta_csv = os.path.join(SALIDA, "metricas_consolidadas.csv")
with open(ruta_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=columnas, extrasaction="ignore")
    w.writeheader()
    for f in filas:
        w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
                    for k, v in f.items() if not k.startswith("_")})

# ---------------------------------------------------------------- agregados
grupo = defaultdict(list)
for f in filas:
    grupo[(f["tarea"], f["condicion"])].append(f)


def pct(xs):
    return sum(1 for x in xs if x) / len(xs) if xs else None


def promedio(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return sum(xs) / len(xs) if xs else None


# Tabla A: nivel por tarea y condición
tabla_niveles = []
for t in sorted(TAREAS):
    for c in CONDICIONES:
        fs = grupo.get((t, c), [])
        if fs:
            cnt = Counter(f["nivel"] for f in fs)
            tabla_niveles.append((t, c, len(fs), cnt))

# Tabla B: reglas respetadas (T1), detectadas por los tests (T2) y bien documentadas (T3)
def reglas_por_condicion(tareas):
    res = {}
    for r in REGLAS:
        res[r] = {}
        for c in CONDICIONES:
            vals = [f["_reglas"][r] for f in filas
                    if f["tarea"] in tareas and f["condicion"] == c and r in f["_reglas"]]
            res[r][c] = (sum(1 for v in vals if v), len(vals))
    return res


tabla_modelo = reglas_por_condicion({"T1"})
tabla_tests = reglas_por_condicion({"T2"})
tabla_doc = reglas_por_condicion({"T3"})

# Tabla C: datos del agente
tabla_agente = []
for t in sorted(TAREAS):
    for c in CONDICIONES:
        fs = grupo.get((t, c), [])
        if fs:
            tabla_agente.append((t, c, promedio([f.get("duracion_segundos") for f in fs]),
                                 promedio([f.get("turnos") for f in fs]),
                                 promedio([f.get("costo_usd") for f in fs]),
                                 pct([f.get("dbt_run_ok") for f in fs]),
                                 pct([f.get("dbt_test_ok") for f in fs])))


def fmt(v, tipo=""):
    if v is None:
        return "–"
    if tipo == "%":
        return f"{v:.0%}"
    if tipo == "$":
        return f"{v:.2f}"
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def estructura(f):
    """Resumen de la estructura del modelo (solo T1) y de la revisión manual del diseño."""
    if f["tarea"] != "T1":
        return "–"
    txt = "completa" if f.get("estructura_ok") else "incompleta"
    if "diseno_aceptable" in f:
        txt += " · diseño " + ("aceptado" if f["diseno_aceptable"] else "observado")
    return txt


def cond_corta(c):
    return "sin" if c.startswith("sin") else "con"


# ---------------------------------------------------------------- Markdown
md = ["# Resultados del experimento", "",
      f"Corridas evaluadas: **{len(filas)}**.", "",
      "## Quién resuelve cada etapa", "",
      "| Tarea | Etapa | Metadatos | n | " + " | ".join(NOMBRE_NIVEL[n] for n in NIVELES) + " |",
      "|---|---|---|---|" + "---|" * len(NIVELES)]
for t, c, n, cnt in tabla_niveles:
    md.append(f"| {t} | {TAREAS[t]} | {cond_corta(c)} | {n} | " + " | ".join(str(cnt.get(x, 0)) for x in NIVELES) + " |")


def md_reglas(titulo, tabla, nota):
    filas_md = [f"## {titulo}", "", nota, "", "| Regla | Sin metadatos | Con metadatos |", "|---|---|---|"]
    hay = False
    for r in REGLAS:
        celdas = []
        for c in CONDICIONES:
            ok, tot = tabla[r][c]
            celdas.append(f"{ok}/{tot}" if tot else "–")
            hay = hay or tot > 0
        filas_md.append(f"| {NOMBRE_REGLA[r]} | " + " | ".join(celdas) + " |")
    return filas_md + [""] if hay else []


md += [""] + md_reglas("Reglas que respeta el modelo (T1)", tabla_modelo,
                       "Corridas que respetan la regla / corridas que la ponen a prueba.")
md += md_reglas("Reglas que detectan los tests del agente (T2)", tabla_tests,
                "Corridas cuyos tests fallan ante un modelo con esa regla rota / corridas de T2.")
md += md_reglas("Reglas bien documentadas (T3, revisión manual)", tabla_doc,
                "Corridas que describen la regla correctamente / corridas revisadas.")
md += ["## Datos del agente (promedios)", "",
       "| Tarea | Metadatos | Duración (s) | Turnos | Costo (USD) | Compila | Tests en verde |",
       "|---|---|---|---|---|---|---|"]
for t, c, d, tu, co, ro, to in tabla_agente:
    md.append(f"| {t} | {cond_corta(c)} | {fmt(d)} | {fmt(tu)} | {fmt(co, '$')} | {fmt(ro, '%')} | {fmt(to, '%')} |")
md += ["", "## Detalle por corrida", "",
       "| Tarea | Metadatos | Corrida | Compila | Tests | Reglas | Estructura | Doc. | Restricciones | Nivel |",
       "|---|---|---|---|---|---|---|---|---|---|"]
for f in sorted(filas, key=lambda f: (f["tarea"], f["condicion"], f["corrida"])):
    md.append(f"| {f['tarea']} | {cond_corta(f['condicion'])} | {f['corrida']} | "
              f"{'sí' if f.get('dbt_run_ok') else 'no'} | {'sí' if f.get('dbt_test_ok') else 'no'} | "
              f"{f.get('reglas_ok', 0)}/{f.get('reglas_total', 0)} | {estructura(f)} | {fmt(f.get('cobertura_documentacion'), '%')} | "
              f"{'ok' if f.get('respeto_restricciones', True) else 'modificó: ' + ', '.join(f.get('archivos_prohibidos_modificados', []))} | "
              f"{NOMBRE_NIVEL[f['nivel']]} |")
open(os.path.join(SALIDA, "reporte.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

# ---------------------------------------------------------------- HTML
e = html.escape


def barra(ok, tot, clase):
    if not tot:
        return '<td class="na">–</td>'
    p = ok / tot
    return (f'<td><div class="bar"><div class="fill {clase}" style="width:{p*100:.0f}%"></div></div>'
            f'<span class="num">{ok}/{tot}</span></td>')


def html_reglas(titulo, tabla, nota):
    if not any(tabla[r][c][1] for r in REGLAS for c in CONDICIONES):
        return ""
    out = [f"<h2>{e(titulo)}</h2><p class='nota'>{e(nota)}</p><table><thead><tr><th>Regla</th>"
           "<th>Sin metadatos</th><th>Con metadatos</th></tr></thead><tbody>"]
    for r in REGLAS:
        out.append(f"<tr><td>{e(NOMBRE_REGLA[r])}</td>{barra(*tabla[r]['sin_metadatos'], 'sin')}"
                   f"{barra(*tabla[r]['con_metadatos'], 'con')}</tr>")
    return "".join(out) + "</tbody></table>"


h = ["""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Resultados TASD</title><style>
:root{--bg:#fafaf9;--fg:#1c1917;--muted:#78716c;--line:#e7e5e4;--card:#fff;--sin:#dc6b4a;--con:#2f7d6d;
--agente:#2f7d6d;--ayuda:#d6a23a;--programador:#dc6b4a;--pendiente:#a8a29e}
@media (prefers-color-scheme:dark){:root{--bg:#1c1917;--fg:#f5f5f4;--muted:#a8a29e;--line:#44403c;--card:#292524}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px 16px}
main{max-width:960px;margin:0 auto}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 6px}
.nota{color:var(--muted);margin:0 0 10px;font-size:13px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:8px;
overflow:hidden;font-size:14px}th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}
th{font-weight:600;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.03em}
.bar{display:inline-block;width:120px;height:10px;background:var(--line);border-radius:5px;vertical-align:middle;
margin-right:8px;overflow:hidden}.fill{height:100%}.fill.sin{background:var(--sin)}.fill.con{background:var(--con)}
.num{font-variant-numeric:tabular-nums}.na{color:var(--muted)}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;color:#fff;font-size:12px;margin-right:4px}
.agente{background:var(--agente)}.ayuda{background:var(--ayuda)}.programador{background:var(--programador)}
.pendiente{background:var(--pendiente)}.wrap{overflow-x:auto}
</style></head><body><main>""",
     f"<h1>Resultados del experimento</h1><p class='nota'>{len(filas)} corridas evaluadas · "
     "IA agéntica aplicada al ciclo de modelado (TASD, K4053)</p>",
     "<h2>Quién resuelve cada etapa</h2><p class='nota'>Cantidad de corridas en cada nivel.</p>"
     "<div class='wrap'><table><thead><tr><th>Tarea</th><th>Etapa</th><th>Metadatos</th><th>Resultado</th></tr>"
     "</thead><tbody>"]
for t, c, n, cnt in tabla_niveles:
    pills = "".join(f"<span class='pill {x}'>{cnt[x]} · {e(NOMBRE_NIVEL[x])}</span>" for x in NIVELES if cnt.get(x))
    h.append(f"<tr><td>{t}</td><td>{e(TAREAS[t])}</td><td>{cond_corta(c)}</td><td>{pills}</td></tr>")
h.append("</tbody></table></div>")
h.append(html_reglas("Reglas que respeta el modelo (T1)", tabla_modelo,
                     "Corridas que respetan la regla, sobre las corridas que la ponen a prueba."))
h.append(html_reglas("Reglas que detectan los tests del agente (T2)", tabla_tests,
                     "Corridas cuyos tests fallan ante un modelo con esa regla rota a propósito."))
h.append(html_reglas("Reglas bien documentadas (T3, revisión manual)", tabla_doc,
                     "Corridas que describen la regla correctamente."))
h.append("<h2>Datos del agente</h2><p class='nota'>Promedios por tarea y condición.</p><div class='wrap'><table>"
         "<thead><tr><th>Tarea</th><th>Metadatos</th><th>Duración (s)</th><th>Turnos</th><th>Costo (USD)</th>"
         "<th>Compila</th><th>Tests en verde</th></tr></thead><tbody>")
for t, c, d, tu, co, ro, to in tabla_agente:
    h.append(f"<tr><td>{t}</td><td>{cond_corta(c)}</td><td>{fmt(d)}</td><td>{fmt(tu)}</td><td>{fmt(co, '$')}</td>"
             f"<td>{fmt(ro, '%')}</td><td>{fmt(to, '%')}</td></tr>")
h.append("</tbody></table></div><h2>Detalle por corrida</h2><div class='wrap'><table><thead><tr><th>Tarea</th>"
         "<th>Metadatos</th><th>Corrida</th><th>Compila</th><th>Tests</th><th>Reglas</th><th>Estructura</th><th>Doc.</th><th>Nivel</th>"
         "</tr></thead><tbody>")
for f in sorted(filas, key=lambda f: (f["tarea"], f["condicion"], f["corrida"])):
    aviso = "" if f.get("respeto_restricciones", True) else " ⚠ modificó archivos prohibidos"
    h.append(f"<tr><td>{f['tarea']}</td><td>{cond_corta(f['condicion'])}</td><td>{e(f['corrida'])}</td>"
             f"<td>{'sí' if f.get('dbt_run_ok') else 'no'}</td><td>{'sí' if f.get('dbt_test_ok') else 'no'}</td>"
             f"<td>{f.get('reglas_ok', 0)}/{f.get('reglas_total', 0)}</td>"
             f"<td>{e(estructura(f))}</td><td>{fmt(f.get('cobertura_documentacion'), '%')}</td>"
             f"<td><span class='pill {f['nivel']}'>{e(NOMBRE_NIVEL[f['nivel']])}</span>{e(aviso)}</td></tr>")
h.append("</tbody></table></div></main></body></html>")
open(os.path.join(SALIDA, "reporte.html"), "w", encoding="utf-8").write("\n".join(h))

# ---------------------------------------------------------------- consola
print("\n".join(md[:len(tabla_niveles) + 8]))
print("\nCSV:      resultados/metricas_consolidadas.csv")
print("Reporte:  resultados/reporte.md")
print("          resultados/reporte.html")
