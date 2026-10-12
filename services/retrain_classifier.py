# --------------------------------------------------
# STANDARD LIBRARY IMPORTS
# --------------------------------------------------

import sys
import shutil
from datetime import datetime
from pathlib import Path


# --------------------------------------------------
# ADD PROJECT ROOT TO PYTHON PATH
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# --------------------------------------------------
# THIRD-PARTY IMPORTS
# --------------------------------------------------

import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# --------------------------------------------------
# PROJECT IMPORTS
# --------------------------------------------------

from app import create_app
from app.models import MLFeedback, Message, db


# --------------------------------------------------
# PATHS
# --------------------------------------------------
# --------------------------------------------------
# PATHS
# --------------------------------------------------

DATASET_FILE = (
    BASE_DIR
    / "dataset"
    / "synthetic_isp_training_data_6000.csv"
)

MODEL_FILE = (
    BASE_DIR
    / "services"
    / "isp_classifier.pkl"
)

BACKUP_DIR = (
    BASE_DIR
    / "services"
    / "model_backups"
)

BACKUP_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# LOAD ORIGINAL DATASET
# --------------------------------------------------

def load_original_dataset():

    print("\nLoading original complaint dataset...")

    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{DATASET_FILE}"
        )

    df = pd.read_csv(DATASET_FILE)

    required_columns = {
        "complaint_text",
        "category",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required dataset columns: {missing}"
        )

    df = df.dropna(
        subset=[
            "complaint_text",
            "category",
        ]
    )

    df["complaint_text"] = (
        df["complaint_text"]
        .astype(str)
        .str.strip()
    )

    df["category"] = (
        df["category"]
        .astype(str)
        .str.strip()
    )

    df = df[
        [
            "complaint_text",
            "category",
        ]
    ]

    print(
        f"Original examples loaded: {len(df):,}"
    )

    return df


# --------------------------------------------------
# LOAD APPROVED ML FEEDBACK
# --------------------------------------------------

def load_approved_feedback():

    print("\nLoading approved ML feedback...")

    rows = (
        MLFeedback.query
        .filter(
            MLFeedback.approved.is_(True),
            MLFeedback.corrected_category.isnot(None),
        )
        .all()
    )

    feedback_rows = []

    for feedback in rows:

        message = db.session.get(Message, feedback.message_id)

        if not message:

            print(
                f"Skipping feedback {feedback.id}: "
                f"message {feedback.message_id} not found."
            )

            continue

        text = (
            message.content or ""
        ).strip()

        category = (
            feedback.corrected_category or ""
        ).strip()

        if not text:
            print(
                f"Skipping feedback {feedback.id}: "
                f"empty message."
            )

            continue

        if not category:
            print(
                f"Skipping feedback {feedback.id}: "
                f"empty corrected category."
            )

            continue

        feedback_rows.append({
            "complaint_text": text,
            "category": category,
        })

    df = pd.DataFrame(
        feedback_rows,
        columns=[
            "complaint_text",
            "category",
        ],
    )

    print(
        f"Approved feedback examples loaded: "
        f"{len(df):,}"
    )

    return df


# --------------------------------------------------
# BUILD TRAINING DATA
# --------------------------------------------------

def build_training_dataset():

    original = load_original_dataset()

    feedback = load_approved_feedback()

    print(
        f"\nOriginal training examples: "
        f"{len(original):,}"
    )

    print(
        f"Approved feedback examples: "
        f"{len(feedback):,}"
    )

    if not feedback.empty:

        print("\nApproved feedback:")

        print(
            feedback.to_string(index=False)
        )

    combined = pd.concat(
        [
            original,
            feedback,
        ],
        ignore_index=True,
    )

    # Remove exact duplicate examples.
    combined = combined.drop_duplicates(
        subset=[
            "complaint_text",
            "category",
        ]
    )

    print(
        f"\nCombined training examples: "
        f"{len(combined):,}"
    )

    print("\nCategory distribution:")

    print(
        combined["category"]
        .value_counts()
        .sort_index()
    )

    return combined


# --------------------------------------------------
# CREATE MODEL
# --------------------------------------------------

def create_model():

    return Pipeline([
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
            "classifier",
            LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
            ),
        ),
    ])


# --------------------------------------------------
# EVALUATE MODEL
# --------------------------------------------------

def evaluate_model(
    model,
    X_test,
    y_test,
):

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    print(
        "\n========================================"
    )

    print(
        "RETRAINED MODEL EVALUATION"
    )

    print(
        "========================================"
    )

    print(
        f"\nAccuracy: {accuracy:.4f}"
    )

    print(
        "\nClassification report:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            digits=4,
        )
    )

    return accuracy


