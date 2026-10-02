"""
NetAssist AI - Sentiment Dataset Generator
==========================================

Generates a synthetic ISP customer-review sentiment dataset
containing English, Filipino/Tagalog, and Taglish examples.

Sentiment classes:
    positive
    negative
    neutral

Dataset strategy:
    1. Manually curated natural examples
    2. Context/hard examples
    3. ISP-specific situations
    4. Controlled sentence variations
    5. Optional realistic noise
    6. Strict train/validation/test separation
    7. Deduplication

Default output:
    data/sentiment_train.csv
    data/sentiment_val.csv
    data/sentiment_test.csv

Default size:
    20,000 examples

Distribution:
    Positive = 40%
    Negative = 40%
    Neutral  = 20%

IMPORTANT:
This generator creates SYNTHETIC/CURATED training data.
It should not be presented as real customer data.
"""

import csv
import random
import re
import os
from pathlib import Path
from collections import Counter

# ==============================================================
# CONFIGURATION
# ==============================================================

SEED = 42
random.seed(SEED)

TOTAL_DATASET_SIZE = 20_000

POSITIVE_RATIO = 0.40
NEGATIVE_RATIO = 0.40
NEUTRAL_RATIO = 0.20

TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10

OUTPUT_DIR = Path("data")

# Percentage of generated examples receiving noise
NOISE_PROBABILITY = 0.15


# ==============================================================
# NATURAL POSITIVE REVIEWS
# ==============================================================

POSITIVE_REVIEWS = [

    # Filipino
    "Okay na po yung internet namin, salamat.",
    "Gumagana na ulit yung WiFi namin.",
    "Ayos na po yung connection.",
    "Naayos na po yung problema.",
    "Mabilis na po ulit yung internet.",
    "Stable na po yung connection namin.",
    "Bumalik na po yung internet.",
    "Okay na po yung router.",
    "Maayos na po yung modem.",
    "Naka-connect na po ako.",
    "Naayos na po yung line namin.",
    "Tapos na po yung repair.",
    "Gumagana na po lahat.",
    "Okay na po ang signal.",
    "Maayos na po yung serbisyo.",
    "Salamat po sa mabilis na tulong.",
    "Maraming salamat po sa assistance.",
    "Salamat po at naayos agad.",
    "Malaking tulong po yung troubleshooting.",
    "Satisfied po ako sa assistance.",

    # Taglish
    "Okay na po yung internet, thank you.",
    "Working na po yung WiFi namin.",
    "Fixed na po yung connection.",
    "Resolved na po yung issue.",
    "Okay na po yung net namin, salamat sa support.",
    "Thank you po, working na ulit.",
    "Much better na po yung connection.",
    "Stable na ulit yung internet namin.",
    "Naayos na po yung problem, thank you.",
    "Mabilis na ulit yung internet, salamat po.",
    "The internet is working na po.",
    "Okay na po, thank you sa assistance.",
    "Good na po yung connection namin.",
    "The problem has been fixed na po.",
    "Salamat po, everything is working now.",

    # English
    "The internet is working now.",
    "My connection is stable now.",
    "The problem has been fixed.",
    "Everything is working properly now.",
    "The connection is much better now.",
    "Thank you for helping me resolve the issue.",
    "The internet is fast again.",
    "My WiFi is working properly now.",
    "The technician fixed the problem.",
    "The service is back now.",
    "I am satisfied with the assistance.",
    "The troubleshooting was helpful.",
    "Thank you for the quick assistance.",
    "My connection is stable again.",
    "The issue has been resolved.",
]


# ==============================================================
# NATURAL NEGATIVE REVIEWS
# ==============================================================

