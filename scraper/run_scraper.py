from jobspy import scrape_jobs
import time, random
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime, date
from db_vacantes import insert_vacante, calculate_hash, finalize_scrape_run, init_db, set_db_path,log_scraper_run
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

def SCRAPYSCRAPY(job_title, job_location, job_country):
    
    try:
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin", "zip_recruiter", "google","glassdoor", "bayt"], #, "bdjobs", "naukri"
            search_term=job_title,
            google_search_term=f"{job_title} jobs near {job_location} since yesterday",
            location=job_location,
            results_wanted=50,
            hours_old=168,
            country_indeed=job_country,
            verbose=0,
            linkedin_fetch_description=True # gets more info such as description, direct job url (slower)
            # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
        )
        return jobs
    except Exception as e:
            # 👇 solo loguea y sigue con el loop
            print(f"⚠️ Error en {job_location}/{job_country}: {e}")
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

    with tqdm(total=total_loops, desc="Scraping jobs") as pbar:
        for role in roles:
            for function in functions:
                for location,country in loc_country:
                   
                    qry_title=f'{role} {function}'
                    qry_loc=f'{loc}'

                    jobs_found=SCRAPYSCRAPY(f'{role} {function}', location, country)

                    if not jobs_found.empty:
                        new_this_batch = 0
                        for _, row in jobs_found.iterrows():
                            vac = map_jobspy_row(row, qry_title, qry_loc)
                            new_this_batch+=insert_vacante(vac)
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
                    
                    time.sleep(random.randint(3, 6))
                    pbar.update(1)

    finalize_scrape_run()

    end = datetime.now()
    duration = int((end - start).total_seconds())

    log_scraper_run(start, total_new_jobs, duration)

    print(f"\n[SCRAPER] Finished at {end.isoformat(sep=' ', timespec='seconds')}")
    print(f"[SCRAPER] Duration: {duration}s")
    print(f"[SCRAPER] New jobs this run: {total_new_jobs}/n")
