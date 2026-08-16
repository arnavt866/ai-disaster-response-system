def calculate_resources(
    population: int,
    severity_level: str,
) -> dict:
    """Rule-based relief resource estimates used by Milestone-1 grid analysis."""
    if population == 0:
        return {
            "food_packets": 0,
            "water_bottles": 0,
            "medical_kits": 0,
            "temporary_shelters": 0,
        }

    if severity_level == "Critical":

        multiplier = 1.5

    elif severity_level == "High":

        multiplier = 1.2

    elif severity_level == "Moderate":

        multiplier = 1.0

    else:

        multiplier = 0.7

    food_packets = int(population * multiplier)

    water_bottles = int(population * 3 * multiplier)

    medical_kits = max(

        1,

        int(population * 0.05 * multiplier)

    )

    shelters = max(

        1,

        int(population / 1000)

    )

    return {

        "food_packets": food_packets,

        "water_bottles": water_bottles,

        "medical_kits": medical_kits,

        "temporary_shelters": shelters,

    }