NEGATIVE_REVIEWS = [

    # Filipino
    "Mabagal pa rin po yung internet.",
    "Hindi pa rin gumagana yung WiFi.",
    "Sobrang bagal pa rin ng net.",
    "Hindi pa rin naayos yung problema.",
    "Wala pa rin kaming internet.",
    "Putol-putol pa rin yung connection.",
    "Hindi pa rin ako makaconnect.",
    "Walang nangyari sa report ko.",
    "Hindi nakatulong yung troubleshooting.",
    "Wala pa ring signal.",
    "Bumabalik pa rin yung problema.",
    "Hindi pa rin umaayos yung connection.",
    "Same pa rin po, walang pagbabago.",
    "Nawawala pa rin yung internet.",
    "Hindi pa rin gumagana yung modem.",
    "Hindi pa rin tapos yung repair.",
    "Hindi pa rin dumadating yung technician.",
    "Sobrang tagal na po nito.",
    "Nakakainis na po yung connection.",
    "Sayang po yung binabayad ko.",

    # Taglish
    "Still slow pa rin po yung internet.",
    "Still not working po.",
    "Hindi pa rin working yung WiFi.",
    "The connection is still down po.",
    "Mabagal pa rin yung internet kahit nag-reset na.",
    "Hindi pa rin fixed yung issue.",
    "Still broken pa rin yung connection.",
    "Wala pa ring improvement sa internet.",
    "The problem is still there po.",
    "Hindi pa rin resolved yung complaint.",
    "Sobrang disappointing ng service.",
    "Very slow pa rin yung connection.",
    "Nag-follow up na ako pero wala pa ring update.",
    "Ilang beses na akong nag-report pero same pa rin.",
    "Hindi pa rin okay yung service.",

    # English
    "The internet is still very slow.",
    "The connection is still not working.",
    "The problem has not been fixed.",
    "My WiFi is still down.",
    "The issue is still unresolved.",
    "The connection keeps disconnecting.",
    "There has been no improvement.",
    "The technician has not arrived yet.",
    "The service is still unavailable.",
    "The troubleshooting did not help.",
    "I am still having the same problem.",
    "The internet keeps going offline.",
    "The connection is still unstable.",
    "I am disappointed with the service.",
    "The issue remains unresolved.",
]


# ==============================================================
# NATURAL NEUTRAL REVIEWS
# ==============================================================

NEUTRAL_REVIEWS = [

    # Filipino
    "Sige po.",
    "Noted po.",
    "Maghihintay po ako.",
    "Titingnan ko po.",
    "Naiintindihan ko po.",
    "Okay po.",
    "Opo, noted.",
    "Sige, salamat sa update.",
    "Feedback lang po.",
    "Nagbibigay lang po ako ng feedback.",
    "Hintayin ko na lang po yung technician.",
    "Susundin ko po yung instructions.",
    "Iche-check ko po.",
    "Nareceive ko po yung information.",
    "Sabihan niyo na lang po ako.",

    # Taglish
    "Okay po, noted.",
    "Sige po, I'll wait.",
    "Noted po, thank you for the update.",
    "I understand po.",
    "I'll check it po.",
    "Okay, I'll wait for the technician.",
    "Received po.",
    "Copy po.",
    "Sure po.",
    "That's all po.",
    "I will follow the instructions.",
    "I'll check the modem first.",
    "Okay, I'll monitor the connection.",
    "Salamat sa update, maghihintay ako.",
    "Noted, I'll wait for further instructions.",

    # English
    "Okay.",
    "Noted.",
    "I understand.",
    "I will check it.",
    "I will wait for the technician.",
    "Thank you for the update.",
    "I received the information.",
    "I will follow the instructions.",
    "I will monitor the connection.",
    "That is all for now.",
    "Understood.",
    "I will check again later.",
    "I will wait for further instructions.",
]


# ==============================================================
# HARD / CONTEXT-DEPENDENT EXAMPLES
# ==============================================================

"""
These are especially important.

They prevent the model from learning:

    "slow" = always negative
    "thank you" = always positive
    "okay" = always neutral

Instead, the model must consider the whole sentence.
"""

HARD_POSITIVE = [

    "Mabagal kanina pero okay na ngayon.",
    "Mabagal siya kanina pero mabilis na ulit.",
    "Nagkaroon ng problema pero naayos na po.",
    "Hindi gumana yung unang troubleshooting pero okay na ngayon.",
    "Akala ko hindi maaayos pero working na ulit.",
    "Medyo matagal yung assistance pero resolved na yung issue.",
    "Nag-disconnect kanina pero stable na ngayon.",
    "Nagkaroon ng outage pero bumalik na yung service.",
    "Nagkaroon ng problema sa modem pero naayos na.",
    "Hindi ako makaconnect kanina pero okay na ngayon.",
    "Mabagal yung internet kanina, pero mabilis na ulit.",
    "Nag-report ako kanina at naayos naman agad.",
    "Medyo matagal yung repair pero okay na po.",
    "Nagkaroon ng issue sa billing pero na-correct na.",
    "Hindi perfect yung process pero resolved na yung concern.",
    "Nagkaroon ng delay pero naayos din naman.",
    "Nag-follow up ako at eventually naayos yung connection.",
    "Thank you po, mabagal kanina pero okay na ngayon.",
    "Mabagal pa rin yung history ng connection pero stable na ngayon.",
    "Nagkaroon ng problema pero satisfied ako sa assistance.",
]


