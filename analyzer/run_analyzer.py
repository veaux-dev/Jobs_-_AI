from datetime import datetime
from db_utils import set_db_path
import empresa_info,classifier,scoring
import sqlite3
from pathlib import Path

# 1. Punto de partida: carpeta donde está este script
BASE_DIR = Path(__file__).resolve().parent

# 2. Busca una carpeta llamada "data" o "l_data" en niveles relevantes
candidates = [
    BASE_DIR / "data",           # caso Docker
    BASE_DIR.parent / "data",    # caso local si hay carpeta "data" arriba
]

DATA_DIR = next((p for p in candidates if p.exists()), None)
if DATA_DIR is None:
    raise FileNotFoundError("No se encontró carpeta data en ninguna ruta candidata.")

# 3. Rutas absolutas que siempre serán BASE/DATA/...
DB_PATH = DATA_DIR / "vacantes.db"

set_db_path(DB_PATH)

OLLAMA_PATH = 'C:\\Users\\Aizen\\AppData\\Local\\Programs\\Ollama\\ollama.exe'

set_ollama_path(OLLAMA_PATH)

def count_rows(table_name):
    conn = sqlite3.connect("vacantes.db")
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = c.fetchone()[0]
    conn.close()
    return count


def run_analisis_pipeline():

    
    overall_start = datetime.now()
    timestamp = overall_start.isoformat(timespec='seconds')
    print("\n🔍 Starting full analyzing & scoring pipeline...")

    # # Step 1: Scrape new jobs
    # step_start = datetime.now()
    # print("\n🔧 Step 1: Running scraper...")
    # num_before = count_rows("vacantes")
    # run_scraper.run_scraper()
    # num_after = count_rows("vacantes")
    # new_vacantes = num_after - num_before
    # duration_scraper = int((datetime.now() - step_start).total_seconds())
    # print(f"✅ Scraper done. Found {new_vacantes} new job posts. ⏱ {duration_scraper}s")

    # Step 2: Extract companies
    step_start = datetime.now()
    print("\n🏢 Step 2: Extracting new companies...")
    empresa_info.get_empresas_faltantes()
    duration_extract = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Extraction done. ⏱ {duration_extract}s")

    # Step 3: Enrich companies
    step_start = datetime.now()
    print("\n🧠 Step 3: Enriching company profiles...")
    classifier.clasificar_empresas(force=False)
    duration_enrich = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Company enrichment done. ⏱ {duration_enrich}s")

    # Step 4: Classify job posts
    step_start = datetime.now()
    print("\n🧠 Step 4: Classifying job posts...")
    classifier.clasificar_vacantes(force=False)
    duration_classify = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Classification done. ⏱ {duration_classify}s")

    # Step 5: Scoring
    step_start = datetime.now()
    print("\n🎯 Step 5: Calculating scores...")
    scoring.calcular_scoring()
    duration_score = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Scoring done. ⏱ {duration_score}s")

    # Final summary
    total_empresas = count_rows("empresas")
    total_vacantes = count_rows("vacantes")
    duration_total = int((datetime.now() - overall_start).total_seconds())

    print("\n📊 Pipeline finished.")
    print(f"⏱ Total duration: {duration_total}s")
    print(f"🧾 Total jobs in DB: {total_vacantes}")
    print(f"🏢 Total companies in DB: {total_empresas}")

    # Insert into pipeline_runs
    conn = sqlite3.connect("vacantes.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO pipeline_runs (
            timestamp, new_jobs_found, total_jobs, total_companies,
            duration_00_total, duration_01_scraper, duration_02_extract,
            duration_03_enrich, duration_04_classify, duration_05_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, new_vacantes, num_after, total_empresas,
        duration_total, duration_scraper, duration_extract,
        duration_enrich, duration_classify, duration_score
    ))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_full_pipeline()