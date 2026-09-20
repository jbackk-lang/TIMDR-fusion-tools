import numpy as np
import pytest

from demo.scenarios import SCENARIOS, generate_scenario, list_scenarios


def test_list_scenarios_returns_all_entries_with_required_fields():
    listed = list_scenarios()
    assert len(listed) == len(SCENARIOS)
    ids = {s["id"] for s in listed}
    assert ids == set(SCENARIOS.keys())
    for s in listed:
        assert s["label"]
        assert s["description"]


def test_generate_scenario_baseline_matches_bundled_csv():
    """baseline must stay byte-identical to the pre-existing example CSV,
    since /analyze's legacy use_example=True path now goes through it."""
    time, signal, meta = generate_scenario("baseline")
    assert len(time) == len(signal) == 2000
    assert meta["id"] == "baseline"
    assert meta["n_samples"] == 2000


@pytest.mark.parametrize("scenario_id", list(SCENARIOS.keys()))
def test_all_scenarios_produce_finite_nonempty_signals(scenario_id):
    time, signal, meta = generate_scenario(scenario_id)
    assert len(signal) > 0
    assert len(time) == len(signal)
    assert np.all(np.isfinite(signal))
    assert np.all(np.isfinite(time))
    assert meta["source"] == "synthetic"


@pytest.mark.parametrize("scenario_id", [sid for sid in SCENARIOS if sid != "baseline"])
def test_generated_scenarios_are_deterministic(scenario_id):
    """Non-baseline scenarios are generated on the fly with a fixed RNG
    seed - must give the exact same signal every call, not just 'similar'."""
    _t1, s1, _m1 = generate_scenario(scenario_id)
    _t2, s2, _m2 = generate_scenario(scenario_id)
    assert np.array_equal(s1, s2)


def test_unknown_scenario_raises_keyerror():
    with pytest.raises(KeyError):
        generate_scenario("does_not_exist")


def test_quiet_scenario_has_no_injected_events():
    """The 'quiet' scenario is a negative control: no events were
    injected, unlike baseline/single_burst which document exactly where
    they injected one."""
    _t, _s, meta = generate_scenario("quiet")
    assert "injected_events_samples" not in meta


def test_single_burst_scenario_documents_injected_event_location():
    _t, signal, meta = generate_scenario("single_burst")
    assert "injected_events_samples" in meta
    center = meta["injected_events_samples"][0]
    # the injected burst should be visible as a local extremum near center
    window = signal[max(0, center - 20):center + 20]
    assert np.max(np.abs(window)) > 3 * np.std(signal[:100])


def test_growing_mode_energy_increases_over_time():
    """rho (mean power) in the back half of the signal should be much
    larger than in the front half, matching the scenario's description
    (exponential growth, no saturation -> back half's rho is ~40x the
    front half's, not just modestly bigger)."""
    _t, signal, _meta = generate_scenario("growing_mode")
    n = len(signal)
    first_half_rho = np.mean(signal[: n // 2] ** 2)
    second_half_rho = np.mean(signal[n // 2 :] ** 2)
    assert second_half_rho > first_half_rho * 20
