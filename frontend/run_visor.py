from numpy import full
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path
import os

# 1. Punto de partida: carpeta donde está este script
BASE_DIR = Path(__file__).resolve().parent

# 2. Busca una carpeta llamada "data" o "l_data" en niveles relevantes
candidates = [
    BASE_DIR / "data",           # caso Docker
    BASE_DIR.parent / "data",    # caso local si hay carpeta "data" arriba
    BASE_DIR.parent / "l_data",  # caso local con tu layout actual
]

DATA_DIR = next((p for p in candidates if p.exists()), None)
if DATA_DIR is None:
    raise FileNotFoundError("No se encontró carpeta data/l_data en ninguna ruta candidata.")

# 3. Rutas absolutas que siempre serán BASE/DATA/...
DB_PATH = DATA_DIR / "vacantes.db"

def _get_conn():
    if DB_PATH is None:
        raise RuntimeError("DB_PATH not set. Call set_db_path() first.")
    timeout = int(os.getenv("SQLITE_TIMEOUT", "60"))
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=timeout)
    conn.execute("PRAGMA busy_timeout = 60000;")
    conn.execute("PRAGMA query_only = ON;")
    conn.execute("PRAGMA foreign_keys = ON;")     # por si metes claves foráneas
    return conn


# --- Cargar datos ---
@st.cache_data(ttl=60)
def cargar_datos():
    conn = _get_conn()
    vacantes = pd.read_sql_query("SELECT * FROM vacantes", conn)
    empresas = pd.read_sql_query("SELECT * FROM empresas", conn)
    conn.close()
    fulldf = pd.merge(vacantes, empresas, on="company", how="left")
    return vacantes, empresas, fulldf

def filtrar_con_keywords(df, columna, texto_raw):
    if not texto_raw:
        return df
    keywords = [kw.strip() for kw in texto_raw.split(',') if kw.strip()]
    patron = '|'.join(keywords)
    return df[df[columna].fillna('').str.lower().str.contains(patron)]



vacantes, empresas, fulldf = cargar_datos()

# --- Título principal ---
st.set_page_config(layout="wide")

st.title("📊 Visor de Vacantes Analizadas")

# # --- Panel de resumen general ---
# st.header("Resumen general")
# col1, col2, col3 = st.columns(3)

# with col1:
#     st.metric("Vacantes totales", len(vacantes))

# with col2:
#     st.metric("Empresas únicas", empresas['company'].nunique())

# with col3:
#     missing_empresas = vacantes[~vacantes['company'].isin(empresas['company'])]['company'].nunique()
#     st.metric("Empresas sin datos", missing_empresas)



# --- Filtros ---
st.sidebar.header("Filtros")
score_min = st.sidebar.slider("Score mínimo", min_value=-1, max_value=120, value=85, step=5)
filtro_lugar = st.sidebar.text_input("📍 Filtrar por lugar (puedes usar múltiples, separados por coma)").strip().lower()
filtro_empresa = st.sidebar.text_input("🏢 Filtrar por empresa (puedes usar múltiples, separados por coma)").strip().lower()
status_sel = st.sidebar.multiselect(
    "STATUS",
    options=["new", "active", "closed"],
    default=["new", "active"],
)


# --- Aplicar filtros ---
df_filtrado = fulldf.copy()
df_filtrado["score_total"] = df_filtrado["score_total"].fillna(-1).astype(int) # asegurar columna score_total // para que no truene la viz si hay vacantes sin score.
df_filtrado = df_filtrado[df_filtrado['score_total'] >= score_min]
#df_filtrado = df_filtrado[df_filtrado['modalidad_trabajo'].isin(modalidad_filtro)]
df_filtrado = filtrar_con_keywords(df_filtrado, 'location', filtro_lugar)
df_filtrado = filtrar_con_keywords(df_filtrado, 'company', filtro_empresa)
df_filtrado = df_filtrado[df_filtrado['status'].isin(status_sel)]

st.subheader("📈 Analíticos")

# 2 columnas: todas las métricas a la izquierda, gráfica a la derecha
col_metrics, col_chart = st.columns([3, 1.2])

def count_status(df, s):
    return int((df.get("status") == s).sum()) if "status" in df.columns else 0

