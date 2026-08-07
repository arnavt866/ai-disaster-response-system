# AI-Based Disaster Response Management System

## Overview

This project is an AI-powered Disaster Response Management System developed to support disaster management authorities in estimating affected populations, assessing disaster severity, allocating relief resources, and coordinating disaster response.

The backend is developed using FastAPI and PostgreSQL with geospatial analysis using OpenStreetMap and WorldPop datasets.

---

## Features

- Disaster Event Management
- Disaster Zone Management
- Relief Center Management
- Resource Inventory Management
- USGS Earthquake Integration
- GDACS Disaster Integration
- Impact Area Estimation
- Grid-based Disaster Analysis
- Population Estimation
- Building Density Analysis
- Resource Requirement Estimation
- Logging and Error Handling

---

## Technology Stack

Backend
- FastAPI
- Python

Database
- PostgreSQL
- SQLAlchemy

Geospatial
- OpenStreetMap
- PyOsmium
- Shapely
- Rasterstats
- WorldPop Population Raster

APIs
- USGS
- GDACS
- NDMA (Placeholder)

---

## Folder Structure

app/

api/

config/

core/

database/

models/

schemas/

services/

data/

logs/

---

## Installation

Clone the repository

```bash
git clone <repository_url>
```

Create virtual environment

```bash
python -m venv .venv
```

Activate

Windows

```bash
.venv\Scripts\activate
```

Install requirements

```bash
pip install -r requirements.txt
```

Create .env

```text
DATABASE_URL=...
USGS_URL=...
GDACS_URL=...
NDMA_URL=...
```

Run

```bash
uvicorn app.main:app --reload
```

Open Swagger

```
http://127.0.0.1:8000/docs
```

---

## Milestone 1

Completed

- CRUD APIs
- Disaster Import
- Grid Generation
- Population Estimation
- Resource Estimation
- Severity Calculation
- PostgreSQL Integration

---

## Future Work

- Machine Learning Resource Prediction
- Route Optimization
- Shelter Recommendation
- Live Satellite Damage Detection
- Real-time Dashboard
- AI-based Resource Allocation

---

## Authors

Team Members

(Your Names)