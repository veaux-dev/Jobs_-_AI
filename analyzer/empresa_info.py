"""
empresa_info.py

Este módulo tiene como propósito central gestionar la tabla `empresas` dentro de la base de datos `vacantes.db`.
Su responsabilidad es detectar automáticamente nuevas empresas a partir de la tabla `vacantes` y enriquecer la tabla `empresas`
con información ejecutiva clave, evitando redundancias y permitiendo análisis inteligentes posteriores.

Funciones clave:
- Identificación de empresas nuevas que aún no están registradas.
- Obtención de información ejecutiva de cada empresa (resumen, sector, tamaño, presencia en México, Glassdoor score, etc.).
- Inserción o actualización automática de registros en la tabla `empresas`.

Este módulo sigue el principio de separación de responsabilidades:
no realiza scraping ni clasificación —únicamente maneja el llenado estructurado y automatizado de información empresarial.

Autor: [VEAUX]
Fecha de creación: 2025-07-24
"""


# modules/empresa_info.py

from modules.db_vacantes import fetch_all_vacantes, insert_or_update_empresa
import sqlite3
import datetime

def get_empresas_faltantes():
    
    conn = sqlite3.connect("vacantes.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT company FROM vacantes
        WHERE company IS NOT NULL AND company NOT IN (
            SELECT company FROM empresas
        )
    """)
    empresas = [row[0] for row in cursor.fetchall()]
    conn.close()
    return empresas

def obtener_info_empresa(company_name):
    # Aquí puedes llamar una API o scraping inteligente
    # Por ahora usaremos datos simulados
    return {
        "company": company_name,
        "resumen_empresa": f"{company_name} is a global leader in XYZ.",
        "sector_empresa": "Technology",
        "tamaño_empresa": "Large",
        "presencia_mexico": "Sí",
        "glassdoor_score": 4.2,
        "last_updated": datetime.date.today().isoformat()
    }

def llenar_tabla_empresas():
    nuevas_empresas = get_empresas_faltantes()
    if nuevas_empresas:
        print(f"🔎 Detectadas {len(nuevas_empresas)} nuevas empresas.")
        if len(nuevas_empresas) <= 10:
            for e in nuevas_empresas:
                print(f" - {e}")
    else:
        print("✅ No hay empresas nuevas por registrar.")

    for company in nuevas_empresas:
        info = obtener_info_empresa(company)
        insert_or_update_empresa(info)
        print(f"✅ Empresa añadida: {company}")
