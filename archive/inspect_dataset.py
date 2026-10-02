import pandas as pd

FILE = "dataset/telecom_conversations.csv"

print("Loading dataset...")

df = pd.read_csv(FILE)

print("\n=== DATASET INFO ===")
print("Rows:", len(df))
print("Columns:", list(df.columns))

print("\n=== SPEAKERS ===")
print(df["speaker"].value_counts())

print("\n=== SAMPLE RECORDS ===")
print(df.head(10).to_string())

print("\n=== MISSING VALUES ===")
print(df.isnull().sum())