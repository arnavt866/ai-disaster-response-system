# Proxy Target Methodology (Phase B2)

Generated: 20260816T184637Z

**Historical observed resource-demand labels were unavailable. Resource-demand targets are deterministic impact-based proxies constructed from available disaster-impact variables and are intended for prototype/model-comparison purposes.**

## Configuration
- Method: `impact_based_proxy_v1`
- Version: `1.0.0`
- Observed labels: `False`

## Formulas
- **relief_population**: `max(affected_population, evacuated_population); if zero and affected_families > 0: affected_families * assumed_persons_per_family`
- **food_packets_demand**: `ceil(relief_population * food_packets_per_person)`
- **water_demand**: `ceil(relief_population * water_units_per_person)`
- **medical_kits_demand**: `ceil((injuries * medical_kits_per_injury + relief_population * medical_population_rate) * (1 + deaths * death_severity_indicator_weight))`
- **shelter_capacity_demand**: `ceil(max(evacuated_population, houses_destroyed * shelter_per_destroyed_house + houses_damaged * shelter_per_damaged_house, affected_families * assumed_persons_per_family if relief_population == 0 else 0))`

## Coefficients
- `assumed_persons_per_family` = 4
- `food_packets_per_person` = 1.0
- `water_units_per_person` = 3.0
- `medical_kits_per_injury` = 0.5
- `medical_population_rate` = 0.02
- `death_severity_indicator_weight` = 0.001
- `shelter_per_destroyed_house` = 1.0
- `shelter_per_damaged_house` = 0.25

## Units
- `food_packets_demand`: proxy food-supply packets (1 packet per relief-population person per relief period)
- `water_demand`: proxy water-supply units (3 units per relief-population person; not litres)
- `medical_kits_demand`: proxy medical-kit count
- `shelter_capacity_demand`: proxy shelter-capacity spaces