# --------------------------------------------------
# BACKUP CURRENT MODEL
# --------------------------------------------------

def backup_current_model():

    if not MODEL_FILE.exists():

        print(
            "\nNo existing production model found."
        )

        return None

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_file = (
        BACKUP_DIR
        / f"isp_classifier_{timestamp}.pkl"
    )

    shutil.copy2(
        MODEL_FILE,
        backup_file,
    )

    print(
        "\nCurrent production model backed up to:"
    )

    print(
        backup_file
    )

    return backup_file


# --------------------------------------------------
# PROMOTE MODEL
# --------------------------------------------------

def promote_model(model):

    print(
        "\n========================================"
    )

    print(
        "PROMOTING MODEL TO PRODUCTION"
    )

    print(
        "========================================"
    )

    # Backup existing model first.
    backup_current_model()

    # Save new model.
    joblib.dump(
        model,
        MODEL_FILE,
    )

    print(
        "\nNew production model saved to:"
    )

    print(
        MODEL_FILE
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print(
        "========================================"
    )

    print(
        "NetAssist AI Complaint Model Retraining"
    )

    print(
        "========================================"
    )

    # ------------------------------------------
    # CHECK MODE
    # ------------------------------------------

    promote = (
        "--promote"
        in sys.argv
    )

    if promote:

        print(
            "\nMODE: PRODUCTION PROMOTION"
        )

    else:

        print(
            "\nMODE: DRY RUN"
        )

        print(
            "Production model will NOT be changed."
        )

    # ------------------------------------------
    # CREATE FLASK APP
    # ------------------------------------------

    app = create_app()

    with app.app_context():

        # --------------------------------------
        # BUILD DATASET
        # --------------------------------------

        dataset = (
            build_training_dataset()
        )

        X = dataset[
            "complaint_text"
        ]

        y = dataset[
            "category"
        ]

        # --------------------------------------
        # VALIDATION SPLIT
        # --------------------------------------

        X_train, X_test, y_train, y_test = (
            train_test_split(
                X,
                y,
                test_size=0.20,
                random_state=42,
                stratify=y,
            )
        )

        print(
            f"\nTraining split: "
            f"{len(X_train):,}"
        )

        print(
            f"Validation split: "
            f"{len(X_test):,}"
        )

        # --------------------------------------
        # TRAIN
        # --------------------------------------

        model = create_model()

        print(
            "\nTraining TF-IDF + "
            "Logistic Regression..."
        )

        model.fit(
            X_train,
            y_train,
        )

        print(
            "\nTraining complete."
        )

        # --------------------------------------
        # VERIFY PREDICT PROBA
        # --------------------------------------

        if not hasattr(
            model,
            "predict_proba"
        ):

            raise RuntimeError(
                "Retrained model does not support "
                "predict_proba()."
            )

        print(
            "predict_proba() support: OK"
        )

        # --------------------------------------
        # EVALUATE
        # --------------------------------------

        accuracy = evaluate_model(
            model,
            X_test,
            y_test,
        )

        # --------------------------------------
        # SAFETY CHECK
        # --------------------------------------

        MIN_ACCURACY = 0.80

        print(
            "\n========================================"
        )

        print(
            "MODEL SAFETY CHECK"
        )

        print(
            "========================================"
        )

        print(
            f"\nMinimum required accuracy: "
            f"{MIN_ACCURACY:.2f}"
        )

        print(
            f"Retrained accuracy: "
            f"{accuracy:.4f}"
        )

        # --------------------------------------
        # REJECT IF BELOW THRESHOLD
        # --------------------------------------

        if accuracy < MIN_ACCURACY:

            print(
                "\nRETRAINING REJECTED."
            )

            print(
                "The new model did not pass "
                "the minimum accuracy threshold."
            )

            print(
                "The production model was NOT changed."
            )

            return

        # --------------------------------------
        # DRY RUN
        # --------------------------------------

        if not promote:

            print(
                "\n========================================"
            )

            print(
                "DRY RUN SUCCESSFUL"
            )

            print(
                "========================================"
            )

            print(
                "\nThe retrained model passed "
                "the accuracy threshold."
            )

            print(
                "\nProduction model was NOT changed."
            )

            print(
                "\nTo promote this model to production, run:"
            )

            print(
                "python services/retrain_classifier.py --promote"
            )

            return

        # --------------------------------------
        # PROMOTE
        # --------------------------------------

        promote_model(
            model
        )

        print(
            "\n========================================"
        )

        print(
            "RETRAINING COMPLETE"
        )

        print(
            "========================================"
        )


# --------------------------------------------------
# RUN SCRIPT
# --------------------------------------------------

if __name__ == "__main__":
    main()