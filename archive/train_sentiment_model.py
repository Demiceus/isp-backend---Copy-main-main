"""
NetAssist AI - Sentiment Model Training

Model:
    TF-IDF + Logistic Regression

Classes:
    positive
    negative
    neutral

Input:
    data/sentiment_train.csv
    data/sentiment_val.csv
    data/sentiment_test.csv
    data/sentiment_hard_test.csv (optional)

Output:
    services/sentiment_classifier.pkl
"""

from pathlib import Path
import pickle

import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TRAIN_FILE = BASE_DIR / "data" / "sentiment_train.csv"
VAL_FILE = BASE_DIR / "data" / "sentiment_val.csv"
TEST_FILE = BASE_DIR / "data" / "sentiment_test.csv"
HARD_TEST_FILE = BASE_DIR / "data" / "sentiment_hard_test.csv"

MODEL_FILE = (
    BASE_DIR
    / "services"
    / "sentiment_classifier.pkl"
)


# ============================================================
# LOAD DATA
# ============================================================

def load_dataset(path):

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    df = pd.read_csv(path)

    required_columns = [
        "review_text",
        "sentiment",
    ]

    for column in required_columns:

        if column not in df.columns:
            raise ValueError(
                f"Missing required column "
                f"'{column}' in {path}"
            )

    # Remove empty rows
    df = df.dropna(
        subset=[
            "review_text",
            "sentiment",
        ]
    )

    df["review_text"] = (
        df["review_text"]
        .astype(str)
        .str.strip()
    )

    df = df[
        df["review_text"] != ""
    ]

    return df


# ============================================================
# BUILD MODEL
# ============================================================

def build_model():

    model = Pipeline([

        (
            "tfidf",

            TfidfVectorizer(

                # Word + character information helps with
                # Filipino/Taglish, typos and informal text.

                analyzer="word",

                ngram_range=(1, 2),

                min_df=2,

                max_df=0.98,

                sublinear_tf=True,

                strip_accents=None,
            )
        ),

        (
            "classifier",

            LogisticRegression(

                max_iter=2000,

                C=2.0,

                class_weight="balanced",

                random_state=42,
            )
        ),
    ])

    return model


# ============================================================
# EVALUATION
# ============================================================

def evaluate_model(
    model,
    df,
    dataset_name
):

    X = df["review_text"]
    y = df["sentiment"]

    predictions = model.predict(X)

    accuracy = accuracy_score(
        y,
        predictions
    )

    print()
    print("=" * 70)
    print(dataset_name)
    print("=" * 70)

    print(
        f"Accuracy: {accuracy:.4f}"
    )

    print()
    print("Classification Report:")

    print(
        classification_report(
            y,
            predictions,
            labels=[
                "negative",
                "neutral",
                "positive",
            ],
            zero_division=0,
        )
    )

    print("Confusion Matrix:")

    cm = confusion_matrix(
        y,
        predictions,
        labels=[
            "negative",
            "neutral",
            "positive",
        ],
    )

    print(
        "                 Predicted"
    )

    print(
        "                 Neg   Neu   Pos"
    )

    print(
        f"Actual Neg      "
        f"{cm[0][0]:4d}  "
        f"{cm[0][1]:4d}  "
        f"{cm[0][2]:4d}"
    )

    print(
        f"Actual Neu      "
        f"{cm[1][0]:4d}  "
        f"{cm[1][1]:4d}  "
        f"{cm[1][2]:4d}"
    )

    print(
        f"Actual Pos      "
        f"{cm[2][0]:4d}  "
        f"{cm[2][1]:4d}  "
        f"{cm[2][2]:4d}"
    )

    return accuracy


# ============================================================
# TEST INDIVIDUAL REVIEWS
# ============================================================

def test_examples(model):

    examples = [

        # Positive
        "Okay na po yung internet namin, salamat.",
        "Gumagana na ulit yung WiFi.",
        "Mabagal kanina pero okay na ngayon.",
        "Naayos na po yung connection.",

        # Negative
        "Mabagal pa rin po yung internet.",
        "Hindi pa rin gumagana yung WiFi.",
        "Salamat po sa response pero hindi pa rin gumagana.",

        # Neutral
        "Noted po.",
        "Maghihintay po ako ng technician.",
        "Salamat sa update, iche-check ko muna.",
    ]

    print()
    print("=" * 70)
    print("MANUAL EXAMPLE TEST")
    print("=" * 70)

    for text in examples:

        prediction = model.predict(
            [text]
        )[0]

        probabilities = model.predict_proba(
            [text]
        )[0]

        classes = model.classes_

        probability_map = {
            cls: float(prob)
            for cls, prob in zip(
                classes,
                probabilities
            )
        }

        confidence = max(
            probability_map.values()
        )

        print()
        print(
            f"Review: {text}"
        )

        print(
            f"Prediction: {prediction}"
        )

        print(
            f"Confidence: {confidence:.4f}"
        )

        print(
            "Probabilities:",
            {
                k: round(v, 4)
                for k, v in probability_map.items()
            }
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("NetAssist AI - Sentiment Model Training")
    print("=" * 70)

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    print()
    print("Loading datasets...")

    train_df = load_dataset(
        TRAIN_FILE
    )

    val_df = load_dataset(
        VAL_FILE
    )

    test_df = load_dataset(
        TEST_FILE
    )

    print(
        f"Training examples:   {len(train_df)}"
    )

    print(
        f"Validation examples: {len(val_df)}"
    )

    print(
        f"Test examples:       {len(test_df)}"
    )

    print()
    print("Training distribution:")

    print(
        train_df["sentiment"]
        .value_counts()
    )

    # --------------------------------------------------------
    # Build model
    # --------------------------------------------------------

    print()
    print("Building TF-IDF + Logistic Regression model...")

    model = build_model()

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------

    print()
    print("Training model...")

    model.fit(
        train_df["review_text"],
        train_df["sentiment"]
    )

    print(
        "Training complete."
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    evaluate_model(
        model,
        val_df,
        "VALIDATION RESULTS"
    )

    # --------------------------------------------------------
    # Test
    # --------------------------------------------------------

    evaluate_model(
        model,
        test_df,
        "FINAL TEST RESULTS"
    )

    # --------------------------------------------------------
    # Hard test
    # --------------------------------------------------------

    if HARD_TEST_FILE.exists():

        hard_test_df = load_dataset(
            HARD_TEST_FILE
        )

        evaluate_model(
            model,
            hard_test_df,
            "HARD TEST RESULTS"
        )

    else:

        print()
        print(
            "No hard test dataset found."
        )

    # --------------------------------------------------------
    # Save model
    # --------------------------------------------------------

    MODEL_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        MODEL_FILE,
        "wb"
    ) as f:

        pickle.dump(
            model,
            f
        )

    print()
    print("=" * 70)
    print("MODEL SAVED")
    print("=" * 70)

    print(
        MODEL_FILE
    )

    # --------------------------------------------------------
    # Manual examples
    # --------------------------------------------------------

    test_examples(
        model
    )

    print()
    print("=" * 70)
    print("TRAINING FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    main()