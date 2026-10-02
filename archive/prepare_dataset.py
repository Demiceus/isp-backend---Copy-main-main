import pandas as pd
import re
import os

INPUT_FILE = "dataset/telecom_conversations.csv"
OUTPUT_FILE = "dataset/isp_training_data.csv"

print("Loading telecom dataset...")
df = pd.read_csv(INPUT_FILE)

print(f"Original rows: {len(df):,}")

# Remove empty messages
df = df.dropna(subset=["text"])

# Clean text
df["text"] = (
    df["text"]
    .astype(str)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# Remove empty strings
df = df[df["text"] != ""]

# Sort conversations chronologically
df = df.sort_values(["conversation_id", "date_time"])

# Create previous/next message
df["next_speaker"] = df.groupby("conversation_id")["speaker"].shift(-1)
df["next_text"] = df.groupby("conversation_id")["text"].shift(-1)

# Keep client -> agent pairs
pairs = df[
    (df["speaker"] == "client") &
    (df["next_speaker"] == "agent")
].copy()

# Rename columns
pairs = pairs.rename(columns={
    "text": "complaint_text",
    "next_text": "agent_response"
})

# Keep only the fields we need
pairs = pairs[
    ["conversation_id", "complaint_text", "agent_response"]
]

# Remove extremely short messages
pairs = pairs[
    pairs["complaint_text"].str.len() >= 10
]

pairs = pairs[
    pairs["agent_response"].str.len() >= 10
]

# Remove duplicate complaint/response pairs
pairs = pairs.drop_duplicates(
    subset=["complaint_text", "agent_response"]
)

# Save
pairs.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8"
)

print("\n=== DATASET CREATED ===")
print(f"Training pairs: {len(pairs):,}")
print(f"Saved to: {OUTPUT_FILE}")

print("\n=== SAMPLE ===")
print(
    pairs.head(10).to_string(index=False)
)