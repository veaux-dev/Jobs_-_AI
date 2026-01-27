from jobspy import scrape_jobs
import time, random, os, multiprocessing as mp
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime, date
from db_vacantes import insert_vacantes, calculate_hash, finalize_scrape_run, init_db, set_db_path,log_scraper_run
import zoneinfo
from pathlib import Path
import yaml

# --- Configuración ---

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
CONFIG_PATH = DATA_DIR / "config_scraper.yaml"

MX = zoneinfo.ZoneInfo("America/Monterrey")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

print(f"[SCRAPER] DATA_DIR={DATA_DIR}")
print(f"[SCRAPER] DB_PATH={DB_PATH}")
print(f"[SCRAPER] CONFIG_PATH={CONFIG_PATH}")

set_db_path(DB_PATH)

roles = config["roles"]
functions = config["functions"]
locations = config["locations"]

SCRAPE_TIMEOUT_S = int(os.getenv("SCRAPE_TIMEOUT_S", config.get("scrape_timeout_s", 900)))
MAX_RUN_SECONDS = int(os.getenv("MAX_RUN_SECONDS", config.get("max_run_seconds", 6 * 3600)))

def _scrape_worker(result_q, job_title, job_location, job_country, sites, linkedin_fetch_description):
    try:
        jobs = scrape_jobs(
            site_name=sites,
            search_term=job_title,
            google_search_term=f"{job_title} jobs near {job_location} since yesterday",
            location=job_location,
            results_wanted=50,
            hours_old=168,
            country_indeed=job_country,
            verbose=0,
            linkedin_fetch_description=linkedin_fetch_description,
            # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
        )
        result_q.put(("ok", jobs))
    except Exception as e:
        result_q.put(("err", f"{type(e).__name__}: {e}"))

def SCRAPYSCRAPY(job_title, job_location, job_country):
    sites = ["indeed", "linkedin", "zip_recruiter", "google", "glassdoor"]  # , "bdjobs", "naukri", "bayt"
    scrape_start = time.monotonic()
    result_q = mp.Queue()
    proc = mp.Process(
        target=_scrape_worker,
        args=(result_q, job_title, job_location, job_country, sites, True),
    )
    proc.start()
    proc.join(SCRAPE_TIMEOUT_S)

    if proc.is_alive():
        proc.terminate()
        proc.join(10)
        print(f"⚠️ Timeout en scrape_jobs({job_title} | {job_location}) after {SCRAPE_TIMEOUT_S}s")
        return pd.DataFrame()

    if not result_q.empty():
        status, payload = result_q.get()
        if status == "ok":
            scrape_elapsed = time.monotonic() - scrape_start
            print(f"[SCRAPER] scrape_jobs({job_title} | {job_location}) -> {len(payload)} rows in {scrape_elapsed:.2f}s")
            return payload
        print(f"⚠️ Error en {job_location}/{job_country}: {payload}")
        return pd.DataFrame()

    print(f"⚠️ Error en {job_location}/{job_country}: no result from worker")
    return pd.DataFrame()
    
# --- Helper: mapear output JobSpy → formato DB ---
def map_jobspy_row(row, qry_title, qry_loc):
    now_local = datetime.now(MX)
    desc = row.get("description")
    return {
        "job_hash": calculate_hash(row["job_url"]),
        "site_name": row["site"],
        "qry_title": qry_title,
        "qry_loc": qry_loc,
        "qry_date": now_local.date().isoformat(),
        "title": row.get("title"),
        "company": row.get("company"),
        "location": row.get("location"),
        "link": row.get("job_url"),
        "job_description": desc if isinstance(desc, str) else "[[NO DESCRIPTION RETURNED]]",
        "scraped_at": now_local.isoformat(),
        "last_seen_on": now_local.date().isoformat(),
        "date": row["date_posted"].isoformat() if isinstance(row.get("date_posted"), date) else None,
        "full_text" : clean_text(desc) if isinstance(desc, str) else "[[NO DESCRIPTION RETURNED]]",
        "modalidad_trabajo": "remote" if(row.get("is_remote") is True or row.get("work_from_home_type") is True) else "not remote",
        "tipo_contrato": row.get("job_type"),
        "salario_estimado": f"{row.get('min_amount') or ''} to {row.get('max_amount') or ''} {row.get('currency') or ''} {row.get('interval') or ''}",
        }

def clean_text(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return " ".join(soup.get_text().split())


if __name__ == "__main__":
    
    start = datetime.now()
    run_start_monotonic = time.monotonic()
    print(f"\n[SCRAPER] Started at {start.isoformat(sep=' ', timespec='seconds')}\n")

    all_jobs=[]
    
    total_loops=len(roles)*len(functions)*len(locations)

    # generar pares (location_completo, solo_pais)
    loc_country = []
    for loc in locations:
        if "," in loc:
            # split en la coma y agarrar lo último (país)
            country = loc.split(",")[-1].strip()
            loc_country.append((loc, country))
        else:
            # si ya es país, usar dos veces lo mismo
            loc_country.append((loc, loc))


    init_db()
    total_new_jobs=0

    stop_requested = False
    with tqdm(total=total_loops, desc="Scraping jobs") as pbar:
        for role in roles:
            for function in functions:
                for location,country in loc_country:
                    loop_start = time.monotonic()
                   
                    qry_title=f'{role} {function}'
                    qry_loc=f'{loc}'

                    total_elapsed = time.monotonic() - run_start_monotonic
                    if total_elapsed > MAX_RUN_SECONDS:
                        print(f"[SCRAPER] Max runtime reached ({MAX_RUN_SECONDS}s). Stopping early.")
                        stop_requested = True
                        break

                    jobs_found=SCRAPYSCRAPY(f'{role} {function}', location, country)

                    if not jobs_found.empty:
                        vacs = [map_jobspy_row(row, qry_title, qry_loc) for _, row in jobs_found.iterrows()]
                        new_this_batch = insert_vacantes(vacs)
                        total_new_jobs+=new_this_batch
                        pbar.set_postfix({
                            "role": role,
                            "func": function,
                            "loc": location,
                            "jobs": new_this_batch
                        })
                    else:
                        pbar.set_postfix({
                            "role": role,
                            "func": function,
                            "loc": location,
                            "jobs": 0
                    })

                    
                    all_jobs.append(jobs_found)
                    
                    sleep_s = random.randint(3, 6)
                    time.sleep(sleep_s)
                    loop_elapsed = time.monotonic() - loop_start
                    print(f"[SCRAPER] loop {qry_title} | {location} finished in {loop_elapsed:.2f}s (sleep {sleep_s}s)")
                    pbar.update(1)
                if stop_requested:
                    break
            if stop_requested:
                break

    finalize_scrape_run()

    end = datetime.now()
    duration = int((end - start).total_seconds())

    log_scraper_run(start, total_new_jobs, duration)

    print(f"\n[SCRAPER] Finished at {end.isoformat(sep=' ', timespec='seconds')}")
    print(f"[SCRAPER] Duration: {duration}s")
    print(f"[SCRAPER] New jobs this run: {total_new_jobs}\n")
