"""Data-derived analyst brief; deterministic template, not article summarization."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data/processed/enriched_automotive_news.csv"


def publication_dates(df):
    return pd.to_datetime(df["published"], errors="coerce", utc=True, format="mixed")


def sort_latest(df):
    # Stable order for identical dates; unknown dates go last.
    return (df.assign(_published_at=publication_dates(df))
            .sort_values("_published_at", ascending=False, kind="stable", na_position="last")
            .drop(columns="_published_at"))


def leading_assignments(series):
    counts = series.dropna().loc[lambda values: values.ne("Other")].value_counts()
    if counts.empty:
        return [], 0
    maximum = int(counts.max())
    return sorted(counts[counts.eq(maximum)].index.tolist()), maximum


def generate_summary(df):
    if df.empty:
        return "No records match the selected filters. Adjust the filters to continue analyst review."
    lines = [f"**{len(df):,} records** in the selected snapshot view."]
    for column, noun in (("primary_brand", "brand"), ("primary_topic", "business-topic")):
        leaders, count = leading_assignments(df[column])
        if leaders:
            tie = " (tie)" if len(leaders) > 1 else ""
            lines.append(f"- Highest primary {noun} assignment count{tie}: **{', '.join(leaders)}** — **{count}** per label.")
        else:
            lines.append(f"- No named {noun} has a primary assignment in this selection.")
    brand_other = int(df["primary_brand"].fillna("Other").eq("Other").sum())
    topic_other = int(df["primary_topic"].fillna("Other").eq("Other").sum())
    lines.append(f"- Review fallback (`Other`): **{brand_other}** primary brand and **{topic_other}** primary topic assignments. These groups can overlap.")
    dated = df.loc[publication_dates(df).notna()]
    if not dated.empty:
        newest = sort_latest(dated).iloc[0]
        date = publication_dates(dated).max().strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"- Latest dated record ({date}): {newest['title']}")
    else:
        lines.append("- No valid publication dates in this selection.")
    lines.append("Primary assignments are not complete mention counts or representative media coverage. Read the source before drawing conclusions.")
    return "\n\n".join(lines)


if __name__ == "__main__":
    print(generate_summary(pd.read_csv(INPUT_PATH, encoding="utf-8")))
