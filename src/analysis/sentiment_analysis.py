"""Lexicon-based TextBlob/Pattern text polarity, not market sentiment."""
from pathlib import Path
import pandas as pd
from textblob import TextBlob
from textblob.sentiments import PatternAnalyzer

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data/processed/classified_automotive_news.csv"
OUTPUT_PATH = ROOT / "data/processed/enriched_automotive_news.csv"


def get_sentiment_score(text):
    if pd.isna(text) or not str(text).strip():
        return 0.0
    return TextBlob(str(text), analyzer=PatternAnalyzer()).sentiment.polarity


def get_sentiment_label(score):
    if score > 0.1:
        return "Positive"
    if score < -0.1:
        return "Negative"
    return "Neutral"


def annotate_dataframe(df):
    missing = {"title", "summary", "primary_brand", "primary_topic"} - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    df = df.copy()
    text = df["title"].fillna("").astype(str) + " " + df["summary"].fillna("").astype(str)
    df["sentiment_score"] = text.apply(get_sentiment_score)
    df["sentiment"] = df["sentiment_score"].apply(get_sentiment_label)
    return df


def analyse_sentiment(input_path=INPUT_PATH, output_path=OUTPUT_PATH):
    df = annotate_dataframe(pd.read_csv(input_path, encoding="utf-8"))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8", lineterminator="\n")
    print(f"Annotated {len(df)} records -> {output_path}")
    print(df["sentiment"].value_counts().to_string())
    return df


if __name__ == "__main__":
    analyse_sentiment()
