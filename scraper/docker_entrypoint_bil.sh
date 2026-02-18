#!/usr/bin/env bash
# This script runs inside the Docker container for the BIL profile
set -e

# Asegurar que estamos en el directorio correcto para imports
cd /app

echo "🔎 Starting Scraping for BIL..."
python scraper/linkedin_public_mvp.py --profile bil

echo "📄 Generating HTML Report..."
python exporter/html_report.py --db /app/data/vacantes_bil.db --output /app/data/report_bil.html

if [ -n "$DISCORD_WEBHOOK_URL" ]; then
    NEW_JOBS=$(cat /tmp/new_jobs_count.txt || echo "0")
    
    if [ "$NEW_JOBS" -eq "0" ]; then
        MSG="No encontré nada nuevo hoy... LinkedIn está más seco que desierto. 🌵"
    else
        # Array de frases graciosas (versión extendida + DBZ)
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
            "¡Es más de 8000! (Bueno, en realidad son $NEW_JOBS, pero tú entiendes). ¡Dale con todo! 💥"
            "¡Kakaroto! Encontré $NEW_JOBS vacantes nuevas. ¡Usa el Kaio-ken para mandar ese CV! 🐉"
            "¡Eleva tu Ki al máximo! Hay $NEW_JOBS oportunidades esperándote. ¡KAME-HAME-HAAAA! ☄️"
            "¿Quieres las Esferas del Dragón? Mejor llévate estas $NEW_JOBS vacantes nuevas. 💫"
            "¡Ni Freezer se atrevió a tanto! $NEW_JOBS vacantes nuevas listas para conquistar. 🛸"
        )
        
        # Seleccionar una al azar
        RANDOM_INDEX=$(( RANDOM % ${#PHRASES[@]} ))
        MSG=${PHRASES[$RANDOM_INDEX]}
    fi

    # 6. Cloudflare Pages Deployment inside Docker
    if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
        echo "☁️ Deploying to Cloudflare Pages..."
        DIST_DIR="/app/data/dist_bil"
        mkdir -p "$DIST_DIR"
        # En docker lo guardamos directamente como report_bil.html
        cp /app/data/report_bil.html "$DIST_DIR/report_bil.html"
        
        # Desplegar a Cloudflare
        CLOUDFLARE_ACCOUNT_ID=$CLOUDFLARE_ACCOUNT_ID npx --yes wrangler pages deploy "$DIST_DIR" --project-name "chambas-bil" --commit-dirty=true
        
        REPORT_URL="https://chambas-bil.pages.dev/report_bil.html"
    fi

    if [ -n "$REPORT_URL" ]; then
        echo "📤 Sending link to Discord..."
        curl -X POST -H "Content-Type: application/json" \
             -d "{\"content\": \"$MSG\n\n🔗 **Ver reporte:** $REPORT_URL\"}" \
             "$DISCORD_WEBHOOK_URL"
    else
        echo "📤 Sending report to Discord with message: $MSG"
        curl -X POST \
             -F "file=@/app/data/report_bil.html" \
             -F "payload_json={\"content\": \"$MSG\"}" \
             "$DISCORD_WEBHOOK_URL"
    fi
fi

echo "✅ BIL Pipeline Finished."
