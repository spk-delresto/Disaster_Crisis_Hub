import pickle
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

SEED = 42
rng  = np.random.default_rng(SEED)

N = 2000
type_codes   = rng.integers(0, 7, N)            # 0-6
affected     = rng.integers(0, 100_001, N)
lat          = rng.uniform(-90, 90, N)
lon          = rng.uniform(-180, 180, N)


def _label(type_code, affected, lat, lon):
    """Heuristic ground truth for synthetic training."""
    score = [0.3, 0.9, 0.75, 0.6, 0.65, 0.55, 0.3][type_code]
    if affected > 50_000: score = min(score + 0.25, 1.0)
    elif affected > 10_000: score = min(score + 0.15, 1.0)
    elif affected > 1_000:  score = min(score + 0.05, 1.0)
    # Coastal proximity proxy (latitude ≈ 0 = equatorial)
    if abs(lat) < 30 and type_code in (1, 2):  # tsunami / hurricane
        score = min(score + 0.1, 1.0)
    noise = rng.uniform(-0.05, 0.05)
    score = max(0, min(1.0, score + noise))
    if score >= 0.75: return 3   # critical
    if score >= 0.5:  return 2   # high
    if score >= 0.25: return 1   # medium
    return 0                      # low


labels = np.array([_label(type_codes[i], affected[i], lat[i], lon[i]) for i in range(N)])
X = np.column_stack([type_codes, affected, np.abs(lat), np.abs(lon)])
y = labels

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED)

clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=SEED)
clf.fit(X_train, y_train)

print(classification_report(y_test, clf.predict(X_test),
                             labels=[0,1,2,3], target_names=["low","medium","high","critical"]))

model_path = os.path.join(os.path.dirname(__file__), "severity_model.pkl")
with open(model_path, "wb") as f:
    pickle.dump(clf, f)

print(f"\nModel saved to {model_path}")
