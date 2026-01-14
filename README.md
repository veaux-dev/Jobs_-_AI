# Jobspy

Modular job scraping and analysis system for job tracking.  
Built with Python, SQLite, Streamlit, and Docker.

---

## 📂 Project Structure

Jobspy/
├── analyzer/ # Classification, scoring, LLM integration
│ ├── classifier.py
│ ├── empresa_info.py
│ ├── prompts.py
│ ├── requirements.txt
│ ├── scoring.py
│ └── tu_llm_wrapper.py
│
├── data/ # Local DB and logs (ignored in git)
│ ├── scraper.log
│ └── vacantes.db
│
├── frontend/ # Streamlit frontend
│ ├── Dockerfile
│ ├── requirements.txt
│ └── visor.py
│
├── scraper/ # Scraper engine
│ ├── db_vacantes.py
│ ├── Dockerfile
│ ├── requirements.txt
│ └── Run_Scraper.py
│
├── .gitignore
├── .dockerignore
└── docker_compose.yml



> `data/` is excluded from version control.  
> It contains your SQLite database (`vacantes.db`) and logs.

---

## 🚀 Getting Started

### Clone the repo
```bash
git clone https://github.com/veaux-dev/Jobs_-_AI.git
```

### Scraper (local run)
```bash
cd scraper
pip install -r requirements.txt
python Run_Scraper.py
```

### Frontend
```bash
cd frontend
pip install -r requirements.txt
streamlit run visor.py
```

### Docker Compose (scraper + frontend)
```bash
docker-compose up --build
```

---

## 🧩 Modules

- **Scraper** → Collects job postings (LinkedIn, Indeed, etc.) and stores them in `vacantes.db`.
- **Analyzer** → Classifies and scores job postings using custom LLM wrappers.
- **Frontend** → Streamlit app for visualization and review of vacancies.

---

## 📌 Roadmap
- [x] Scraper with deduplication and DB integration  
- [x] Initial LLM wrapper for classification  
- [x] Company enrichment (`empresa_info`) automation  
- [x] Full analyzer pipeline integration  
- [x] Deployment with auto-updating Docker in Portainer  

---

## ⚙️ .gitignore
```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
.env
.venv/

# Data
data/*
!data/.gitkeep

# OS
.DS_Store
Thumbs.db
```

## ⚙️ .dockerignore
```dockerignore
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
.env
.venv/

data/*
.git
.gitignore
docker-compose.yml
README.md
```

---

## ⚖️ License
MIT License – free to use and adapt.
