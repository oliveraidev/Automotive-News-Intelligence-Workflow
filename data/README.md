# Snapshot provenance and data dictionary

## Origin and scope

The bundled raw snapshot contains **700 Google News RSS metadata records**, collected by seven searches for BYD, Geely, Zeekr, NIO, XPeng, Li Auto and Xiaomi (100 results each). Query URLs are defined in `src/collectors/news_collector.py`. Tesla is classified when mentioned but has no dedicated feed.

Original `collected_at` values run from **2026-06-29 18:16:22 to 18:16:25**. Their timezone was not saved and has not been invented or retroactively converted. The collector now creates timezone-aware UTC timestamps for future, separate snapshots.

Stored publication coverage is **2025-07-29 07:00:00 UTC to 2026-06-29 16:01:00 UTC**. All 679 retained publication dates parse successfully. This broad range is a search-result snapshot, not a continuously sampled time series.

The raw file is preserved byte-for-byte, SHA-256:

```text
51635cbe5da97a3696e9192d7c7c7337446ad92da56506949dc850a8a5643379
```

## Processing and counts

| Stage | Records | Operation |
|---|---:|---|
| Raw | 700 | Original saved RSS metadata |
| Cleaned | 679 | UTF-8, tag/entity cleanup, 19 repeated URLs removed, 2 records excluded by broad keyword filter |
| Classified | 679 | Primary and all detected brand/topic labels |
| Enriched | 679 | Lexicon text polarity score and label |

No missing links were removed in this snapshot. All stored fields in the processed artifacts are non-null. There are **0 repeated URLs**, but **1 repeated title and 1 repeated snippet** remain under different Google News URLs. A title alone cannot prove two records are the same article. No full article body exists for body-level deduplication.

HTML is removed before entities are decoded; whitespace is normalized. Missing text is made empty. Strict UTF-8/CSV parsing and required-column checks fail visibly rather than silently dropping malformed input. URL deduplication keeps the first occurrence and therefore its first query attribution. The broad relevance filter still uses substring matching and can have false positives.

## Fields

| Field | Meaning and limitation |
|---|---|
| `source` | RSS query/feed label, e.g. BYD News; **not the original publisher** |
| `title` | Supplied RSS title; often includes a publisher name |
| `link` | Google News redirect URL for the record; not a resolved original article URL |
| `published` | Supplied RSS publication timestamp; parsed as UTC for display/sorting |
| `summary` | Raw RSS HTML; cleaned metadata/snippet after processing, not an article body or generated summary |
| `collected_at` | Original collection timestamp with unknown timezone |
| `primary_brand` | Highest keyword-count brand; dictionary-order ties; Other means no match |
| `brand` | JSON array of all detected brands; [] for no match |
| `primary_topic` | Highest keyword-count topic; dictionary-order ties; Other means no match |
| `topic` | JSON array of all detected topics; preserves commas inside topic names |
| `sentiment_score` | TextBlob PatternAnalyzer lexicon polarity in [-1, 1] on title + snippet |
| `sentiment` | Positive > 0.1, Negative < -0.1, Neutral otherwise |

For **future live outputs only**, the repaired collector also saves `feed_url`, `publisher` and `publisher_url` from explicit RSS metadata if present. `publisher_url` is the source website, not a resolved article URL. Missing publisher information stays empty. These fields were not backfilled into the historical snapshot by guessing from titles.

## Classification and annotation

The ordered dictionaries in `classify_articles.py` define 8 named brands and 18 business topics. Single words use word boundaries; phrases use substring counts. Overlapping keywords and text repeated in titles/snippets can inflate counts. Scores are match counts, never probabilities or confidence. Ties choose the first dictionary label deterministically.

The snapshot has **70 multi-brand** and **105 multi-topic** records. The highest match count is tied in **65 brand** and **82 topic** decisions. Primary counts are not all mentions: Tesla has 40 detected mentions and 7 primary assignments. Other is a review fallback, not an entity or topic. There is no annotated evaluation set or measured classification accuracy.

TextBlob annotation is lexicon-based NLP, not trained automotive sentiment inference. Positive / Neutral / Negative counts are **188 / 458 / 33**; positive share is **27.7%**, and mean polarity rounds to **0.065**. Wording polarity cannot establish consumer, investor or market sentiment.

## Primary brand distribution

| Primary label | Records |
|---|---:|
| NIO | 102 |
| BYD | 99 |
| Xiaomi Auto | 95 |
| XPeng | 91 |
| Li Auto | 81 |
| Geely | 76 |
| Zeekr | 74 |
| Other | 54 |
| Tesla | 7 |

## Primary topic distribution

| Primary label | Records |
|---|---:|
| Other | 253 |
| Sales & Deliveries | 114 |
| Product Launch | 100 |
| Pricing & Competition | 31 |
| Battery & Energy | 25 |
| International Expansion | 23 |
| Autonomous Driving & ADAS | 22 |
| Financial Performance | 22 |
| Charging Infrastructure | 20 |
| Manufacturing | 14 |
| Reviews & Comparisons | 13 |
| Technology & Innovation | 9 |
| Partnerships & Investment | 8 |
| Market & Strategy | 8 |
| Dealer & Retail Network | 5 |
| Trade, Tariffs & Regulation | 4 |
| Safety & Recalls | 4 |
| Software & AI | 2 |
| Supply Chain | 2 |

## Provenance, sampling and reuse limitations

- `source/feed` is not automatically `original publisher`. Publisher attribution visible inside text is not a structured or independently verified source field.
- All 679 links are Google News redirects. Original bodies, canonical article URLs and historical RSS responses are not archived. Two publisher-title checks during the audit do not verify all records.
- Feeds request English/US results, but language is not detected or guaranteed; non-English publisher names occur.
- Query selection, equal raw feed sizes, result ordering, deduplication, historical coverage and deterministic tie rules affect distributions. Counts are not representative media shares or market indicators.
- Snippets commonly repeat titles. No missing article content, publisher, timezone or sector insight has been invented.
- The most recent stored publication is “How China Got EVs That Charge in 5 Minutes, and Why the U.S. Likely Won’t - The Information” at 2026-06-29 16:01 UTC. This is a metadata observation, not a verification of the article's substantive claims.
- Only metadata and short RSS snippets are stored, not full article bodies. Source terms and reuse rights have not been established; inclusion here does not grant them. Follow the original publisher and applicable source conditions for further use.
