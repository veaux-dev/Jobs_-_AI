import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from st_aggrid import AgGrid as AgGridType, GridOptionsBuilder as GridOptionsBuilderType, JsCode as JsCodeType

try:
    from st_aggrid import AgGrid as _AgGrid, GridOptionsBuilder as _GridOptionsBuilder, JsCode as _JsCode
    AgGrid: Any = _AgGrid
    GridOptionsBuilder: Any = _GridOptionsBuilder
    JsCode: Any = _JsCode
except Exception:  # pragma: no cover - optional dependency
    AgGrid = None
    GridOptionsBuilder = None
    JsCode = None

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


def _table_cols(conn, table: str) -> list[str]:
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cur.fetchall()]
    except Exception:
        return []


# --- Cargar datos ---
@st.cache_data(ttl=60)
def cargar_datos():
    conn = _get_conn()
    view_limit = int(os.getenv("VISOR_LIMIT", "5000"))

    vac_cols_wanted = [
        "job_hash",
        "qry_title",
        "qry_loc",
        "title",
        "company",
        "location",
        "date",
        "date_text",
        "link",
        "job_description",
        "full_text",
        "scraped_at",
        "last_seen_on",
        "status",
        "modalidad_trabajo",
        "tipo_contrato",
        "salario_estimado",
        "applicants_count",
        "es_procurement",
        "es_fit_usuario",
        "nivel_estimado",
        "score_total",
        "categoria_fit",
        "presencia_mexico",
    ]
    vac_cols = _table_cols(conn, "vacantes")
    vac_select = [c for c in vac_cols_wanted if c in vac_cols] or ["rowid"]

    vacantes = pd.read_sql_query(
        f"SELECT {', '.join(vac_select)} FROM vacantes ORDER BY scraped_at DESC LIMIT {view_limit}",
        conn,
    )

    emp_cols = _table_cols(conn, "empresas")
    emp_wanted = ["company", "sector_empresa", "presencia_mexico"]
    emp_select = [c for c in emp_wanted if c in emp_cols]
    if emp_select:
        empresas = pd.read_sql_query(f"SELECT {', '.join(emp_select)} FROM empresas", conn)
    else:
        empresas = pd.DataFrame()
    conn.close()
    fulldf = pd.merge(vacantes, empresas, on="company", how="left") if not empresas.empty else vacantes
    return vacantes, empresas, fulldf

def filtrar_con_keywords(df, columna, texto_raw):
    if not texto_raw:
        return df
    keywords = [kw.strip() for kw in texto_raw.split(',') if kw.strip()]
    patron = '|'.join(keywords)
    return df[df[columna].fillna('').str.lower().str.contains(patron)]



vacantes, empresas, fulldf = cargar_datos()
full_metrics = os.getenv("VISOR_FULL_METRICS", "0") in {"1", "true", "True"}

