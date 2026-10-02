import pandas as pd

INPUT_FILE = "dataset/isp_clean_data.csv"
OUTPUT_FILE = "dataset/final_isp_dataset.csv"

MIN_SAMPLES = 50

print("Loading cleaned dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Original records: {len(df):,}")

# Remove duplicate complaint/response pairs
df = df.drop_duplicates(
    subset=["complaint_text", "agent_response"]
)

# Remove categories with too few examples
category_counts = df["category"].value_counts()

valid_categories = category_counts[
    category_counts >= MIN_SAMPLES
].index

df = df[df["category"].isin(valid_categories)]

# Shuffle dataset
df = df.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)

# Save
df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8"
)

print("\n=== FINAL DATASET ===")
print(f"Records: {len(df):,}")

print("\nCategories:")
print(df["category"].value_counts())

print("\nSaved to:")
print(OUTPUT_FILE)