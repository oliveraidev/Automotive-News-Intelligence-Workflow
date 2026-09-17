import json
from pathlib import Path
import re

import pandas as pd


# ============================================================
# File paths
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data/processed/cleaned_automotive_news.csv"
OUTPUT_PATH = ROOT / "data/processed/classified_automotive_news.csv"


# ============================================================
# Brand taxonomy
# ============================================================

BRAND_KEYWORDS = {
    "BYD": [
        "byd",
    ],
    "Geely": [
        "geely",
    ],
    "Zeekr": [
        "zeekr",
    ],
    "NIO": [
        "nio",
    ],
    "XPeng": [
        "xpeng",
        "x-peng",
    ],
    "Li Auto": [
        "li auto",
    ],
    "Xiaomi Auto": [
        "xiaomi auto",
        "xiaomi ev",
        "xiaomi",
    ],
    "Tesla": [
        "tesla",
    ],
}


# ============================================================
# Topic taxonomy
# ============================================================

TOPIC_KEYWORDS = {
    "Battery & Energy": [
        "battery",
        "batteries",
        "battery pack",
        "battery cell",
        "blade battery",
        "lithium",
        "lithium-ion",
        "solid-state",
        "solid state battery",
        "sodium-ion",
        "energy storage",
        "battery technology",
        "battery capacity",
        "battery range",
        "energy density",
    ],

    "Charging Infrastructure": [
        "charging",
        "charger",
        "chargers",
        "charging station",
        "charging network",
        "charging infrastructure",
        "fast charging",
        "ultra-fast charging",
        "supercharger",
        "megawatt charging",
        "charging speed",
        "charging time",
    ],

    "Product Launch": [
        "new model",
        "new vehicle",
        "new car",
        "new suv",
        "new sedan",
        "new ev",
        "launch",
        "launched",
        "launches",
        "debut",
        "debuts",
        "debuted",
        "unveil",
        "unveiled",
        "unveils",
        "introduces",
        "introduced",
        "reveals",
        "revealed",
        "premiere",
        "new generation",
        "facelift",
        "refresh",
    ],

    "Sales & Deliveries": [
        "sales",
        "vehicle sales",
        "ev sales",
        "sold",
        "units sold",
        "deliveries",
        "delivery",
        "delivery figures",
        "registrations",
        "vehicle registrations",
        "market share",
        "sales volume",
        "sales growth",
        "monthly sales",
        "quarterly sales",
        "annual sales",
    ],

    "Financial Performance": [
        "revenue",
        "profit",
        "profits",
        "loss",
        "losses",
        "earnings",
        "financial results",
        "quarterly results",
        "net income",
        "operating income",
        "margin",
        "gross margin",
        "cash flow",
        "forecast",
        "guidance",
    ],

    "International Expansion": [
        "expansion",
        "expand",
        "expanding",
        "overseas",
        "international",
        "international market",
        "international expansion",
        "global expansion",
        "market entry",
        "enter the market",
        "enters the market",
        "new market",
        "overseas market",
        "export",
        "exports",
        "exporting",
        "european market",
        "launch in europe",
    ],

    "Manufacturing": [
        "factory",
        "plant",
        "vehicle plant",
        "production plant",
        "manufacturing",
        "manufacturing facility",
        "production",
        "production capacity",
        "production line",
        "mass production",
        "assembly",
        "assembly line",
        "factory capacity",
        "factory expansion",
        "gigafactory",
        "manufacturing base",
    ],

    "Autonomous Driving & ADAS": [
        "autonomous",
        "autonomous driving",
        "self-driving",
        "self driving",
        "driverless",
        "adas",
        "driver assistance",
        "advanced driver assistance",
        "automated driving",
        "lidar",
        "robotaxi",
        "pilot system",
        "smart driving",
    ],

    "Software & AI": [
        "software",
        "automotive software",
        "operating system",
        "vehicle operating system",
        "infotainment",
        "connected car",
        "connectivity",
        "over-the-air",
        "ota update",
        "ota",
        "digital cockpit",
        "smart cockpit",
        "artificial intelligence",
        "machine learning",
        "large language model",
        "llm",
    ],

    "Partnerships & Investment": [
        "partnership",
        "partnerships",
        "partner",
        "partners",
        "joint venture",
        "collaboration",
        "collaborate",
        "strategic alliance",
        "investment",
        "invest",
        "invests",
        "stake",
        "acquisition",
        "acquire",
        "acquires",
        "merger",
    ],

    "Supply Chain": [
        "supply chain",
        "supplier",
        "suppliers",
        "raw materials",
        "semiconductor",
        "semiconductors",
        "chip shortage",
        "chips",
        "components",
        "procurement",
        "logistics",
        "sourcing",
        "rare earth",
        "critical minerals",
    ],

    "Trade, Tariffs & Regulation": [
        "tariff",
        "tariffs",
        "trade duty",
        "import duty",
        "duties",
        "regulation",
        "regulations",
        "regulatory",
        "policy",
        "government",
        "subsidy",
        "subsidies",
        "eu investigation",
        "anti-subsidy",
        "trade investigation",
        "compliance",
        "regulator",
        "approval",
    ],

    "Safety & Recalls": [
        "recall",
        "recalls",
        "safety",
        "safety issue",
        "defect",
        "defective",
        "crash",
        "crash test",
        "collision",
        "fire risk",
        "battery fire",
        "airbag",
        "brake issue",
        "investigation",
    ],

    "Pricing & Competition": [
        "price",
        "pricing",
        "price cut",
        "price cuts",
        "discount",
        "discounts",
        "affordable",
        "price war",
        "competition",
        "competitive",
        "competitor",
        "competitors",
        "rival",
        "rivals",
        "undercut",
    ],

    "Dealer & Retail Network": [
        "dealer",
        "dealers",
        "dealership",
        "dealer network",
        "retail network",
        "showroom",
        "showrooms",
        "sales network",
        "distribution network",
        "retail expansion",
    ],

    "Technology & Innovation": [
        "technology",
        "innovation",
        "innovative",
        "breakthrough",
        "research",
        "development",
        "engineering",
        "platform",
        "vehicle platform",
        "architecture",
        "800-volt",
        "800v",
        "thermal management",
        "electric drivetrain",
        "drivetrain",
        "motor technology",
        "efficiency",
    ],

    "Reviews & Comparisons": [
        "review",
        "reviewed",
        "road test",
        "test drive",
        "comparison",
        "compare",
        "compared",
        "versus",
        " vs ",
        "range test",
        "performance test",
        "first drive",
        "driving impressions",
    ],

    "Market & Strategy": [
        "market trend",
        "market trends",
        "industry trend",
        "industry trends",
        "strategy",
        "strategic",
        "growth strategy",
        "market outlook",
        "industry outlook",
        "ev market",
        "electric vehicle market",
        "automotive market",
        "market forecast",
        "consumer demand",
        "demand growth",
    ],
}


