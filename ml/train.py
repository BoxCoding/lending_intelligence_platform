"""Model training pipeline.

Trains three models on the synthetic AA dataset using the SAME feature
builder the API uses (no training/serving skew):

  income_model  – LightGBM regressor  -> monthly income (RMSE/MAE/MAPE)
  intent_model  – XGBoost classifier  -> applies within 90d (AUC/P/R/F1)
  risk_model    – LightGBM classifier -> default (AUC/KS/Gini)

Artifacts + metrics registry are written to ml/models/.

Usage:
    python train.py --data ../data/samples
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    precision_score,
    recall_score,
    roc_auc_score,
    root_mean_squared_error,
)
from sklearn.model_selection import train_test_split

from app.schemas.models import AAPayload
from app.services.aa_parser import parse_aa_payload
from app.services.feature_engineering import FEATURE_NAMES, build_features, to_vector


def build_dataset(data_dir: Path):
    payloads = json.loads((data_dir / "aa_payloads.json").read_text())
    labels = {l["customer_id"]: l for l in json.loads((data_dir / "labels.json").read_text())}
    X, y_income, y_intent, y_default = [], [], [], []
    for raw in payloads:
        parsed = parse_aa_payload(AAPayload(**raw))
        features = build_features(parsed)
        label = labels[raw["customer_id"]]
        X.append(to_vector(features))
        y_income.append(label["true_monthly_income"])
        y_intent.append(label["applied_within_90d"])
        y_default.append(label["defaulted"])
    return np.array(X), np.array(y_income), np.array(y_intent), np.array(y_default)


def ks_statistic(y_true, y_prob) -> float:
    order = np.argsort(-y_prob)
    y = y_true[order]
    cum_pos = np.cumsum(y) / max(y.sum(), 1)
    cum_neg = np.cumsum(1 - y) / max((1 - y).sum(), 1)
    return float(np.max(np.abs(cum_pos - cum_neg)))


def train_income(X_tr, X_te, y_tr, y_te):
    from lightgbm import LGBMRegressor

    model = LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31,
                          subsample=0.9, colsample_bytree=0.8, random_state=42, verbose=-1)
    model.fit(X_tr, y_tr, feature_name=FEATURE_NAMES)
    pred = model.predict(X_te)
    return model, {
        "rmse": round(float(root_mean_squared_error(y_te, pred)), 2),
        "mae": round(float(mean_absolute_error(y_te, pred)), 2),
        "mape": round(float(mean_absolute_percentage_error(y_te, pred)), 4),
    }


def train_intent(X_tr, X_te, y_tr, y_te):
    from xgboost import XGBClassifier

    model = XGBClassifier(n_estimators=300, learning_rate=0.06, max_depth=4,
                          subsample=0.9, colsample_bytree=0.8, eval_metric="auc",
                          random_state=42)
    model.fit(X_tr, y_tr)
    prob = model.predict_proba(X_te)[:, 1]
    pred = (prob >= 0.5).astype(int)
    return model, {
        "auc": round(float(roc_auc_score(y_te, prob)), 4),
        "precision": round(float(precision_score(y_te, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_te, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_te, pred, zero_division=0)), 4),
    }


def train_risk(X_tr, X_te, y_tr, y_te):
    from lightgbm import LGBMClassifier

    model = LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                           subsample=0.9, colsample_bytree=0.8, random_state=42,
                           verbose=-1)
    model.fit(X_tr, y_tr, feature_name=FEATURE_NAMES)
    prob = model.predict_proba(X_te)[:, 1]
    auc = float(roc_auc_score(y_te, prob))
    ks = ks_statistic(y_te, prob)
    return model, {"roc_auc": round(auc, 4), "ks": round(ks, 4), "gini": round(2 * auc - 1, 4)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(Path(__file__).parent.parent / "data" / "samples"))
    parser.add_argument("--out", default=str(Path(__file__).parent / "models"))
    args = parser.parse_args()

    data_dir, out_dir = Path(args.data), Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Building dataset with the production feature pipeline...")
    X, y_income, y_intent, y_default = build_dataset(data_dir)
    print(f"Dataset: {X.shape[0]} customers x {X.shape[1]} features")

    idx_tr, idx_te = train_test_split(np.arange(len(X)), test_size=0.25, random_state=42,
                                      stratify=y_default)
    metrics_registry = {"trained_at": datetime.now(timezone.utc).isoformat(),
                        "n_train": len(idx_tr), "n_test": len(idx_te),
                        "features": FEATURE_NAMES, "models": {}}

    for name, trainer, y in [("income", train_income, y_income),
                             ("intent", train_intent, y_intent),
                             ("risk", train_risk, y_default)]:
        model, metrics = trainer(X[idx_tr], X[idx_te], y[idx_tr], y[idx_te])
        joblib.dump(model, out_dir / f"{name}_model.joblib")
        metrics_registry["models"][name] = metrics
        print(f"  {name:>7}: {metrics}")

    # Baseline feature stats for drift detection
    metrics_registry["feature_baseline"] = {
        name: {"mean": round(float(X[:, i].mean()), 4), "std": round(float(X[:, i].std()), 4)}
        for i, name in enumerate(FEATURE_NAMES)
    }
    (out_dir / "model_registry.json").write_text(json.dumps(metrics_registry, indent=2))
    print(f"Artifacts saved to {out_dir}/")


if __name__ == "__main__":
    main()
