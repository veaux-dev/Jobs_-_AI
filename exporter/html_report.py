import sqlite3
import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime
import requests

# URLs de las librerías para inyectar (Inline) y evitar bloqueos de ORB/CORS
YADCF_JS_URL = "https://cdn.jsdelivr.net/npm/yadcf@0.9.4/jquery.dataTables.yadcf.js"
YADCF_CSS_URL = "https://cdn.jsdelivr.net/npm/yadcf@0.9.4/jquery.dataTables.yadcf.css"

def generate_html(db_path, output_path):
    if not Path(db_path).exists():
        print(f"Error: Database {db_path} not found.")
        return

    # Descargar YADCF para inyectarlo (esto evita errores de ORB en Brave/Firefox)
    print("📥 Downloading YADCF for inlining...")
    try:
        yadcf_js = requests.get(YADCF_JS_URL, timeout=10).text
        yadcf_css = requests.get(YADCF_CSS_URL, timeout=10).text
    except Exception as e:
        print(f"⚠️ Warning: Could not download YADCF, falling back to external links. Error: {e}")
        yadcf_js = ""
        yadcf_css = ""

    conn = sqlite3.connect(db_path)
    query = "SELECT title as Title, company as Company, location as Location, date as Posted, link as Link FROM vacantes WHERE status != 'closed' ORDER BY date DESC, scraped_at DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("No active jobs found in database to export.")
        return

    # Limpieza para L'Oreal y otros
    for col in ['Title', 'Company', 'Location']:
        df[col] = df[col].astype(str).str.replace("'", "’", regex=False)

    df['Link'] = df['Link'].apply(lambda x: f'<a href="{x}" target="_blank" class="btn btn-sm btn-outline-primary">Open</a>' if x else "")
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Jobs - {datetime.now().strftime('%Y-%m-%d')}</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css">
        <link rel="stylesheet" href="https://code.jquery.com/ui/1.13.2/themes/base/jquery-ui.css">
        <style>
            /* YADCF INLINED CSS */
            {yadcf_css if yadcf_css else f'@import url("{YADCF_CSS_URL}");'}
            
            body {{ background-color: #f0f2f5; padding: 10px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
            .report-card {{ background: white; padding: 12px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            h1 {{ color: #1a1a1a; font-weight: 700; font-size: 1.25rem; margin-bottom: 0; }}
            .table {{ font-size: 0.82rem; margin-top: 0 !important; width: 100% !important; }}
            .table td, .table th {{ padding: 4px 8px !important; vertical-align: middle; }}
            .btn-outline-primary {{ border-radius: 4px; padding: 1px 8px; font-size: 0.75rem; }}
            .badge {{ font-size: 0.7rem; }}
            .yadcf-filter-wrapper {{ display: flex !important; align-items: center; margin-top: 4px; width: 100%; }}
            .yadcf-filter {{ font-size: 0.72rem; padding: 1px 2px; border-radius: 3px; border: 1px solid #ddd; flex-grow: 1; min-width: 0; }}
            .yadcf-filter-range-date {{ width: 65px !important; font-size: 0.7rem; }}
            .yadcf-filter-reset-button {{ font-size: 0.75rem; line-height: 1; padding: 0 4px; margin-left: 4px; color: #dc3545; text-decoration: none; border: 1px solid #ddd; border-radius: 3px; background: #fff; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="report-card">
                <div class="d-flex justify-content-between align-items-end mb-2">
                    <div><h1>Job Opportunities</h1></div>
                    <div class="d-flex align-items-center gap-3">
                        <div class="d-flex align-items-center bg-light border rounded px-2 py-1">
                            <label for="fontSize" class="me-2 mb-0" style="font-size: 0.7rem; font-weight: bold; color: #666;">FONT</label>
                            <input type="range" class="form-range" id="fontSize" min="0.6" max="1.1" step="0.05" value="0.82" style="width: 80px; height: 1.2rem;">
                        </div>
                        <div class="text-end">
                            <span class="badge bg-primary">Total: {len(df)}</span>
                            <div class="text-muted" style="font-size: 0.7rem;">Updated: {datetime.now().strftime('%d %b, %H:%M')}</div>
                        </div>
                    </div>
                </div>
                <div class="table-responsive">
                    {df.to_html(index=False, escape=False, classes='table table-sm table-hover border-top', table_id='jobsTable')}
                </div>
            </div>
        </div>

        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://code.jquery.com/ui/1.13.2/jquery-ui.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
        
        <script>
            /* YADCF INLINED JS */
            {yadcf_js if yadcf_js else ''}
            
            $(document).ready(function() {{
                const table = $('#jobsTable').DataTable({{
                    "pageLength": 50,
                    "order": [[ 3, "desc" ]],
                    "autoWidth": false,
                    "dom": "<'row'<'col-sm-12 col-md-6'l><'col-sm-12 col-md-6'f>>" +
                           "<'row'<'col-sm-12'tr>>" +
                           "<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
                    "language": {{ "search": "", "searchPlaceholder": "Global Search..." }}
                }});

                yadcf.init(table, [
                    {{ column_number: 1, filter_type: "select", filter_default_label: "Company", cumulative_filtering: true, filter_reset_button_text: "&times;" }},
                    {{ column_number: 2, filter_type: "select", filter_default_label: "Location", cumulative_filtering: true, filter_reset_button_text: "&times;" }},
                    {{ column_number: 3, filter_type: "range_date", date_format: "yyyy-mm-dd", filter_delay: 500, filter_reset_button_text: "&times;" }}
                ]);

                $('#fontSize').on('input', function() {{
                    $('.table').css('font-size', $(this).val() + 'rem');
                }});
            }});
        </script>
    </body>
    </html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✅ Report generated successfully: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a static HTML report from the jobs database.")
    parser.add_argument("--db", type=str, required=True, help="Path to the SQLite database.")
    parser.add_argument("--output", type=str, default="job_report.html", help="Path to the output HTML file.")
    
    args = parser.parse_args()
    generate_html(args.db, args.output)
