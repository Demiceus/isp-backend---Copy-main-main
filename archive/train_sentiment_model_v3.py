"""
NetAssist AI - Sentiment Model Training V3
============================================
TF-IDF (word + char n-grams) + Logistic Regression.
Saves a single Pipeline object so vectorizers + classifier travel together.

Why word + char n-grams:
- Filipino/Taglish spelling variation is high (po/poh, yung/ung, mabagal/mbagal).
- Word n-grams capture semantic context (e.g., "pero hindi pa rin").
- Char n-grams (3-5) add robustness to informal spelling and typos.
- A FeatureUnion lets both contribute; LogisticRegression weights them.
"""

from __future__ import annotations
import json, os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    classification_report, confusion_matrix, f1_score
)

TRAIN = "data/sentiment_train.csv"
VAL   = "data/sentiment_val.csv"
TEST  = "data/sentiment_test.csv"
HARD  = "data/sentiment_hard_test.csv"
MODEL_OUT = "services/sentiment_classifier.pkl"
RESULTS_OUT = "data/sentiment_model_results.json"

LABELS = ["positive", "neutral", "negative"]

def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.dropna(subset=["review_text", "sentiment"])
    df["review_text"] = df["review_text"].astype(str)
    return df

def build_pipeline() -> Pipeline:
    word = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        sublinear_tf=True,
        lowercase=True,
        strip_accents="unicode",
    )
    char = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=3,
        max_df=0.95,
        sublinear_tf=True,
        lowercase=True,
    )
    features = FeatureUnion([("word", word), ("char", char)])
    clf = LogisticRegression(
    max_iter=3000,
    C=1.0,
    class_weight="balanced",
    solver="lbfgs",
    )
    return Pipeline([("features", features), ("clf", clf)])

def evaluate(name: str, y_true, y_pred) -> dict:
    print(f"\n=== {name} ===")
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, labels=LABELS, average="weighted", zero_division=0)
    print(f"Accuracy:   {acc:.4f}")
    print(f"Macro F1:   {macro_f1:.4f}")
    print(f"Weighted F1:{weighted_f1:.4f}")
    p, r, f1, sup = precision_recall_fscore_support(
        y_true, y_pred, labels=LABELS, zero_division=0
    )
    print("\nPer-class metrics:")
    for i, lab in enumerate(LABELS):
        print(f"  {lab:>9}: P={p[i]:.4f} R={r[i]:.4f} F1={f1[i]:.4f} N={sup[i]}")
    print("\nClassification report:")
    print(classification_report(y_true, y_pred, labels=LABELS, zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    print("Confusion matrix (rows=true, cols=pred):")
    print(f"  order: {LABELS}")
    print(cm)
    return {
        "name": name,
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "per_class": {
            LABELS[i]: {
                "precision": float(p[i]),
                "recall": float(r[i]),
                "f1": float(f1[i]),
                "support": int(sup[i]),
            } for i in range(len(LABELS))
        },
        "confusion_matrix": cm.tolist(),
        "labels_order": LABELS,
    }

def main():
    train_df = load(TRAIN)
    val_df   = load(VAL)
    test_df  = load(TEST)

    print(f"Train: {len(train_df)}  Val: {len(val_df)}  Test: {len(test_df)}")

    pipe = build_pipeline()
    pipe.fit(train_df["review_text"], train_df["sentiment"])

    results = {"model": "tfidf_word+char + logistic_regression"}

    val_pred = pipe.predict(val_df["review_text"])
    results["validation"] = evaluate("VALIDATION", val_df["sentiment"], val_pred)

    test_pred = pipe.predict(test_df["review_text"])
    results["test"] = evaluate("TEST", test_df["sentiment"], test_pred)

    if os.path.exists(HARD):
        hard_df = load(HARD)
        hard_pred = pipe.predict(hard_df["review_text"])
        results["hard_test"] = evaluate("HARD TEST (contextual)", hard_df["sentiment"], hard_pred)

    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    joblib.dump(pipe, MODEL_OUT)
    print(f"\nSaved pipeline -> {MODEL_OUT}")

    with open(RESULTS_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved metrics  -> {RESULTS_OUT}")

if __name__ == "__main__":
    main()