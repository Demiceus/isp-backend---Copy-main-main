import pandas as pd

FILE = "dataset/isp_clean_data.csv"

df = pd.read_csv(FILE)

print("=== CLEAN DATASET CHECK ===")

print(f"Total records: {len(df):,}")

print(
    f"Unique conversations: "
    f"{df['conversation_id'].nunique():,}"
)

print("\nCategory distribution:")
print(df["category"].value_counts())

print("\nDuplicate complaints:")
print(
    df["complaint_text"].duplicated().sum()
)

print("\nEmpty values:")
print(df.isnull().sum())

print("\nAverage complaint length:")
print(
    df["complaint_text"]
    .str.len()
    .mean()
)

print("\nAverage response length:")
print(
    df["agent_response"]
    .str.len()
    .mean()
)