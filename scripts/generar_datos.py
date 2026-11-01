"""
Genera los CSV de la capa bronze (tablas 'legacy' con nombres crípticos)
y los guarda en base/seeds/.

Uso:  python scripts/generar_datos.py
Requiere: solo la biblioteca estándar de Python (no hace falta instalar nada).

La semilla fija (SEED) hace que siempre se generen exactamente los mismos datos,
así el experimento es reproducible.
"""
import csv
import os
import random
from datetime import date, timedelta

SEED = 20260919
random.seed(SEED)

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "..", "base", "seeds")
os.makedirs(DESTINO, exist_ok=True)

FECHA_INI = date(2024, 1, 1)
FECHA_FIN = date(2025, 12, 31)
DIAS = (FECHA_FIN - FECHA_INI).days + 1

N_CLIENTES = 400
N_CUENTAS = 700
N_MOVIMIENTOS = 20000


def yyyymmdd(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def escribir(nombre, columnas, filas):
    ruta = os.path.join(DESTINO, nombre + ".csv")
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        w.writerows(filas)
    print(f"  {nombre}.csv  ->  {len(filas)} filas")


# ---------------------------------------------------------------- T_SUC
sucursales = [
    (1, "CASA CENTRAL", "CABA"),
    (2, "SUC. LA PLATA", "BUENOS AIRES"),
    (3, "SUC. ROSARIO", "SANTA FE"),
    (4, "SUC. CORDOBA", "CORDOBA"),
    (5, "SUC. MENDOZA", "MENDOZA"),
]
escribir("T_SUC", ["SUC_ID", "SUC_DESC", "SUC_PROV"], sucursales)

# ---------------------------------------------------------------- T_PRD
# Jerarquía de 3 niveles guardada en una sola tabla autorreferencial.
# PRD_NIV: 1 = familia, 2 = producto, 3 = subproducto.
productos = [
    (100, "CUENTAS", None, 1),
    (110, "CAJA DE AHORRO", 100, 2),
    (111, "CA PESOS", 110, 3),
    (112, "CA DOLARES", 110, 3),
    (120, "CUENTA CORRIENTE", 100, 2),
    (121, "CC PESOS", 120, 3),
    (200, "TARJETAS", None, 1),
    (210, "TARJETA DE CREDITO", 200, 2),
    (211, "TC VISA", 210, 3),
    (212, "TC MASTER", 210, 3),
    (300, "PRESTAMOS", None, 1),
    (310, "PRESTAMO PERSONAL", 300, 2),
    (311, "PP PESOS", 310, 3),
]
escribir("T_PRD", ["PRD_ID", "PRD_DESC", "PRD_PADRE", "PRD_NIV"], productos)
SUBPRODUCTOS = [p for p in productos if p[3] == 3]
MONEDA_POR_SUBPRODUCTO = {111: "ARS", 112: "USD", 121: "ARS", 211: "ARS", 212: "ARS", 311: "ARS"}

# ---------------------------------------------------------------- T_TIPCAMB
# Un tipo de cambio por día y moneda extranjera. ARS no aparece (vale 1).
tipcamb = []
valor = 820.0
for i in range(DIAS):
    d = FECHA_INI + timedelta(days=i)
    valor = valor * (1 + random.uniform(-0.004, 0.006))
    tipcamb.append((yyyymmdd(d), "USD", round(valor, 2)))
escribir("T_TIPCAMB", ["TC_FEC", "TC_MON", "TC_VAL"], tipcamb)

# ---------------------------------------------------------------- T_CLI
# Trampa: varias filas por cliente (histórico de segmento).
# La fila vigente es la que tiene CLI_FEC_HASTA = 99991231.
SEGMENTOS = ["MAS", "PRE", "BLK"]
NOMBRES = ["GARCIA", "PEREZ", "LOPEZ", "MARTINEZ", "GOMEZ", "DIAZ", "FERNANDEZ",
           "RODRIGUEZ", "SANCHEZ", "ROMERO", "SOSA", "TORRES", "ALVAREZ", "RUIZ"]
clientes = []
for cli_id in range(1, N_CLIENTES + 1):
    nombre = f"{random.choice(NOMBRES)} {random.choice(NOMBRES)}"
    doc = random.randint(10_000_000, 45_000_000)
    suc = random.choice(sucursales)[0]
    n_versiones = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
    desde = date(2020, 1, 1) + timedelta(days=random.randint(0, 1200))
    seg = random.choice(SEGMENTOS)
    for v in range(n_versiones):
        es_ultima = v == n_versiones - 1
        if es_ultima:
            hasta = 99991231
        else:
            fin = desde + timedelta(days=random.randint(90, 500))
            hasta = yyyymmdd(fin)
        clientes.append((cli_id, nombre, doc, seg, yyyymmdd(desde), hasta, suc))
        if not es_ultima:
            desde = fin + timedelta(days=1)
            seg = random.choice([s for s in SEGMENTOS if s != seg])
escribir("T_CLI", ["CLI_ID", "CLI_NOM", "CLI_DOC", "CLI_COD_SEG",
                   "CLI_FEC_DESDE", "CLI_FEC_HASTA", "CLI_SUC"], clientes)

# ---------------------------------------------------------------- T_CTA
# Trampa: CTA_EST = 'X' es "anulada" y NO debe contar en nada.
cuentas = []
for cta_id in range(1, N_CUENTAS + 1):
    cli = random.randint(1, N_CLIENTES)
    sub = random.choice(SUBPRODUCTOS)
    prd_id = sub[0]
    mon = MONEDA_POR_SUBPRODUCTO[prd_id]
    est = random.choices(["A", "B", "C", "X"], weights=[70, 12, 10, 8])[0]
    alta = date(2022, 1, 1) + timedelta(days=random.randint(0, 900))
    cuentas.append((cta_id, cli, prd_id, mon, est, yyyymmdd(alta)))
escribir("T_CTA", ["CTA_ID", "CLI_ID", "PRD_ID", "CTA_MON", "CTA_EST", "CTA_FEC_ALTA"], cuentas)

# ---------------------------------------------------------------- T_MOV
# Trampas:
#  - MOV_IMP_ORI siempre positivo; el signo lo da MOV_TIP: D=débito (resta),
#    C=crédito (suma), R=reverso (anula un débito anterior => suma).
#  - MOV_IMP_ORI está en la moneda de la cuenta (MOV_MON). Para pasar a pesos
#    hay que multiplicar por T_TIPCAMB del día (por fecha Y moneda).
#  - Hay movimientos sobre cuentas anuladas ('X'), que no deben contarse.
movimientos = []
mov_id = 0
for _ in range(N_MOVIMIENTOS):
    mov_id += 1
    cta = random.choice(cuentas)
    d = FECHA_INI + timedelta(days=random.randint(0, DIAS - 1))
    tip = random.choices(["D", "C", "R"], weights=[55, 40, 5])[0]
    if cta[3] == "USD":
        imp = round(random.uniform(10, 3000), 2)
    else:
        imp = round(random.uniform(500, 900000), 2)
    movimientos.append((mov_id, cta[0], yyyymmdd(d), tip, imp, cta[3]))
escribir("T_MOV", ["MOV_ID", "CTA_ID", "MOV_FEC", "MOV_TIP", "MOV_IMP_ORI", "MOV_MON"], movimientos)

print("\nListo. Seeds generados en", os.path.abspath(DESTINO))
