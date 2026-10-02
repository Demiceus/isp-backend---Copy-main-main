import pandas as pd

REAL_FILE = "dataset/isp_clean_data.csv"
SYNTHETIC_FILE = "dataset/synthetic_isp_training_data_6000.csv"

OUTPUT_FILE = "dataset/combined_isp_dataset.csv"

print("Loading datasets...")

real = pd.read_csv(REAL_FILE)
synthetic = pd.read_csv(SYNTHETIC_FILE)

# Keep only the fields needed for intent classification
real = real[
    ["complaint_text", "agent_response", "category"]
]

synthetic = synthetic[
    ["complaint_text", "agent_response", "category"]
]

# Mark the source
real["data_source"] = "telecom_filtered"
synthetic["data_source"] = "synthetic"

# Combine
combined = pd.concat(
    [real, synthetic],
    ignore_index=True
)

# Remove duplicate complaint + response pairs
combined = combined.drop_duplicates(
    subset=["complaint_text", "agent_response"]
)

# Remove account because your current dataset only has 1 example
combined = combined[
    combined["category"] != "account"
]

# Shuffle
combined = combined.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)

combined.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print("\n=== COMBINED DATASET ===")
print(f"Total records: {len(combined):,}")

print("\nCategory distribution:")
print(combined["category"].value_counts())

print("\nData source:")
print(combined["data_source"].value_counts())

print(f"\nSaved to: {OUTPUT_FILE}")