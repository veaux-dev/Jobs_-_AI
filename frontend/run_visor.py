import streamlit as st
import sqlite3
import time
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


def _terms_from_csv(raw: str) -> list[str]:
    return [t.strip().lower() for t in raw.split(",") if t.strip()]


def _build_like_clause(col: str, terms: list[str], params: list[str]) -> str | None:
    if not terms:
        return None
    parts = []
    for term in terms:
        parts.append(f"LOWER({col}) LIKE ?")
        params.append(f"%{term}%")
    return "(" + " OR ".join(parts) + ")"


def _build_global_text_clause(cols: list[str], terms: list[str], params: list[str]) -> str | None:
    if not terms or not cols:
        return None
    parts = []
    for term in terms:
        like_params = f"%{term}%"
        for col in cols:
            parts.append(f"LOWER({col}) LIKE ?")
            params.append(like_params)
    return "(" + " OR ".join(parts) + ")"


def _build_where(filters: dict, available_cols: list[str], alias: str | None = None) -> tuple[str, list[str]]:
    clauses: list[str] = []
    params: list[str] = []

    def col(name: str) -> str:
        return f"{alias}.{name}" if alias else name

    score_min = filters.get("score_min")
    if score_min is not None and "score_total" in available_cols:
        clauses.append(f"{col('score_total')} >= ?")
        params.append(str(score_min))

    status_sel = filters.get("status_sel") or []
    if status_sel and "status" in available_cols:
        placeholders = ", ".join("?" for _ in status_sel)
        clauses.append(f"{col('status')} IN ({placeholders})")
        params.extend(status_sel)

    lugar_terms = filters.get("filtro_lugar_terms") or []
    if lugar_terms and "location" in available_cols:
        clause = _build_like_clause(col("location"), lugar_terms, params)
        if clause:
            clauses.append(clause)

    empresa_terms = filters.get("filtro_empresa_terms") or []
    if empresa_terms and "company" in available_cols:
        clause = _build_like_clause(col("company"), empresa_terms, params)
        if clause:
            clauses.append(clause)

    texto_terms = filters.get("filtro_texto_terms") or []
    if texto_terms:
        text_cols = [c for c in ["title", "company", "location"] if c in available_cols]
        text_cols = [col(c) for c in text_cols]
        clause = _build_global_text_clause(text_cols, texto_terms, params)
        if clause:
            clauses.append(clause)

    date_quick = filters.get("date_quick")
    fecha_ref = filters.get("fecha_ref")
    cutoff = filters.get("cutoff")
    if date_quick and date_quick != "all" and fecha_ref in available_cols and cutoff:
        clauses.append(f"DATE({col(fecha_ref)}) >= DATE(?)")
        params.append(cutoff)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


# --- Helpers for SQL filtering ---
full_metrics = os.getenv("VISOR_FULL_METRICS", "1") in {"1", "true", "True"}

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
perf_mode = True
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


# --- Filtro de fecha (para SQL) ---
cutoff = None
if date_quick != "all":
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

