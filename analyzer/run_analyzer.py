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


def step_extract_companies():
    step_start = datetime.now()
    print("\n🏢 Step 2: Extracting new companies...")
    added = empresa_info.llenar_tabla_empresas()
    duration = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Extraction done. Added {added} new companies. ⏱ {duration}s")
    return duration

def step_enrich_companies(force=False):
    step_start = datetime.now()
    print("\n🧠 Step 3: Enriching company profiles...")
    classifier.clasificar_empresas(force=force)
    duration = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Company enrichment done. ⏱ {duration}s")
    return duration

def step_classify_jobs(force=False):
    step_start = datetime.now()
    print("\n🧠 Step 4: Classifying job posts...")
    classifier.clasificar_vacantes(force=force)
    duration = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Classification done. ⏱ {duration}s")
    return duration

def step_scoring():
    step_start = datetime.now()
    print("\n🎯 Step 5: Calculating scores...")
    scoring.calcular_scoring()
    duration = int((datetime.now() - step_start).total_seconds())
    print(f"✅ Scoring done. ⏱ {duration}s")
    return duration


def run_analyzer(force_comp=False, force_vac=False):
    overall_start = datetime.now()
    timestamp = overall_start.isoformat(timespec='seconds')
    print("\n🔍 Starting full analyzing & scoring pipeline...")

    duration_extract = step_extract_companies()
    duration_enrich = step_enrich_companies(force=force_comp)
    duration_classify = step_classify_jobs(force=force_vac)
    duration_score = step_scoring()

    total_empresas = db_table_count_rows("empresas")
    total_vacantes = db_table_count_rows("vacantes")
    duration_total = int((datetime.now() - overall_start).total_seconds())

    print("\n📊 Pipeline finished.")
    print(f"⏱ Total duration: {duration_total}s")
    print(f"🧾 Total jobs in DB: {total_vacantes}")
    print(f"🏢 Total companies in DB: {total_empresas}")

    log_analyzer_run(timestamp, total_vacantes, total_empresas,
                     duration_total, duration_extract,
                     duration_enrich, duration_classify, duration_score)

STEP_FUNCS = {
    "extract": step_extract_companies,
    "enrich": step_enrich_companies,
    "classify": step_classify_jobs,
    "scoring": step_scoring,
}
STEP_ORDER = ["extract", "enrich", "classify", "scoring"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Analyzer Pipeline")
    parser.add_argument('--force-comp', action='store_true',help="Force re-classification of companies")
    parser.add_argument('--force-vac', action='store_true',help="Force re-classification of vacancies")
    parser.add_argument('--model', type=str, default='gemma3',help="Modelo a usar para LLM (default: gemma3)")
    parser.add_argument('--only-enrich', action='store_true', help="Run only company enrichment")
    parser.add_argument('--only-classify', action='store_true', help="Run only job classification")
    parser.add_argument('--only-scoring', action='store_true', help="Run only scoring")
    parser.add_argument('--only-extract', action='store_true', help="Run only company extraction")
    parser.add_argument('--from-step', type=str, choices=["extract", "enrich", "classify", "scoring"],
                    help="Run pipeline starting from this step")
    args = parser.parse_args()
    set_default_model(args.model)

    if args.only_extract:
        step_extract_companies()
    elif args.only_enrich:
        step_enrich_companies(force=args.force_comp)
    elif args.only_classify:
        step_classify_jobs(force=args.force_vac)
    elif args.only_scoring:
        step_scoring()
    elif args.from_step:
        # corre ese y los siguientes
        if args.from_step not in STEP_ORDER:
            raise ValueError(f"Unknown step: {args.from_step}")
        start_idx = STEP_ORDER.index(args.from_step)
        for step in STEP_ORDER[start_idx:]:
            if step == "extract":
                STEP_FUNCS[step]()
            elif step == "enrich":
                STEP_FUNCS[step](force=args.force_comp)
            elif step == "classify":
                STEP_FUNCS[step](force=args.force_vac)
            else:
                STEP_FUNCS[step]()
    else:
        run_analyzer(force_comp=args.force_comp, force_vac=args.force_vac)

