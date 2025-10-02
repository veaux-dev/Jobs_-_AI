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
    """
    Abre una conexión SQLite hacia la base de datos configurada con `set_db_path`.

    Returns:
        sqlite3.Connection: Objeto de conexión activo.

    Notas:
        - Usar siempre `with _get_conn() as conn:` para garantizar cierre automático.
        - La ruta de la DB se establece con `set_db_path(path)` en el programa principal.
    """
    
    if DB_PATH is None:
        raise RuntimeError("DB_PATH not set. Call set_db_path() first.")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def insert_or_update_empresa(empresa):

    """
    Inserta una empresa nueva o actualiza una existente en la tabla `empresas`.

    Args:
        info (dict): Datos de la empresa. Claves esperadas:
            - company (str)
            - resumen_empresa (str | None)
            - sector_empresa (str | None)
            - tamaño_empresa (str | None)
            - presencia_mexico (str | None)
            - glassdoor_score (float | None)
            - last_updated (str, formato 'YYYY-MM-DD')

    Notas:
        - Usado en `empresa_info.py` para crear registros mínimos.
        - Usado en `classifier.py` para enriquecer empresas con LLM/websearch.
    """

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

def fetch_all_vacantes():

    """
    Recupera todas las vacantes de la tabla `vacantes`.

    Returns:
        list[dict]: Lista de registros, cada vacante representada como diccionario.

    Uso:
        - `classifier.clasificar_vacantes()` recorre este listado para aplicar la lógica de clasificación.
    """

    conn = _get_conn()

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vacantes")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_vacante_fields(vacante_id, cambios: dict):

    """
    Actualiza campos específicos de una vacante existente.

    Args:
        job_hash (str): Identificador único de la vacante (hash).
        cambios (dict): Pares campo:valor a actualizar en la fila correspondiente.

    Ejemplo:
        update_vacante_fields("abc123", {"es_procurement": 1, "nivel_estimado": "director"})

    Notas:
        - Usado en `classifier.py` para guardar resultados de LLM (procurement, fit, nivel).
    """

    if not cambios:
        return
    with _get_conn() as conn:
        cur = conn.cursor()
        for campo, valor in cambios.items():
            cur.execute(f"UPDATE vacantes SET {campo} = ? WHERE job_hash = ?", (valor, vacante_id))
        conn.commit()

def get_empresas_pendientes(force=False):
    """
    Devuelve una lista de empresas a enriquecer.
    - Si force=True: devuelve todas las empresas.
    - Si force=False: devuelve solo las que no tienen resumen.
    """
    with _get_conn() as conn:
        cur = conn.cursor()
        if force:
            cur.execute("SELECT company FROM empresas")
        else:
            cur.execute("SELECT company FROM empresas WHERE resumen_empresa IS NULL")
        return [row[0] for row in cur.fetchall()]