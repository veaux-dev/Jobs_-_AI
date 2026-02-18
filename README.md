# Jobspy 🐉🚀

Modular job scraping and analysis system. Now with **multi-profile support**, automated **Cloudflare Pages** deployment, and **Discord** notifications.

---

## 📂 Project Structure

Jobspy/
├── analyzer/           # AI Classification & Scoring (Ollama)
├── data/               # SQLite DBs, Configs & Logs (ignored in git)
│   ├── config_scraper.yaml  # Your config
│   ├── config_bil.yaml      # Brother-in-law config
│   └── dist_bil/            # HTML reports for deployment
├── exporter/           # Static HTML Report Generator
│   └── html_report.py       # Premium interactive template
├── frontend/           # Streamlit dashboard
└── scraper/            # Scraper engine
    ├── linkedin_public_mvp.py # Current working scraper
    ├── docker_entrypoint_bil.sh # Automation for BIL profile
    └── db_vacantes.py       # Database logic

---

## 🚀 Getting Started

### 1. Multi-Profile Runner (Local)
To run a specific profile (e.g., `bil`), use the new orchestrator:
```bash
./run_profile.sh bil
```
This script handles: Scraping → HTML Generation → Cloudflare Upload → Discord Notification.

### 2. Manual Export
If you just want to regenerate the HTML report for a database:
```bash
python exporter/html_report.py --db data/vacantes_bil.db --output data/report_bil.html
```

### 3. Deployment (NAS/Docker)
The system is optimized for **Portainer/Docker Compose**.
- **Main Scraper**: Runs your personal AI pipeline.
- **BIL Scraper**: Runs the LinkedIn MVP, generates a compact report, and pushes it to Cloudflare Pages.

---

## 🤖 Bot Personality (Zeno-Sama)
The BIL pipeline includes a Discord integration that sends random Dragon Ball Z and Mexican-themed messages:
- *"¡INSEEEEECTO! Tu nivel de vacantes es de 9000..."*
- *"¡Habemus chamba! Encontré 15 puestos que te están gritando."*

---

## ⚙️ Environment Variables
For the automated reporting to work, ensure these are set in your `.env` or NAS:
- `CLOUDFLARE_API_TOKEN`: Token with Pages Edit permissions.
- `CLOUDFLARE_ACCOUNT_ID`: Your Cloudflare Account ID.
- `DISCORD_WEBHOOK_URL`: Discord channel webhook.

---

## 🧩 Key Features
- **Excel-style Filters**: Interactive dropdowns and date-range calendars in the HTML report.
- **Ultra-Compact Design**: Data-dense view with dynamic font size slider.
- **Anti-Blocking**: Libraries are inlined in the HTML to avoid browser security blocks (ORB/CORS).
- **Zero Maintenance**: Fully automated daily runs via Docker.

---

## ⚖️ License
MIT License – free to use and adapt.
