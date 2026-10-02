import pandas as pd
import re

INPUT_FILE = "dataset/isp_filtered_data.csv"
OUTPUT_FILE = "dataset/isp_clean_data.csv"

# Maximum examples per category
MAX_PER_CATEGORY = 5000


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    text = str(text)

    # Email
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        '[EMAIL]',
        text
    )

    # Phone numbers
    text = re.sub(
        r'(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)',
        '[PHONE]',
        text
    )

    # Credit/debit card numbers
    text = re.sub(
        r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)',
        '[CARD_NUMBER]',
        text
    )

    # PIN
    text = re.sub(
        r'\b(?:account\s*)?pin\s*(?:is|:)?\s*[0-9Xx*_-]{3,8}\b',
        '[PIN]',
        text,
        flags=re.IGNORECASE
    )

    # Account number
    text = re.sub(
        r'\baccount\s*(?:number|no\.?|#)?\s*(?:is|:)?\s*[#]?[A-Za-z0-9_-]{6,}\b',
        'account [ACCOUNT_NUMBER]',
        text,
        flags=re.IGNORECASE
    )

    # Whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ============================================================
# ISP / BROADBAND TERMS
# ============================================================

ISP_TERMS = [
    "internet",
    "wifi",
    "wi-fi",
    "broadband",
    "router",
    "modem",
    "connection",
    "network",
    "download speed",
    "upload speed",
    "internet speed",
    "fiber",
    "fibre",
    "ethernet",
    "lan",
    "home internet",
    "home wifi",
    "home wi-fi",
    "isp",
]


# ============================================================
# MOBILE-ONLY TERMS
# ============================================================

MOBILE_TERMS = [
    "mobile phone",
    "cell phone",
    "cellular",
    "mobile service",
    "mobile network",
    "mobile data",
    "data plan",
    "text message",
    "texting",
    "sms",
    "phone call",
    "phone calls",
    "dropped calls",
    "make a call",
    "receive calls",
    "lost phone",
    "stolen phone",
    "imei",
    "sim card",
    "sim",
    "roaming",
    "iphone",
    "android phone",
]


# ============================================================
# DETERMINE WHETHER TEXT IS ISP RELATED
# ============================================================

def is_isp_related(text):
    text = text.lower()

    has_isp_term = any(
        term in text
        for term in ISP_TERMS
    )

    if not has_isp_term:
        return False

    # Reject clearly mobile-only complaints
    mobile_hits = sum(
        1 for term in MOBILE_TERMS
        if term in text
    )

    # If the text contains several mobile-specific terms
    # and doesn't clearly discuss home Internet, reject it.
    if mobile_hits >= 2:
        return False

    return True


# ============================================================
# CATEGORY VALIDATION
# ============================================================

CATEGORY_KEYWORDS = {

    "slow_internet": [
        "slow internet",
        "internet is slow",
        "internet too slow",
        "slow connection",
        "slow wifi",
        "slow wi-fi",
        "slow speed",
        "internet speed",
        "internet speeds",
        "download speed",
        "upload speed",
        "poor internet speed",
        "connection speed",
    ],

    "no_internet": [
        "no internet",
        "no connection",
        "internet not working",
        "internet isn't working",
        "internet is not working",
        "cannot connect to internet",
        "can't connect to internet",
        "unable to connect to internet",
        "lost internet connection",
        "no network connection",
    ],

    "intermittent_connection": [
        "keeps disconnecting",
        "keep disconnecting",
        "connection keeps dropping",
        "connection drops",
        "internet keeps dropping",
        "internet keeps disconnecting",
        "unstable connection",
        "connection is unstable",
        "intermittent connection",
        "frequent disconnect",
    ],

    "service_outage": [
        "internet outage",
        "service outage",
        "network outage",
        "area outage",
        "outage in my area",
        "internet is down",
        "service is down",
        "network is down",
    ],

    "router_modem": [
        "router",
        "modem",
        "router not working",
        "modem not working",
        "router problem",
        "modem problem",
        "restart router",
        "restart modem",
        "reboot router",
        "reboot modem",
    ],

    "billing": [
        "internet bill",
        "internet billing",
        "broadband bill",
        "broadband billing",
        "wifi bill",
        "wifi billing",
        "internet charge",
        "internet charged",
        "billing for internet",
        "billing issue",
        "billing problem",
        "incorrect bill",
        "wrong bill",
        "incorrect charge",
        "overcharged",
        "monthly internet bill",
    ],

    "installation": [
        "internet installation",
        "wifi installation",
        "broadband installation",
        "install internet",
        "install wifi",
        "internet technician",
        "installation appointment",
        "new internet connection",
        "new broadband connection",
    ],

    "account": [
        "internet account",
        "broadband account",
        "account access",
        "account locked",
        "account login",
        "account password",
        "password recovery",
        "cannot access my account",
        "can't access my account",
    ],

    "plan_change": [
        "internet plan",
        "broadband plan",
        "wifi plan",
        "change internet plan",
        "change my internet plan",
        "upgrade internet plan",
        "upgrade my internet",
        "downgrade internet plan",
        "change broadband plan",
        "upgrade broadband",
        "downgrade broadband",
    ],

    "technical_support": [
        "internet problem",
        "internet issue",
        "internet technical",
        "technical internet support",
        "technical support for internet",
        "network problem",
        "network issue",
        "connection problem",
        "connection issue",
        "wifi problem",
        "wifi issue",
        "broadband problem",
        "broadband issue",
    ],
}


