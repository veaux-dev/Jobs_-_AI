import os
import time
import random
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from typing import Optional, List

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import yaml
import zoneinfo
import argparse

from db_vacantes import insert_vacantes, calculate_hash, set_db_path, init_db

# --- Configuración ---
BASE_DIR = Path(__file__).resolve().parent
candidates = [
    BASE_DIR / "data",           # caso Docker
    BASE_DIR.parent / "data",    # caso local
]

DATA_DIR = next((p for p in candidates if p.exists()), None)
if DATA_DIR is None:
    raise FileNotFoundError("No se encontró carpeta data en ninguna ruta candidata.")

parser = argparse.ArgumentParser(description="Run the LinkedIn Public MVP job scraper.")
parser.add_argument("--profile", type=str, help="Profile name.")
parser.add_argument("--config", type=Path, help="Path to config.")
parser.add_argument("--db", type=Path, help="Path to DB.")
args = parser.parse_args()

if args.profile:
    CONFIG_PATH = DATA_DIR / f"config_{args.profile}.yaml"
    DB_PATH = DATA_DIR / f"vacantes_{args.profile}.db"
else:
    CONFIG_PATH = args.config if args.config else DATA_DIR / "config_scraper.yaml"
    DB_PATH = args.db if args.db else DATA_DIR / "vacantes.db"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

print(f"[MVP] DATA_DIR={DATA_DIR}")
print(f"[MVP] DB_PATH={DB_PATH}")
print(f"[MVP] CONFIG_PATH={CONFIG_PATH}")

set_db_path(str(DB_PATH))

roles = config["roles"]
functions = config["functions"]
locations = config["locations"]

LI_PAGES = int(os.getenv("LI_PAGES", config.get("li_pages", 2)))
LI_SLEEP_MIN = int(os.getenv("LI_SLEEP_MIN", "3"))
LI_SLEEP_MAX = int(os.getenv("LI_SLEEP_MAX", "7"))
REQUEST_TIMEOUT = int(os.getenv("LI_TIMEOUT", "30"))
FETCH_DETAIL = os.getenv("LI_FETCH_DETAIL", "1") not in {"0", "false", "False"}
DETAIL_SLEEP_MIN = int(os.getenv("LI_DETAIL_SLEEP_MIN", "2"))
DETAIL_SLEEP_MAX = int(os.getenv("LI_DETAIL_SLEEP_MAX", "5"))
WRITE_DB = os.getenv("LI_WRITE_DB", "1") in {"1", "true", "True"}

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0"
]

MX = zoneinfo.ZoneInfo("America/Monterrey")

def _get_random_ua():
    return random.choice(USER_AGENTS)

