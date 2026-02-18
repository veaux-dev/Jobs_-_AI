#!/usr/bin/env bash

# Usage: ./publish_report.sh [profile_name]
# Example: ./publish_report.sh bil

PROFILE=${1:-"bil"}
BASE_DIR=$(pwd)
VENV="$BASE_DIR/.venvlinux/bin/python"
DIST_DIR="$BASE_DIR/data/dist_$PROFILE"
DB_FILE="$BASE_DIR/data/vacantes_$PROFILE.db"

# --- Cargar Variables de Entorno ---
if [ -f "$BASE_DIR/.env-$PROFILE" ]; then
    echo "env: Loading $BASE_DIR/.env-$PROFILE"
    export $(grep -v '^#' "$BASE_DIR/.env-$PROFILE" | xargs)
elif [ -f "$BASE_DIR/.env" ]; then
    echo "env: Loading $BASE_DIR/.env"
    export $(grep -v '^#' "$BASE_DIR/.env" | xargs)
fi

echo "📄 Step 1: Regenerating HTML report..."
mkdir -p "$DIST_DIR"
# Generamos el reporte con la lógica más reciente del script de Python
"$VENV" exporter/html_report.py --db "$DB_FILE" --output "$DIST_DIR/report_$PROFILE.html"

if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo "❌ Error: CLOUDFLARE_API_TOKEN no configurada."
    exit 1
fi

echo "☁️ Step 2: Publishing to Cloudflare Pages..."
# npx --yes evita que pida confirmación para instalar wrangler
CLOUDFLARE_ACCOUNT_ID=$CLOUDFLARE_ACCOUNT_ID npx --yes wrangler pages deploy "$DIST_DIR" --project-name "chambas-$PROFILE" --commit-dirty=true

REPORT_URL="https://chambas-$PROFILE.pages.dev/report_$PROFILE.html"

echo "✅ Report published at: $REPORT_URL"

# Opcional: Mandar a Discord también si quieres avisar del cambio
if [ -n "$DISCORD_WEBHOOK_URL" ]; then
    echo "📤 Sending updated link to Discord..."
    curl -X POST -H "Content-Type: application/json" \
         -d "{\"content\": \"🔄 **Reporte Actualizado:** Aquí tienes el link corregido con los últimos parches: $REPORT_URL\"}" \
         "$DISCORD_WEBHOOK_URL"
fi
