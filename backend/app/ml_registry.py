"""Model Registry.

Lazily loads trained model artifacts (joblib) produced by ml/train.py.
Missing artifacts are tolerated — engines fall back to calibrated rules,
so the API stays functional before models are trained.
"""

from pathlib import Path

from app.core.config import get_settings
from app.core.logging import logger

MODEL_FILES = {
    "income": "income_model.joblib",
    "intent": "intent_model.joblib",
    "risk": "risk_model.joblib",
}


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, object] = {}
        self._explainers: dict[str, object] = {}
        self._loaded = False

    def _model_dir(self) -> Path:
        configured = get_settings().model_dir
        base = Path(__file__).resolve().parent.parent  # backend/
        path = Path(configured)
        return path if path.is_absolute() else (base / configured).resolve()

    def load_all(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        model_dir = self._model_dir()
        for name, filename in MODEL_FILES.items():
            path = model_dir / filename
            if not path.exists():
                logger.warning("Model artifact missing: %s (rule-based fallback active)", path)
                continue
            try:
                import joblib

                self._models[name] = joblib.load(path)
                logger.info("Loaded model '%s' from %s", name, path)
            except Exception as exc:
                logger.error("Failed loading model %s: %s", name, exc)

    def get(self, name: str):
        self.load_all()
        return self._models.get(name)

    def get_explainer(self, name: str, model):
        """Cache one SHAP TreeExplainer per model."""
        if name not in self._explainers:
            import shap

            self._explainers[name] = shap.TreeExplainer(model)
        return self._explainers[name]

    def status(self) -> dict:
        self.load_all()
        return {name: (name in self._models) for name in MODEL_FILES}


registry = ModelRegistry()
