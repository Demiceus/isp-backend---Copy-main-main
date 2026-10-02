import joblib

MODEL_FILE = "services/isp_classifier.pkl"

model = joblib.load(MODEL_FILE)


def classify_complaint(text):

    prediction = model.predict([text])[0]

    probabilities = model.predict_proba([text])[0]

    confidence = max(probabilities)

    return {
        "category": prediction,
        "confidence": float(confidence)
    }