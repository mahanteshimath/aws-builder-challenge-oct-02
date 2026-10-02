import json

from src.models.scenario import Scenario
from src.simulation.accessibility import pair_status, service_reduced
from src.simulation.dataset import get_dataset
from src.simulation.presets import MAJOR_ROAD, OUTAGE_POWER_NODE
from src.simulation.scenario_engine import assess, conditions_from, evaluate, get_baseline, run_scenario

DS = get_dataset()


def metrics(s, **kw):
    return run_scenario(s, with_timeline=False, with_bottlenecks=False)["disaster"]["metrics"]


def test_pair_status_rules():
    assert pair_status(None, 5, 20, 1.25) == "inaccessible"
    assert pair_status(25, 5, 20, 1.25) == "inaccessible"
    assert pair_status(12, 5, 20, 1.25) == "accessible_with_delay"
    assert pair_status(5.5, 5, 20, 1.25) == "accessible"
    assert service_reduced(None, 5, 20, 1.25) and not service_reduced(5, 5, 20, 1.25)


def test_baseline_reproducible_and_clean():
    a = run_scenario(Scenario(), with_timeline=False)["baseline"]
    b = run_scenario(Scenario(rainfall_mm=170, closed_road_ids=[MAJOR_ROAD]), with_timeline=False)["baseline"]
    assert a["metrics"] == b["metrics"]  # baseline ignores disaster inputs
    assert a["metrics"]["roads_affected"] == 0 and a["metrics"]["exposed_population"] == 0
    assert a["metrics"]["hospitals_accessible"] == 4


def test_identical_inputs_identical_outputs():
    s = Scenario(rainfall_mm=140, drainage_effectiveness=0.4, closed_road_ids=[MAJOR_ROAD], affected_power_nodes=[OUTAGE_POWER_NODE])
    a, b = run_scenario(s), run_scenario(s)
    for r in (a, b):
        r.pop("generated_at")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_more_rain_never_reduces_hazard_for_same_feature():
    prev = None
    for mm in range(0, 201, 20):
        r = run_scenario(Scenario(rainfall_mm=mm), with_timeline=False, with_bottlenecks=False)["disaster"]
        risks = {k: v["risk"] for k, v in r["roads"].items()} | {k: v["risk"] for k, v in r["hazards"].items()}
        if prev:
            assert all(risks[k] >= prev[k] - 1e-9 for k in risks)
        prev = risks


def test_closing_a_road_never_improves_reachability():
    base_s = Scenario(rainfall_mm=90)
    base_ev = evaluate(DS, conditions_from(base_s))
    for rid in [MAJOR_ROAD] + sorted(DS.roads, key=lambda r: -DS.roads[r].criticality_score)[:3]:
        ev = evaluate(DS, conditions_from(Scenario(rainfall_mm=90, closed_road_ids=[rid])))
        for zid in DS.zones:
            for fid, t in base_ev["times"][zid].items():
                t2 = ev["times"][zid][fid]
                if t is None:
                    assert t2 is None
                else:
                    assert t2 is None or t2 >= t - 1e-9


def test_facility_not_reachable_through_closed_edge():
    s = Scenario(closed_road_ids=[r for r in DS.roads if DS.facilities["H-01"].node_id in (DS.roads[r].start_node_id, DS.roads[r].end_node_id)])
    ev = evaluate(DS, conditions_from(s))
    for zid, z in DS.zones.items():
        if z.anchor_node_id != DS.facilities["H-01"].node_id:
            assert ev["times"][zid]["H-01"] is None  # every incident edge closed -> unreachable


def test_isolated_facility_reported_inaccessible():
    inc = [r for r, road in DS.roads.items() if DS.facilities["H-01"].node_id in (road.start_node_id, road.end_node_id)]
    sim = run_scenario(Scenario(closed_road_ids=inc), with_timeline=False, with_bottlenecks=False)
    f = next(f for f in sim["disaster"]["facilities"] if f["id"] == "H-01")
    assert f["accessibility_status"] == "inaccessible" and "H-01" in sim["disaster"]["inaccessible_facility_ids"]
    assert sim["disaster"]["metrics"]["facilities_inaccessible_some_zone"] >= 1


