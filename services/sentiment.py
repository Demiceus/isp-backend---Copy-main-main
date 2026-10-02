import joblib
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = BASE_DIR / "services" / "sentiment_classifier.pkl"

# Production sentiment model: TF-IDF + Linear SVM.
model = joblib.load(MODEL_FILE)


def _decision_confidence(scores):
    """Convert SVM decision scores to a relative confidence value.

    LinearSVC does not expose calibrated predict_proba values. This softmax
    score is therefore a relative model confidence, not a calibrated
    probability. It preserves the existing API's confidence field.
    """
    scores = np.asarray(scores, dtype=float).reshape(-1)
    shifted = scores - np.max(scores)
    probabilities = np.exp(shifted)
    probabilities /= probabilities.sum()
    return probabilities


def score_sentiment(review_text: str):
    """Predict customer review sentiment using TF-IDF + Linear SVM.

    Returns:
        sentiment: positive / negative / neutral
        confidence: relative confidence derived from SVM decision scores
    """
    prediction = model.predict([review_text])[0]

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba([review_text])[0]
        classes = model.classes_
    else:
        scores = model.decision_function([review_text])
        probabilities = _decision_confidence(scores)
        classes = model.classes_

    probability_map = {
        label: float(probability)
        for label, probability in zip(classes, probabilities)
    }

    confidence = probability_map[prediction]

    return prediction, confidence
