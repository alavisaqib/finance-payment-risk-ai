"""Deterministic training and honest held-out metrics on synthetic records."""
import csv
from functools import lru_cache
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, mean_absolute_error, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .config import ROOT, SPEC

@lru_cache(maxsize=1)
def fitted_model():
    from .domain import transform
    with (ROOT / 'data/training.csv').open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    x = np.array([transform({name:float(value) for name,value in row.items()}) for row in rows])
    y = np.array([float(row['target']) for row in rows])
    classification = SPEC['task'] == 'classification'
    train_x, test_x, train_y, test_y = train_test_split(
        x, y, test_size=0.25, random_state=42, stratify=y if classification else None)
    if classification:
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=42))
        model.fit(train_x, train_y)
        predicted = model.predict_proba(test_x)[:, 1]
        metrics = {'roc_auc': round(float(roc_auc_score(test_y, predicted)), 4),
                   'average_precision': round(float(average_precision_score(test_y, predicted)), 4),
                   'positive_prevalence': round(float(test_y.mean()), 4)}
        residual = None
    else:
        model = RandomForestRegressor(n_estimators=80, min_samples_leaf=4, random_state=42, n_jobs=1)
        model.fit(train_x, train_y)
        predicted = model.predict(test_x)
        residual = float(np.quantile(np.abs(test_y - predicted), 0.9))
        metrics = {'mae': round(float(mean_absolute_error(test_y, predicted)), 4),
                   'mean_baseline_mae': round(float(mean_absolute_error(test_y, np.repeat(train_y.mean(), len(test_y)))), 4),
                   'residual_p90': round(residual, 4)}
    return model, {'task': SPEC['task'], 'target': SPEC['target'], 'units': SPEC['target_units'],
                   'train_rows': len(train_y), 'test_rows': len(test_y), 'seed': 42,
                   'data': 'synthetic; not evidence of real-world performance', **metrics}, residual

def predict(features):
    from .domain import transform
    model, _, residual = fitted_model()
    row = np.array([transform(features)])
    value = model.predict_proba(row)[0, 1] if SPEC['task'] == 'classification' else model.predict(row)[0]
    return float(value), residual
