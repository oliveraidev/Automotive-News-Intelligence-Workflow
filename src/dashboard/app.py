"""Searchable analyst interface for the bundled automotive news snapshot."""
from pathlib import Path
import json
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
# Supports both `streamlit run` and direct module imports from any working directory.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.analysis.executive_summary import generate_summary, publication_dates, sort_latest

DATA_PATH = ROOT / "data/processed/enriched_automotive_news.csv"
REQUIRED_COLUMNS = {"source", "title", "summary", "link", "published", "collected_at",
                    "primary_brand", "primary_topic", "brand", "topic", "sentiment", "sentiment_score"}
POLARITY_ORDER = ["Negative", "Neutral", "Positive"]
POLARITY_COLORS = {"Negative": "#b45349", "Neutral": "#8796a5", "Positive": "#23877c"}


def load_data(path=DATA_PATH):
    df = pd.read_csv(path, encoding="utf-8")
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    for field in ("title", "summary", "source", "link"):
        df[field] = df[field].fillna("").astype(str)
    for field in ("primary_brand", "primary_topic", "sentiment"):
        if df[field].isna().any():
            raise ValueError(f"Missing {field} annotations; rerun the offline pipeline")
    df["sentiment_score"] = pd.to_numeric(df["sentiment_score"], errors="raise")
    if df["sentiment_score"].isna().any() or not df["sentiment_score"].between(-1, 1).all():
        raise ValueError("Text polarity must be present and between -1 and 1")
    if not df["sentiment"].isin(POLARITY_ORDER).all():
        raise ValueError("Unexpected text-polarity label")
    for field in ("brand", "topic"):
        for value in df[field]:
            labels = json.loads(value)
            if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
                raise ValueError(f"{field} must contain JSON arrays of labels")
    return df


def filter_records(df, brands, topics, sentiments, query=""):
    selected = df.loc[df["primary_brand"].isin(brands)
                      & df["primary_topic"].isin(topics)
                      & df["sentiment"].isin(sentiments)]
    if query:
        matches = (selected["title"].str.contains(query, case=False, regex=False, na=False)
                   | selected["summary"].str.contains(query, case=False, regex=False, na=False))
        selected = selected.loc[matches]
    return selected


def calculate_metrics(df):
    return {
        "records": len(df),
        "brands": df.loc[df["primary_brand"].ne("Other"), "primary_brand"].nunique(),
        "topics": df.loc[df["primary_topic"].ne("Other"), "primary_topic"].nunique(),
        "positive_share": float(df["sentiment"].eq("Positive").mean() * 100) if len(df) else None,
        "average_polarity": float(df["sentiment_score"].mean()) if len(df) else None,
    }


def assignment_chart(df, field, label):
    counts = (df.loc[df[field].ne("Other"), field].value_counts()
              .rename_axis(label).reset_index(name="Records"))
    fig = px.bar(counts, x="Records", y=label, orientation="h", text="Records",
                 color_discrete_sequence=["#287c8e"], height=max(330, len(counts) * 28))
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(rangemode="tozero", dtick=None)
    fig.update_layout(margin=dict(l=0, r=40, t=15, b=20))
    return fig