HARD_NEGATIVE = [

    "Salamat po sa response pero hindi pa rin gumagana.",
    "Thank you sa assistance pero mabagal pa rin yung internet.",
    "Okay yung support pero hindi pa rin naayos yung connection.",
    "Na-restart ko na po pero wala pa ring internet.",
    "Nag-follow up na ako pero hindi pa rin resolved.",
    "Salamat sa update pero wala pa ring connection.",
    "Mabilis yung response pero hindi pa rin gumagana yung service.",
    "Naayos daw pero bumalik ulit yung problema.",
    "Working siya kanina pero down na naman ngayon.",
    "Thank you po pero same problem pa rin.",
    "Okay yung technician pero hindi pa rin stable yung internet.",
    "Nag-report na ako ilang beses pero walang improvement.",
    "Na-restart ko na lahat pero disconnected pa rin.",
    "Sige po, pero hindi pa rin resolved yung issue.",
    "Helpful yung instructions pero hindi pa rin gumagana.",
    "Mabilis sumagot ang support pero unresolved pa rin.",
    "Salamat sa response, pero sobrang bagal pa rin.",
    "Na-check na yung modem pero wala pa ring signal.",
    "Nagbayad naman ako pero wala pa ring service.",
    "The support responded quickly, but the problem remains.",
]


HARD_NEUTRAL = [

    "Salamat sa update, maghihintay ako ng technician.",
    "Okay po, susundin ko muna yung instructions.",
    "Thank you sa information, iche-check ko muna.",
    "Noted po, babalik ako kapag may update.",
    "Sige po, monitor ko muna yung connection.",
    "Okay po, maghihintay muna ako.",
    "Salamat sa update, wala pa akong ibang concern.",
    "I understand po, I'll wait for the next update.",
    "Received po, iche-check ko muna yung modem.",
    "Okay, I'll follow the instructions first.",
    "Noted po, sabihin niyo na lang kung may kailangan.",
    "Thank you for the information, I'll check it.",
    "Sige, wait ko muna yung technician.",
    "Okay po, I'll monitor it for now.",
    "I understand, I'll wait for further instructions.",
]


# ==============================================================
# ISP CONTEXTS
# ==============================================================

SITUATIONS = [

    "nag-report ako tungkol sa slow internet",
    "nag-report ako tungkol sa walang connection",
    "nag-follow up ako tungkol sa intermittent connection",
    "nag-follow up ako tungkol sa router problem",
    "nag-request ako ng technician dahil sa modem issue",
    "nag-file ako ng complaint tungkol sa service outage",
    "nag-message ako tungkol sa billing concern",
    "nag-report ako tungkol sa wrong charge",
    "nag-request ako ng installation",
    "nag-follow up ako tungkol sa installation delay",
    "nag-request ako ng plan change",
    "nag-message ako tungkol sa account concern",
    "nag-report ako ng unstable WiFi",
    "nag-report ako ng red light sa modem",
    "nag-report ako ng mahinang signal",
    "nag-follow up ako tungkol sa putol-putol na connection",
    "nag-report ako ng mabagal na upload",
    "nag-contact ako ng customer support",
]


POSITIVE_CONTEXT_ENDINGS = [

    "at naayos naman agad",
    "at gumagana na ngayon",
    "at stable na ulit",
    "at okay na po ngayon",
    "at mabilis na ulit",
    "at resolved na yung concern",
    "at wala nang problema",
    "at nakakapag-browse na ulit ako",
    "at nakakapag-work na ulit ako",
    "at nakakapag-online class na ako",
]


NEGATIVE_CONTEXT_ENDINGS = [

    "pero hindi pa rin naayos",
    "pero wala pa ring connection",
    "pero mabagal pa rin",
    "pero nagdi-disconnect pa rin",
    "pero hindi pa rin gumagana",
    "pero wala pa ring improvement",
    "pero unresolved pa rin",
    "pero hindi pa rin bumabalik yung service",
    "pero same problem pa rin",
]


