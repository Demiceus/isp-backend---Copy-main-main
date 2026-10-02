import pandas as pd
import re

INPUT_FILE = "dataset/isp_training_data.csv"
OUTPUT_FILE = "dataset/isp_filtered_data.csv"

print("Loading training pairs...")

# Keywords related to ISP / internet support
patterns = {
    "slow_internet": [
        r"\bslow internet\b",
        r"\binternet.*slow\b",
        r"\bslow.*internet\b",
        r"\bslow connection\b",
        r"\bslow wifi\b",
        r"\bslow wi-fi\b",
        r"\bpoor internet speed\b",
        r"\bslow speed\b",
    ],

    "no_internet": [
        r"\bno internet\b",
        r"\binternet.*not working\b",
        r"\binternet.*down\b",
        r"\bno connection\b",
        r"\bcan't connect\b",
        r"\bcannot connect\b",
        r"\bunable to connect\b",
        r"\blost.*connection\b",
    ],

    "intermittent_connection": [
        r"\bdisconnecting\b",
        r"\bkeeps disconnecting\b",
        r"\bconnection.*drops\b",
        r"\bdrops.*connection\b",
        r"\binternet.*drops\b",
        r"\bconnection.*unstable\b",
        r"\bunstable connection\b",
    ],

    "service_outage": [
        r"\boutage\b",
        r"\bservice.*outage\b",
        r"\bnetwork.*outage\b",
        r"\barea.*outage\b",
        r"\bservice.*down\b",
        r"\bnetwork.*down\b",
    ],

    "router_modem": [
        r"\brouter\b",
        r"\bmodem\b",
        r"\breboot.*router\b",
        r"\brestart.*router\b",
        r"\brouter.*restart\b",
        r"\bmodem.*restart\b",
    ],

    "billing": [
        r"\bbill\b",
        r"\bbilling\b",
        r"\bcharged\b",
        r"\bcharge\b",
        r"\bovercharged\b",
        r"\bpayment\b",
        r"\bmonthly fee\b",
        r"\binvoice\b",
    ],

    "installation": [
        r"\binstallation\b",
        r"\binstall.*internet\b",
        r"\binstall.*wifi\b",
        r"\btechnician.*install\b",
        r"\bnew connection\b",
    ],

    "account": [
        r"\baccount\b",
        r"\baccount number\b",
        r"\baccount information\b",
        r"\baccount.*problem\b",
    ],

    "plan_change": [
        r"\bchange.*plan\b",
        r"\bupgrade.*plan\b",
        r"\bdowngrade.*plan\b",
        r"\bchange.*subscription\b",
        r"\bupgrade.*internet\b",
        r"\binternet plan\b",
    ],

    "technical_support": [
        r"\btechnical support\b",
        r"\btechnical issue\b",
        r"\bconnection problem\b",
        r"\bnetwork problem\b",
        r"\binternet problem\b",
        r"\bnetwork issue\b",
    ],
}


def classify(text):
    text = str(text).lower()

    for category, regex_list in patterns.items():
        for pattern in regex_list:
            if re.search(pattern, text):
                return category

    return None


print("Filtering ISP-related complaints...")

# Process in chunks so we don't need to load everything into RAM.
chunks = []

for chunk in pd.read_csv(
    INPUT_FILE,
    chunksize=100_000
):
    chunk["category"] = chunk["complaint_text"].apply(classify)

    chunk = chunk.dropna(subset=["category"])

    chunks.append(chunk)

    print(
        f"Processed {sum(len(x) for x in chunks):,} ISP-related records..."
    )


print("Combining results...")

result = pd.concat(chunks, ignore_index=True)

# Remove duplicate complaint/response pairs
result = result.drop_duplicates(
    subset=["complaint_text", "agent_response"]
)

# Save
result.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8"
)

print("\n==============================")
print("ISP DATASET CREATED")
print("==============================")

print(f"Total ISP records: {len(result):,}")
print(f"Saved to: {OUTPUT_FILE}")

print("\nCATEGORY DISTRIBUTION:")
print(result["category"].value_counts())

print("\nSAMPLE:")
print(
    result[
        ["complaint_text", "category", "agent_response"]
    ].head(20).to_string(index=False)
)