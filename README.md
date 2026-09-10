# AI-Based Disaster Response Management System

**Resource allocation and relief coordination command center** — ingest live disasters, estimate impact and AI demand, optimize depot allocation, route field missions, and export situation reports.

[![Repository](https://img.shields.io/badge/repo-ai--disaster--response--system-blue)](https://github.com/arnavt866/ai-disaster-response-system)

---

## What it does

Coordinators use a single web dashboard to:

- View **USGS / GDACS** disaster feeds and **NDMA** early warnings
- Map **impact zones** with WorldPop population and OSM building density
- Run **ML demand prediction** (food, water, medical, shelter) per zone
- **Optimize allocation** from relief depots with OR-Tools
- Generate **road routes** and **field missions**
- Review **analytics reports** and download **post-event situation reports**

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| **Backend** | Python, FastAPI, SQLAlchemy, Alembic, PostGIS |
| **Database** | PostgreSQL + PostGIS |
| **ML** | scikit-learn (Ridge regression), joblib |
| **Optimization** | Google OR-Tools, NetworkX (road routing) |
| **Frontend** | React, Vite, Leaflet, Recharts |
| **Auth** | JWT (commander login) |
| **Deploy** | Docker Compose |

---

## Quick start (Docker)

**Prerequisites:** Docker Desktop, Git

```bash
git clone https://github.com/arnavt866/ai-disaster-response-system.git
cd ai-disaster-response-system
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API docs** | http://localhost:8000/docs |

**Default login:** `commander` / `commander`

On first boot the backend runs migrations and loads a demo DB snapshot when present under `backend/snapshots/`.

---

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp ..\.env.example ..\.env      # set DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — set `VITE_API_URL=http://127.0.0.1:8000` if needed.

---

## Project structure

```
├── backend/          FastAPI app, models, services, migrations, tests
├── frontend/         React dashboard (Vite)
├── docker-compose.yml
├── scripts/          Docker helpers and demo snapshot export
└── .env.example      Environment template
```

---

## Data & models (not in Git)

Large assets are **gitignored** and must be placed locally:

| Asset | Typical path |
|-------|----------------|
| WorldPop rasters | `backend/data/population/` |
| India OSM PBF | `backend/data/osm/` |
| Trained ML models | `backend/models/` |
| Historical DESINVENTAR XML | `backend/data/{orissa,tamil_nadu,uttarakhand}/` |
| Demo DB snapshot | `backend/snapshots/demo_snapshot.sql.gz` |

Import scripts live under `backend/scripts/` (e.g. `import_cems_data.py`, `build_chennai_scenario.py`).

---

## Main pages

| Page | Purpose |
|------|---------|
| **Dashboard** | KPIs, map, AI demand strip, operational summary |
| **Disasters** | Ingested incidents, advisories, situation reports |
| **Zones** | Impact zones, severity, priority |
| **Resources** | Depot inventory and stock |
| **AI Demand** | ML predictions + scenario simulation |
| **Operations** | Run optimizer, generate routes, create missions |
| **Missions / Teams** | Field delivery lifecycle |
| **Reports** | Allocation analytics charts |
| **Satellite** | Sentinel scene lookup |

---

## Tests

```bash
# Backend
cd backend && pytest

# Frontend E2E (backend must be running)
cd frontend && npx playwright test
```

---

## Authors

**Arnav Thapliyal** — [GitHub](https://github.com/arnavt866)

---

## License

Academic / internship project — see repository history for milestone tags.