def test_power_outage_reduces_dependent_facility_capacity():
    m0 = run_scenario(Scenario(), with_timeline=False, with_bottlenecks=False)["disaster"]
    s = Scenario(affected_power_nodes=["P-03"])
    r = run_scenario(s, with_timeline=False, with_bottlenecks=False)["disaster"]
    h3 = next(f for f in r["facilities"] if f["id"] == "H-03")
    assert h3["operational_status"] == "offline" and h3["capacity_available"] == 0
    assert r["metrics"]["service_capacity_available"] < m0["metrics"]["service_capacity_available"]
    assert r["metrics"]["electricity_dependent_affected"] >= 2


def test_operational_status_separate_from_reachability():
    r = run_scenario(Scenario(affected_power_nodes=["P-02"]), with_timeline=False, with_bottlenecks=False)["disaster"]
    h2 = next(f for f in r["facilities"] if f["id"] == "H-02")
    assert h2["operational_status"] == "reduced" and h2["accessibility_status"] in ("accessible", "accessible_with_delay")
    assert h2["display_status"] == "operationally_affected"


def test_backup_power_exhausted_by_long_event():
    short = run_scenario(Scenario(affected_power_nodes=["P-02"], duration_hours=6), with_timeline=False, with_bottlenecks=False)["disaster"]
    long = run_scenario(Scenario(affected_power_nodes=["P-02"], duration_hours=24), with_timeline=False, with_bottlenecks=False)["disaster"]
    g = lambda r: next(f for f in r["facilities"] if f["id"] == "H-02")["capacity_multiplier"]
    assert g(long) < g(short)


def test_power_outage_cascades_to_drainage_and_flood_risk():
    with_pump = run_scenario(Scenario(rainfall_mm=120, drainage_effectiveness=0.5), with_timeline=False, with_bottlenecks=False)["disaster"]
    no_power = run_scenario(Scenario(rainfall_mm=120, drainage_effectiveness=0.5, affected_power_nodes=["P-02"]), with_timeline=False, with_bottlenecks=False)["disaster"]
    assert no_power["drainage"]["D-01"]["failed"] and not with_pump["drainage"]["D-01"]["failed"]
    assert sum(r["risk"] for r in no_power["roads"].values()) > sum(r["risk"] for r in with_pump["roads"].values())


def test_exposure_counts_each_zone_once_and_bounded():
    m = run_scenario(Scenario(rainfall_mm=200, drainage_effectiveness=0.2), with_timeline=False, with_bottlenecks=False)["disaster"]["metrics"]
    assert m["exposed_population"] <= m["population_total"]
    assert m["pop_reduced_any"] <= m["population_total"]
    assert m["pop_reduced_any"] >= max(m["pop_reduced_hospital"], m["pop_reduced_shelter"], m["pop_reduced_water"])


def test_timeline_stages_are_explicit_states():
    r = run_scenario(Scenario(rainfall_mm=150, closed_road_ids=[MAJOR_ROAD], affected_power_nodes=[OUTAGE_POWER_NODE]))
    tl = r["timeline"]
    assert [t["t_minutes"] for t in tl] == [0, 15, 30, 45, 60, 90]
    exposed = [t["metrics"]["exposed_population"] for t in tl[:5]]
    assert exposed == sorted(exposed) and exposed[0] == 0
    assert tl[3]["metrics"]["roads_closed"] >= 1


def test_unknown_ids_rejected():
    import pytest
    from src.simulation.interventions import ScenarioError
    with pytest.raises(ScenarioError):
        run_scenario(Scenario(closed_road_ids=["R-999"]))


def test_bottlenecks_identify_critical_roads():
    r = run_scenario(Scenario(rainfall_mm=150))
    assert r["bottlenecks"] and r["bottlenecks"][0]["score"] >= r["bottlenecks"][-1]["score"]
    assert all(b["road_id"] in DS.roads for b in r["bottlenecks"])
    assert "explanation" in r["bottlenecks"][0]


def test_results_carry_data_provenance_label():
    r = run_scenario(Scenario(rainfall_mm=50), with_timeline=False)
    assert r["synthetic_data"] is False and "MODELED ATTRIBUTES" in r["data_label"] and "OpenStreetMap" in r["data_label"]
    assert r["metric_definitions"] and r["assumptions"]