NEUTRAL_CONTEXT_ENDINGS = [

    "at maghihintay muna ako",
    "at susundin ko muna yung instructions",
    "at iche-check ko muna",
    "at monitor ko muna yung connection",
    "at hihintayin ko yung technician",
    "at babalik ako kapag may update",
]


# ==============================================================
# LANGUAGE / STYLE VARIATIONS
# ==============================================================

POSITIVE_PREFIXES = [
    "",
    "Hi, ",
    "Hello, ",
    "For now, ",
    "Sa ngayon, ",
]

NEGATIVE_PREFIXES = [
    "",
    "Hi, ",
    "Hello, ",
    "Until now, ",
    "Sa ngayon, ",
]

NEUTRAL_PREFIXES = [
    "",
    "Hi, ",
    "Hello, ",
]


# ==============================================================
# NOISE
# ==============================================================

TYPO_MAP = {
    "internet": ["internet", "intenet", "internet", "internt"],
    "connection": ["connection", "conection", "connecton", "connection"],
    "gumagana": ["gumagana", "gumagagana", "gumagaga", "gumagana"],
    "salamat": ["salamat", "salamt", "salamat"],
    "hindi": ["hindi", "hndi", "hindi", "d hindi"],
    "mabagal": ["mabagal", "mbagal", "mabagal"],
    "mabilis": ["mabilis", "mabilis", "mablis"],
    "router": ["router", "routr", "router"],
    "modem": ["modem", "modm", "modem"],
    "problema": ["problema", "problem", "problema"],
    "connection": ["connection", "conection"],
    "working": ["working", "workng", "working"],
    "resolved": ["resolved", "resloved", "resolved"],
    "thank": ["thank", "thnak", "thank"],
}


def typo_noise(text, probability=0.12):
    """
    Adds realistic occasional spelling mistakes.
    """
    if random.random() > probability:
        return text

    words = text.split()
    result = []

    for word in words:

        clean = re.sub(
            r"[^a-zA-Z]",
            "",
            word
        ).lower()

        if clean in TYPO_MAP and random.random() < 0.35:
            replacement = random.choice(TYPO_MAP[clean])

            # Preserve basic punctuation
            if word.endswith("."):
                replacement += "."

            result.append(replacement)
        else:
            result.append(word)

    return " ".join(result)


def case_noise(text, probability=0.15):

    if random.random() > probability:
        return text

    choice = random.random()

    if choice < 0.25:
        return text.lower()

    if choice < 0.50:
        return text.upper()

    if choice < 0.75:
        return text.capitalize()

    return text


def punctuation_noise(text, probability=0.20):

    if random.random() > probability:
        return text

    # Don't add punctuation if it already has one.
    if text.endswith((".", "!", "?", "...")):
        return text

    punctuation = random.choice([
        ".",
        "!",
        "...",
        "!!",
    ])

    return text + punctuation


def emoji_noise(text, probability=0.08):

    if random.random() > probability:
        return text

    emojis = [
        "😊",
        "🙏",
        "👍",
        "❤️",
        "😐",
        "😩",
        "😤",
        "😭",
        "🙄",
    ]

    return text + " " + random.choice(emojis)


def elongation_noise(text, probability=0.06):

    if random.random() > probability:
        return text

    # Only elongate common conversational words.
    candidates = [
        "po",
        "na",
        "oo",
        "sige",
        "thank",
        "okay",
    ]

    for word in candidates:

        pattern = r"\b" + re.escape(word) + r"\b"

        if re.search(pattern, text, flags=re.IGNORECASE):

            replacement = word + random.choice([
                "o",
                "oo",
                "ooo",
            ])

            text = re.sub(
                pattern,
                replacement,
                text,
                count=1,
                flags=re.IGNORECASE
            )

            break

    return text


def spacing_noise(text, probability=0.05):

    if random.random() > probability:
        return text

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # Occasionally remove space after comma.
    if "," in text and random.random() < 0.5:
        text = text.replace(", ", ",")

    return text


def apply_noise(text):

    text = typo_noise(text)
    text = case_noise(text)
    text = punctuation_noise(text)
    text = emoji_noise(text)
    text = elongation_noise(text)
    text = spacing_noise(text)

    return text.strip()


# ==============================================================
# HELPERS
# ==============================================================

