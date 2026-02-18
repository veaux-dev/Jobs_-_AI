import os
import subprocess
import zipfile
from datetime import datetime

webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

if not webhook_url:
    print("❌ Error: DISCORD_WEBHOOK_URL no está configurada.")
    exit(1)

# 1. Crear el HTML
html_file = "/tmp/reporte_oportunidades.html"
with open(html_file, "w") as f:
    f.write("<html><body><h1>Reporte de Empleos</h1><p>Hola Cuñado, aqui estan las vacantes.</p></body></html>")

# 2. Comprimirlo en un ZIP
zip_file = "/tmp/Reporte_Chamba.zip"
with zipfile.ZipFile(zip_file, 'w') as z:
    z.write(html_file, arcname="Reporte_Oportunidades.html")

msg = "¡INSEEEEECTO! Te mando el reporte comprimido para que Discord no se ponga nena. 🐉"

print(f"🚀 Enviando ZIP a Discord...")

cmd = [
    "curl", "-X", "POST",
    "-F", f"file=@{zip_file}",
    "-F", f"payload_json={{\"content\": \"{msg}\"}}",
    webhook_url
]

subprocess.run(cmd)
print("✅ ZIP enviado. ¿Qué tal se ve ahora en tu PC y iPhone?")
