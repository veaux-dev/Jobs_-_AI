from datetime import datetime
from db_utils import set_db_path, log_analyzer_run,db_table_count_rows
from llm_wrapper import set_ollama_path,set_default_model
import empresa_info,classifier,scoring
from pathlib import Path
import argparse

# 1. Punto de partida: carpeta donde está este script
BASE_DIR = Path(__file__).resolve().parent

UNC_PATH = Path(r"\\TRUENAS\Job_Scraper\vacantes.db")

if UNC_PATH.exists():
    DB_PATH = UNC_PATH
else:
    # fallback a las rutas relativas de test/local
    candidates = [
        BASE_DIR / "data",
        BASE_DIR.parent / "data",
    ]
    DATA_DIR = next((p for p in candidates if p.exists()), None)
    if DATA_DIR is None:
        raise FileNotFoundError("No se encontró carpeta data en ninguna ruta candidata.")
    DB_PATH = DATA_DIR / "vacantes.db"

set_db_path(DB_PATH)
print(f"[DB] Using database: {DB_PATH}")


OLLAMA_PATH = 'ollama' #ollama is in PATH 'C:\\Users\\Aizen\\AppData\\Local\\Programs\\Ollama\\ollama.exe'

set_ollama_path(OLLAMA_PATH)

def run_analyzer(force_comp=False,force_vac=False):

    
    overall_start = datetime.now()
    timestamp = overall_start.isoformat(timespec='seconds')
    print("\n🔍 Starting full analyzing & scoring pipeline...")

    # Step 2: Extract companies
    step_start = datetime.now()
    print("\n🏢 Step 2: Extracting new companies...")
    added = empresa_info.llenar_tabla_empresas()
    duration_extract = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Extraction done. Added {added} new companies. ⏱ {duration_extract}s")

    # Step 3: Enrich companies
    step_start = datetime.now()
    print("\n🧠 Step 3: Enriching company profiles...")
    classifier.clasificar_empresas(force=force_comp)
    duration_enrich = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Company enrichment done. ⏱ {duration_enrich}s")

    # Step 4: Classify job posts
    step_start = datetime.now()
    print("\n🧠 Step 4: Classifying job posts...")
    classifier.clasificar_vacantes(force=force_vac)
    duration_classify = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Classification done. ⏱ {duration_classify}s")

    # Step 5: Scoring
    step_start = datetime.now()
    print("\n🎯 Step 5: Calculating scores...")
    scoring.calcular_scoring()
    duration_score = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Scoring done. ⏱ {duration_score}s")

    # Final summary
    total_empresas = db_table_count_rows("empresas")
    total_vacantes = db_table_count_rows("vacantes")
    duration_total = int((datetime.now() - overall_start).total_seconds())

    print("\n📊 Pipeline finished.")
    print(f"⏱ Total duration: {duration_total}s")
    print(f"🧾 Total jobs in DB: {total_vacantes}")
    print(f"🏢 Total companies in DB: {total_empresas}")

    # Log run
    log_analyzer_run(timestamp, total_vacantes, total_empresas,
                     duration_total, duration_extract,
                     duration_enrich, duration_classify, duration_score)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Analyzer Pipeline")
    parser.add_argument('--force-comp', action='store_true',help="Force re-classification of companies")
    parser.add_argument('--force-vac', action='store_true',help="Force re-classification of vacancies")
    parser.add_argument('--model', type=str, default='gemma3',help="Modelo a usar para LLM (default: gemma3)")
    args = parser.parse_args()
    set_default_model(args.model)

    run_analyzer(force_comp=args.force_comp,force_vac=args.force_vac)