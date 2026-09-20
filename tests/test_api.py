import io
import os

import h5py
import numpy as np
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_CSV = os.path.join(REPO_ROOT, "data", "w7x_mirnov_example.csv")
EXAMPLE_H5 = os.path.join(REPO_ROOT, "data", "w7x_mirnov_example.h5")


def _make_h5_bytes(datasets):
    """Builds an in-memory HDF5 file with the given {name: array} datasets."""
    buf = io.BytesIO()
    with h5py.File(buf, "w") as f:
        for name, arr in datasets.items():
            f.create_dataset(name, data=np.asarray(arr, dtype=float))
    buf.seek(0)
    return buf.read()


def test_dashboard_served_at_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "fusion-tools" in resp.text


def test_dashboard_loads_chartjs_from_local_vendor_not_cdn():
    """
    Regression test: Chart.js was vendored locally at static/vendor/
    (see git history: 'Rename static/chart.umd.js to
    static/vendor/chart.umd.js'), but index.html's <script> tag kept
    pointing at cdnjs.cloudflare.com instead of the local copy - so on
    any machine without internet access to that CDN, `Chart` was never
    defined and every chart call failed with 'Chart is not defined'.
    index.html must reference the local vendored file, and that file
    must actually be served (and be the real ~200KB build, not a stub).
    """
    resp = client.get("/")
    assert resp.status_code == 200
    assert "cdnjs.cloudflare.com" not in resp.text
    assert "/static/vendor/chart.umd.js" in resp.text

    vendor_resp = client.get("/static/vendor/chart.umd.js")
    assert vendor_resp.status_code == 200
    assert len(vendor_resp.content) > 100_000


def test_example_metadata_endpoint():
    resp = client.get("/example")
    assert resp.status_code == 200
    body = resp.json()
    assert "notes" in body
    assert "syntetyczny" in body["source"].lower() or "synthetic" in body["source"].lower()