# --- Tabla SQL (filtros aplicados en DB) ---
table_total_rows = None
df_view = pd.DataFrame()
perf = {} if perf_mode else None
try:
    t_conn = time.perf_counter() if perf_mode else None
    conn_table = _get_conn()
    vac_cols = _table_cols(conn_table, "vacantes")
    emp_cols = _table_cols(conn_table, "empresas")
    if perf_mode:
        perf["conn+cols_ms"] = int((time.perf_counter() - t_conn) * 1000)
    base_cols = [
        "score_total",
        "categoria_fit",
        "status",
        "title",
        "company",
        "sector_empresa",
        "location",
        "presencia_mexico",
        "es_procurement",
        "es_fit_usuario",
        "nivel_estimado",
        "link",
        "scraped_at",
    ]
    select_cols_sql = []
    for col_name in base_cols:
        if col_name in vac_cols:
            select_cols_sql.append(f"v.{col_name}")
        elif col_name == "sector_empresa" and "sector_empresa" in emp_cols:
            select_cols_sql.append("e.sector_empresa")
        elif col_name == "presencia_mexico" and "presencia_mexico" in emp_cols:
            select_cols_sql.append("e.presencia_mexico")

    filtro_lugar_terms = _terms_from_csv(filtro_lugar)
    filtro_empresa_terms = _terms_from_csv(filtro_empresa)
    filtro_texto_terms = _terms_from_csv(filtro_texto)
    fecha_ref_db = next((c for c in ["scraped_at", "date", "last_seen_on"] if c in vac_cols), None)
    filters = {
        "score_min": score_min,
        "status_sel": status_sel,
        "filtro_lugar_terms": filtro_lugar_terms,
        "filtro_empresa_terms": filtro_empresa_terms,
        "filtro_texto_terms": filtro_texto_terms,
        "date_quick": date_quick,
        "fecha_ref": fecha_ref_db,
        "cutoff": cutoff.strftime("%Y-%m-%d") if cutoff is not None else None,
    }
    t_where = time.perf_counter() if perf_mode else None
    where_sql, params = _build_where(filters, vac_cols, alias="v")
    if perf_mode:
        perf["build_where_ms"] = int((time.perf_counter() - t_where) * 1000)
    cutoff_key = filters.get("cutoff")
    filters_key = (
        score_min,
        tuple(status_sel),
        tuple(filtro_lugar_terms),
        tuple(filtro_empresa_terms),
        tuple(filtro_texto_terms),
        date_quick,
        cutoff_key,
    )
    if st.session_state.get("filters_key") != filters_key:
        st.session_state["filters_key"] = filters_key
        st.session_state["table_total_rows"] = None

    order_by = "v.score_total DESC" if "score_total" in vac_cols else "v.scraped_at DESC"
    offset = (st.session_state.get("page", 1) - 1) * page_size
    data_q = f"""
        SELECT {', '.join(select_cols_sql)}
        FROM vacantes v
        LEFT JOIN empresas e ON v.company = e.company
        {where_sql}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
    """
    data_params = params + [page_size, offset]
    t_query = time.perf_counter() if perf_mode else None
    df_view = pd.read_sql_query(data_q, conn_table, params=data_params)
    if perf_mode:
        perf["query_page_ms"] = int((time.perf_counter() - t_query) * 1000)
finally:
    try:
        conn_table.close()
    except Exception:
        pass