# --- Título principal ---
st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
      .block-container { padding-top: 0.6rem; }
      h1 { margin-bottom: 0.1rem; }
      h2 { margin-top: 0.2rem; margin-bottom: 0.2rem; }
      h3 { margin-top: 0.2rem; margin-bottom: 0.2rem; }
      .metrics-line { font-size: 14px; line-height: 1.35; margin-bottom: 0.2rem; }
      .debug-frame { padding: 6px 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

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
filtro_texto = st.sidebar.text_input("🔎 Búsqueda global (title/company/location)").strip().lower()
status_sel = st.sidebar.multiselect(
    "STATUS",
    options=["new", "active", "closed"],
    default=["new", "active"],
)
page_size = st.sidebar.selectbox("Filas por página", [50, 100, 200, 500], index=1)
date_quick = st.sidebar.radio(
    "🗓️ Quick date filter",
    ["all", "today", "last 2 days", "last 3 days", "this week", "last 2 weeks"],
    index=0,
)


# --- Aplicar filtros ---
df_filtrado = fulldf.copy()
df_filtrado["score_total"] = df_filtrado["score_total"].fillna(-1).astype(int) # asegurar columna score_total // para que no truene la viz si hay vacantes sin score.
df_filtrado = df_filtrado[df_filtrado['score_total'] >= score_min]
#df_filtrado = df_filtrado[df_filtrado['modalidad_trabajo'].isin(modalidad_filtro)]
df_filtrado = filtrar_con_keywords(df_filtrado, 'location', filtro_lugar)
df_filtrado = filtrar_con_keywords(df_filtrado, 'company', filtro_empresa)
df_filtrado = df_filtrado[df_filtrado['status'].isin(status_sel)]
fecha_ref = next((c for c in ["scraped_at", "date", "last_seen_on"] if c in df_filtrado.columns), None)
if fecha_ref and date_quick != "all":
    serie_fechas = pd.to_datetime(df_filtrado[fecha_ref], errors="coerce").dt.normalize()
    hoy = pd.Timestamp.today().normalize()
    if date_quick == "today":
        cutoff = hoy
    elif date_quick == "last 2 days":
        cutoff = hoy - pd.Timedelta(days=1)
    elif date_quick == "last 3 days":
        cutoff = hoy - pd.Timedelta(days=2)
    elif date_quick == "this week":
        cutoff = hoy - pd.Timedelta(days=hoy.weekday())
    elif date_quick == "last 2 weeks":
        cutoff = hoy - pd.Timedelta(days=13)
    else:
        cutoff = None
    if cutoff is not None:
        df_filtrado = df_filtrado[serie_fechas >= cutoff]

# layout principal: columna izquierda (4/5) y derecha (1/5)
col_left, col_right = st.columns([4, 1], vertical_alignment="top")

def count_status(df, s):
    return int((df.get("status") == s).sum()) if "status" in df.columns else 0

with col_left:
    st.markdown("<div class='debug-frame'>", unsafe_allow_html=True)
    if full_metrics:
        conn = _get_conn()
        total_vac = conn.execute("SELECT COUNT(*) FROM vacantes").fetchone()[0]
        total_emp = conn.execute("SELECT COUNT(DISTINCT company) FROM vacantes").fetchone()[0]
        avg_score = conn.execute("SELECT AVG(score_total) FROM vacantes").fetchone()[0]
        new_db = conn.execute("SELECT COUNT(*) FROM vacantes WHERE status='new'").fetchone()[0]
        active_db = conn.execute("SELECT COUNT(*) FROM vacantes WHERE status='active'").fetchone()[0]
        closed_db = conn.execute("SELECT COUNT(*) FROM vacantes WHERE status='closed'").fetchone()[0]
        unanalyzed_db = conn.execute("SELECT COUNT(*) FROM vacantes WHERE score_total IS NULL").fetchone()[0]
        conn.close()
        st.markdown(
            f"<div class='metrics-line'>DB: {total_vac} vacantes • {total_emp} empresas • "
            f"score {round(avg_score,1) if avg_score is not None else '-'} • "
            f"New {new_db} • Active {active_db} • Closed {closed_db} • "
            f"Sin analizar {unanalyzed_db}</div>",
            unsafe_allow_html=True,
        )
    else:
        unanalyzed_view = int(fulldf["score_total"].isna().sum()) if "score_total" in fulldf.columns else 0
        st.markdown(
            f"<div class='metrics-line'>DB(vista): {len(fulldf)} vacantes • "
            f"{fulldf['company'].nunique() if 'company' in fulldf.columns else 0} empresas • "
            f"score {round(fulldf['score_total'].mean(),1) if 'score_total' in fulldf.columns else '-'} • "
            f"New {count_status(fulldf, 'new')} • Active {count_status(fulldf, 'active')} • Closed {count_status(fulldf, 'closed')} • "
            f"Sin analizar {unanalyzed_view}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div class='metrics-line'>Vista: {len(df_filtrado)} total • "
        f"New {count_status(df_filtrado, 'new')} • "
        f"Active {count_status(df_filtrado, 'active')} • "
        f"Closed {count_status(df_filtrado, 'closed')}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ===== Gráfica en columna derecha =====
fecha_ref = next((c for c in ["first_seen_at", "date", "scraped_at"] if c in df_filtrado.columns), None)
with col_right:
    st.markdown("<div class='debug-frame'>", unsafe_allow_html=True)
    if fecha_ref:
        tmp = df_filtrado[[fecha_ref]].copy()
        tmp[fecha_ref] = pd.to_datetime(tmp[fecha_ref], errors="coerce").dt.normalize()
        hoy = pd.Timestamp.today().normalize()
        delta = (hoy - tmp[fecha_ref])
        tmp["age_days"] = pd.to_timedelta(delta).dt.days

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

        fig, ax = plt.subplots(figsize=(2.6, 1.8))
        colors = ["#2a9d8f", "#4ea8de", "#6c757d", "#f4a261", "#e76f51", "#adb5bd", "#c0c0c0"]
        ax.barh(counts.index.tolist(), counts.to_numpy(), color=colors[: len(counts)])
        ax.set_title("Antigüedad", fontsize=9, pad=2)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(axis="y", labelsize=6)
        ax.tick_params(axis="x", labelsize=6)
        ax.grid(axis="x", alpha=0.2)
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        st.pyplot(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- Tabla de resultados ---
# Container 2 (izquierda)
with col_left:
    st.markdown("<div class='debug-frame'>", unsafe_allow_html=True)
    st.markdown("**Vacantes filtradas**")
    st.caption(f"Mostrando {len(df_filtrado)} vacantes con score >= {score_min}")
    st.markdown("</div>", unsafe_allow_html=True)

df_detail = df_filtrado.copy()
columnas_mostrar = [
    "score_total",
    "categoria_fit",
    "status",
    "title",
    "company",
    "sector_empresa",
    "scraped_at",
    "location",
    "presencia_mexico",
    "es_procurement",
    "es_fit_usuario",
    "nivel_estimado",
    "link",
]

df_table = df_detail[columnas_mostrar].sort_values(by="score_total", ascending=False)
if filtro_texto:
    texto = filtro_texto.lower()
    mask = (
        df_table[columnas_mostrar]
        .astype(str)
        .apply(lambda s: s.str.lower().str.contains(texto, na=False))
        .any(axis=1)
    )
    df_table = df_table[mask]

total_rows = len(df_table)
total_pages = max(1, (total_rows + page_size - 1) // page_size)
page = st.sidebar.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1)
start_idx = (page - 1) * page_size
end_idx = start_idx + page_size
df_view = df_table.iloc[start_idx:end_idx]
df_view = df_view.replace(r"\|", " ", regex=True)

st.caption(f"Página {page}/{total_pages} • filas {start_idx + 1}-{min(end_idx, total_rows)}")
if AgGrid is None or GridOptionsBuilder is None or JsCode is None:
    st.error("AgGrid no está instalado. Instala con: `pip install streamlit-aggrid`")
    st.dataframe(df_view, use_container_width=True)
else:
    if "grid_fullscreen" not in st.session_state:
        st.session_state.grid_fullscreen = False
    if st.button("Fullscreen" if not st.session_state.grid_fullscreen else "Salir fullscreen"):
        st.session_state.grid_fullscreen = not st.session_state.grid_fullscreen

    link_renderer = JsCode(
        """
        class UrlCellRenderer {
          init(params) {
            this.eGui = document.createElement('a');
            this.eGui.innerText = 'Abrir';
            this.eGui.setAttribute('href', params.value || '');
            this.eGui.setAttribute('target', '_blank');
          }
          getGui() { return this.eGui; }
        }
        """
    )
    gb = GridOptionsBuilder.from_dataframe(df_view)
    gb.configure_default_column(filter=True, sortable=True, resizable=True)
    gb.configure_column("link", headerName="Link", cellRenderer=link_renderer, sortable=False, filter=False)
    gb.configure_column("score_total", sort="desc")
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
    grid_options = gb.build()

    AgGrid(
        df_view,
        gridOptions=grid_options,
        height=900 if st.session_state.grid_fullscreen else 600,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
    )

# --- Detalle expandible ---
st.subheader("Detalle por vacante")
for _, row in df_detail.iterrows():
    with st.expander(f"{row['title']} – {row['company']} [{row['score_total']}]"):
        st.markdown(f"**Ubicación:** {row['location']}")
        st.markdown(f"**Modalidad:** {row['modalidad_trabajo']}")
        st.markdown(f"**Nivel estimado:** {row['nivel_estimado']}")
        st.markdown(f"**Fit usuario:** {'✅' if row['es_fit_usuario'] else '❌'}")
        st.markdown(f"**Es procurement:** {'✅' if row['es_procurement'] else '❌'}")
        st.markdown("**Descripción completa:**")
        st.text(row['job_description'] or row.get('full_text', 'Sin descripción'))
