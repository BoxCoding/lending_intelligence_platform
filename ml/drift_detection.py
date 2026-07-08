"""Feature drift monitoring.

Compares live feature distributions (from the store) against the training
baseline saved in model_registry.json using a z-score of means. Emits a
drift report; wire this into a cron/Cloud Scheduler in production.

Usage:
    python drift_detection.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.store import store
from app.services.feature_engineering import FEATURE_NAMES

DRIFT_Z_THRESHOLD = 2.0


def main():
    registry_path = Path(__file__).parent / "models" / "model_registry.json"
    if not registry_path.exists():
        print("No model_registry.json — train models first.")
        return
    baseline = json.loads(registry_path.read_text())["feature_baseline"]

    live = store.list("features")
    if len(live) < 10:
        print(f"Only {len(live)} live feature rows — need >=10 for a meaningful check.")
        return

    report = {"n_live": len(live), "drifted": [], "ok": []}
    for name in FEATURE_NAMES:
        values = [row.get(name, 0.0) for row in live]
        live_mean = sum(values) / len(values)
        base = baseline[name]
        std = base["std"] or 1e-9
        z = abs(live_mean - base["mean"]) / std
        entry = {
            "feature": name,
            "baseline_mean": base["mean"],
            "live_mean": round(live_mean, 4),
            "z": round(z, 2),
        }
        (report["drifted"] if z > DRIFT_Z_THRESHOLD else report["ok"]).append(entry)

    out = Path(__file__).parent / "models" / "drift_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"Drift check: {len(report['drifted'])} drifted / {len(FEATURE_NAMES)} features -> {out}")
    for d in report["drifted"]:
        print(
            f"  DRIFT {d['feature']}: baseline {d['baseline_mean']} vs live {d['live_mean']} (z={d['z']})"
        )


if __name__ == "__main__":
    main()
