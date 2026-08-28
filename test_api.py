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