def clean_text(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = text.strip()

    text = text.strip(
        " ,"
    )

    return text


def create_context_examples(
    positive_count,
    negative_count,
    neutral_count
):

    rows = []

    for _ in range(positive_count):

        situation = random.choice(
            SITUATIONS
        )

        ending = random.choice(
            POSITIVE_CONTEXT_ENDINGS
        )

        text = (
            f"{situation}, "
            f"{ending}"
        )

        rows.append(
            (
                clean_text(text),
                "positive",
                "context"
            )
        )

    for _ in range(negative_count):

        situation = random.choice(
            SITUATIONS
        )

        ending = random.choice(
            NEGATIVE_CONTEXT_ENDINGS
        )

        text = (
            f"{situation}, "
            f"{ending}"
        )

        rows.append(
            (
                clean_text(text),
                "negative",
                "context"
            )
        )

    for _ in range(neutral_count):

        situation = random.choice(
            SITUATIONS
        )

        ending = random.choice(
            NEUTRAL_CONTEXT_ENDINGS
        )

        text = (
            f"{situation}, "
            f"{ending}"
        )

        rows.append(
            (
                clean_text(text),
                "neutral",
                "context"
            )
        )

    return rows


# ==============================================================
# LANGUAGE TAGGER
# ==============================================================

FILIPINO_MARKERS = {
    "po",
    "opo",
    "salamat",
    "yung",
    "ang",
    "ng",
    "mga",
    "ako",
    "kami",
    "namin",
    "hindi",
    "wala",
    "pa",
    "rin",
    "din",
    "na",
    "mabagal",
    "mabilis",
    "gumagana",
    "naayos",
    "problema",
    "sige",
    "maghihintay",
    "titingnan",
    "ayos",
    "ulít",
    "ulit",
    "natin",
    "ko",
    "mo",
    "nila",
    "niyo",
    "kayo",
}


def tag_language(text):

    words = set(
        re.findall(
            r"[a-zA-Z]+",
            text.lower()
        )
    )

    filipino_hits = len(
        words & FILIPINO_MARKERS
    )

    # Common English indicators.
    english_markers = {
        "the",
        "is",
        "are",
        "was",
        "were",
        "working",
        "fixed",
        "resolved",
        "thank",
        "thanks",
        "internet",
        "connection",
        "problem",
        "support",
        "service",
        "issue",
        "still",
        "very",
        "now",
        "help",
        "assistance",
        "update",
        "wait",
        "technician",
    }

    english_hits = len(
        words & english_markers
    )

    if filipino_hits > 0 and english_hits > 0:
        return "taglish"

    if filipino_hits > 0:
        return "tagalog"

    return "english"


# ==============================================================
# GENERATE BASE DATA
# ==============================================================

def generate_base_examples():

    rows = []

    # Natural examples
    for text in POSITIVE_REVIEWS:
        rows.append(
            (
                text,
                "positive",
                "natural"
            )
        )

    for text in NEGATIVE_REVIEWS:
        rows.append(
            (
                text,
                "negative",
                "natural"
            )
        )

    for text in NEUTRAL_REVIEWS:
        rows.append(
            (
                text,
                "neutral",
                "natural"
            )
        )

    # Hard examples
    for text in HARD_POSITIVE:
        rows.append(
            (
                text,
                "positive",
                "hard"
            )
        )

    for text in HARD_NEGATIVE:
        rows.append(
            (
                text,
                "negative",
                "hard"
            )
        )

    for text in HARD_NEUTRAL:
        rows.append(
            (
                text,
                "neutral",
                "hard"
            )
        )

    return rows


# ==============================================================
# AUGMENTATION
# ==============================================================

def augment_examples(
    base_rows,
    target_count
):

    result = []

    # Start with base examples.
    result.extend(base_rows)

    used = set(
        text.lower()
        for text, _, _ in base_rows
    )

    while len(result) < target_count:

        text, sentiment, source = random.choice(
            base_rows
        )

        new_text = text

        # Occasionally add ISP context.
        if random.random() < 0.30:

            situation = random.choice(
                SITUATIONS
            )

            if sentiment == "positive":
                ending = random.choice(
                    POSITIVE_CONTEXT_ENDINGS
                )

                new_text = (
                    f"{situation}, "
                    f"{ending}"
                )

            elif sentiment == "negative":
                ending = random.choice(
                    NEGATIVE_CONTEXT_ENDINGS
                )

                new_text = (
                    f"{situation}, "
                    f"{ending}"
                )

            else:
                ending = random.choice(
                    NEUTRAL_CONTEXT_ENDINGS
                )

                new_text = (
                    f"{situation}, "
                    f"{ending}"
                )

        else:

            # Add a conversational prefix occasionally.
            if sentiment == "positive":
                prefix = random.choice(
                    POSITIVE_PREFIXES
                )

            elif sentiment == "negative":
                prefix = random.choice(
                    NEGATIVE_PREFIXES
                )

            else:
                prefix = random.choice(
                    NEUTRAL_PREFIXES
                )

            new_text = prefix + new_text

        new_text = clean_text(
            new_text
        )

        # Apply noise only to a minority.
        if random.random() < NOISE_PROBABILITY:
            new_text = apply_noise(
                new_text
            )

        key = new_text.lower()

        if (
            new_text
            and key not in used
        ):

            used.add(key)

            result.append(
                (
                    new_text,
                    sentiment,
                    "augmented"
                )
            )

    return result


# ==============================================================
# BUILD DATASET WITH SPLIT ISOLATION
# ==============================================================

def build_dataset(total_size=TOTAL_DATASET_SIZE):

    if total_size < 1000:
        raise ValueError(
            "Use at least 1000 examples."
        )

    # ----------------------------------------------------------
    # Calculate class counts
    # ----------------------------------------------------------

    positive_total = int(
        total_size * POSITIVE_RATIO
    )

    negative_total = int(
        total_size * NEGATIVE_RATIO
    )

    neutral_total = (
        total_size
        - positive_total
        - negative_total
    )

    # ----------------------------------------------------------
    # Generate base examples
    # ----------------------------------------------------------

    base_rows = generate_base_examples()

    print(
        f"Base examples: {len(base_rows)}"
    )

    # ----------------------------------------------------------
    # IMPORTANT:
    #
    # We first create each sentiment separately.
    # Then split the BASE examples into seed groups.
    #
    # This prevents the same base seed from appearing in
    # train/validation/test.
    # ----------------------------------------------------------

    by_sentiment = {
        "positive": [
            row for row in base_rows
            if row[1] == "positive"
        ],

        "negative": [
            row for row in base_rows
            if row[1] == "negative"
        ],

        "neutral": [
            row for row in base_rows
            if row[1] == "neutral"
        ],
    }

    seed_groups = {}

    for sentiment, rows in by_sentiment.items():

        random.shuffle(rows)

        n = len(rows)

        train_end = int(
            n * TRAIN_RATIO
        )

        val_end = train_end + int(
            n * VAL_RATIO
        )

        seed_groups[sentiment] = {
            "train": rows[:train_end],
            "val": rows[train_end:val_end],
            "test": rows[val_end:],
        }

    # ----------------------------------------------------------
    # Target counts per split
    # ----------------------------------------------------------

    train_targets = {
        "positive": int(
            positive_total * TRAIN_RATIO
        ),
        "negative": int(
            negative_total * TRAIN_RATIO
        ),
        "neutral": int(
            neutral_total * TRAIN_RATIO
        ),
    }

    val_targets = {
        "positive": int(
            positive_total * VAL_RATIO
        ),
        "negative": int(
            negative_total * VAL_RATIO
        ),
        "neutral": int(
            neutral_total * VAL_RATIO
        ),
    }

    test_targets = {
        "positive": (
            positive_total
            - train_targets["positive"]
            - val_targets["positive"]
        ),

        "negative": (
            negative_total
            - train_targets["negative"]
            - val_targets["negative"]
        ),

        "neutral": (
            neutral_total
            - train_targets["neutral"]
            - val_targets["neutral"]
        ),
    }

    targets = {
        "train": train_targets,
        "val": val_targets,
        "test": test_targets,
    }

    datasets = {}

    # ----------------------------------------------------------
    # Generate each split independently
    # ----------------------------------------------------------

    for split in [
        "train",
        "val",
        "test"
    ]:

        split_rows = []

        for sentiment in [
            "positive",
            "negative",
            "neutral"
        ]:

            target = targets[
                split
            ][sentiment]

            seeds = seed_groups[
                sentiment
            ][split]

            if not seeds:
                raise RuntimeError(
                    f"No seed examples available for "
                    f"{sentiment}/{split}"
                )

            # Generate only from this split's seeds.
            generated = augment_examples(
                seeds,
                target
            )

            split_rows.extend(
                generated[:target]
            )

        random.shuffle(
            split_rows
        )

        datasets[split] = split_rows

    return datasets


# ==============================================================
# CHECK LEAKAGE
# ==============================================================

def check_leakage(datasets):

    train_texts = {
        text.lower()
        for text, _, _ in datasets["train"]
    }

    val_texts = {
        text.lower()
        for text, _, _ in datasets["val"]
    }

    test_texts = {
        text.lower()
        for text, _, _ in datasets["test"]
    }

    train_val = train_texts & val_texts
    train_test = train_texts & test_texts
    val_test = val_texts & test_texts

    print("\n========== LEAKAGE CHECK ==========")

    print(
        f"Train ∩ Validation: {len(train_val)}"
    )

    print(
        f"Train ∩ Test:       {len(train_test)}"
    )

    print(
        f"Validation ∩ Test:  {len(val_test)}"
    )

    if (
        train_val
        or train_test
        or val_test
    ):
        print(
            "WARNING: Exact duplicate leakage detected."
        )
    else:
        print(
            "PASS: No exact text duplicates across splits."
        )


# ==============================================================
# WRITE CSV
# ==============================================================

def write_csv(
    filepath,
    rows
):

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "review_text",
            "sentiment",
            "language",
            "source",
        ])

        for text, sentiment, source in rows:

            writer.writerow([
                text,
                sentiment,
                tag_language(text),
                source,
            ])