def test_analyze_with_bundled_example():
    resp = client.post("/analyze", data={"use_example": "true", "window": 64, "threshold": 2.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_samples"] == 2000
    assert len(body["reduced"]) == len(body["reduced_x"])
    assert set(body["latro"].keys()) == {"lambda", "tau", "rho"}
    # example signal has 3 injected events near samples 400, 950, 1600
    assert len(body["model_j_points"]) > 0
    for center in (400, 950, 1600):
        assert any(abs(p - center) < 30 for p in body["model_j_points"])


def test_analyze_with_uploaded_csv():
    csv_bytes = b"time,signal\n0,0\n1,1\n2,0\n3,-1\n4,0\n5,1\n6,0\n7,-1\n8,0\n9,1\n"
    files = {"file": ("tiny.csv", io.BytesIO(csv_bytes), "text/csv")}
    resp = client.post("/analyze", data={"window": 2, "threshold": 1.0}, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_samples"] == 10


def test_analyze_rejects_non_csv_upload():
    files = {"file": ("tiny.txt", io.BytesIO(b"not a csv"), "text/plain")}
    resp = client.post("/analyze", data={}, files=files)
    assert resp.status_code == 400


def test_analyze_rejects_oversized_signal():
    n = 200_001  # one over MAX_SAMPLES
    csv_text = "time,signal\n" + "\n".join(f"{i},{i % 3}" for i in range(n))
    files = {"file": ("big.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    resp = client.post("/analyze", data={"window": 64}, files=files)
    assert resp.status_code == 400
    assert "limit" in resp.json()["detail"].lower()


def test_analyze_rejects_zero_window():
    resp = client.post("/analyze", data={"use_example": "true", "window": 0})
    assert resp.status_code == 400


def test_analyze_includes_windowed_latro_and_description():
    resp = client.post("/analyze", data={"use_example": "true", "window": 64, "threshold": 2.0})
    assert resp.status_code == 200
    body = resp.json()
    lw = body["latro_windowed"]
    assert len(lw["x"]) == len(body["reduced"])
    assert len(lw["lambda"]) == len(body["reduced"])
    assert len(lw["tau"]) == len(body["reduced"])
    assert len(lw["rho"]) == len(body["reduced"])
    assert isinstance(body["description"], str)
    assert len(body["description"]) > 20
    # description should mention the actual sample counts, not be a generic placeholder
    assert str(body["n_samples"]) in body["description"]


def test_analyze_hdf5_with_named_time_and_signal_datasets():
    raw = _make_h5_bytes({"time": np.arange(20), "signal": np.sin(np.arange(20) / 3.0)})
    files = {"file": ("test.h5", io.BytesIO(raw), "application/x-hdf5")}
    resp = client.post("/analyze", data={"window": 4, "threshold": 1.0}, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_samples"] == 20
    info = body["hdf5_info"]
    assert info["signal_dataset"] == "signal"
    assert info["time_dataset"] == "time"
    assert info["time_source"] == "dataset:time"
    assert not info["ambiguous"]


def test_analyze_hdf5_single_unnamed_dataset_uses_synthetic_index():
    raw = _make_h5_bytes({"mirnov_ch3": np.arange(15, dtype=float)})
    files = {"file": ("test.h5", io.BytesIO(raw), "application/x-hdf5")}
    resp = client.post("/analyze", data={"window": 5}, files=files)
    assert resp.status_code == 200
    body = resp.json()
    info = body["hdf5_info"]
    assert info["signal_dataset"] == "mirnov_ch3"
    assert info["time_dataset"] is None
    assert info["time_source"] == "synthetic_index"
    assert body["time"] == list(range(15))


def test_analyze_hdf5_ambiguous_datasets_reports_ambiguity_and_lists_options():
    raw = _make_h5_bytes({"ch_a": np.arange(10, dtype=float), "ch_b": np.arange(10, dtype=float) * 2})
    files = {"file": ("test.h5", io.BytesIO(raw), "application/x-hdf5")}
    resp = client.post("/analyze", data={"window": 5}, files=files)
    assert resp.status_code == 200
    info = resp.json()["hdf5_info"]
    assert info["ambiguous"] is True
    assert set(info["available_datasets"]) == {"ch_a", "ch_b"}


def test_analyze_hdf5_explicit_dataset_param_overrides_autodetect():
    raw = _make_h5_bytes({"ch_a": np.arange(10, dtype=float), "ch_b": np.arange(10, dtype=float) * 2})
    files = {"file": ("test.h5", io.BytesIO(raw), "application/x-hdf5")}
    resp = client.post("/analyze", data={"window": 5, "dataset": "ch_b"}, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["hdf5_info"]["signal_dataset"] == "ch_b"
    assert body["hdf5_info"]["ambiguous"] is False
    assert body["signal"] == list(np.arange(10, dtype=float) * 2)


def test_analyze_hdf5_unknown_dataset_param_returns_400():
    raw = _make_h5_bytes({"signal": np.arange(10, dtype=float)})
    files = {"file": ("test.h5", io.BytesIO(raw), "application/x-hdf5")}
    resp = client.post("/analyze", data={"dataset": "does_not_exist"}, files=files)
    assert resp.status_code == 400


def test_analyze_rejects_unsupported_extension():
    files = {"file": ("tiny.txt", io.BytesIO(b"not a csv or hdf5"), "text/plain")}
    resp = client.post("/analyze", data={}, files=files)
    assert resp.status_code == 400


def test_bundled_example_h5_file_exists_and_is_loadable():
    """The bundled data/w7x_mirnov_example.h5 should mirror the CSV example."""
    assert os.path.isfile(EXAMPLE_H5)
    with open(EXAMPLE_H5, "rb") as f:
        raw = f.read()
    files = {"file": ("w7x_mirnov_example.h5", io.BytesIO(raw), "application/x-hdf5")}
    resp = client.post("/analyze", data={"window": 64, "threshold": 2.0}, files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_samples"] == 2000
    assert body["hdf5_info"]["signal_dataset"] == "signal"
    assert body["hdf5_info"]["time_dataset"] == "time"


def test_data_dir_served_for_example_downloads():
    resp = client.get("/data/w7x_mirnov_example.h5")
    assert resp.status_code == 200
    resp2 = client.get("/data/w7x_mirnov_example.csv")
    assert resp2.status_code == 200


def test_scenarios_endpoint_lists_five_scenarios():
    resp = client.get("/scenarios")
    assert resp.status_code == 200
    body = resp.json()
    ids = {s["id"] for s in body["scenarios"]}
    assert ids == {"baseline", "quiet", "single_burst", "growing_mode", "noisy_flat"}
    for s in body["scenarios"]:
        assert s["label"]
        assert s["description"]


def test_analyze_with_scenario_param_baseline_matches_use_example():
    resp_scenario = client.post("/analyze", data={"scenario": "baseline", "window": 64, "threshold": 2.0})
    resp_legacy = client.post("/analyze", data={"use_example": "true", "window": 64, "threshold": 2.0})
    assert resp_scenario.status_code == resp_legacy.status_code == 200
    assert resp_scenario.json()["signal"] == resp_legacy.json()["signal"]


def test_analyze_with_unknown_scenario_returns_400():
    resp = client.post("/analyze", data={"scenario": "does_not_exist"})
    assert resp.status_code == 400
    assert "does_not_exist" in resp.json()["detail"]


def test_analyze_with_quiet_scenario_runs_and_includes_scenario_metadata():
    resp = client.post("/analyze", data={"scenario": "quiet", "window": 32, "threshold": 2.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["scenario"]["id"] == "quiet"
    assert body["scenario"]["source"] == "synthetic"


def test_analyze_response_includes_spectrum():
    resp = client.post("/analyze", data={"use_example": "true", "window": 64, "threshold": 2.0})
    assert resp.status_code == 200
    spectrum = resp.json()["spectrum"]
    assert len(spectrum["freq"]) == len(spectrum["magnitude"])
    assert len(spectrum["freq"]) > 0
    # the baseline signal has a real 17 Hz component - the spectrum's peak
    # magnitude should land near a frequency bin close to it.
    freqs = spectrum["freq"]
    mags = spectrum["magnitude"]
    peak_freq = freqs[mags.index(max(mags))]
    assert any(abs(peak_freq - f) < 1.0 for f in (3.0, 17.0))


def test_analyze_response_includes_model_j_zscore_histogram():
    resp = client.post("/analyze", data={"use_example": "true", "window": 64, "threshold": 2.0})
    assert resp.status_code == 200
    hist = resp.json()["model_j_zscore_hist"]
    assert hist["is_flat"] is False
    assert len(hist["bin_edges"]) == len(hist["counts"]) + 1
    assert sum(hist["counts"]) == 2000
    assert hist["threshold"] == 2.0


def test_analyze_model_j_zscore_histogram_flat_for_constant_signal():
    csv_bytes = b"time,signal\n" + b"\n".join(f"{i},5.0".encode() for i in range(20))
    files = {"file": ("flat.csv", io.BytesIO(csv_bytes), "text/csv")}
    resp = client.post("/analyze", data={"window": 4}, files=files)
    assert resp.status_code == 200
    hist = resp.json()["model_j_zscore_hist"]
    assert hist["is_flat"] is True
    assert hist["counts"] == []


def test_scenarios_compare_endpoint_returns_all_scenarios():
    resp = client.get("/scenarios/compare", params={"window": 64, "threshold": 2.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["window"] == 64
    assert body["threshold"] == 2.0
    ids = {s["id"] for s in body["scenarios"]}
    assert ids == {"baseline", "quiet", "single_burst", "growing_mode", "noisy_flat"}
    for s in body["scenarios"]:
        assert set(["id", "label", "n_samples", "lambda", "tau", "rho", "model_j_count"]) <= set(s.keys())
    # Sanity check on a real, slightly counterintuitive statistical fact
    # (this is exactly the "don't trust a raw threshold count without a
    # background comparison" lesson this whole ecosystem's anti-numerology
    # protocol is built around): 'quiet' is pure Gaussian noise, so
    # Model J's |z|>2 threshold flags ~4-5% of samples by chance alone
    # (n=2000 -> roughly 60-140). 'single_burst' has ONE huge injected
    # event, which inflates std(gradient) used to normalize the z-score,
    # which in turn SUPPRESSES ordinary noise-driven false positives
    # elsewhere in that signal - so single_burst's raw count is actually
    # smaller than quiet's, even though single_burst is the one with a
    # real injected event. The point isn't "more detections = more real
    # events"; it's that raw counts need this kind of context.
    by_id = {s["id"]: s for s in body["scenarios"]}
    assert 40 <= by_id["quiet"]["model_j_count"] <= 160
    assert by_id["single_burst"]["model_j_count"] < by_id["quiet"]["model_j_count"]