with col_metrics:
    # Fila 1 — métricas base completa
    c1, c2, c3 = st.columns(3)
    c1.metric("Vacantes en DB", len(fulldf))
    c2.metric("Empresas en DB", fulldf['company'].nunique())
    c3.metric("Promedio Score DB", round(fulldf['score_total'].mean(), 1) if 'score_total' in fulldf.columns else "-")

    # Fila 2 — estatus en base completa
    c4, c5, c6 = st.columns(3)
    c4.metric("🆕 New (DB)",   count_status(fulldf, "new"))
    c5.metric("✅ Active (DB)", count_status(fulldf, "active"))
    c6.metric("🔒 Closed (DB)", count_status(fulldf, "closed"))

    # Fila 3 — métricas de la vista filtrada
    c7, c8, c9 = st.columns(3)
    c7.metric("Total en vista", len(df_filtrado))
    c8.metric("🆕 New (vista)",   count_status(df_filtrado, "new"))
    c9.metric("✅ Active (vista)", count_status(df_filtrado, "active"))

with col_chart:
    # ===== Gráfica chiquitica a la derecha: distribución por antigüedad (sobre df_filtrado) =====
    # Usamos la mejor fecha disponible: first_seen_at > date > scraped_at
    fecha_ref = next((c for c in ["first_seen_at", "date", "scraped_at"] if c in df_filtrado.columns), None)

    if not fecha_ref:
        st.info("Sin columna de fecha (first_seen_at/date/scraped_at).")
    else:
        tmp = df_filtrado[[fecha_ref]].copy()
        tmp[fecha_ref] = pd.to_datetime(tmp[fecha_ref], errors="coerce").dt.normalize()
        hoy = pd.Timestamp.today().normalize()
        tmp["age_days"] = (hoy - tmp[fecha_ref]).dt.days

        def bucketize(d):
            if pd.isna(d): return "Unknown"
            if d == 0: return "New"
            if 1 <= d <= 7: return "One week old"
            if 8 <= d <= 14: return "2 weeks old"
            if 15 <= d <= 30: return "One month old"
            if 31 <= d <= 60: return "2 months old"
            return "Older"

        order = ["New","One week old","2 weeks old","One month old","2 months old","Older","Unknown"]
        tmp["age_bucket"] = tmp["age_days"].apply(bucketize)
        counts = tmp["age_bucket"].value_counts().reindex(order, fill_value=0)

        fig, ax = plt.subplots(figsize=(3.2, 2.0))  # chiquitica
        ax.bar(counts.index, counts.values)
        ax.set_title("Antigüedad (vista)", fontsize=10)
        ax.set_xlabel("")
        ax.set_ylabel("Vacantes")
        ax.set_xticklabels(counts.index, rotation=30, ha="right", fontsize=6)
        ax.grid(False)
        st.pyplot(fig, use_container_width=False)

def formatear_link(url):
    if not url:
        return ""
    return f"[🔗 Ver]({url})"

df_filtrado['link_click'] = df_filtrado['link'].apply(formatear_link)

# --- Tabla de resultados ---
st.subheader("Vacantes filtradas")
st.caption(f"Mostrando {len(df_filtrado)} vacantes con score >= {score_min}")

columnas_mostrar = ['score_total', 'categoria_fit','status','title', 'company','sector_empresa', 'scraped_at','location', 'presencia_mexico', 'es_procurement', 'es_fit_usuario', 'nivel_estimado','link']

df_markdown = df_filtrado[columnas_mostrar].astype(str).replace("\|", " ", regex=True)
df_markdown['score_total'] = df_markdown['score_total'].astype(int)

st.markdown(
    df_markdown
    .sort_values(by='score_total', ascending=False)
    .to_markdown(index=False),
    unsafe_allow_html=True

)

# --- Detalle expandible ---
st.subheader("Detalle por vacante")
for _, row in df_filtrado.iterrows():
    with st.expander(f"{row['title']} – {row['company']} [{row['score_total']}]"):
        st.markdown(f"**Ubicación:** {row['location']}")
        st.markdown(f"**Modalidad:** {row['modalidad_trabajo']}")
        st.markdown(f"**Nivel estimado:** {row['nivel_estimado']}")
        st.markdown(f"**Fit usuario:** {'✅' if row['es_fit_usuario'] else '❌'}")
        st.markdown(f"**Es procurement:** {'✅' if row['es_procurement'] else '❌'}")
        st.markdown("**Descripción completa:**")
        st.text(row['job_description'] or row.get('full_text', 'Sin descripción'))
