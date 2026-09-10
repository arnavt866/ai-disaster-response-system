# AI Disaster Response Management System — Master Documentation

Single source of truth for Milestone 1 and Milestone 2 (Weeks 1–4). This document describes the system as implemented in August 2026. It does **not** claim production readiness.

---

## 1. Project Overview and Problem Statement

India faces frequent natural disasters (floods, cyclones, earthquakes, landslides). Relief agencies must allocate food, water, medical kits, and shelter capacity across affected districts under uncertainty and time pressure.

This backend supports:

1. **Milestone 1** — ingest disaster events, estimate impact areas, generate spatial grids, compute rule-based severity and resources, and persist disaster zones.
2. **Milestone 2** — train proxy-demand models on historical NWDP/DESINVENTAR records, predict resource demand with uncertainty intervals, integrate with M1 zones, support dynamic recalibration and scenario simulation.

The system is a research/prototype backend (FastAPI + PostgreSQL). Weeks 5–6 (logistics optimization, routing, dashboard) are **not implemented** *(accurate as of the M1/M2 documentation freeze, 2026-08-17)*. See **§23 Milestone 3 addendum** and `docs/M3_COMPLETION_NOTES.md` for current status after Weeks 5–6 work.

---

## 2. Final Technology Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI 0.141, Uvicorn, Starlette |
| Database | PostgreSQL 17, SQLAlchemy 2.x, Alembic |
| PostGIS | Extension enabled; `disaster_zones.location` (`Geometry POINT`, SRID 4326); spatial queries via GeoAlchemy2 (`ST_DWithin` in `zone_service.get_zones_near_depot`) |
| HTTP clients | httpx, requests |
| Geospatial | Shapely, GeoPandas, PyProj, Fiona, rasterio, rasterstats |
| OSM import | osmium (PBF streaming) |
| ML | scikit-learn, XGBoost, joblib |
| Validation | Pydantic 2.x |
| Config | python-dotenv |
| Testing | pytest |

---

## 3. Complete Architecture

```
External feeds (USGS, GDACS) ──► disaster_events
Local OSM PBF + WorldPop TIF ──► buildings + population
Impact heuristics ──► grid cells ──► severity + rule resources ──► disaster_zones

Historical XML (3 states) ──► normalized CSV ──► proxy targets ──► ML dataset
ML training ──► Ridge models + conformal intervals ──► models/

DisasterZone (M1 DB record + PostGIS location) ──► analyze_grid ──► district overlap ──► M2 predict_demand
Field reports / recalculate ──► prediction_history.jsonl
NDMA SACHET CAP ──► ndma_alerts (early warning only)
Copernicus EMS EMSR357 ──► satellite_assessments ──► in-coverage damage lookup
```

**Geospatial processing:** polygon/area operations run in Python via Shapely and GeoPandas. The database stores scalar `latitude`/`longitude` **and** a PostGIS `location` point on `disaster_zones`. Depot proximity uses `ST_DWithin` on geography casts (`zone_service.get_zones_near_depot`). Road routing for allocation/missions uses cached OSM graphs (NetworkX shortest path) under `data/road_graphs/` when both endpoints fall in a demo region; otherwise Haversine fallback.

---

