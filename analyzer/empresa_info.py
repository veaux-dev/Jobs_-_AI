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

import re, unicodedata

# === REGEX PRECOMPILADOS ===
_PUNCT_RE = re.compile(r"[^0-9a-z\s&'-]+")
_THE_PREFIX = re.compile(r"^\s*the\s+", re.IGNORECASE)
_PAREN_RE = re.compile(r"\([^)]*\)")
_DOING_BUSINESS_RE = re.compile(r"\b(o/a|dba|doing business as)\b.*", re.IGNORECASE)

_SUFFIXES = [
    r"inc", r"ltd", r"corp", r"corporation", r"company",
    r"plc", r"llc", r"lp", r"llp", r"holdings",
    r"s\.?\s*a\.?\s*b\.?\s*de\s*c\.?\s*v\.?",
    r"s\.?\s*a\.?\s*de\s*c\.?\s*v\.?",
    r"sapi\s*de\s*cv",
    r"s\.?\s*de\s*r\.?\s*l\.?\s*de\s*c\.?\s*v\.?",
    r"s\.?\s*de\s*r\.?\s*l\.?",
    r"sa\s*de\s*cv", r"s\s*de\s*rl\s*de\s*cv", r"s\s*de\s*rl",
    r"s\.?\s*c\.?", r"sc", r"a\.?\s*c\.?", r"ac",
    r"gmbh", r"ag", r"kg", r"sarl", r"sas", r"sa", r"spa", r"srl",
    r"bv", r"nv", r"oyj?", r"ab", r"kk", r"ltda"
]
_SUFFIX_RE = re.compile(
    r"(?:\s|,|-)*(?:(" + "|".join(_SUFFIXES) + r"))\b(?=$|\s|,|-)",
    re.IGNORECASE,
)
_CO_SUFFIX_RE = re.compile(r"(?:\s|,|&|-)+co\b(?=$|\s|,|-)", re.IGNORECASE)

def _ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")

def normalize_company_name(raw: str) -> str:
    """Deterministic normalization of company names (v3.2 refined)."""
    if not raw:
        return ""

    s = raw.strip()
    s = _ascii_fold(s.lower())

    # limpiar comillas/apóstrofes iniciales o finales
    s = re.sub(r"^[\"'`]+|[\"'`]+$", "", s)

    # limpiar paréntesis y frases tipo o/a, dba
    s = _PAREN_RE.sub(" ", s)
    s = _DOING_BUSINESS_RE.sub("", s)

    # proteger '& co' antes del replace de &
    s = re.sub(r"&\s*co\b", " andco", s, flags=re.IGNORECASE)

    # símbolos comunes
    s = s.replace("&", " and ")
    s = _PUNCT_RE.sub(" ", s)
    s = _THE_PREFIX.sub("", s)

    # eliminar sufijos legales (excepto co)
    prev = None
    while prev != s:
        prev = s
        s = _SUFFIX_RE.sub("", s)

    # eliminar 'co' solo si aislado y sin guion (no 'co-op', no 'cooperatives')
    s = _CO_SUFFIX_RE.sub("", s)

    # evitar truncar 'sa', 'ac', etc. solo si palabra completa
    s = re.sub(r"\b(sa|ac)\b(?=$|\s|,|-)", "", s)

    # apóstrofes: "arby's" -> "arbys" pero NO "bass" -> "bas"
    s = re.sub(
        r"\b([a-z]{2,})(?:\s+|')s\b",
        lambda m: m.group(1) if not m.group(1).endswith("ss") else m.group(1) + "s",
        s,
    )

    # eliminar apóstrofes residuales
    s = s.replace("'", "")

    # normalizar espacios / guiones
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace(" ", "-")

    # colapsar guiones múltiples
    s = re.sub(r"-{2,}", "-", s)

    return s
