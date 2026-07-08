import os
import pickle
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "severity_model.pkl")

_model = None


def _load_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
    return _model


# Ordinal encoding maps --------------------------------------------------------
TYPE_MAP = {
    "earthquake": 0, "tsunami": 1, "hurricane": 2,
    "flood": 3, "fire": 4, "landslide": 5, "other": 6,
}


def predict_severity(
    disaster_type: str,
    affected_people: int,
    latitude: float,
    longitude: float,
) -> float:
    """Return a severity score between 0.0 (minimal) and 1.0 (critical)."""

    model = _load_model()

    features = np.array([[
        TYPE_MAP.get(disaster_type, 6),
        min(affected_people, 100_000),
        abs(latitude),
        abs(longitude),
    ]])

    if model is not None:
        try:
            # Model outputs class probabilities; use P(high|critical) as score
            proba = model.predict_proba(features)[0]
            # classes: [low, medium, high, critical] → weighted score
            score = proba[1] * 0.33 + proba[2] * 0.66 + proba[3] * 1.0
            return float(min(score, 1.0))
        except Exception:
            pass

    # Fallback: simple heuristic
    base = {"earthquake": 0.8, "tsunami": 0.9, "hurricane": 0.75,
            "flood": 0.6, "fire": 0.65, "landslide": 0.55, "other": 0.3}
    score = base.get(disaster_type, 0.4)
    if affected_people > 10_000:
        score = min(score + 0.2, 1.0)
    elif affected_people > 1_000:
        score = min(score + 0.1, 1.0)
    return round(score, 3)
