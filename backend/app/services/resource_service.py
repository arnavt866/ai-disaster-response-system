def calculate_resources(
    population: int,
    severity_level: str,
) -> dict:
    """
    Estimate the relief resources required for
    an affected population.

    This rule-based approach will be replaced
    by an ML model in Milestone 2.
    """
    if population == 0:

        return {

            "food_packets": 0,

            "water_bottles": 0,

            "medical_kits": 0,

            "temporary_shelters": 0,

        }
    """
    Estimate relief resources required.

    These values are rule-based for Milestone 1.

    In Milestone 2 they will be replaced
    by the ML model.
    """

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