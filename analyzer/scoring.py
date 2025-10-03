from datetime import datetime
from db_utils import fetch_all_vacantes_enriched , update_vacante_fields


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

def puntaje_industria(resumen):
    if not resumen:
        return 0
    resumen = resumen.lower()
    if any(k in resumen for k in ["aeroespacial", "energía", "automotriz", "manufactura"]):
        return 10
    return 0

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

    for vac in vacantes:
        

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
        
        update_vacante_fields(vac['job_hash'], {
            "score_total": score,
            "categoria_fit": categoria
        })

    print("Scoring actualizado.")