"""Clean RSS metadata without fetching or reconstructing article content."""
from html import unescape
from pathlib import Path
import re

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data/raw/automotive_news.csv"
OUTPUT_PATH = ROOT / "data/processed/cleaned_automotive_news.csv"
REQUIRED_COLUMNS = {"source", "title", "summary", "link", "published", "collected_at"}
EV_KEYWORDS = [
    "ev", "electric", "battery", "charging", "vehicle", "automotive", "car",
    "cars", "byd", "geely", "zeekr", "nio", "xpeng", "li auto", "xiaomi", "tesla"
]


def clean_text(text):
    if pd.isna(text):
        return ""
    # Strip actual HTML first; preserve encoded literal characters in headlines.
    text = re.sub(r"<[^>]*>", " ", str(text))
    return re.sub(r"\s+", " ", unescape(text)).strip()


def is_relevant_article(row):
    # Retained broad substring heuristic; not a relevance model.
    text = f"{row['title']} {row['summary']}".lower()
    return any(keyword in text for keyword in EV_KEYWORDS)


def clean_dataframe(df):
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    df = df.copy()
    raw_count = len(df)
    for column in ("title", "summary"):
        df[column] = df[column].apply(clean_text)
    valid_link = df["link"].fillna("").astype(str).str.strip().ne("")
    missing_links = int((~valid_link).sum())
    df = df.loc[valid_link].copy()
    df["link"] = df["link"].astype(str).str.strip()
    duplicates = int(df["link"].duplicated().sum())
    df = df.drop_duplicates(subset=["link"], keep="first")
    relevant = df.apply(is_relevant_article, axis=1).astype(bool)
    excluded = int((~relevant).sum())
    df = df.loc[relevant].reset_index(drop=True)
    report = {"input": raw_count, "missing_links_removed": missing_links,
              "duplicate_urls_removed": duplicates, "irrelevant_removed": excluded,
              "output": len(df)}
    return df, report


def process_articles(input_path=INPUT_PATH, output_path=OUTPUT_PATH):
    # Strict decoding and parsing: malformed CSV must fail visibly.
    df, report = clean_dataframe(pd.read_csv(input_path, encoding="utf-8"))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8", lineterminator="\n")
    print(f"Cleaning: {report}")
    return df


if __name__ == "__main__":
    process_articles()
