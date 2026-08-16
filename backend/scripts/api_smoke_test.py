"""Lightweight API smoke tests for Milestone-2 audit."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

results = []


def check(name, method, path, **kwargs):
    response = getattr(client, method)(path, **kwargs)
    ok = response.status_code in {200, 201}
    detail = "OK" if ok else response.text[:120]
    results.append((name, response.status_code, detail))
    return response


check("model", "get", "/prediction/model")
check("evaluation", "get", "/prediction/evaluation")
check("history", "get", "/prediction/history")

demand_payload = {
    "features": {
        "disaster_type_normalized": "Flood",
        "event_year": 2018,
        "event_month": 8,
        "state_normalized": "Odisha",
        "district_normalized": "Cuttack",
        "affected_population": 500,
        "injuries": 2,
    },
    "severity_multiplier": 1.0,
}
r = check("demand", "post", "/prediction/demand", json=demand_payload)
if r.status_code == 200:
    body = r.json()
    n = len(body.get("resource_estimates", {}))
    results[-1] = ("demand", 200, f"{n} resource_estimates with intervals")

grid_payload = {
    "grid_geojson": {
        "type": "Polygon",
        "coordinates": [
            [
                [85.8, 20.2],
                [85.81, 20.2],
                [85.81, 20.21],
                [85.8, 20.21],
                [85.8, 20.2],
            ]
        ],
    },
    "disaster_type": "FL",
    "estimated_population": 500,
    "building_count": 10,
    "severity_score": 60,
    "severity_level": "Moderate",
}
r = check("grid_demand", "post", "/prediction/demand/grid", json=grid_payload)
if r.status_code == 200:
    body = r.json()
    districts = body.get("district_overlap", {}).get("district_count", 0)
    results[-1] = ("grid_demand", 200, f"{districts} district overlaps")

scenario_payload = {
    "features": {
        "disaster_type_normalized": "Cyclone",
        "event_year": 2019,
        "event_month": 10,
        "affected_population": 1200,
    },
    "severity_multiplier": 1.5,
    "response_speed_factor": 0.5,
    "resource_availability_factor": 0.7,
}
check("scenario", "post", "/prediction/scenario", json=scenario_payload)

print("API SMOKE TEST RESULTS")
for name, code, detail in results:
    print(f"  {name}: {code} - {detail}")
