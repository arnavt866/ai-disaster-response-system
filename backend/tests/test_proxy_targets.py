"""Tests for proxy resource-demand target generation."""

import pandas as pd
import pytest

from app.services.historical.proxy_target_generator import (
    add_proxy_targets,
    compute_proxy_targets_for_row,
    compute_relief_population,
    load_proxy_target_config,
    target_correlation_summary,
    target_distribution_summary,
    validate_proxy_targets,
)


@pytest.fixture
def config():
    return load_proxy_target_config()


@pytest.fixture
def sample_row():
    return {
        "affected_population": 1000,
        "evacuated_population": 200,
        "affected_families": 50,
        "injuries": 10,
        "deaths": 2,
        "houses_destroyed": 30,
        "houses_damaged": 40,
    }


def test_relief_population_uses_max_not_sum(config, sample_row):
    # evacuated is subset of affected; should not double-count.
    relief = compute_relief_population(sample_row, config)
    assert relief == 1000


def test_relief_population_family_fallback(config):
    row = {"affected_population": 0, "evacuated_population": 0, "affected_families": 10}
    relief = compute_relief_population(row, config)
    assert relief == 40


def test_proxy_targets_are_non_negative_integers(config, sample_row):
    targets = compute_proxy_targets_for_row(sample_row, config)
    for key in (
        "food_packets_demand",
        "water_demand",
        "medical_kits_demand",
        "shelter_capacity_demand",
    ):
        assert targets[key] >= 0
        assert isinstance(targets[key], int)

    assert targets["target_is_observed"] is False
    assert targets["target_method"] == "impact_based_proxy_v1"


def test_add_proxy_targets_to_dataframe(config):
    df = pd.DataFrame(
        [
            {
                "affected_population": 500,
                "evacuated_population": 100,
                "affected_families": 0,
                "injuries": 5,
                "deaths": 1,
                "houses_destroyed": 10,
                "houses_damaged": 5,
            }
        ]
    )
    result = add_proxy_targets(df, config)
    assert validate_proxy_targets(result)["valid"] is True
    stats = target_distribution_summary(result)
    assert stats["food_packets_demand"]["count"] == 1


def test_target_correlations_are_positive_for_expected_pairs(config):
    df = pd.DataFrame(
        [
            {
                "affected_population": n * 100,
                "evacuated_population": n * 20,
                "affected_families": 0,
                "injuries": n,
                "deaths": 0,
                "houses_destroyed": n,
                "houses_damaged": 0,
            }
            for n in range(1, 20)
        ]
    )
    result = add_proxy_targets(df, config)
    correlations = target_correlation_summary(result)

    assert correlations["food_packets_demand"]["relief_population_proxy"] > 0
    assert correlations["water_demand"]["relief_population_proxy"] > 0
    assert correlations["medical_kits_demand"]["injuries"] > 0
    assert correlations["shelter_capacity_demand"]["houses_destroyed"] > 0
