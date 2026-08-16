"""Explicit state and district alias mappings for historical XML ↔ GeoJSON matching."""

from __future__ import annotations

# Canonical state names used in district_target_states.geojson.
TARGET_STATES: frozenset[str] = frozenset({"Odisha", "Tamil Nadu", "Uttarakhand"})

EXPECTED_STATE_COUNTS: dict[str, int] = {
    "Odisha": 30,
    "Tamil Nadu": 37,
    "Uttarakhand": 13,
}

# Historical XML state name -> canonical GeoJSON state name.
STATE_ALIASES: dict[str, str] = {
    "orissa": "Odisha",
    "odisha": "Odisha",
    "tamil nadu": "Tamil Nadu",
    "uttarakhand": "Uttarakhand",
}

# (canonical_state, normalized_xml_district_key) -> canonical GeoJSON district name.
# Keys are lowercase, punctuation-stripped district tokens from XML name1.
DISTRICT_ALIASES: dict[tuple[str, str], str] = {
    # Odisha spelling differences (NWDP XML vs NWIC GeoJSON).
    ("Odisha", "angul"): "Anugul",
    ("Odisha", "balasore"): "Baleshwar",
    ("Odisha", "bolangir"): "Balangir",
    ("Odisha", "jagatsingpur"): "Jagatsinghapur",
    ("Odisha", "jajpur"): "Jajapur",
    ("Odisha", "keonjhar"): "Kendujhar",
    ("Odisha", "khurda"): "Khordha",
    ("Odisha", "nabrangpur"): "Nabarangpur",
    ("Odisha", "nuapara"): "Nuapada",
    # Tamil Nadu spelling / casing differences.
    ("Tamil Nadu", "dindugal"): "Dindigul",
    ("Tamil Nadu", "nagappattinam"): "Nagapattinam",
    ("Tamil Nadu", "nilgiri"): "The Nilgiris",
    ("Tamil Nadu", "nilgiris"): "The Nilgiris",
    ("Tamil Nadu", "sivagangai"): "Sivaganga",
    ("Tamil Nadu", "thiruvannamalai"): "Tiruvannamalai",
    ("Tamil Nadu", "thoothukudi"): "Tuticorin",
    ("Tamil Nadu", "tuticorin"): "Tuticorin",
    ("Tamil Nadu", "trichirappalli"): "Tiruchirappalli",
    ("Tamil Nadu", "tiruchirappalli"): "Tiruchirappalli",
    ("Tamil Nadu", "tiruvallur"): "Thiruvallur",
    ("Tamil Nadu", "thiruvallur"): "Thiruvallur",
    ("Tamil Nadu", "villupuram"): "Villupuram",
    ("Tamil Nadu", "villuppuram"): "Villupuram",
    ("Tamil Nadu", "viruthunagar"): "Virudhunagar",
    ("Tamil Nadu", "virudhunagar"): "Virudhunagar",
    # Uttarakhand spelling differences.
    ("Uttarakhand", "garhwal"): "Pauri Garhwal",
    ("Uttarakhand", "hardwar"): "Haridwar",
    ("Uttarakhand", "pauri"): "Pauri Garhwal",
    ("Uttarakhand", "rudraprayag"): "Rudra Prayag",
    ("Uttarakhand", "udham singh nagar"): "Udam Singh Nagar",
    ("Uttarakhand", "udam singh nagar"): "Udam Singh Nagar",
    ("Uttarakhand", "uttarkashi"): "Uttar Kashi",
}