def main():
    st.set_page_config(page_title="Automotive News Intelligence Workflow", layout="wide")
    st.title("Automotive News Intelligence")
    st.caption("RSS metadata → cleaning → rule-based classification → lexicon-based text polarity → analyst review")
    try:
        df = load_data()
    except (OSError, ValueError, TypeError, pd.errors.ParserError) as error:
        st.error(f"The processed snapshot could not be loaded: {error}")
        st.info("From the repository root, run the cleaning, classification and sentiment scripts listed in the README.")
        st.stop()

    st.sidebar.header("Filter records")
    brands = sorted(df["primary_brand"].unique())
    topics = sorted(df["primary_topic"].unique())
    sentiments = [value for value in POLARITY_ORDER if value in df["sentiment"].unique()]
    selected_brands = st.sidebar.multiselect("Primary brand", brands, default=brands)
    selected_topics = st.sidebar.multiselect("Primary topic", topics, default=topics)
    selected_sentiments = st.sidebar.multiselect("Text polarity", sentiments, default=sentiments)
    search = st.sidebar.text_input("Search title / RSS snippet", help="Literal, case-insensitive text search. Symbols are safe.")
    st.sidebar.caption("Filters use primary assignments. Other is a review fallback. Additional detected labels remain available in the record table.")
    filtered = filter_records(df, selected_brands, selected_topics, selected_sentiments, search)
    dates = publication_dates(df)
    coverage = f"{dates.min():%d %b %Y}–{dates.max():%d %b %Y} (UTC)" if dates.notna().any() else "unavailable"
    collection_values = df["collected_at"].dropna().astype(str)
    collection_day = collection_values.str[:10].min() if len(collection_values) else "unknown"
    st.info(f"Static snapshot · {len(df):,} records · collected {collection_day} · publication coverage {coverage}. "
            "Google News search results are a selected sample, not representative media coverage.")
    if dates.isna().any():
        st.warning(f"{dates.isna().sum()} records have no valid publication date and appear last in the record list.")
    st.caption("Rule-based labels and lexicon-based polarity support first-pass triage. Analyst review of the original source remains necessary.")

    overview, classification, polarity, records = st.tabs(["Overview", "Classification", "Text polarity", "Records"])
    metrics = calculate_metrics(filtered)
    with overview:
        columns = st.columns(5)
        for column, label, value in zip(columns,
                ["Selected records", "Named primary brands", "Classified primary topics", "Positive text share", "Average text polarity"],
                [metrics["records"], metrics["brands"], metrics["topics"],
                 f"{metrics['positive_share']:.1f}%" if metrics["positive_share"] is not None else "N/A",
                 f"{metrics['average_polarity']:.3f}" if metrics["average_polarity"] is not None else "N/A"]):
            column.metric(label, value)
        st.caption("Brand/topic counts exclude Other. Polarity statistics describe the selected records, not consumers, investors or the market.")
        st.subheader("Analyst brief")
        with st.container(border=True):
            st.markdown(generate_summary(filtered))
        st.caption("Automatically filled statistical template; no article synthesis or recommendations.")
    if filtered.empty:
        st.info("No records match these filters. Clear the search or broaden the selection.")
        return
    with classification:
        st.subheader("Primary assignments in the selected records")
        st.caption("One primary label per record. Keyword-match counts are not confidence scores. Ties follow the declared taxonomy order.")
        brand_other = int(filtered["primary_brand"].eq("Other").sum())
        topic_other = int(filtered["primary_topic"].eq("Other").sum())
        st.info(f"Review fallback — {brand_other} records without a named primary brand; {topic_other} without a classified primary topic. These groups can overlap and are excluded from the charts below.")
        left, right = st.columns(2)
        with left:
            st.markdown("**Primary brand assignments**")
            st.plotly_chart(assignment_chart(filtered, "primary_brand", "Brand"), width="stretch")
        with right:
            st.markdown("**Primary business-topic assignments**")
            st.plotly_chart(assignment_chart(filtered, "primary_topic", "Topic"), width="stretch")
        st.caption("Primary counts are neither complete brand mentions nor market/media shares. Records with several detected labels are counted once in each primary-label view.")
    with polarity:
        st.subheader("Lexicon-based text polarity")
        st.caption("TextBlob PatternAnalyzer on title + RSS snippet. Positive > 0.1; negative < −0.1; neutral otherwise. No validated domain-level sentiment inference.")
        left, right = st.columns(2)
        with left:
            st.markdown("**Selected record counts**")
            counts = filtered["sentiment"].value_counts().rename_axis("Polarity").reset_index(name="Records")
            fig = px.bar(counts, x="Polarity", y="Records", color="Polarity", text="Records",
                         color_discrete_map=POLARITY_COLORS, category_orders={"Polarity": POLARITY_ORDER})
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width="stretch")
        with right:
            st.markdown("**Within-primary-brand composition**")
            named = filtered.loc[filtered["primary_brand"].ne("Other")]
            counts = named.groupby(["primary_brand", "sentiment"]).size().reset_index(name="Records")
            counts["Brand records"] = counts.groupby("primary_brand")["Records"].transform("sum")
            counts["Percent"] = counts["Records"] / counts["Brand records"] * 100
            totals = named["primary_brand"].value_counts()
            counts["Primary brand"] = counts["primary_brand"].map(lambda brand: f"{brand} (n={totals[brand]})")
            fig = px.bar(counts, x="Primary brand", y="Percent", color="sentiment", barmode="stack",
                         color_discrete_map=POLARITY_COLORS, category_orders={"sentiment": POLARITY_ORDER},
                         hover_data=["Records", "Brand records"], labels={"sentiment": "Polarity"})
            fig.update_yaxes(range=[0, 100], title="Within-brand records (%)")
            st.plotly_chart(fig, width="stretch")
        st.caption("Left: counts of all selected records. Right: percentages within each primary brand, with sample sizes; Other excluded. Unequal and selected samples do not support population comparisons.")
    with records:
        st.subheader("Latest selected headlines")
        ordered = sort_latest(filtered)
        st.caption("Sorted by publication time, newest first; no relevance or business-priority ranking. Feed names are not original publishers.")
        for _, row in ordered.head(5).iterrows():
            date = pd.to_datetime(row["published"], utc=True, errors="coerce")
            display_date = date.strftime("%d %b %Y %H:%M UTC") if pd.notna(date) else "Unknown date"
            st.markdown(f"**{row['title']}**")
            st.caption(f"{display_date} · {row['source']} · {row['primary_brand']} · {row['primary_topic']}")
            if row["link"].startswith(("https://", "http://")):
                st.markdown(f"[Open Google News record]({row['link']})")
        st.subheader("Record database")
        display = ordered[["published", "title", "source", "primary_brand", "primary_topic", "brand", "topic", "sentiment", "sentiment_score", "link"]].copy()
        for field in ("brand", "topic"):
            display[field] = display[field].map(lambda value: " · ".join(json.loads(value)) or "None detected")
        st.dataframe(display.rename(columns={"source": "RSS feed", "brand": "All detected brands", "topic": "All detected topics", "sentiment": "Text polarity", "sentiment_score": "Polarity score"}), hide_index=True, width="stretch", column_config={"link": st.column_config.LinkColumn("Google News link", display_text="Open record")})


if __name__ == "__main__":
    main()