## 4. Final Folder Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, router registration
│   ├── api/                    # Route handlers
│   ├── config/                 # settings.py, proxy_target_config.json
│   ├── core/                   # logger
│   ├── database/               # SQLAlchemy connection, get_db
│   ├── models/                 # ORM models
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Business logic
│   │   ├── geospatial/         # Grid, impact, population, satellite, districts
│   │   ├── historical/         # M2 data pipeline (B1/B2)
│   │   ├── ingestion/          # OSM PBF, disaster import
│   │   └── prediction/         # M2 ML inference, scenario, history
│   └── utils/
├── data/                       # Local datasets (gitignored): OSM, TIF, XML, GeoJSON
├── datasets/                   # Generated CSV/JSONL/reports
├── docs/                       # MILESTONE2.md, this file
├── logs/                       # app.log (gitignored)
├── migrations/                 # Alembic
├── models/                     # Trained ML artifacts (gitignored)
├── scripts/                    # Data prep, training, smoke tests
├── tests/                      # pytest suite
├── requirements.txt
└── pytest.ini
```

---

## 5. Source File Reference

### API (`app/api/`)

| File | Purpose | Inputs | Outputs | Used by |
|------|---------|--------|---------|---------|
| `disaster_routes.py` | DisasterEvent CRUD | Pydantic schemas | DB records | Frontend, ingestion |
| `zone_routes.py` | DisasterZone CRUD | lat/lon, severity, population | DB records | Manual zone management |
| `inventory_routes.py` | Resource inventory CRUD | resource type, quantity | DB records | Relief logistics (M1) |
| `relief_routes.py` | Relief center CRUD | center location, capacity | DB records | Relief logistics (M1) |
| `gdacs_routes.py` | `GET /gdacs/import` | `GDACS_URL` env | Imported events | External feed |
| `usgs_routes.py` | `GET /usgs/import` | USGS GeoJSON URL | Imported events | External feed |
| `ndma_routes.py` | `GET /ndma/` | DB session | SACHET CAP alerts from `ndma_alerts` | Early warning feed |
| `satellite_routes.py` | `/satellite/nearby`, `/satellite/damage` | lat/lon | Overpass facilities; CEMS damage when in EMSR357 coverage | Spatial context |
| `grid_routes.py` | `GET /grid/generate` | lat/lon, disaster_type | Grid analysis + zones | Core M1 pipeline |
| `impact_routes.py` | `GET /impact/estimate` | lat/lon, disaster_type | Impact polygon only | Pre-grid estimate |
| `building_routes.py` | `POST /buildings/import` | force/confirm flags | OSM PBF → DB | One-time setup |
| `prediction_routes.py` | M2 demand/scenario/history | Feature payloads | ML predictions + intervals | M2 consumers |

### Services — Milestone 1

| File | Purpose |
|------|---------|
| `gdacs_service.py` / `usgs_service.py` | Fetch GeoJSON, dedupe, insert `disaster_events` |
| `ndma_service.py` | Poll SACHET RSS/CAP; parse and upsert `ndma_alerts` (early warning only; not disaster impact) |
| `geospatial/impact_service.py` | Heuristic impact radius + circle polygon |
| `geospatial/grid_service.py` | Clip impact polygon into `GRID_CELL_SIZE` cells |
| `geospatial/grid_analysis_service.py` | Per-cell buildings, population, severity, rule resources |
| `geospatial/population_service.py` | WorldPop zonal stats from local TIF |
| `geospatial/satellite_service.py` | Overpass nearby facilities; Sentinel STAC scene metadata |
| `geospatial/satellite_assessment_service.py` | Copernicus EMS (EMSR357) point-in-polygon damage lookup from `satellite_assessments` |
| `severity_service.py` | Rule-based score 0–100 → Low/Moderate/High/Critical |
| `resource_service.py` | Rule-based food/water/medical/shelter (M1 fallback) |
| `disaster_zone_service.py` | Bulk persist zones from grid analysis |
| `ingestion/building_import_service.py` | Stream `india-latest.osm.pbf` into `buildings` |
| `ingestion/disaster_import_service.py` | Deduped disaster insert |

### Services — Milestone 2

| File | Purpose |
|------|---------|
| `historical/desinventar_parser.py` | Parse NWDP XML `<fichas><TR>` records |
| `historical/historical_normalizer.py` | Normalize fields, dates, disaster types |
| `historical/district_*.py` | Aliases, matching, 80-district validation |
| `historical/proxy_target_generator.py` | Deterministic proxy demand targets |
| `historical/data_preparation.py` | B1 pipeline → `historical_normalized.csv` |
| `historical/phase_b2_preparation.py` | B2 pipeline → `historical_ml_dataset.csv` |
| `prediction/training.py` | Ridge/RF/XGBoost, chronological split |
| `prediction/inference.py` | Load artifacts, `predict_demand`, grid feature mapping |
| `prediction/uncertainty.py` | Split conformal 90% intervals |
| `prediction/vulnerability.py` | WorldPop age/sex weighting when zone cache populated; neutral 1.0 fallback otherwise |
| `prediction/demand_service.py` | Grid recalculation with field overrides |
| `prediction/scenario_service.py` | Response speed + resource availability simulation |
| `prediction/prediction_history.py` | Append-only JSONL audit log |
| `prediction/zone_integration_service.py` | M1 DisasterZone → M2 prediction |
| `geospatial/grid_district_service.py` | EPSG:7755 polygon intersection |

### Config

| File | Purpose |
|------|---------|
| `app/config/settings.py` | Paths, URLs, grid size, timeouts |
| `app/config/proxy_target_config.json` | Approved B2 proxy formulas (do not change) |

### Scripts

| Script | Purpose |
|--------|---------|
| `prepare_historical_data.py` | Run B1 |
| `prepare_ml_dataset.py` | Run B2 |
| `train_demand_models.py` | Train all four targets |
| `api_smoke_test.py` | M2 endpoint smoke test |
| `connectivity_probe.py` | One-off external API audit (not production) |
| `cache_zone_vulnerability.py` | WorldPop age/sex cache onto `disaster_zones` |
| `import_emsr357_cems.py` | Import Copernicus EMS damage into `satellite_assessments` |
| `run_scenario_validation.py` | Compare scenario CSV figures vs predict + allocate |
| `load/run_demo_load_test.py` | Locust load test for key endpoints |

---

## 6. Milestone 1 — Components and Data Flow

### CRUD

- **Disasters** (`/disasters/*`) — event metadata from feeds or manual entry
- **Zones** (`/zones/*`) — affected areas with centroid, severity level, population
- **Inventory** (`/inventory/*`) — relief stock tracking
- **Relief centers** (`/relief-centers/*`) — shelter/distribution points

### Ingestion

- **GDACS** — `GET /gdacs/import` requires `GDACS_URL` in `.env`
- **USGS** — `GET /usgs/import` defaults to USGS all-day GeoJSON
- **NDMA** — `GET /ndma/` polls SACHET RSS/CAP and returns parsed alerts from `ndma_alerts` (early warning only; does not create `disaster_events`)
- **Buildings** — `POST /buildings/import` streams local OSM PBF

### OSM and Population

- **OSM PBF:** `data/osm/india-latest.osm.pbf` (2026 extract) → `buildings` table
- **Population TIF:** `data/population/india_population.tif` (WorldPop) → zonal sum per grid cell

### Impact → Grid → Severity → Resources → DisasterZone

```
GET /grid/generate?latitude=&longitude=&disaster_type=&magnitude=&alert_level=
  1. compute_impact_area() → radius_km + circle polygon
  2. generate_grid() → list of cell polygons (0.02°)
  3. For each cell: analyze_grid()
       - buildings in cell (bbox + point-in-polygon)
       - estimate_population() from TIF
       - calculate_severity(pop, buildings, radius)
       - calculate_resources(pop, severity_level)
  4. create_disaster_zones() → persist centroid + severity + population
  5. Return totals + per-cell geometry + analysis
```

**Disaster type codes:** `EQ`, `FL`, `TC`.

**Severity scoring:** population (0–40) + buildings (0–40) + radius (0–20) → level thresholds at 40/60/80.

**Rule resources:** severity multipliers Critical 1.5, High 1.2, Moderate 1.0, Low 0.7.

---

## 7. Milestone 1 Limitations and Deliberate Decisions

1. Impact radius is **heuristic**, not satellite-derived.
2. Zones store **centroid only** — full grid geometry is returned in API but not persisted. Persisted coordinates are the geometric centroid of each grid-cell polygon.
3. GDACS requires explicit `GDACS_URL` configuration.
4. NDMA SACHET provides early-warning CAP alerts only (not verified impact data).
5. Satellite **damage** outside Copernicus EMS coverage falls back to STAC metadata with `Unknown` classification; in EMSR357 coverage, CEMS classifications are returned from `satellite_assessments`.
6. `/satellite/nearby` uses live Overpass (may timeout); failures return empty facilities safely.
7. `building_service.py` and `osm_service.py` are unused legacy stubs.

---

## 8. Milestone 2 Historical Data

| Item | Value |
|------|-------|
| Source | NWDP DESINVENTAR XML exports |
| States | Odisha, Tamil Nadu, Uttarakhand |
| Records | 33,032 normalized |
| Target districts | 80 in `district_target_states.geojson` |
| Districts with XML data | 73 unique GeoJSON districts |
| Unmatched | 7 newer Tamil Nadu districts (no historical XML) |

**XML structure:** `<fichas>` containing `<TR>` records with child elements for impact variables (deaths, injuries, houses, sectors, etc.). No observed food/water/medical/shelter labels exist in XML.

**Normalization:** state/district spelling, disaster type mapping, safe numeric parsing, event date extraction.

**District matching:** explicit alias table (`district_aliases.py`), fuzzy token normalization, reconciliation reports in `datasets/reports/`.

**Day-1 decision:** Real historical records + deterministic proxy targets were used instead of a synthetic dataset because real NWDP data was obtained and observed demand labels were absent.

---

## 9. Proxy-Target Methodology

**Method:** `impact_based_proxy_v1`  
**`target_is_observed`:** `false` (never claim observed consumption)

### Coefficients (`proxy_target_config.json`)

| Coefficient | Value |
|-------------|-------|
| `assumed_persons_per_family` | 4 |
| `food_packets_per_person` | 1.0 |
| `water_units_per_person` | 3.0 |
| `medical_kits_per_injury` | 0.5 |
| `medical_population_rate` | 0.02 |
| `death_severity_indicator_weight` | 0.001 |
| `shelter_per_destroyed_house` | 1.0 |
| `shelter_per_damaged_house` | 0.25 |

### Formulas

1. **relief_population** = `max(affected_population, evacuated_population)`; if zero and families > 0: `affected_families × 4`
2. **food_packets_demand** = `ceil(relief_population × 1.0)`
3. **water_demand** = `ceil(relief_population × 3.0)`
4. **medical_kits_demand** = `ceil((injuries × 0.5 + relief_population × 0.02) × (1 + deaths × 0.001))`
5. **shelter_capacity_demand** = `ceil(max(evacuated, houses_destroyed × 1.0 + houses_damaged × 0.25, family fallback))`

**Why proxies:** Historical XML contains impact variables only. Proxy targets enable supervised learning for prototype comparison. They are **not** ground-truth consumption.

---

## 10. ML Pipeline

### Features (30)

Categorical: `disaster_type_normalized`, `state_normalized`, `district_normalized`  
Temporal: `event_year`, `event_month`  
Impact: deaths, injuries, affected/evacuated population, houses, sectors, etc.  
(See `feature_schema.py` → `ML_FEATURE_COLUMNS`)

### Targets (4)

`food_packets_demand`, `water_demand`, `medical_kits_demand`, `shelter_capacity_demand`

### Preprocessing

Median imputation, OneHotEncoder for categoricals, StandardScaler for Ridge.

### Split

Chronological by `event_year`: train ≤2003, validation 2004–2010, test 2011–2019.

### Models compared

| Model | Role |
|-------|------|
| Ridge | Linear baseline — **selected for all 4 targets** after comparison with Random Forest and XGBoost on validation RMSE |
| Random Forest | Nonlinear ensemble |
| XGBoost | Boosted trees |

**Selection:** lowest validation RMSE per target.

### Artifacts (`models/`)

Per target: `pipeline.joblib`, `conformal.joblib`, `metadata.json`  
Registry: `model_registry.json` (`model_version: milestone2_v1`)

### Limitations

- Proxy targets, not observed demand
- Zero-inflated historical impacts
- Current-event prediction maps M1 grid stats; many historical fields default to 0
- Distribution shift between historical and live events

---

## 11. Uncertainty

**Method:** Split conformal prediction with absolute residuals (`alpha=0.1` → 90% nominal coverage).

**API fields:** `prediction_interval_lower`, `prediction_interval_upper`, `uncertainty_method: split_conformal_abs_residual`

**Interpretation:** Prediction intervals, not classical confidence intervals. Coverage assumes exchangeability; may degrade under shift.

---

## 12. Vulnerability

Historical XML lacks elderly/children/medically-dependent demographics.

- **Default:** `vulnerability_factor = 1.0` when `data_available=false`
- **Optional API input:** ratios via `VulnerabilityInput` schema
- **No fabricated demographics**

---

## 13. Grid/District Intersection

- **CRS:** EPSG:7755 projected CRS used for area-based polygon intersection
- **Method:** Polygon intersection, not centroid assignment
- **One-to-many:** Single grid cell may overlap multiple districts
- **Normalization:** Overlap proportions sum to 1.0
- **Primary district:** Highest overlap proportion used for state/district ML features

---

## 13a. PostgreSQL / PostGIS Usage

| Aspect | Current behavior (2026-09) |
|--------|----------------------------|
| PostGIS extension | Enabled; required for `disaster_zones.location` |
| Database geometry columns | `disaster_zones.location` — `Geometry(POINT, 4326)` with GiST index |
| Spatial queries in SQL | `ST_DWithin` on geography casts in `zone_service.get_zones_near_depot` |
| Runtime geospatial stack | Shapely, GeoPandas, PyProj, rasterio/rasterstats for in-process geometry and raster work |
| Alembic | Ignores reflected `spatial_ref_sys` if present (`migrations/env.py`) |

Zones also store scalar `latitude`/`longitude` for APIs and ML features. Full grid cell polygons are not persisted on the zone row.

---

## 14. Dynamic Recalibration

- **Field reports:** `field_report_overrides` on grid/zone endpoints update feature values without retraining
- **Recalculate:** `POST /prediction/demand/zone/{id}/recalculate`
- **History:** `datasets/prediction_history.jsonl` — zone_id, timestamp, update_source, model_version, predictions + intervals
- **Satellite damage:** Copernicus EMS EMSR357 features in `satellite_assessments` (4,354 rows as of 2026-09); outside coverage, STAC metadata only with `Unknown` damage

---

## 15. Scenario Simulation

`POST /prediction/scenario`

| Parameter | Effect |
|-----------|--------|
| `response_speed_factor` | Slower response → higher `effective_severity = severity / response_speed` |
| `resource_availability_factor` | Scarcer resources → higher `scenario_adjusted_estimate = point / availability` |
| `severity_multiplier` | Direct demand scaling |

Does not retrain models.

---

## 16. Complete API Reference

### Health

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check |

### Milestone 1

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/disasters/` | DisasterEventCreate | Created event |
| GET | `/disasters/` | — | List events |
| GET | `/disasters/{id}` | — | Single event |
| PUT | `/disasters/{id}` | DisasterEventUpdate | Updated event |
| DELETE | `/disasters/{id}` | — | Deleted event |
| POST | `/zones/` | DisasterZoneCreate | Created zone |
| GET | `/zones/` | — | List zones |
| GET | `/zones/{id}` | — | Single zone |
| PUT | `/zones/{id}` | DisasterZoneUpdate | Updated zone |
| DELETE | `/zones/{id}` | — | Deleted zone |
| POST | `/inventory/` | ResourceInventoryCreate | Created inventory |
| GET | `/inventory/` | — | List inventory |
| GET | `/inventory/{id}` | — | Single inventory |
| PUT | `/inventory/{id}` | ResourceInventoryUpdate | Updated |
| DELETE | `/inventory/{id}` | — | Deleted |
| POST | `/relief-centers/` | ReliefCenterCreate | Created center |
| GET | `/relief-centers/` | — | List centers |
| GET | `/relief-centers/{id}` | — | Single center |
| PUT | `/relief-centers/{id}` | ReliefCenterUpdate | Updated |
| DELETE | `/relief-centers/{id}` | — | Deleted |
| GET | `/gdacs/import` | — | Import GDACS events |
| GET | `/usgs/import` | — | Import USGS events |
| GET | `/ndma/` | — | SACHET CAP alerts (`ndma_alerts`; early warning) |
| GET | `/satellite/nearby` | `latitude`, `longitude`, `radius` | Nearby OSM facilities |
| GET | `/satellite/damage` | `latitude`, `longitude` | CEMS damage when in EMSR357 coverage; else STAC + Unknown |
| GET | `/impact/estimate` | `latitude`, `longitude`, `disaster_type`, optional `magnitude`, `alert_level` | Impact polygon |
| GET | `/grid/generate` | Same as impact + `disaster_type` | Full grid analysis + zones |
| POST | `/buildings/import` | `force`, `confirm` query params | Import OSM PBF |

### Milestone 2

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/prediction/model` | — | Model registry metadata |
| GET | `/prediction/evaluation` | — | Comparison metrics |
| GET | `/prediction/history` | `limit` | Recent prediction history |
| POST | `/prediction/demand` | `DemandPredictionRequest` | `resource_estimates` + intervals |
| POST | `/prediction/demand/grid` | `GridDemandPredictionRequest` | Grid demand + district overlap |
| POST | `/prediction/demand/zone/{zone_id}` | Optional `ZoneRecalculateRequest` | M1-integrated demand |
| POST | `/prediction/demand/zone/{zone_id}/recalculate` | `ZoneRecalculateRequest` | Field-report recalculation |
| POST | `/prediction/scenario` | `ScenarioPredictionRequest` | Scenario-adjusted predictions |

**`POST /prediction/demand` response shape:** `resource_estimates` dict per target with `point_estimate`, `prediction_interval_lower`, `prediction_interval_upper`, `target_is_observed: false`.

### Milestone 3

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/allocation/status` | — | Optimizer metadata |
| POST | `/allocation/optimize` | `zone_ids`, `persist`, optional `confirm_all_zones` | LP allocation + flows |
| GET | `/allocation/history` | — | Persisted allocation records |
| POST | `/allocation/zones/{id}/priority` | priority level | Updated zone |
| POST | `/allocation/zones/{id}/recalculate` | — | Re-run allocation for zone |
| POST | `/allocation/route` | depot + zone coords | Road route (GraphML) or Haversine fallback |
| GET | `/analytics/dashboard` | — | Operational KPIs |
| GET/POST/PATCH | `/field-teams/*`, `/missions/*` | — | Teams and mission lifecycle |

List endpoints `GET /zones/` and `GET /disasters/` return paginated `{total, offset, limit, records}`.

---

## 17. Testing Strategy and Current Results

Run: `cd backend && python -m pytest tests/ -v`

| Test module | Coverage |
|-------------|----------|
| `test_milestone1_regression.py` | M1 route existence, NDMA/satellite fallbacks |
| `test_desinventar_parser.py` | XML parsing |
| `test_district_matching*.py` | 80-district matching |
| `test_proxy_targets.py` | Proxy formulas |
| `test_ml_training.py` | Training, artifacts, inference |
| `test_prediction_api.py` | M2 API endpoints |
| `test_prediction_edge_cases.py` | Invalid zone, intervals, history |
| `test_scenario_simulation.py` | Scenario math |
| `test_vulnerability.py` | WorldPop cache weighting + neutral fallback |
| `test_grid_district_intersection.py` | Polygon overlaps |
| `test_satellite_service.py` | Mocked Overpass/STAC |
| `test_ndma_service.py` | Mocked SACHET CAP ingestion |
| `test_m3_allocation.py` | Allocation LP, routing, priority, transport cap |
| `test_m3_resource_tracking.py` | Inventory reservation and mission side effects |
| `test_road_routing.py` | Road graph shortest path (mocked tiny graph) |
| `test_worldpop_vulnerability.py` | WorldPop vulnerability weighting |
| `conftest.py` | SAVEPOINT-based DB isolation for tests |

External APIs are **mocked in tests**. Live connectivity audited separately via `scripts/connectivity_probe.py`.

---

## 18. External Data Sources

| Source | Purpose | Local/Live | Availability (2026-08-17) | Limitations |
|--------|---------|------------|---------------------------|-------------|
| USGS GeoJSON | Earthquake feed | Live | Implemented (default URL) | US events focus |
| GDACS | Global disaster alerts | Live | Implemented when `GDACS_URL` set | Must configure |
| NDMA SACHET | India early-warning CAP | Live RSS/CAP | Implemented via SACHET RSS/CAP → `ndma_alerts` | Early warning only; not verified disaster impact or zone creation |
| Overpass API | Nearby facilities | Live | Best-effort live query | Often slow/timeout; safe empty fallback |
| EarthSearch STAC | Sentinel-2 catalog | Live | Implemented (public, no creds) | Used for metadata when outside EMS coverage; damage level Unknown |
| Copernicus EMS EMSR357 | Flood damage polygons | Local DB import | Implemented via imported EMSR357 polygons (4,354 features in `satellite_assessments`) | Single activation coverage only; elsewhere STAC + Unknown |
| Copernicus STAC | Sentinel-2 catalog | Live | Timeout in audit | Credentials may be needed for reliable access |
| OSM PBF `india-latest.osm.pbf` | Buildings | Local 2026 | Required for grid analysis | Large file, gitignored |
| WorldPop TIF | Population | Local 2026 | Required for population estimate | Current snapshot, not historical |
| NWDP XML | Historical impacts | Local | 33,032 records | 3 states only |
| `district_target_states.geojson` | District boundaries | Local | 80 districts | 7 TN districts without XML |

---

## 19. Known Limitations

1. Proxy ML targets are not observed resource consumption.
2. NDMA SACHET is early-warning CAP only (not verified impact or zone creation).
3. Satellite damage lookup requires Copernicus EMS import; outside EMSR357 coverage, damage is Unknown.
4. M1 zones store centroid lat/lon plus PostGIS point; full grid cell polygons are not persisted on the zone row.
5. Overpass and Copernicus STAC may be unreliable without retries/alternate endpoints.
6. GDACS requires environment configuration.
7. ML models trained on historical proxy labels may not generalize to live events.
8. Vulnerability weighting uses cached WorldPop age/sex on zones when populated (`scripts/cache_zone_vulnerability.py`); otherwise neutral 1.0.

---

## 20. How to Run

### Install

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Configure (`.env`)

```
DATABASE_URL=postgresql://user:pass@localhost:5432/disaster_db
GDACS_URL=<gdacs geojson url>   # optional
NDMA_SACHET_RSS_URL=              # SACHET CAP RSS feed (see settings.py)
NDMA_SACHET_CAP_URL=              # optional CAP detail base URL
OVERPASS_URL=                   # optional override
SENTINEL_STAC_URL=              # optional override
```

### Database

```bash
alembic upgrade head
```

### Provision local data

Place under `backend/data/`:
- `osm/india-latest.osm.pbf`
- `population/india_population.tif`
- Historical XML and GeoJSON (see `settings.py`)

### Import buildings (once)

```bash
curl -X POST "http://localhost:8000/buildings/import?confirm=true"
```

### Train models (M2)

```bash
python scripts/prepare_historical_data.py
python scripts/prepare_ml_dataset.py
python scripts/train_demand_models.py
```

### Start backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run tests

```bash
python -m pytest tests/ -v
```

### Smoke tests

```bash
set PYTHONPATH=.
python scripts/api_smoke_test.py
```

---

## 21. Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `503` on `/prediction/*` | Missing `models/model_registry.json` | Run `train_demand_models.py` |
| Grid population always 0 | TIF missing | Add `data/population/india_population.tif` |
| Building count 0 | PBF not imported | `POST /buildings/import` |
| GDACS import fails | `GDACS_URL` empty | Set in `.env` |
| Overpass timeout | External server slow | Retry; endpoint returns safe empty result |
| Zone prediction 404 | Zone ID not in DB | Create via `/grid/generate` or `/zones/` |
| Tests skip ML tests | Artifacts absent | Train models or accept skips |

---

## 22. Future Weeks 5–6 Integration Plan (Architectural Only)

> **Historical (M1/M2 freeze, 2026-08-17):** The text below describes the planned scope before Milestone 3 was implemented. M3 delivered OR-Tools allocation, mission lifecycle, field teams, analytics dashboard, and frontend integration. See **§23 Milestone 3** and `docs/M3_COMPLETION_NOTES.md` for what is now in place.

**Not implemented** *(as of 2026-08-17)*. Planned extensions:

1. **Logistics optimization** — OR-Tools or similar for vehicle routing and resource allocation from predicted demand to relief centers/inventory.
2. **Dashboard** — Frontend consuming `/grid/generate`, `/prediction/demand/zone/{id}`, scenario endpoints.
3. **Real-time feeds** — NDMA SACHET early warning is live; extend with additional official feeds as needed. Copernicus EMS import covers demo regions; broader EMS coverage would require additional imports.
4. **Authentication** — API keys/JWT for production deployment.

**Integration points:** `disaster_zones`, `resource_inventory`, `relief_centers`, M2 `resource_estimates`, `prediction_history`.

---

## 23. Final Milestone Status

### Milestone 1 — implemented scope (prototype)

**Implemented:** CRUD, USGS import, grid pipeline, severity, rule resources, zone persistence, OSM/TIF integration.

**NDMA:** SACHET RSS/CAP ingestion into `ndma_alerts` (early warning only; alerts are not auto-inserted as verified impact or zones).

**Satellite:** `/satellite/nearby` via Overpass (best-effort); `/satellite/damage` returns Copernicus EMS CEMS classifications inside imported EMSR357 coverage only; elsewhere Sentinel STAC metadata with `damage_level: Unknown`.

**Not implemented:** NDMA as disaster-impact feed; automated satellite damage outside imported EMS regions.

### Milestone 2 — implemented scope (prototype)

**Implemented:** 33,032-record pipeline, proxy targets, Ridge models (selected after Random Forest and XGBoost comparison on validation RMSE), conformal intervals, district intersection, zone integration, recalibration, history, scenario APIs.

**With documented limits:** WorldPop vulnerability weighting when zone cache is populated; neutral factor 1.0 otherwise. Training labels are proxy-derived (`target_is_observed=false`), not observed consumption. Reported MAE/RMSE/R² are proxy-formula fit diagnostics, not real-world predictive accuracy (`KNOWN_LIMITATIONS.md` §2.5).

### Milestone 3 — implemented scope (prototype)

**Implemented:** OR-Tools priority-weighted allocation (`/allocation/*`) with per-depot transport-capacity constraint (`compute_depot_transport_capacity_kg` — team-based mass budget + default payload cap; not full fleet VRP), commander priority override and per-zone recalculate, inventory reservation lifecycle (available → reserved → in-transit → delivered), mission lifecycle with enforced status transitions, field team CRUD and mission assignment (`PATCH /missions/{id}/team`), analytics dashboard KPIs from database, and React frontend pages wired to live APIs. Automated tests in `tests/test_m3_allocation.py` and `tests/test_m3_resource_tracking.py`.

**Routing:** NetworkX on cached OSM GraphML when both endpoints fall in Chennai/Bhubaneswar/Delhi demo regions; Haversine fallback elsewhere; no live road-closure ingestion into edge weights.

See `docs/M3_COMPLETION_NOTES.md` for route/service mapping and test coverage detail.

**Prototype limits:** Road graphs limited to pre-built demo regions (`data/road_graphs/`); local-only manual deployment (no production hosting/CI in repo).

### Do NOT change when starting Weeks 5–6

- Approved B2 proxy formulas (`proxy_target_config.json`)
- Trained model artifacts and selection (Ridge) unless retraining is explicitly required
- M1 grid generation and severity implementation
- `target_is_observed=false` semantics
- Chronological ML split strategy

---

*Document version: M1/M2 freeze 2026-08-17. M3 addendum 2026-08-30. See also `docs/MILESTONE2.md` for M2 checklist and `docs/M3_COMPLETION_NOTES.md` for M3 detail.*
