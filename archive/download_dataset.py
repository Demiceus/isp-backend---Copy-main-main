from datasets import load_dataset

print("Downloading telecom dataset...")

dataset = load_dataset(
    "talkmap/telecom-conversation-corpus",
    split="train"
)

print("Download complete!")
print(dataset)

dataset.to_csv(
    "dataset/telecom_conversations.csv",
    index=False
)

print("Saved to dataset/telecom_conversations.csv")