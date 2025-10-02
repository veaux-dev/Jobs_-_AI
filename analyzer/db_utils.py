''' 
Este modulo tiene como proposito el manejo de lecturas y escrituras a la base de datos SQL

ASUME QUE LA DB YA EXISTE CON TODAS SUS TABLAS Y COLUMNAS ... ESTA LA GENERA EL SCRAPER

'''

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


def insert_or_update_empresa(empresa):
    conn = _get_conn()

    cursor = conn.cursor()

    def parse_date(value):
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None

    cursor.execute("""
        INSERT INTO empresas (
            company, resumen_empresa, sector_empresa, tamaño_empresa,
            presencia_mexico, glassdoor_score, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company) DO UPDATE SET
            resumen_empresa = excluded.resumen_empresa,
            sector_empresa = excluded.sector_empresa,
            tamaño_empresa = excluded.tamaño_empresa,
            presencia_mexico = excluded.presencia_mexico,
            glassdoor_score = excluded.glassdoor_score,
            last_updated = excluded.last_updated
    """, (
        empresa.get("company"),
        empresa.get("resumen_empresa"),
        empresa.get("sector_empresa"),
        empresa.get("tamaño_empresa"),
        empresa.get("presencia_mexico"),
        empresa.get("glassdoor_score"),
        parse_date(empresa.get("last_updated"))
    ))

    conn.commit()
    conn.close()