def category_is_valid(text, category):
    text = text.lower()

    keywords = CATEGORY_KEYWORDS.get(category, [])

    return any(
        keyword in text
        for keyword in keywords
    )


# ============================================================
# LOAD
# ============================================================

print("Loading dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Original records: {len(df):,}")


# ============================================================
# REMOVE EMPTY
# ============================================================

df = df.dropna(
    subset=[
        "complaint_text",
        "agent_response",
        "category"
    ]
)


# ============================================================
# CLEAN
# ============================================================

print("Cleaning text...")

df["complaint_text"] = (
    df["complaint_text"]
    .astype(str)
    .apply(clean_text)
)

df["agent_response"] = (
    df["agent_response"]
    .astype(str)
    .apply(clean_text)
)


# ============================================================
# REMOVE VERY SHORT MESSAGES
# ============================================================

df = df[
    (df["complaint_text"].str.len() >= 20) &
    (df["agent_response"].str.len() >= 20)
]


# ============================================================
# REMOVE ACCOUNT/PIN-ONLY MESSAGES
# ============================================================

text_lower = df["complaint_text"].str.lower()

account_noise = (
    text_lower.str.match(
        r'^(sure,?\s*)?(my\s+)?account\s*(number|no\.?|#)',
        na=False
    )
    |
    text_lower.str.match(
        r'^(sure,?\s*)?(my\s+)?account\s*pin',
        na=False
    )
)

df = df[~account_noise]


# ============================================================
# ISP FILTER
# ============================================================

print("Filtering for broadband / ISP content...")

df = df[
    df["complaint_text"].apply(is_isp_related)
]


# ============================================================
# CATEGORY VALIDATION
# ============================================================

print("Validating categories...")

df = df[
    df.apply(
        lambda row: category_is_valid(
            row["complaint_text"],
            row["category"]
        ),
        axis=1
    )
]


# ============================================================
# REMOVE DUPLICATES
# ============================================================

df = df.drop_duplicates(
    subset=[
        "complaint_text",
        "agent_response"
    ]
)


# ============================================================
# BALANCE DATA
# ============================================================

print("Balancing categories...")

balanced = []

for category in CATEGORY_KEYWORDS.keys():

    category_df = df[
        df["category"] == category
    ]

    if len(category_df) == 0:
        continue

    category_df = category_df.sample(
        frac=1,
        random_state=42
    )

    category_df = category_df.head(
        MAX_PER_CATEGORY
    )

    balanced.append(category_df)


if balanced:
    df = pd.concat(
        balanced,
        ignore_index=True
    )

df = df.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8"
)


# ============================================================
# RESULTS
# ============================================================

print()
print("====================================")
print("CLEAN ISP DATASET CREATED")
print("====================================")

print(f"Final records: {len(df):,}")

print()
print("CATEGORY DISTRIBUTION:")

print(
    df["category"].value_counts()
)

print()
print("SAVED TO:")
print(OUTPUT_FILE)

print()
print("SAMPLE:")

print(
    df[
        [
            "complaint_text",
            "category",
            "agent_response"
        ]
    ].head(15).to_string(index=False)
)