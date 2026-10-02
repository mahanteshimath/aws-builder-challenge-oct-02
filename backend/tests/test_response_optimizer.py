import pytest

from src.models.scenario import Intervention, Scenario
from src.simulation.dataset import get_dataset
from src.simulation.interventions import ScenarioError
from src.simulation.presets import MAJOR_ROAD, OUTAGE_POWER_NODE
from src.simulation.response_optimizer import STRATEGIES, optimize, optimize_and_run
from src.simulation.scenario_engine import run_scenario

DS = get_dataset()
COMPOUND = Scenario(rainfall_mm=150, drainage_effectiveness=0.4, closed_road_ids=[MAJOR_ROAD], affected_power_nodes=[OUTAGE_POWER_NODE], resource_budget=30)


@pytest.fixture(scope="module")
def plans():
    return {k: optimize_and_run(COMPOUND, k) for k in STRATEGIES}


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_budget_and_resource_constraints(plans, strategy):
    plan = plans[strategy]["plan"]
    assert plan["budget_consumed"] <= COMPOUND.resource_budget + 1e-9
    assert plan["budget_consumed"] + plan["budget_remaining"] == pytest.approx(COMPOUND.resource_budget, abs=0.01)
    used = {}
    for i in plan["interventions"]:
        used[i["resource_id"]] = used.get(i["resource_id"], 0) + 1
    for rid, n in used.items():
        assert n <= DS.resources[rid].quantity_available
    keys = [(i["resource_type"], i["target_id"]) for i in plan["interventions"]]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_recovery_is_rerun_and_improves(plans, strategy):
    sim = plans[strategy]["simulation"]
    assert sim["recovery"] is not None and sim["recovery_summary"]["population_access_restored"] > 0
    assert sim["recovery"]["metrics"]["pop_reduced_any"] < sim["disaster"]["metrics"]["pop_reduced_any"]
    # Independent re-run with the returned scenario reproduces identical recovery metrics.
    again = run_scenario(Scenario(**plans[strategy]["plan"]["scenario"]), with_timeline=False, with_bottlenecks=False)
    assert again["recovery"]["metrics"] == sim["recovery"]["metrics"]
    assert sim["recovery"]["metrics"]["budget_consumed"] == plans[strategy]["plan"]["budget_consumed"]


def test_strategies_produce_different_allocations(plans):
    sigs = {k: tuple(sorted((i["resource_type"], i["target_id"]) for i in v["plan"]["interventions"])) for k, v in plans.items()}
    assert len(set(sigs.values())) >= 2


def test_zero_budget_allocates_nothing():
    plan = optimize(COMPOUND.model_copy(update={"resource_budget": 0}), "balanced")
    assert plan["interventions"] == [] and plan["budget_consumed"] == 0


def test_zero_availability_allocates_nothing():
    plan = optimize(COMPOUND.model_copy(update={"resource_availability": 0}), "balanced")
    assert plan["interventions"] == []


def test_small_budget_never_exceeded():
    for b in (1, 3, 7.5, 12):
        plan = optimize(COMPOUND.model_copy(update={"resource_budget": b}), "maximize_access")
        assert plan["budget_consumed"] <= b + 1e-9


def test_over_budget_manual_deployment_rejected():
    iv = [Intervention(resource_id="RES-MED1", resource_type="temporary_medical_unit", target_id="Z-01")]
    with pytest.raises(ScenarioError):
        run_scenario(COMPOUND.model_copy(update={"resource_budget": 2, "deployed_resources": iv}), with_timeline=False)


def test_over_resource_manual_deployment_rejected():
    iv = [Intervention(resource_id="RES-MED1", resource_type="temporary_medical_unit", target_id=z)
          for z in sorted(DS.zones)[:DS.resources["RES-MED1"].quantity_available + 1]]
    with pytest.raises(ScenarioError):
        run_scenario(COMPOUND.model_copy(update={"resource_budget": 500, "deployed_resources": iv}), with_timeline=False)


def test_cannot_clear_unblocked_road():
    iv = [Intervention(resource_id="RES-RC1", resource_type="road_clearance_team", target_id="R-001")]
    with pytest.raises(ScenarioError):
        run_scenario(Scenario(resource_budget=50, deployed_resources=iv), with_timeline=False)


def test_closed_road_stays_closed_unless_explicitly_reopened(plans):
    for k, v in plans.items():
        reopened = {i["target_id"] for i in v["plan"]["interventions"] if i["resource_type"] == "road_clearance_team"}
        drain_fixed = any(i["resource_type"] == "portable_generator" and i["target_id"].startswith("D-") for i in v["plan"]["interventions"])
        rec, dis = v["simulation"]["recovery"]["roads"], v["simulation"]["disaster"]["roads"]
        for rid in COMPOUND.closed_road_ids:  # explicit closures never reopen on their own
            if rid not in reopened:
                assert rec[rid]["status"] == "closed"
        for rid, r in dis.items():
            if r["status"] == "closed" and rid not in reopened and rec[rid]["status"] != "closed":
                assert drain_fixed  # only a modeled drainage restoration can lower flood-closed roads

def test_generator_restores_facility_capacity():
    base = run_scenario(Scenario(affected_power_nodes=["P-03"], resource_budget=10), with_timeline=False, with_bottlenecks=False)
    iv = [Intervention(resource_id="RES-GEN2", resource_type="portable_generator", target_id="H-03")]
    r = run_scenario(Scenario(affected_power_nodes=["P-03"], resource_budget=10, deployed_resources=iv), with_timeline=False, with_bottlenecks=False)
    h = lambda blk: next(f for f in blk["facilities"] if f["id"] == "H-03")["capacity_available"]
    assert h(r["disaster"]) == 0 and h(r["recovery"]) > 0
    assert r["recovery_summary"]["budget_remaining"] == pytest.approx(10 - r["recovery"]["metrics"]["budget_consumed"])



def test_reconnecting_a_cut_off_zone_earns_recovery_credit():
    """Reopening a closed bridge that turns 'no route' into 'reachable but slower' must count as partial recovery."""
    s = Scenario(rainfall_mm=160, drainage_effectiveness=0.35, closed_road_ids=[MAJOR_ROAD], resource_budget=30)
    iv = [Intervention(resource_id="RES-RC1", resource_type="road_clearance_team", target_id=MAJOR_ROAD)]
    r = run_scenario(s.model_copy(update={"deployed_resources": iv}), with_timeline=False, with_bottlenecks=False)
    cut_off = [z for z in r["disaster"]["zones"] if z["services"]["hospital"]["no_route"]]
    assert cut_off, "scenario should isolate at least one zone from every hospital"
    rec = {z["id"]: z for z in r["recovery"]["zones"]}
    assert all(not rec[z["id"]]["services"]["hospital"]["no_route"] for z in cut_off)
    assert all(rec[z["id"]]["reduced_severity"] < z["reduced_severity"] for z in cut_off)
    assert r["recovery_summary"]["population_access_restored"] > 0
