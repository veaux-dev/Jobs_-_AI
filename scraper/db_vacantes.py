import sqlite3
import hashlib
from datetime import datetime
from urllib.parse import urlparse
import os

DB_PATH = None

def set_db_path(path: str):
    global DB_PATH
    DB_PATH = path

def _get_conn():
    if DB_PATH is None:
        raise RuntimeError("DB_PATH not set. Call set_db_path() first.")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    conn = _get_conn()
    cursor = conn.cursor()

        # Tabla de vacantes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vacantes (
            job_hash TEXT PRIMARY KEY,                -- Hash único basado en título, empresa, ubicación y link
            site_name TEXT,                           -- Plataforma (LinkedIn, Indeed, etc.)
            qry_title TEXT,                          -- Query original: título usado para búsqueda
            qry_loc TEXT,                            -- Query original: ubicación usada para búsqueda
            title TEXT,                              -- Título de la vacante
            company TEXT,                            -- Empresa que publica la vacante
            location TEXT,                           -- Ubicación indicada en la vacante
            date DATE,                               -- Fecha estructurada (formato fecha) de publicación
            date_text TEXT,                          -- Fecha en texto libre (ej. "3 días atrás")
            insights TEXT,                           -- JSON crudo de insights de LinkedIn (modalidad, aplicantes, etc.)
            link TEXT,                               -- Enlace directo a la vacante
            tags TEXT,                               -- Tags adicionales extraídas (futuro uso NLP)
            job_description TEXT,                    -- Descripción principal de la vacante (sin limpiar)
            full_text TEXT,                          -- Texto completo normalizado (para análisis NLP)
            scraped_at DATE,                         -- Fecha en que se hizo el scraping
            last_seen_on DATE,                       -- Fecha en que se vio la vacante por ultimo
            updated_at DATE,                         -- Fecha de última actualización manual
            status TEXT,                             -- Estado: active, closed, discarded, etc.
            processed_at DATE,                       -- Fecha en que fue procesada por IA
            last_reviewed DATE,                      -- Última fecha de revisión manual
            reviewed_flag INTEGER,                   -- Flag binario (0/1) si ya fue revisada
            modalidad_trabajo TEXT,                  -- Modalidad: remoto, híbrido, presencial
            tipo_contrato TEXT,                      -- Tipo de contrato si está disponible
            salario_estimado TEXT,                   -- Rango salarial estimado (si existe)
            applicants_count INTEGER,                -- Número de aplicantes según LinkedIn
            es_procurement INTEGER,                  -- Flag binario (0/1) si es relevante al área de Procurement
            es_fit_usuario INTEGER,                  -- Flag binario (0/1) si hace match con el perfil del usuario
            nivel_estimado TEXT,                      -- estimacion por IA del nivel de la vacante
            comentario_ai TEXT,                       -- Comentario generado por IA sobre la vacante
            score_total INTEGER,                     -- scoring de fit de la vacante
            categoria_fit TEXT                          -- fit intuido en funccion del score. 
        )
    """)

    # Tabla de información ejecutiva por empresa
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            company TEXT PRIMARY KEY,                -- Nombre de la empresa (clave única)
            resumen_empresa TEXT,                    -- Resumen ejecutivo de la empresa
            sector_empresa TEXT,                     -- Sector industrial de la empresa
            tamaño_empresa TEXT,                     -- Tamaño (Small, Medium, Large)
            presencia_mexico TEXT,                   -- Presencia confirmada en México (Sí, No, Parcial)
            glassdoor_score REAL,                    -- Puntaje Glassdoor (si está disponible)
            last_updated DATE                        -- Última fecha de actualización de esta info
        )
    """)

    conn.commit()
    conn.close()

def calculate_hash(link:str)->str:
    """Se genera un Hash por vacante que funge con el primary key de la base de datos. usamos el link del job para ello"""
    linknorm = normalize_link(link.strip())
    return hashlib.sha256(linknorm.encode()).hexdigest()

