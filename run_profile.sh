#!/usr/bin/env bash

# Usage: ./run_profile.sh [profile_name]
# Example: ./run_profile.sh bil

PROFILE=${1:-"bil"}
BASE_DIR=$(pwd)
VENV="$BASE_DIR/.venvlinux/bin/python"

# --- Cargar Variables de Entorno ---
# Busca .env-bil o .env en la raíz
if [ -f "$BASE_DIR/.env-$PROFILE" ]; then
    echo "env: Loading $BASE_DIR/.env-$PROFILE"
    export $(grep -v '^#' "$BASE_DIR/.env-$PROFILE" | xargs)
elif [ -f "$BASE_DIR/.env" ]; then
    echo "env: Loading $BASE_DIR/.env"
    export $(grep -v '^#' "$BASE_DIR/.env" | xargs)
fi

echo "🚀 Starting Jobspy for profile: $PROFILE (using LinkedIn MVP Scraper)"

# 1. Validate venv
if [ ! -x "$VENV" ]; then
    echo "❌ Error: Linux Virtual Environment not found at $VENV"
    echo "Please ensure you are running this on Linux and .venvlinux is configured."
    exit 1
fi

# 2. Paths
CONFIG_FILE="$BASE_DIR/data/config_$PROFILE.yaml"
DB_FILE="$BASE_DIR/data/vacantes_$PROFILE.db"
# Carpeta para el despliegue de Cloudflare
DIST_DIR="$BASE_DIR/data/dist_$PROFILE"
mkdir -p "$DIST_DIR"
REPORT_FILE="$DIST_DIR/report_$PROFILE.html"

# 3. Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file $CONFIG_FILE not found."
    exit 1
fi

# 4. Run Scraper (MVP version)
echo "🔎 Step 1: Scraping jobs with linkedin_public_mvp..."
"$VENV" scraper/linkedin_public_mvp.py --profile "$PROFILE"

# 5. Generate HTML Report
echo "📄 Step 2: Generating HTML report..."
"$VENV" exporter/html_report.py --db "$DB_FILE" --output "$REPORT_FILE"

# 6. Cloudflare Pages Deployment
if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
    echo "☁️ Step 3: Deploying to Cloudflare Pages..."
    # npx --yes evita que pida confirmación para instalar wrangler en el NAS
    CLOUDFLARE_ACCOUNT_ID=$CLOUDFLARE_ACCOUNT_ID npx --yes wrangler pages deploy "$DIST_DIR" --project-name "chambas-$PROFILE" --commit-dirty=true
    
    # URL directa al archivo
    REPORT_URL="https://chambas-$PROFILE.pages.dev/report_$PROFILE.html"
fi

# 7. Discord Notification
if [ -n "$DISCORD_WEBHOOK_URL" ]; then
    NEW_JOBS=$(cat /tmp/new_jobs_count.txt || echo "0")
    
    if [ "$NEW_JOBS" -eq "0" ]; then
        MSG="No encontré nada nuevo hoy... LinkedIn está más seco que desierto. 🌵"
    else
        PHRASES=(
            "¡Ándale! Hay chamba. Encontré $NEW_JOBS vacantes nuevas. ¡Ponte las pilas! 🚀"
            "El tamaño no importa... pero $NEW_JOBS vacantes nuevas son $NEW_JOBS vacantes. ¡Chécale! 📏"
            "Sobres. No te atragantes, aquí tienes $NEW_JOBS oportunidades fresquecitas. 🌯"
            "¡Habemus chamba! Encontré $NEW_JOBS puestos que te están gritando. 🗣️"
            "Ni el SAT te busca tanto como estas $NEW_JOBS empresas. ¡Suerte! 💸"
            "Ojo aquí: $NEW_JOBS vacantes nuevas. No digas que no te aviso. 🕵️‍♂️"
            "¡A darle que es mole de olla! Encontré $NEW_JOBS oportunidades para ti. 🍲"
            "¿Qué esperas? ¿Una invitación de la Casa Blanca? Aquí hay $NEW_JOBS opciones. 🏛️"
            "Menos Netflix y más CV, que hoy salieron $NEW_JOBS joyitas. 📺"
            "Si el éxito fuera fácil, se llamaría 'dormir hasta mediodía'. ¡Mira estas $NEW_JOBS! ⏰"
            "Más vale vacante en PDF que cien volando. Aquí tienes $NEW_JOBS. 📄"
            "¡Fuga por esa chamba! $NEW_JOBS vacantes listas para el ataque. 🏎️"
            "Saca el CV de la vitrina, que hoy despertamos con $NEW_JOBS ofertas. 💎"
            "¿Buscas chamba o te la mando por Uber? $NEW_JOBS encontradas. 🚗"
            "¡INSEEEEECTO! Tu nivel de vacantes encontradas es de $NEW_JOBS... ¡y aún así no aplicas! 😡"
            "¡Es más de 9000! (Bueno, en realidad son $NEW_JOBS, pero tú entiendes). ¡Dale con todo! 💥"
            "¡Kakaroto! Encontré $NEW_JOBS vacantes nuevas. ¡Usa el Kaio-ken para mandar ese CV! 🐉"
            "¡Eleva tu Ki al máximo! Hay $NEW_JOBS oportunidades esperándote. ¡KAME-HAME-HAAAA! ☄️"
            "¿Quieres las Esferas del Dragón? Mejor llévate estas $NEW_JOBS vacantes nuevas. 💫"
            "¡Ni Freezer se atrevió a tanto! $NEW_JOBS vacantes nuevas listas para conquistar. 🛸"
        )
        RANDOM_INDEX=$(( RANDOM % ${#PHRASES[@]} ))
        MSG=${PHRASES[$RANDOM_INDEX]}
    fi

    if [ -n "$REPORT_URL" ]; then
        # Si hay Cloudflare, mandamos el link (más limpio)
        FINAL_MSG="$MSG\n\n🔗 **Ver reporte:** $REPORT_URL"
        echo "📤 Sending link to Discord..."
        curl -X POST -H "Content-Type: application/json" \
             -d "{\"content\": \"$FINAL_MSG\"}" \
             "$DISCORD_WEBHOOK_URL"
    else
        # Fallback: mandar el archivo si Cloudflare falla o no está configurado
        echo "📤 Sending file to Discord..."
        curl -X POST \
             -F "file=@$REPORT_FILE" \
             -F "payload_json={\"content\": \"$MSG\"}" \
             "$DISCORD_WEBHOOK_URL"
    fi
fi

echo "--------------------------------------------------------"
echo "✅ Done! Execution finished for profile: $PROFILE"
echo "--------------------------------------------------------"
