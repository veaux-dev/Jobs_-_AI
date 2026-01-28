import os
import time
import random
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from typing import Optional

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import yaml
import zoneinfo

from db_vacantes import insert_vacantes, calculate_hash, set_db_path

# --- Configuración ---
BASE_DIR = Path(__file__).resolve().parent
candidates = [
    BASE_DIR / "data",           # caso Docker
    BASE_DIR.parent / "data",    # caso local si hay carpeta "data" arriba
]

DATA_DIR = next((p for p in candidates if p.exists()), None)
if DATA_DIR is None:
    raise FileNotFoundError("No se encontró carpeta data en ninguna ruta candidata.")

DB_PATH = DATA_DIR / "vacantes.db"
CONFIG_PATH = DATA_DIR / "config_scraper.yaml"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

print(f"[MVP] DATA_DIR={DATA_DIR}")
print(f"[MVP] DB_PATH={DB_PATH}")
print(f"[MVP] CONFIG_PATH={CONFIG_PATH}")
input("[MVP] Pause: confirma DB_PATH arriba y presiona Enter para continuar...")

set_db_path(str(DB_PATH))

roles = config["roles"]
functions = config["functions"]
locations = config["locations"]

LI_PAGES = int(os.getenv("LI_PAGES", config.get("li_pages", 2)))
LI_SLEEP_MIN = int(os.getenv("LI_SLEEP_MIN", "2"))
LI_SLEEP_MAX = int(os.getenv("LI_SLEEP_MAX", "5"))
REQUEST_TIMEOUT = int(os.getenv("LI_TIMEOUT", "20"))
FETCH_DETAIL = os.getenv("LI_FETCH_DETAIL", "1") not in {"0", "false", "False"}
DETAIL_SLEEP_MIN = int(os.getenv("LI_DETAIL_SLEEP_MIN", "1"))
DETAIL_SLEEP_MAX = int(os.getenv("LI_DETAIL_SLEEP_MAX", "3"))
WRITE_DB = os.getenv("LI_WRITE_DB", "0") in {"1", "true", "True"}

USER_AGENT = os.getenv(
    "LI_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)

MX = zoneinfo.ZoneInfo("America/Monterrey")


def _clean_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    # Remove query params for stable hash
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _parse_date(text: Optional[str], dt_attr: Optional[str]) -> Optional[date]:
    if dt_attr:
        try:
            return datetime.fromisoformat(dt_attr).date()
        except ValueError:
            return None
    if not text:
        return None
    return None


def clean_text(text: str) -> str:
    if not text:
        return ""
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
        "modalidad_trabajo": "remote"
        if (row.get("is_remote") is True or row.get("work_from_home_type") is True)
        else "not remote",
        "tipo_contrato": row.get("job_type"),
        "salario_estimado": f"{row.get('min_amount') or ''} to {row.get('max_amount') or ''} {row.get('currency') or ''} {row.get('interval') or ''}",
    }


def fetch_linkedin_public(search_term: str, location: str, pages: int = 2) -> list[dict]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results: list[dict] = []
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    for page in range(pages):
        start = page * 25
        params = {
            "keywords": search_term,
            "location": location,
            "start": start,
        }
        resp = session.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for li in soup.select("li"):
            card = li.select_one(".base-card")
            if not card:
                continue
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

            results.append(
                {
                    "site": "linkedin_public",
                    "job_url": job_url,
                    "title": title,
                    "company": company,
                    "location": loc,
                    "date_posted": _parse_date(dt_text, dt_attr),
                    "description": None,
                    "is_remote": None,
                    "work_from_home_type": None,
                    "job_type": None,
                    "min_amount": None,
                    "max_amount": None,
                    "currency": None,
                    "interval": None,
                }
            )

        sleep_s = random.randint(LI_SLEEP_MIN, LI_SLEEP_MAX)
        time.sleep(sleep_s)

    return results


def format_row(row: dict, qry_title: str, qry_loc: str) -> str:
    dt = row.get("date_posted")
    dt_str = dt.isoformat() if isinstance(dt, date) else ""
    desc = row.get("description") or ""
    desc = " ".join(desc.split())
    desc_preview_len = int(os.getenv("LI_DESC_PREVIEW_LEN", "0"))
    if desc_preview_len > 0:
        desc = desc[:desc_preview_len]
    else:
        desc = ""
    return (
        f"[MVP] {qry_title} | {qry_loc} | {row.get('title') or ''} | "
        f"{row.get('company') or ''} | {row.get('location') or ''} | "
        f"{dt_str} | {row.get('job_url') or ''} | DESC: {desc}"
    )


def fetch_job_detail_description(session: requests.Session, job_url: str) -> str:
    if not job_url:
        return ""
    try:
        resp = session.get(job_url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    # LinkedIn public job page description container
    desc_el = soup.select_one(".show-more-less-html__markup") or soup.select_one(
        ".description__text"
    )
    if not desc_el:
        return ""
    return desc_el.get_text(separator=" ", strip=True)


if __name__ == "__main__":
    start = datetime.now()
    print(f"\n[MVP] Started at {start.isoformat(sep=' ', timespec='seconds')}\n")

    loc_country = []
    for loc in locations:
        if "," in loc:
            country = loc.split(",")[-1].strip()
            loc_country.append((loc, country))
        else:
            loc_country.append((loc, loc))

    total_loops = len(roles) * len(functions) * len(loc_country)
    with tqdm(total=total_loops, desc="Scraping LinkedIn public") as pbar:
        for role in roles:
            for function in functions:
                for location, _ in loc_country:
                    qry_title = f"{role} {function}"
                    qry_loc = location

                    rows = fetch_linkedin_public(qry_title, location, pages=LI_PAGES)
                    if FETCH_DETAIL and rows:
                        session = requests.Session()
                        session.headers.update({"User-Agent": USER_AGENT})
                        for r in rows:
                            if not r.get("job_url"):
                                continue
                            r["description"] = fetch_job_detail_description(
                                session, r["job_url"]
                            )
                            time.sleep(random.randint(DETAIL_SLEEP_MIN, DETAIL_SLEEP_MAX))
                    count = 0
                    vacs = []
                    for r in rows:
                        if not r.get("job_url"):
                            continue
                        print(format_row(r, qry_title, qry_loc))
                        vacs.append(map_mvp_row(r, qry_title, qry_loc))
                        count += 1

                    if WRITE_DB and vacs:
                        inserted = insert_vacantes(vacs)
                        print(f"[MVP] DB insert: {inserted} new rows")

                    pbar.set_postfix(
                        {"role": role, "func": function, "loc": location, "jobs": count}
                    )

                    pbar.update(1)

    end = datetime.now()
    duration = int((end - start).total_seconds())

    print(f"\n[MVP] Finished at {end.isoformat(sep=' ', timespec='seconds')}")
    print(f"[MVP] Duration: {duration}s")
    print(f"[MVP] Done.\n")
