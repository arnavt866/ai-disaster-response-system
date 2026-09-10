"""Build Kerala 2018 flood scenario pack from Kerala_PDNA_2018.pdf.

Only figures explicitly present in the PDNA are included. District-level affected
population is NOT published in the PDNA; statewide human-impact figures live in
separate statewide_summary rows. District rows carry housing damage counts from
Table 3 (Rebuild Kerala mobile app, 4 Oct 2018).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

SCENARIO_PATH = Path(__file__).parent.parent / "data" / "scenarios" / "kerala_floods_2018"
OUTPUT_PATH = SCENARIO_PATH / "district_metrics.csv"
SOURCE_DOCUMENT = "Kerala PDNA 2018 (Floods and Landslides, October 2018)"
SCENARIO = "Kerala Floods 2018"
YEAR = 2018

# Executive Summary — Disaster Event paragraph (printed p. 10; cites Figure 1).
STATEWIDE_HUMAN_IMPACT = {
    "affected_population": 5_400_000,
    "displaced_population": 1_400_000,
    "deaths": 433,
    "source_page": "10",
    "source_table": None,
    "data_quality_note": (
        "Statewide human-impact totals from PDNA Executive Summary, Disaster Event "
        "paragraph (printed p. 10, citing Figure 1). No district-level affected-population "
        "breakdown is published in the PDNA."
    ),
}

# Housing chapter summary (printed p. 84) cross-checks Table 3 statewide totals.
STATEWIDE_HOUSING_SUMMARY = {
    "both_land_and_building_lost": 947,
    "only_building_lost": 14_877,
    "building_damage_over_75_pct": 1_492,
    "buildings_to_rebuild": 17_316,
    "partially_damaged_concrete_roof": 139_210,
    "partially_damaged_non_concrete_roof": 77_707,
    "households_lost_goods_requiring_cleaning": 119_765,
    "total_buildings_affected": 234_233,
    "source_page": "84, 91-92",
    "source_table": "Table 3 (district totals on printed pp. 91-92)",
    "data_quality_note": (
        "Statewide housing totals from PDNA Housing chapter Table 3 (Rebuild Kerala "
        "mobile app, accessed 4 Oct 2018, 4:35 p.m.). Narrative on printed p. 84 "
        "reports 17,316 buildings to rebuild and ~2.17 lakh needing repair/retrofit "
        "(139,210 + 77,707 partial-damage cases)."
    ),
}

# Table 3 — District-wise Damage Assessment (printed pp. 91-92).
# Columns: both_land_and_building_lost, only_building_lost, damage_over_75_pct,
#          buildings_to_rebuild, partial_concrete, partial_non_concrete,
#          households_cleaning, total_buildings_affected
HOUSING_TABLE_3_BY_DISTRICT: list[tuple[str, int, int, int, int, int, int, int, int]] = [
    ("Thiruvananthapuram", 7, 374, 31, 412, 745, 1_415, 1_675, 2_572),
    ("Kollam", 11, 321, 38, 370, 956, 2_058, 1_809, 3_384),
    ("Pathanamthitta", 28, 856, 118, 1_002, 10_143, 6_660, 10_877, 17_805),
    ("Alappuzha", 128, 1_653, 114, 1_895, 21_054, 17_973, 21_497, 40_922),
    ("Kottayam", 18, 566, 128, 712, 7_007, 9_389, 8_999, 17_108),
    ("Idukki", 259, 1_530, 83, 1_872, 2_019, 4_605, 6_150, 8_496),
    ("Ernakulam", 153, 2_523, 293, 2_969, 73_866, 11_836, 35_488, 88_671),
    ("Thrissur", 66, 3_610, 369, 4_045, 12_286, 8_122, 16_044, 24_453),
    ("Palakkad", 70, 1_622, 127, 1_819, 1_282, 4_972, 5_730, 8_073),
    ("Malappuram", 49, 679, 59, 787, 3_332, 3_511, 3_831, 7_630),
    ("Kozhikode", 27, 314, 42, 383, 2_784, 2_171, 2_756, 5_338),
    ("Wayanad", 116, 629, 68, 813, 3_356, 3_544, 3_760, 7_713),
    ("Kannur", 13, 147, 19, 179, 347, 1_209, 926, 1_735),
    ("Kasaragod", 2, 53, 3, 58, 33, 242, 223, 333),
]

HOUSING_COLUMNS = [
    "both_land_and_building_lost",
    "only_building_lost",
    "building_damage_over_75_pct",
    "buildings_to_rebuild",
    "partially_damaged_concrete_roof",
    "partially_damaged_non_concrete_roof",
    "households_lost_goods_requiring_cleaning",
    "total_buildings_affected",
]

CSV_COLUMNS = [
    "row_type",
    "geography",
    "affected_population",
    "displaced_population",
    "deaths",
    *HOUSING_COLUMNS,
    "source_document",
    "source_page",
    "source_table",
    "data_quality_note",
    "scenario",
    "year",
]


def _empty_housing() -> dict[str, int | None]:
    return dict.fromkeys(HOUSING_COLUMNS, None)


def _statewide_human_row() -> dict:
    row = {
        "row_type": "statewide_summary",
        "geography": "Kerala (statewide)",
        "affected_population": STATEWIDE_HUMAN_IMPACT["affected_population"],
        "displaced_population": STATEWIDE_HUMAN_IMPACT["displaced_population"],
        "deaths": STATEWIDE_HUMAN_IMPACT["deaths"],
        "source_document": SOURCE_DOCUMENT,
        "source_page": STATEWIDE_HUMAN_IMPACT["source_page"],
        "source_table": STATEWIDE_HUMAN_IMPACT["source_table"],
        "data_quality_note": STATEWIDE_HUMAN_IMPACT["data_quality_note"],
        "scenario": SCENARIO,
        "year": YEAR,
    }
    row.update(_empty_housing())
    return row


def _statewide_housing_row() -> dict:
    row = {
        "row_type": "statewide_summary",
        "geography": "Kerala (statewide)",
        "affected_population": None,
        "displaced_population": None,
        "deaths": None,
        **{col: STATEWIDE_HOUSING_SUMMARY[col] for col in HOUSING_COLUMNS},
        "source_document": SOURCE_DOCUMENT,
        "source_page": STATEWIDE_HOUSING_SUMMARY["source_page"],
        "source_table": STATEWIDE_HOUSING_SUMMARY["source_table"],
        "data_quality_note": STATEWIDE_HOUSING_SUMMARY["data_quality_note"],
        "scenario": SCENARIO,
        "year": YEAR,
    }
    return row


def _district_housing_rows() -> list[dict]:
    rows: list[dict] = []
    for district, *values in HOUSING_TABLE_3_BY_DISTRICT:
        housing = dict(zip(HOUSING_COLUMNS, values))
        rows.append(
            {
                "row_type": "district_housing",
                "geography": district,
                "affected_population": None,
                "displaced_population": None,
                "deaths": None,
                **housing,
                "source_document": SOURCE_DOCUMENT,
                "source_page": "91-92",
                "source_table": "Table 3 — District-wise Damage Assessment (Number of Cases by Extent of Damage)",
                "data_quality_note": (
                    "District housing damage counts from PDNA Table 3 (Rebuild Kerala "
                    "mobile app, accessed 4 Oct 2018, 4:35 p.m.). Affected population "
                    "is not reported at district level in the PDNA."
                ),
                "scenario": SCENARIO,
                "year": YEAR,
            }
        )
    return rows


def build_dataframe() -> pd.DataFrame:
    records = [_statewide_human_row(), _statewide_housing_row(), *_district_housing_rows()]
    return pd.DataFrame(records, columns=CSV_COLUMNS)


def main() -> None:
    print("Building Kerala 2018 scenario pack from PDNA citations...")
    df = build_dataframe()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    district = df[df["row_type"] == "district_housing"]
    print(f"Saved {len(df)} rows to {OUTPUT_PATH}")
    print(f"  statewide_summary rows: {len(df) - len(district)}")
    print(f"  district_housing rows: {len(district)}")
    print(
        "Statewide affected population (PDNA p.10): "
        f"{STATEWIDE_HUMAN_IMPACT['affected_population']:,}"
    )
    print(
        "Statewide total buildings affected (Table 3): "
        f"{STATEWIDE_HOUSING_SUMMARY['total_buildings_affected']:,}"
    )
    print(
        "District housing total (sum of total_buildings_affected): "
        f"{district['total_buildings_affected'].sum():,}"
    )


if __name__ == "__main__":
    main()
