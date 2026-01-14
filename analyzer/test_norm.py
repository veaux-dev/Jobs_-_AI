import sqlite3
from empresa_info import normalize_company_name
from db_utils import _get_conn, set_db_path
from pathlib import Path
import csv

UNC_PATH = Path(r"\\TRUENAS\Job_Scraper\vacantes.db")

set_db_path(UNC_PATH)

conn = _get_conn()

cursor = conn.cursor()

cursor.execute('''SELECT DISTINCT company FROM vacantes''')

rows=cursor.fetchall()
conn.close

# aplanar la lista (quita los paréntesis de cada tupla)
out_list = sorted((r[0] for r in rows if r[0]), key=lambda x: x.lower())

# --- generar pares (original, normalizado) ---
pairs = []
cnl = []
for c in out_list:
    cn = normalize_company_name(c)
    pairs.append((c, cn))
    if cn not in cnl:
        cnl.append(cn)

print(f"\nTotal empresas distintas original: {len(out_list)}")
print(f"Total empresas distintas normalizada: {len(cnl)}")

# --- exportar a CSV ---
csv_path = Path(r"D:\Data\Projects\Python\Jobspy\analyzer\empresas_norm.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["empresa_original", "empresa_normalizada"])
    writer.writerows(pairs)

print(f"\n✅ CSV generado en: {csv_path}")
print(f"Total filas exportadas: {len(pairs)}")