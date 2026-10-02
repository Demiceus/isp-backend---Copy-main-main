"""Train the production review sentiment classifier.

The production model is TF-IDF + Linear SVM. The held-out test set is never
used for fitting; training uses sentiment_train + sentiment_val, while
sentiment_test and sentiment_hard_test are reserved for evaluation.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

BASE_DIR = Path(__file__).resolve().parent.parent
TRAIN_FILE = BASE_DIR / "data" / "sentiment_train.csv"
VAL_FILE = BASE_DIR / "data" / "sentiment_val.csv"
TEST_FILE = BASE_DIR / "data" / "sentiment_test.csv"
HARD_TEST_FILE = BASE_DIR / "data" / "sentiment_hard_test.csv"
MODEL_FILE = BASE_DIR / "services" / "sentiment_classifier.pkl"
FULL_MODEL_FILE = BASE_DIR / "dataset" / "linear_svm_sentiment_model_fulltrain.pkl"


def load_data(path):
    df = pd.read_csv(path).dropna(subset=["review_text", "sentiment"])
    return df["review_text"].astype(str), df["sentiment"].astype(str)


print("Loading sentiment datasets...")
X_train, y_train = load_data(TRAIN_FILE)
X_val, y_val = load_data(VAL_FILE)
X_test, y_test = load_data(TEST_FILE)
X_hard, y_hard = load_data(HARD_TEST_FILE)

X_full = pd.concat([X_train, X_val], ignore_index=True)
y_full = pd.concat([y_train, y_val], ignore_index=True)

print(f"Training examples: {len(X_full):,}")
print(y_full.value_counts())

model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
        ),
    ),
    (
        "clf",
        LinearSVC(
            C=1.0,
            class_weight="balanced",
            max_iter=1000,
        ),
    ),
])

print("\nTraining Linear SVM...")
model.fit(X_full, y_full)

for name, X_eval, y_eval in [
    ("TEST", X_test, y_test),
    ("HARD TEST", X_hard, y_hard),
]:
    predictions = model.predict(X_eval)
    print(f"\n=== {name} RESULTS ===")
    print(f"Accuracy: {accuracy_score(y_eval, predictions):.4f}")
    print(classification_report(y_eval, predictions, digits=4))

joblib.dump(model, MODEL_FILE)
joblib.dump(model, FULL_MODEL_FILE)

print(f"\nProduction model saved to: {MODEL_FILE}")
print(f"Full-train copy saved to: {FULL_MODEL_FILE}")