# ==============================================================
# STATISTICS
# ==============================================================

def print_statistics(
    datasets
):

    print(
        "\n========== DATASET STATISTICS =========="
    )

    for split, rows in datasets.items():

        print(
            f"\n{split.upper()}: {len(rows)} examples"
        )

        sentiment_counts = Counter(
            sentiment
            for _, sentiment, _ in rows
        )

        source_counts = Counter(
            source
            for _, _, source in rows
        )

        language_counts = Counter(
            tag_language(text)
            for text, _, _ in rows
        )

        print(
            "Sentiment:"
        )

        for label in [
            "positive",
            "negative",
            "neutral"
        ]:
            print(
                f"  {label}: "
                f"{sentiment_counts[label]}"
            )

        print(
            "Source:"
        )

        for source, count in source_counts.items():
            print(
                f"  {source}: {count}"
            )

        print(
            "Language:"
        )

        for language, count in language_counts.items():
            print(
                f"  {language}: {count}"
            )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print(
        "=========================================="
    )

    print(
        "NetAssist AI Sentiment Dataset Generator"
    )

    print(
        "=========================================="
    )

    print(
        f"Target dataset size: {TOTAL_DATASET_SIZE}"
    )

    print(
        "Distribution: 40% positive / "
        "40% negative / 20% neutral"
    )

    print(
        "Language: English / Tagalog / Taglish"
    )

    print(
        "Split: 80% train / 10% validation / 10% test"
    )

    print()

    datasets = build_dataset(
        TOTAL_DATASET_SIZE
    )

    # ----------------------------------------------------------
    # Verify exact duplicate leakage
    # ----------------------------------------------------------

    check_leakage(
        datasets
    )

    # ----------------------------------------------------------
    # Create output directory
    # ----------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ----------------------------------------------------------
    # Write datasets
    # ----------------------------------------------------------

    train_path = (
        OUTPUT_DIR
        / "sentiment_train.csv"
    )

    val_path = (
        OUTPUT_DIR
        / "sentiment_val.csv"
    )

    test_path = (
        OUTPUT_DIR
        / "sentiment_test.csv"
    )

    write_csv(
        train_path,
        datasets["train"]
    )

    write_csv(
        val_path,
        datasets["val"]
    )

    write_csv(
        test_path,
        datasets["test"]
    )

    # ----------------------------------------------------------
    # Statistics
    # ----------------------------------------------------------

    print_statistics(
        datasets
    )

    # ----------------------------------------------------------
    # Final output
    # ----------------------------------------------------------

    print(
        "\n========== FILES CREATED =========="
    )

    print(
        train_path
    )

    print(
        val_path
    )

    print(
        test_path
    )

    print(
        "\nDataset generation complete."
    )


if __name__ == "__main__":
    main()