# ============================================================
# Text processing
# ============================================================

def normalize_text(text):
    """
    Convert text to lowercase and normalize whitespace.
    """
    if pd.isna(text):
        return ""

    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def keyword_matches(text, keyword):
    """
    Count the number of times a keyword appears in the text.

    Single-word keywords use word boundaries to reduce
    accidental partial matches.
    """
    keyword = keyword.lower().strip()

    if not keyword:
        return 0

    # Multi-word phrases
    if " " in keyword or "-" in keyword:
        return text.count(keyword)

    # Single words
    pattern = rf"\b{re.escape(keyword)}\b"

    return len(
        re.findall(
            pattern,
            text
        )
    )


# ============================================================
# Classification logic
# ============================================================

def score_labels(text, keyword_dict):
    """
    Count keyword matches for every label. Counts are not probabilities or
    confidence scores; overlapping keywords and repeated text can add matches.
    """
    normalized_text = normalize_text(text)

    scores = {}

    for label, keywords in keyword_dict.items():

        score = sum(
            keyword_matches(
                normalized_text,
                keyword
            )
            for keyword in keywords
        )

        if score > 0:
            scores[label] = score

    return scores


def get_primary_label(text, keyword_dict):
    """
    Return the label with the highest keyword score.

    Ties use the declared dictionary order (first wins), never randomness.
    If no label has evidence, return 'Other', a review fallback, not a brand/topic.
    """
    scores = score_labels(
        text,
        keyword_dict
    )

    if not scores:
        return "Other"

    return max(
        scores,
        key=scores.get
    )


def find_labels(text, keyword_dict):
    """
    Return every detected label, ordered from the strongest
    keyword match to the weakest.
    """
    scores = score_labels(
        text,
        keyword_dict
    )

    if not scores:
        return []

    sorted_scores = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return [
        label
        for label, _ in sorted_scores
    ]


def join_labels(labels):
    """JSON arrays preserve labels containing commas; [] means no match."""
    return json.dumps(labels, ensure_ascii=False)


def classify_dataframe(df):
    missing = {"title", "summary"} - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    df = df.copy()
    text = df["title"].fillna("").astype(str) + " " + df["summary"].fillna("").astype(str)
    for kind, taxonomy in (("brand", BRAND_KEYWORDS), ("topic", TOPIC_KEYWORDS)):
        df[f"primary_{kind}"] = text.apply(lambda value: get_primary_label(value, taxonomy))
        df[kind] = text.apply(lambda value: join_labels(find_labels(value, taxonomy)))
    return df


def classify_articles(input_path=INPUT_PATH, output_path=OUTPUT_PATH):
    df = classify_dataframe(pd.read_csv(input_path, encoding="utf-8"))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8", lineterminator="\n")
    print(f"Classified {len(df)} records -> {output_path}")
    return df


if __name__ == "__main__":
    result = classify_articles()
    print(result["primary_brand"].value_counts().to_string())
    print(result["primary_topic"].value_counts().to_string())
