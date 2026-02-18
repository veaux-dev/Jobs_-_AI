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

    # Descargar YADCF para inyectarlo
    print("📥 Downloading YADCF for inlining...")
    try:
        yadcf_js = requests.get(YADCF_JS_URL, timeout=10).text
        yadcf_css = requests.get(YADCF_CSS_URL, timeout=10).text
    except Exception as e:
        print(f"⚠️ Warning: Could not download YADCF. Error: {e}")
        yadcf_js = ""
        yadcf_css = ""

    conn = sqlite3.connect(db_path)
    query = "SELECT title as Title, company as Company, location as Location, date as Posted, link as Link FROM vacantes WHERE status != 'closed' ORDER BY date DESC, scraped_at DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("No active jobs found in database to export.")
        return

    # Limpieza para evitar errores en JS
    for col in ['Title', 'Company', 'Location']:
        df[col] = df[col].astype(str).str.replace("'", "’", regex=False)

    df['Link'] = df['Link'].apply(lambda x: f'<a href="{x}" target="_blank" class="btn btn-sm btn-primary px-3">OPEN JOB</a>' if x else "")
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Jobs - {datetime.now().strftime('%Y-%m-%d')}</title>
        
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css">
        <link rel="stylesheet" href="https://code.jquery.com/ui/1.13.2/themes/base/jquery-ui.css">
        
        <style>
            /* YADCF INLINED CSS */
            {yadcf_css if yadcf_css else ''}
            
            body {{ background-color: #f0f2f5; padding: 10px; font-family: -apple-system, system-ui, sans-serif; }}
            .report-card {{ background: white; padding: 12px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
            h1 {{ color: #1a1a1a; font-weight: 800; font-size: 1.4rem; margin-bottom: 4px; }}
            
            /* Table Styling */
            .table {{ font-size: 0.85rem; width: 100% !important; border-collapse: collapse !important; }}
            .table th {{ background-color: #f8f9fa; font-weight: 600; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.5px; color: #666; }}
            .table td, .table th {{ padding: 10px 8px !important; border-bottom: 1px solid #eee !important; }}
            
            /* Responsive / Mobile View */
            @media (max-width: 768px) {{
                body {{ padding: 5px; }}
                .report-card {{ padding: 8px; border-radius: 0; box-shadow: none; }}
                
                /* Transform Table to Cards on Mobile */
                thead {{ display: none; }}
                tr {{ 
                    display: block; 
                    margin-bottom: 8px; 
                    border: 1px solid #e0e4e8 !important; 
                    border-radius: 6px; 
                    padding: 8px;
                    background: #fff;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
                }}
                td {{ 
                    display: flex !important; 
                    text-align: left !important; 
                    border: none !important;
                    padding: 3px 0 !important;
                    align-items: flex-start;
                }}
                td::before {{ 
                    content: attr(data-label); 
                    flex: 0 0 35%; /* Ancho fijo para la etiqueta */
                    font-weight: bold; 
                    font-size: 0.65rem;
                    color: #999;
                    text-transform: uppercase;
                    margin-top: 2px;
                }}
                /* Special formatting for specific mobile fields */
                td:first-child {{ font-size: 0.95rem; font-weight: bold; color: #0d6efd; margin-bottom: 4px; display: block !important; }}
                td:first-child::before {{ content: none; }}
                td:last-child {{ margin-top: 8px; border-top: 1px solid #f0f0f0 !important; padding-top: 8px !important; display: block !important; }}
                td:last-child::before {{ content: none; }}
                
                .yadcf-filter-wrapper {{ flex-direction: row; flex-wrap: wrap; gap: 4px; }}
                .yadcf-filter {{ font-size: 0.7rem; padding: 2px; }}
                .dataTables_filter input {{ width: 100% !important; margin-left: 0 !important; margin-top: 5px; }}
            }}

            /* Controls Styling */
            .btn-primary {{ border-radius: 6px; font-weight: bold; font-size: 0.8rem; }}
            .badge {{ font-size: 0.75rem; padding: 5px 10px; }}
            .yadcf-filter-wrapper {{ display: flex !important; align-items: center; margin-top: 4px; }}
            .yadcf-filter {{ font-size: 0.75rem; padding: 4px; border-radius: 4px; border: 1px solid #ccc; flex-grow: 1; }}
            .yadcf-filter-reset-button {{ padding: 2px 8px; margin-left: 5px; background: #fff; border: 1px solid #ddd; border-radius: 4px; color: #d9534f; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="report-card">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div>
                        <h1>Job Report</h1>
                        <p class="text-muted mb-0" style="font-size: 0.7rem; font-weight: 500;">
                            🗓️ Actualizado: {datetime.now().strftime('%d %b %Y, %H:%M')}
                        </p>
                        <span class="badge bg-light text-dark border mt-1">Total: {len(df)} Jobs</span>
                    </div>
                    <div class="d-flex align-items-center bg-light border rounded px-2 py-1">
                        <label for="fontSize" class="me-2 mb-0" style="font-size: 0.65rem; font-weight: bold;">TEXT</label>
                        <input type="range" class="form-range" id="fontSize" min="0.6" max="1.2" step="0.05" value="0.85" style="width: 60px;">
                    </div>
                </div>
                
                <div class="table-responsive">
                    <table id="jobsTable" class="table table-hover">
                        <thead>
                            <tr>
                                <th>Title</th>
                                <th>Company</th>
                                <th>Location</th>
                                <th>Posted</th>
                                <th>Link</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'<tr><td data-label="Title">{row["Title"]}</td><td data-label="Company">{row["Company"]}</td><td data-label="Location">{row["Location"]}</td><td data-label="Posted">{row["Posted"]}</td><td>{row["Link"]}</td></tr>' for _, row in df.iterrows()])}
                        </tbody>
                    </table>
                </div>
                <div class="mt-3 text-center border-top pt-2">
                    <p class="text-muted mb-0" style="font-size: 0.75rem; font-weight: 500;">
                        🗓️ Reporte actualizado: {datetime.now().strftime('%d %b %Y, %H:%M')}
                    </p>
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
                    "dom": "<'row'<'col-12'f>><'row'<'col-12'tr>><'row'<'col-12'p>>",
                    "language": {{ "search": "", "searchPlaceholder": "Quick Search..." }}
                }});

                yadcf.init(table, [
                    {{ column_number: 1, filter_type: "select", filter_default_label: "Company", cumulative_filtering: true }},
                    {{ column_number: 2, filter_type: "select", filter_default_label: "Location", cumulative_filtering: true }},
                    {{ column_number: 3, filter_type: "range_date", date_format: "yyyy-mm-dd", filter_delay: 500 }}
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
    
    print(f"✅ Mobile-Ready Report generated: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a mobile-ready HTML report.")
    parser.add_argument("--db", type=str, required=True, help="Path to database.")
    parser.add_argument("--output", type=str, required=True, help="Path to output.")
    args = parser.parse_args()
    generate_html(args.db, args.output)