# --- Métricas SQL (totales y filtradas en DB completa) ---
sql_metrics = None
sql_view = None
try:
    t_conn_m = time.perf_counter() if perf_mode else None
    conn_metrics = _get_conn()
    vac_cols = _table_cols(conn_metrics, "vacantes")
    if perf_mode:
        perf["metrics_conn+cols_ms"] = int((time.perf_counter() - t_conn_m) * 1000)
    # Totales
    total_q = """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status='new' THEN 1 ELSE 0 END) AS new_cnt,
            SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active_cnt,
            SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) AS closed_cnt,
            SUM(CASE WHEN score_total IS NULL THEN 1 ELSE 0 END) AS unanalyzed_cnt,
            COUNT(DISTINCT company) AS empresas_cnt,
            AVG(score_total) AS avg_score
        FROM vacantes
    """
    t_metrics = time.perf_counter() if perf_mode else None
    cur = conn_metrics.execute(total_q)
    sql_metrics = cur.fetchone()
    if perf_mode:
        perf["metrics_total_ms"] = int((time.perf_counter() - t_metrics) * 1000)

    # Filtros aplicados a DB completa (incluye score_min y filtros activos)
    filtro_lugar_terms = _terms_from_csv(filtro_lugar)
    filtro_empresa_terms = _terms_from_csv(filtro_empresa)
    filtro_texto_terms = _terms_from_csv(filtro_texto)
    filters = {
        "score_min": score_min,
        "status_sel": status_sel,
        "filtro_lugar_terms": filtro_lugar_terms,
        "filtro_empresa_terms": filtro_empresa_terms,
        "filtro_texto_terms": filtro_texto_terms,
        "date_quick": date_quick,
        "fecha_ref": next((c for c in ["scraped_at", "date", "last_seen_on"] if c in vac_cols), None),
        "cutoff": cutoff.strftime("%Y-%m-%d") if cutoff is not None else None,
    }
    where_sql, params = _build_where(filters, vac_cols, alias="v")
    view_q = f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status='new' THEN 1 ELSE 0 END) AS new_cnt,
            SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active_cnt,
            SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) AS closed_cnt
        FROM vacantes v
        {where_sql}
    """
    t_view = time.perf_counter() if perf_mode else None
    cur = conn_metrics.execute(view_q, params)
    sql_view = cur.fetchone()
    if perf_mode:
        perf["metrics_view_ms"] = int((time.perf_counter() - t_view) * 1000)

    # --- Métrica de antigüedad desde DB (solo no closed) ---
    fecha_ref_db = next((c for c in ["scraped_at", "date", "last_seen_on"] if c in vac_cols), None)
    if fecha_ref_db:
        age_q = f"""
            SELECT
                CASE
                    WHEN {fecha_ref_db} IS NULL THEN 'Unknown'
                    WHEN CAST(julianday('now') - julianday({fecha_ref_db}) AS INT) = 0 THEN 'New'
                    WHEN CAST(julianday('now') - julianday({fecha_ref_db}) AS INT) BETWEEN 1 AND 7 THEN 'One week old'
                    WHEN CAST(julianday('now') - julianday({fecha_ref_db}) AS INT) BETWEEN 8 AND 14 THEN '2 weeks old'
                    WHEN CAST(julianday('now') - julianday({fecha_ref_db}) AS INT) BETWEEN 15 AND 30 THEN 'One month old'
                    WHEN CAST(julianday('now') - julianday({fecha_ref_db}) AS INT) BETWEEN 31 AND 60 THEN '2 months old'
                    ELSE 'Older'
                END AS bucket,
                COUNT(*) AS cnt
            FROM vacantes
            WHERE status != 'closed'
            GROUP BY bucket
        """
        t_age = time.perf_counter() if perf_mode else None
        cur = conn_metrics.execute(age_q)
        sql_age_rows = cur.fetchall()
        if perf_mode:
            perf["metrics_age_ms"] = int((time.perf_counter() - t_age) * 1000)
    else:
        sql_age_rows = []
finally:
    try:
        conn_metrics.close()
    except Exception:
        pass

# layout principal: columna izquierda (4/5) y derecha (1/5)
col_left, col_right = st.columns([4, 1], vertical_alignment="top")

with col_left:
    st.markdown("<div class='debug-frame'>", unsafe_allow_html=True)
    if full_metrics:
        if sql_metrics:
            total_vac = sql_metrics[0] or 0
            new_db = sql_metrics[1] or 0
            active_db = sql_metrics[2] or 0
            closed_db = sql_metrics[3] or 0
            unanalyzed_db = sql_metrics[4] or 0
            total_emp = sql_metrics[5] or 0
            avg_score = sql_metrics[6]
        else:
            total_vac = 0
            total_emp = 0
            avg_score = None
            new_db = 0
            active_db = 0
            closed_db = 0
            unanalyzed_db = 0
        st.markdown(
            f"<div class='metrics-line'>DB: {total_vac} vacantes • {total_emp} empresas • "
            f"score {round(avg_score,1) if avg_score is not None else '-'} • "
            f"New {new_db} • Active {active_db} • Closed {closed_db} • "
            f"Sin analizar {unanalyzed_db}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='metrics-line'>DB(vista): 0 vacantes • 0 empresas • score - • "
            "New 0 • Active 0 • Closed 0 • Sin analizar 0</div>",
            unsafe_allow_html=True,
        )

    if sql_view:
        st.markdown(
            f"<div class='metrics-line'>Vista (filtros, DB): {sql_view[0] or 0} total • "
            f"New {sql_view[1] or 0} • "
            f"Active {sql_view[2] or 0} • "
            f"Closed {sql_view[3] or 0}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='metrics-line'>Vista (filtros, DB): 0 total • New 0 • Active 0 • Closed 0</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ===== Gráfica en columna derecha =====
with col_right:
    st.markdown("<div class='debug-frame'>", unsafe_allow_html=True)
    if "sql_age_rows" in locals() and sql_age_rows:
        order = ["New", "One week old", "2 weeks old", "One month old", "2 months old", "Older", "Unknown"]
        counts = {k: 0 for k in order}
        for bucket, cnt in sql_age_rows:
            if bucket in counts:
                counts[bucket] = cnt
        fig, ax = plt.subplots(figsize=(2.6, 1.8))
        colors = ["#2a9d8f", "#4ea8de", "#6c757d", "#f4a261", "#e76f51", "#adb5bd", "#c0c0c0"]
        ax.barh(list(counts.keys()), list(counts.values()), color=colors[: len(counts)])
        ax.set_title("Antigüedad (no closed)", fontsize=9, pad=2)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(axis="y", labelsize=6)
        ax.tick_params(axis="x", labelsize=6)
        ax.grid(axis="x", alpha=0.2)
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        st.pyplot(fig, use_container_width=True)
    else:
        st.caption("Sin datos de antigüedad.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- Tabla de resultados ---
# Container 2 (izquierda)
with col_left:
    st.markdown("<div class='debug-frame'>", unsafe_allow_html=True)
    st.markdown("**Vacantes filtradas**")
    table_total_rows = st.session_state.get("table_total_rows")
    if table_total_rows is None:
        st.caption(f"Mostrando {len(df_view)} vacantes (total no calculado) • score >= {score_min}")
    else:
        st.caption(f"Mostrando {table_total_rows} vacantes con score >= {score_min}")
    st.markdown("</div>", unsafe_allow_html=True)

total_rows = table_total_rows if table_total_rows is not None else None
total_pages = max(1, (total_rows + page_size - 1) // page_size) if total_rows is not None else 1000
page = st.sidebar.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1, key="page")
start_idx = (page - 1) * page_size
end_idx = start_idx + len(df_view)
t_replace = time.perf_counter() if perf_mode else None
df_view = df_view.replace(r"\|", " ", regex=True)
if perf_mode:
    perf["replace_regex_ms"] = int((time.perf_counter() - t_replace) * 1000)

caption_total = total_rows if total_rows is not None else "?"
st.caption(f"Página {page}/{total_pages} • filas {start_idx + 1}-{end_idx} de {caption_total}")
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
    t_grid = time.perf_counter() if perf_mode else None
    gb = GridOptionsBuilder.from_dataframe(df_view)
    gb.configure_default_column(filter=True, sortable=True, resizable=True)
    gb.configure_column("link", headerName="Link", cellRenderer=link_renderer, sortable=False, filter=False)
    gb.configure_column("score_total", sort="desc")
    gb.configure_column("score_total", width=90)
    gb.configure_column("categoria_fit", width=140)
    gb.configure_column("status", width=110)
    gb.configure_column("title", width=260)
    gb.configure_column("company", width=180)
    gb.configure_column("sector_empresa", width=160)
    gb.configure_column("location", width=180)
    gb.configure_column("presencia_mexico", width=140)
    gb.configure_column("es_procurement", width=130)
    gb.configure_column("es_fit_usuario", width=120)
    gb.configure_column("nivel_estimado", width=130)
    gb.configure_column("link", width=90)
    gb.configure_column("scraped_at", width=140)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
    grid_options = gb.build()
    if perf_mode:
        perf["grid_build_ms"] = int((time.perf_counter() - t_grid) * 1000)

    t_render = time.perf_counter() if perf_mode else None
    AgGrid(
        df_view,
        gridOptions=grid_options,
        height=900 if st.session_state.grid_fullscreen else 600,
        fit_columns_on_grid_load=True,
        columns_auto_size_mode="FIT_ALL_COLUMNS_TO_VIEW",
        allow_unsafe_jscode=True,
    )
    if perf_mode:
        perf["grid_render_ms"] = int((time.perf_counter() - t_render) * 1000)

# --- Conteo total (lento, diferido) ---
if st.session_state.get("table_total_rows") is None:
    with st.spinner("Calculando total de vacantes..."):
        try:
            conn_count = _get_conn()
            count_q = f"SELECT COUNT(*) FROM vacantes v {where_sql}"
            t_count = time.perf_counter() if perf_mode else None
            st.session_state["table_total_rows"] = conn_count.execute(count_q, params).fetchone()[0]
            if perf_mode:
                perf["count_total_ms"] = int((time.perf_counter() - t_count) * 1000)
        finally:
            try:
                conn_count.close()
            except Exception:
                pass

if perf_mode and perf:
    st.sidebar.subheader("Tiempos (ms)")
    for k, v in perf.items():
        st.sidebar.caption(f"{k}: {v}")
    st.sidebar.caption(f"total_visible_ms: {sum(perf.values())}")

