import pytest

from src.models.scenario import Scenario, Thresholds
from src.simulation.flood_model import classify, clamp, flood_risk, rainfall_intensity_factor


def test_rainfall_factor_monotonic_and_bounded():
    vals = [rainfall_intensity_factor(mm, 6) for mm in range(0, 201, 10)]
    assert vals == sorted(vals)
    assert vals[0] == 0 and 0 <= vals[-1] <= 1


def test_shorter_duration_is_more_intense():
    assert rainfall_intensity_factor(100, 2) > rainfall_intensity_factor(100, 24)


@pytest.mark.parametrize("susc", [0.1, 0.5, 0.9])
def test_more_rain_never_reduces_risk(susc):
    risks = [flood_risk(rainfall_intensity_factor(mm, 6), susc, 0.5) for mm in range(0, 201, 5)]
    assert all(b >= a for a, b in zip(risks, risks[1:]))
    assert all(0 <= r <= 1 for r in risks)


def test_better_drainage_reduces_risk():
    rif = rainfall_intensity_factor(120, 6)
    assert flood_risk(rif, 0.8, 0.9) < flood_risk(rif, 0.8, 0.1)


def test_classification_thresholds():
    th = Thresholds()
    assert classify(0.0, th) == "normal"
    assert classify(th.watch, th) == "watch"
    assert classify(th.flood_risk, th) == "flood_risk"
    assert classify(th.impassable, th) == "impassable"
    assert classify(th.impassable, th, bonus=0.12) == "flood_risk"  # elevated bridge is more resilient


def test_thresholds_must_be_ordered():
    with pytest.raises(ValueError):
        Thresholds(watch=0.6, flood_risk=0.5, impassable=0.7)


def test_scenario_input_bounds():
    with pytest.raises(ValueError):
        Scenario(rainfall_mm=201)
    with pytest.raises(ValueError):
        Scenario(duration_hours=0)
    assert clamp(2) == 1 and clamp(-1) == 0
