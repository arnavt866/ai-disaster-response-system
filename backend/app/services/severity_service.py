def calculate_severity(

    population: int,

    building_count: int,

    radius_km: float,

) -> dict:
    """
    Rule-based severity calculation.

    Output:
        severity_score : 0 - 100
        severity_level : Low / Moderate / High / Critical
    """

    # Population Score (0 - 40)

    if population >= 50000:
        population_score = 40

    elif population >= 20000:
        population_score = 30

    elif population >= 10000:
        population_score = 20

    elif population >= 5000:
        population_score = 10

    else:
        population_score = 5

    # -------------------------------
    # Building Score (0 - 40)
    # -------------------------------

    if building_count >= 5000:
        building_score = 40

    elif building_count >= 2000:
        building_score = 30

    elif building_count >= 1000:
        building_score = 20

    elif building_count >= 500:
        building_score = 10

    else:
        building_score = 5

    # -------------------------------
    # Disaster Radius Score (0 - 20)
    # -------------------------------

    if radius_km >= 100:
        radius_score = 20

    elif radius_km >= 50:
        radius_score = 15

    elif radius_km >= 25:
        radius_score = 10

    else:
        radius_score = 5

    severity_score = (
        population_score
        + building_score
        + radius_score
    )

    if severity_score >= 80:

        level = "Critical"

    elif severity_score >= 60:

        level = "High"

    elif severity_score >= 40:

        level = "Moderate"

    else:

        level = "Low"

    return {

        "severity_score": severity_score,

        "severity_level": level

    }