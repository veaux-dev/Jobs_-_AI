import sqlite3
from datetime import datetime

DB_PATH = "vacantes.db"
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("PRAGMA table_info(vacantes)")
    columnas = [col[1] for col in c.fetchall()]
    if "score_total" not in columnas:
        c.execute("ALTER TABLE vacantes ADD COLUMN score_total INTEGER")
    if "categoria_fit" not in columnas:
        c.execute("ALTER TABLE vacantes ADD COLUMN categoria_fit TEXT")

    query = """
    SELECT v.rowid, v.es_fit_usuario, v.es_procurement, v.nivel_estimado,
           v.modalidad_trabajo, v.location, v.date,
           e.resumen_empresa, e.presencia_mexico
    FROM vacantes v
    LEFT JOIN empresas e ON v.company = e.company
    """

    rows = c.execute(query).fetchall()

    for row in rows:
        rowid, fit_usuario, es_proc, nivel, modalidad, loc, fecha, resumen, presencia_mx = row

        score = 0
        score += puntaje_fit_usuario(fit_usuario)
        score += puntaje_procurement(es_proc)
        score += puntaje_nivel(nivel)
        score += puntaje_industria(resumen)
        score += puntaje_ubicacion(presencia_mx, loc)
        score += puntaje_modalidad(modalidad, loc)
        score += puntaje_francia(resumen)
        score += puntaje_recencia(fecha)

        if score >= 100:
            categoria = "🔵 Excelente fit"
        elif score >= 80:
            categoria = "🟢 Buen fit"
        elif score >= 60:
            categoria = "🟡 Fit moderado"
        else:
            categoria = "🔴 No relevante"

        c.execute("""
            UPDATE vacantes SET score_total = ?, categoria_fit = ? WHERE rowid = ?
        """, (score, categoria, rowid))

    conn.commit()
    conn.close()
    print("Scoring actualizado.")