def insert_vacante(vac):
    NEW_TO_ACTIVE_DAYS = 5  # ajustable

    conn = _get_conn()

    cursor = conn.cursor()

    now = datetime.today().strftime("%Y-%m-%d")

    vac["link"] = normalize_link(vac.get("link"))
    vac["job_hash"] = calculate_hash(vac.get("link"))

    # Verifica si ya existe en base
    cursor.execute("SELECT 1 FROM vacantes WHERE job_hash = ?", (vac["job_hash"],))
    exists = cursor.fetchone()

    if exists:
        # Solo actualiza last_seen_on & Status if needed.

        # 1) Lee estado actual y primera vez visto
        cursor.execute("""
            SELECT scraped_at
            FROM vacantes
            WHERE job_hash = ?
        """, (vac["job_hash"],))
        
        row = cursor.fetchone()
        first_seen_date = parse_date(row[0]) if row and row[0] else None

        status="active" if (datetime.today().date()-first_seen_date).days >NEW_TO_ACTIVE_DAYS else "new"

        cursor.execute("""
            UPDATE vacantes
            SET last_seen_on = ?,
            status = ?
            WHERE job_hash = ?
        """, (now, status, vac["job_hash"]))

    else:
        # Inserta nueva vacante
        vac = {
            "scraped_at": now,
            "last_seen_on": now,
            "status": "new",
            "reviewed_flag": 0,
            **vac
        }

        cursor.execute("""
            INSERT INTO vacantes (
                job_hash, qry_title, qry_loc, title, company, location, date, date_text,
                insights, link, tags, job_description, full_text, scraped_at, last_seen_on, updated_at,
                status, processed_at, last_reviewed, reviewed_flag, modalidad_trabajo,
                tipo_contrato, salario_estimado, applicants_count, es_procurement,
                es_fit_usuario, nivel_estimado, comentario_ai,site_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
        """, (
            vac.get("job_hash"),
            vac.get("qry_title"),
            vac.get("qry_loc"),
            vac.get("title"),
            vac.get("company"),
            vac.get("location"),
            parse_date(vac.get("date")),
            vac.get("date_text"),
            vac.get("insights"),
            vac.get("link"),
            vac.get("tags"),
            vac.get("job_description"),
            vac.get("full_text"),
            parse_date(vac.get("scraped_at")),
            parse_date(vac.get("last_seen_on")),
            parse_date(vac.get("updated_at")),
            vac.get("status"),
            parse_date(vac.get("processed_at")),
            parse_date(vac.get("last_reviewed")),
            vac.get("reviewed_flag", 0),
            vac.get("modalidad_trabajo"),
            vac.get("tipo_contrato"),
            vac.get("salario_estimado"),
            vac.get("applicants_count"),
            vac.get("es_procurement"),
            vac.get("es_fit_usuario"),
            vac.get("nivel_estimado"),
            vac.get("comentario_ai"),
            vac.get("site_name")
        ))

    conn.commit()
    conn.close()


def fetch_all_vacantes():
    conn = _get_conn()

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vacantes")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_vacante_by_id(vac_id):
    conn = _get_conn()

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vacantes WHERE job_hash = ?", (vac_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_vacante_status(vac_id, status):
    conn = _get_conn()

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE vacantes
        SET status = ?, updated_at = datetime('now')
        WHERE job_hash = ?
    """, (status, vac_id))
    conn.commit()
    conn.close()

def normalize_link(link: str) -> str:
    if not link:
        return ""
    link = link.strip()
    parsed = urlparse(link)
    host = parsed.netloc.lower()

    if "linkedin." in host:
        # ID va en el path -> corta query
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    # indeed / glassdoor y demás -> conserva query
    return link

def update_vacante_fields(vacante_id, cambios: dict):
    if not cambios:
        return
    with _get_conn() as conn:
        cur = conn.cursor()
        for campo, valor in cambios.items():
            cur.execute(f"UPDATE vacantes SET {campo} = ? WHERE job_hash = ?", (valor, vacante_id))
        conn.commit()

def finalize_scrape_run ():
    today_str = datetime.today().strftime("%Y-%m-%d")
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE vacantes
            SET status = 'closed'
            WHERE last_seen_on IS NOT NULL
            AND DATE(last_seen_on) < DATE(?)
            AND status IN ('new', 'active')
        """, (today_str,))
    conn.commit()

def empresa_ya_clasificada(nombre):
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM empresas WHERE company = ? AND last_updated IS NOT NULL", (nombre,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None