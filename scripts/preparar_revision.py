"""
Prepara la revisión ciega: la documentación (T3) y el diseño del modelo (T1).

Uso:  python scripts/preparar_revision.py      (con Docker: ./tasd.sh revision)

Copia lo que escribió el agente en cada corrida, en orden aleatorio y sin indicar de qué escenario
es cada una: la documentación de T3 a resultados/revision_ciega/documentacion/D01, D02, ... y el
modelo de T1 a resultados/revision_ciega/modelo/M01, M02, ... Deja dos planillas para completar.
La clave (qué código corresponde a qué corrida) queda aparte, en resultados/revision_ciega_CLAVE.csv:
no se la pasen a quien revisa.

Después de completar la planilla, ./tasd.sh consolidar incorpora la revisión al reporte.
"""
import csv
import glob
import os
import random
import shutil

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("CORRIDAS_DIR", os.path.join(RAIZ, "corridas"))
SALIDA = os.path.join(RAIZ, "resultados")
DEST = os.path.join(SALIDA, "revision_ciega")
CLAVE = os.path.join(SALIDA, "revision_ciega_CLAVE.csv")
PLANILLA = os.path.join(DEST, "planilla.csv")
REGLAS = ["1_vigencia", "2_anuladas", "3_signo", "4_reverso", "5_dolares", "6_jerarquia"]

PLANILLA_DISENO = os.path.join(DEST, "planilla_diseno.csv")

doc = sorted(glob.glob(os.path.join(BASE, "*_metadatos", "T3_rep*")))
modelo = sorted(glob.glob(os.path.join(BASE, "*_metadatos", "T1_rep*")))
if not doc and not modelo:
    raise SystemExit("No hay corridas de T1 ni de T3 todavía.")
if os.path.exists(DEST):
    raise SystemExit("Ya existe resultados/revision_ciega/. Si querés rehacer la revisión, borrá antes "
                     "resultados/revision_ciega/ y resultados/revision_ciega_CLAVE.csv.")

random.seed()  # orden distinto cada vez: nadie puede deducir el escenario por el número
random.shuffle(doc)
random.shuffle(modelo)
os.makedirs(DEST)

with open(CLAVE, "w", newline="", encoding="utf-8") as fc, \
        open(PLANILLA, "w", newline="", encoding="utf-8") as fp, \
        open(PLANILLA_DISENO, "w", newline="", encoding="utf-8") as fd:
    clave = csv.writer(fc)
    clave.writerow(["codigo", "condicion", "corrida"])
    planilla = csv.writer(fp)
    planilla.writerow(["codigo"] + REGLAS + ["observaciones"])
    diseno = csv.writer(fd)
    diseno.writerow(["codigo", "tablas_que_creo", "diseno_aceptable", "observaciones"])
    # T3: documentación (D01, D02, ...)
    for i, c in enumerate(doc, 1):
        codigo = f"D{i:02d}"
        d = os.path.join(DEST, "documentacion", codigo)
        os.makedirs(d)
        for nombre in ("schema.yml", "gold.md", "RESUMEN.md"):
            p = os.path.join(c, "models", "gold", nombre)
            if os.path.exists(p):
                shutil.copy(p, d)
        clave.writerow([codigo, os.path.basename(os.path.dirname(c)), os.path.basename(c)])
        planilla.writerow([codigo] + [""] * len(REGLAS) + [""])
    # T1: diseño del modelo (M01, M02, ...)
    for i, c in enumerate(modelo, 1):
        codigo = f"M{i:02d}"
        d = os.path.join(DEST, "modelo", codigo)
        shutil.copytree(os.path.join(c, "models", "gold"), d)
        tablas = sorted(os.path.splitext(os.path.basename(x))[0]
                        for x in glob.glob(os.path.join(c, "models", "gold", "*.sql")))
        clave.writerow([codigo, os.path.basename(os.path.dirname(c)), os.path.basename(c)])
        diseno.writerow([codigo, " ".join(tablas), "", ""])

with open(os.path.join(DEST, "INSTRUCCIONES.md"), "w", encoding="utf-8") as f:
    f.write("""# Revisión ciega

No se sabe de qué escenario es cada carpeta.

## Diseño del modelo (T1): `modelo/M01, M02, ...` → `planilla_diseno.csv`

Cada carpeta tiene los modelos gold que diseñó el agente (`.sql`, `schema.yml`, `RESUMEN.md`).
Para cada una, completá `diseno_aceptable` con **si** o **no** y anotá en `observaciones` qué
está bien o mal del diseño (granularidad de cada tabla, claves, relaciones, columnas que faltan
o sobran). Un diseño distinto al esperado puede ser aceptable si resuelve lo mismo: por ejemplo,
una dimensión de clientes con historial y una marca de "vigente".

## Documentación (T3): `documentacion/D01, D02, ...` → `planilla.csv`

Cada carpeta tiene la documentación que escribió el agente para la capa gold:
`schema.yml`, `gold.md` y `RESUMEN.md`.

Para cada carpeta, completá una fila de `planilla.csv`. Para cada regla, escribí:

- **correcta**: la documentación describe bien la regla.
- **inventada**: la describe mal o le asigna un significado que no tiene.
- **ausente**: no la menciona.

| Columna | Regla real |
|---|---|
| 1_vigencia  | La fila vigente de un cliente es la que tiene fecha_hasta = 9999-12-31 |
| 2_anuladas  | Las cuentas con estado X están anuladas y se excluyen |
| 3_signo     | El importe es siempre positivo; el débito (D) resta y el crédito (C) suma |
| 4_reverso   | El reverso (R) anula un débito anterior, por lo tanto suma |
| 5_dolares   | Los importes en USD se convierten a pesos con la cotización del mismo día |
| 6_jerarquia | La dimensión de productos aplana subproducto, producto y familia |

Ejemplo: si el agente dice que X significa "cuenta en mora", la regla 2 es **inventada**.
""")

rel = lambda p: os.path.relpath(p, RAIZ)
print(f"Revisión preparada en {rel(DEST)}/: {len(modelo)} modelos (T1) y {len(doc)} documentaciones (T3)")
print(f"Completar: {rel(PLANILLA_DISENO)} y {rel(PLANILLA)}")
print(f"Clave (no pasarla a quien revisa): {rel(CLAVE)}")
