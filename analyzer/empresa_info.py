"""
empresa_info.py

Este módulo tiene como propósito central gestionar la tabla `empresas` dentro de la base de datos `vacantes.db`.
Su responsabilidad actual es detectar automáticamente nuevas empresas a partir de la tabla `vacantes`
e insertarlas en la tabla `empresas` con un registro mínimo (nombre y fecha de detección).
El enriquecimiento posterior de información ejecutiva (sector, tamaño, presencia en México, Glassdoor score, etc.)
se realiza en el módulo `classifier.py`.

Funciones clave:
- Identificación de empresas nuevas que aún no están registradas.
- Inserción de registros mínimos en la tabla `empresas`.

Este módulo sigue el principio de separación de responsabilidades:
no realiza scraping ni clasificación, únicamente garantiza que la tabla `empresas`
esté siempre sincronizada con las vacantes detectadas.

Autor: [VEAUX]
Fecha de creación: 2025-07-24
Última actualización: 2025-10-01
"""


# analyzer/empresa_info.py

from db_utils import insert_or_update_empresa, _get_conn
import datetime

def get_empresas_faltantes():
    """
    Busca empresas en la tabla vacantes que no estén registradas en la tabla empresas.
    Devuelve una lista de nombres de empresas nuevas.
    """
    
    conn = _get_conn()
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


def llenar_tabla_empresas():
    """
    Inserta en la tabla empresas los registros de compañías nuevas,
    inicializándolos solo con el nombre y la fecha de detección.
    """
    nuevas_empresas = get_empresas_faltantes()
    if nuevas_empresas:
        print(f"🔎 Detectadas {len(nuevas_empresas)} nuevas empresas.")
        if len(nuevas_empresas) <= 10:
            for e in nuevas_empresas:
                print(f" - {e}")
    else:
        print("✅ No hay empresas nuevas por registrar.")
        return 0
    count=0
    for company in nuevas_empresas:
        info = {
            "company": company,
            "resumen_empresa": None,
            "sector_empresa": None,
            "tamaño_empresa": None,
            "presencia_mexico": None,
            "glassdoor_score": None,
            "last_updated": datetime.date.today().isoformat()
        }
        insert_or_update_empresa(info)
        print(f"✅ Empresa añadida: {company}")
        count += 1
    return count