def safe_request(url, params=None, method="GET", session=None):
    """Realiza peticiones manejando el error 429 con esperas largas."""
    if not session:
        session = requests.Session()
    
    headers = {"User-Agent": _get_random_ua()}
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"   [HTTP] {method} {url} (Intento {attempt+1}/{max_retries})...", flush=True)
            if method == "GET":
                resp = session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            else:
                resp = session.post(url, json=params, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if resp.status_code == 429:
                wait_time = (attempt + 1) * 300 # 5, 10, 15 minutos
                print(f"\n🛑 [ERROR 429] LinkedIn detectó tráfico de bot. Entrando en enfriamiento: {wait_time/60} min...", flush=True)
                time.sleep(wait_time)
                continue
            
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                continue
            raise e
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(10)
    return None

def _clean_url(url: str) -> str:
    if not url: return ""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

def _parse_date(text: Optional[str], dt_attr: Optional[str]) -> Optional[date]:
    if dt_attr:
        try: return datetime.fromisoformat(dt_attr).date()
        except ValueError: return None
    return None

def clean_text(text: str) -> str:
    if not text: return ""
    soup = BeautifulSoup(text, "html.parser")
    return " ".join(soup.get_text().split())

def map_mvp_row(row: dict, qry_title: str, qry_loc: str) -> dict:
    now_local = datetime.now(MX)
    desc = row.get("description")
    posted = row.get("date_posted")
    return {
        "job_hash": calculate_hash(str(row.get("job_url") or "")),
        "site_name": row.get("site"),
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
        "date": posted.isoformat() if isinstance(posted, date) else None,
        "full_text": clean_text(desc) if isinstance(desc, str) else "[[NO DESCRIPTION RETURNED]]",
        "modalidad_trabajo": "remote" if (row.get("is_remote") is True or row.get("work_from_home_type") is True) else "not remote",
        "tipo_contrato": row.get("job_type"),
        "salario_estimado": f"{row.get('min_amount') or ''} to {row.get('max_amount') or ''} {row.get('currency') or ''} {row.get('interval') or ''}",
    }

def fetch_linkedin_public(search_term: str, location: str, pages: int = 2) -> list[dict]:
    results: list[dict] = []
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    for page in range(pages):
        start = page * 25
        params = {"keywords": search_term, "location": location, "start": start}
        
        resp = safe_request(base_url, params=params)
        if not resp: continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for li in soup.select("li"):
            card = li.select_one(".base-card")
            if not card: continue
            link_el = card.select_one("a.base-card__full-link")
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle a")
            location_el = card.select_one("span.job-search-card__location")
            time_el = card.select_one("time")

            href = str(link_el.get("href")) if link_el and link_el.get("href") else ""
            job_url = _clean_url(href) if href else ""
            title = title_el.get_text(strip=True) if title_el else None
            company = company_el.get_text(strip=True) if company_el else None
            loc = location_el.get_text(strip=True) if location_el else None
            dt_attr = str(time_el.get("datetime")) if time_el and time_el.get("datetime") else None
            dt_text = time_el.get_text(strip=True) if time_el else None

            results.append({
                "site": "linkedin_public", "job_url": job_url, "title": title, "company": company,
                "location": loc, "date_posted": _parse_date(dt_text, dt_attr), "description": None,
                "is_remote": None, "work_from_home_type": None, "job_type": None, "min_amount": None,
                "max_amount": None, "currency": None, "interval": None,
            })
        time.sleep(random.randint(LI_SLEEP_MIN, LI_SLEEP_MAX))
    return results

def fetch_job_detail_description(session: requests.Session, job_url: str) -> str:
    if not job_url: return ""
    resp = safe_request(job_url, session=session)
    if not resp: return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    desc_el = soup.select_one(".show-more-less-html__markup") or soup.select_one(".description__text")
    return desc_el.get_text(separator=" ", strip=True) if desc_el else ""

if __name__ == "__main__":
    start = datetime.now()
    print(f"\n[MVP] Started at {start.isoformat(sep=' ', timespec='seconds')}\n")
    init_db()

    loc_country = []
    for loc in locations:
        country = loc.split(",")[-1].strip() if "," in loc else loc
        loc_country.append((loc, country))

    total_inserted = 0
    total_loops = len(roles) * len(functions) * len(loc_country)
    
    with tqdm(total=total_loops, desc="Scraping LinkedIn public") as pbar:
        for role in roles:
            for function in functions:
                for location, _ in loc_country:
                    qry_title = f"{role} {function}".strip()
                    print(f"\n🚀 [MVP] Iniciando búsqueda: '{qry_title}' en '{location}'...", flush=True)
                    try:
                        rows = fetch_linkedin_public(qry_title, location, pages=LI_PAGES)
                        vacs = []
                        if FETCH_DETAIL and rows:
                            session = requests.Session()
                            for r in rows:
                                if r.get("job_url"):
                                    r["description"] = fetch_job_detail_description(session, r["job_url"])
                                    time.sleep(random.randint(DETAIL_SLEEP_MIN, DETAIL_SLEEP_MAX))
                                vacs.append(map_mvp_row(r, qry_title, location))
                        
                        if WRITE_DB and vacs:
                            inserted = insert_vacantes(vacs)
                            total_inserted += inserted
                    except Exception as e:
                        print(f"\n⚠️ Error en búsqueda '{qry_title}' en '{location}': {e}. Saltando...")
                    
                    pbar.update(1)

    with open("/tmp/new_jobs_count.txt", "w") as f:
        f.write(str(total_inserted))

    print(f"\n[MVP] Finished. Duration: {int((datetime.now() - start).total_seconds())}s. New jobs: {total_inserted}")
