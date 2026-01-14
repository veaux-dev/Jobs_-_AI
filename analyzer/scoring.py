from datetime import datetime
from db_utils import fetch_all_vacantes_enriched , bulk_update_vacantes_df
import pandas as pd
from tqdm import tqdm


HOY = datetime.today().date()

# --- Funciones de puntaje ---
def puntaje_fit_usuario(valor):
    return 40 if valor == 1 else 0

def puntaje_procurement(valor):
    return 25 if valor == 1 else 0

def puntaje_nivel(nivel):
    if not nivel:
        return 0
    nivel = nivel.lower()
    if "vp" in nivel:
        return 25
    if "director" in nivel:
        return 20
    if "manager" in nivel:
        return 5
    return 0

def puntaje_industria(resumen: str) -> int:
    """
    Returns an industry alignment score (0–20) based on standardized sector names.
    Calibrated so sector weight = 20 points in the global 125-point model.
    """

    if not resumen:
        return 5  # neutral midpoint

    resumen = resumen.strip().lower()

    # --- Core expertise (direct domain match) ---
    if any(k in resumen for k in [
        "energy / oil & gas", "power generation",
        "chemicals", "materials", "mining", "metals",
        "industrial manufacturing", "machinery", "automation",
        "aerospace", "defense", "aviation", "space",
        "automotive", "mobility", "transportation equipment"
    ]):
        return 20

    # --- Strong adjacency (industrial / engineering DNA) ---
    if any(k in resumen for k in [
        "electrical", "electronics", "semiconductors",
        "engineering", "construction", "infrastructure",
        "logistics", "supply chain", "distribution", "transportation services"
    ]):
        return 16

    # --- Strategic adjacency (relevant for procurement / transformation) ---
    if any(k in resumen for k in [
        "technology", "software", "automation software", "ai",
        "consulting", "advisory", "professional services",
        "environmental", "recycling", "sustainability", "waste management"
    ]):
        return 12

    # --- Moderate relevance ---
    if any(k in resumen for k in [
        "finance", "banking", "investment", "insurance",
        "real estate", "property", "construction materials"
    ]):
        return 8

    # --- Low relevance (operational / consumer focus) ---
    if any(k in resumen for k in [
        "consumer", "retail", "fmcg", "apparel",
        "food", "beverage", "agriculture", "processing",
        "hospitality", "travel", "tourism", "leisure",
        "healthcare", "medical", "pharmaceutical", "biotechnology",
        "education", "government", "public", "ngo",
        "marketing", "media", "advertising", "events"
    ]):
        return 4

    # --- Unknown or mixed domains ---
    if any(k in resumen for k in ["miscellaneous", "diversified", "unknown"]):
        return 8

    # --- Legacy Spanish support (for backward compatibility) ---
    if any(k in resumen for k in [
        "aeroespacial", "energía", "automotriz",
        "manufactura", "industrial", "ingeniería"
    ]):
        return 20

    return 5  # neutral default

def puntaje_ubicacion(presencia, location):
    puntos = 0
    if presencia and presencia.strip().lower() == "yes":
        puntos += 10
    if location and ("nuevo león" in location.lower() or "monterrey" in location.lower()):
        puntos += 10
    return puntos

def puntaje_modalidad(valor, location):
    valor = (valor or "").lower()
    location = (location or "").lower()
    if "remoto" in valor or "remote" in valor or "monterrey" in location:
        return 10
    if "híbrido" in valor or "hibrido" in valor or "hybrid" in valor:
        return 5
    return 0

def puntaje_francia(resumen):
    if not resumen:
        return 0
    resumen = resumen.lower()
    if any(k in resumen for k in ["france", "française", "paris"]):
        return 5
    return 0

def puntaje_recencia(fecha):
    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()
        return 5 if (HOY - fecha_dt).days <= 7 else 0
    except:
        return 0

# --- Calcular scoring ---
def calcular_scoring():
    vacantes = fetch_all_vacantes_enriched()
    results = []

    for vac in tqdm(vacantes,desc='Scoring Vacantes', unit='vac'):
        

        score = 0
        score += puntaje_fit_usuario(vac.get("es_fit_usuario"))
        score += puntaje_procurement(vac.get("es_procurement"))
        score += puntaje_nivel(vac.get("nivel_estimado"))
        score += puntaje_industria(vac.get("resumen_empresa"))
        score += puntaje_ubicacion(vac.get("presencia_mexico"), vac.get("location"))
        score += puntaje_modalidad(vac.get("modalidad_trabajo"), vac.get("location"))
        score += puntaje_francia(vac.get("resumen_empresa"))
        score += puntaje_recencia(vac.get("date"))

        if score >= 100:    categoria = "🔵 Excelente fit"
        elif score >= 80:   categoria = "🟢 Buen fit"
        elif score >= 60:   categoria = "🟡 Fit moderado"
        else:               categoria = "🔴 No relevante"
        
        
        # update_vacante_fields(vac['job_hash'], {
        #     "score_total": score,
        #     "categoria_fit": categoria
        # })

        results.append({
            "job_hash": vac["job_hash"],
            "score_total": score,
            "categoria_fit": categoria
            })

    # Convert to DataFrame and bulk update all at once
    df_updates = pd.DataFrame(results, columns=["job_hash", "score_total", "categoria_fit"])
    bulk_update_vacantes_df(df_updates)

    print(f"✅ Scoring actualizado ({len(df_updates)} registros).")