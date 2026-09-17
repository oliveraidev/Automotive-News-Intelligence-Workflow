"""Small offline regression suite. No RSS network calls are made."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests

from src.processing.clean_articles import clean_text, clean_dataframe, process_articles
from src.analysis.classify_articles import (score_labels, get_primary_label, find_labels,
    join_labels, classify_dataframe, TOPIC_KEYWORDS)
from src.analysis.sentiment_analysis import get_sentiment_score, get_sentiment_label, annotate_dataframe
from src.analysis.executive_summary import generate_summary, sort_latest
from src.collectors.news_collector import fetch_feed, collect_news, save_collection, ROOT


class PipelineTests(unittest.TestCase):
    def raw(self):
        return pd.DataFrame([dict(source='BYD News', title='BYD’s new EV – 吉利',
            summary='<a>Battery &amp; charging</a>&nbsp;&nbsp;<font>Publisher</font>',
            link='https://example.org/a', published='Mon, 29 Jun 2026 13:00:00 GMT',
            collected_at='2026-06-29 18:16:22')])

    def test_utf8_file_and_entities(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            raw, output = Path(directory)/'raw.csv', Path(directory)/'clean.csv'
            self.raw().to_csv(raw, index=False, encoding='utf-8')
            result = process_articles(raw, output)
            self.assertEqual(result.iloc[0].title, 'BYD’s new EV – 吉利')
            self.assertEqual(result.iloc[0]['summary'], 'Battery & charging Publisher')
            self.assertNotIn('&nbsp;', output.read_text())
            self.assertEqual(classify_dataframe(result).iloc[0].primary_brand, 'BYD')

    def test_url_duplicates_and_missing_text(self):
        raw = pd.concat([self.raw(), self.raw()], ignore_index=True)
        raw.loc[0, 'summary'] = None
        result, report = clean_dataframe(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(report['duplicate_urls_removed'], 1)
        self.assertEqual(result.iloc[0]['summary'], '')
        self.assertEqual(clean_text(pd.NA), '')
        empty_text = pd.DataFrame({'title': [None], 'summary': [None]})
        classified = classify_dataframe(empty_text)
        self.assertEqual(classified.iloc[0].primary_brand, 'Other')
        self.assertEqual(json.loads(classified.iloc[0].brand), [])
        self.assertEqual(annotate_dataframe(classified).iloc[0].sentiment_score, 0)

    def test_schema_and_strict_utf8(self):
        with self.assertRaisesRegex(ValueError, 'Missing required columns'):
            clean_dataframe(pd.DataFrame({'title': ['test']}))
        with self.assertRaises(ValueError):
            classify_dataframe(pd.DataFrame({'title': ['test']}))
        with self.assertRaises(ValueError):
            annotate_dataframe(pd.DataFrame({'title': ['test']}))
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            bad = Path(directory)/'bad.csv'
            bad.write_bytes(b'title\n\xff\n')
            with self.assertRaises(UnicodeDecodeError):
                process_articles(bad, Path(directory)/'out.csv')

    def test_deterministic_ties_and_count_not_probability(self):
        taxonomy = {'First': ['byd'], 'Second': ['nio']}
        text = 'NIO BYD BYD NIO'
        self.assertEqual(score_labels(text, taxonomy), {'First': 2, 'Second': 2})
        self.assertEqual(get_primary_label(text, taxonomy), 'First')
        self.assertEqual(find_labels(text, taxonomy), ['First', 'Second'])
        self.assertEqual(get_primary_label('byd byd byd', taxonomy), 'First')
        self.assertEqual(score_labels('byd byd byd', taxonomy)['First'], 3)
        self.assertEqual(get_primary_label('unmatched', taxonomy), 'Other')

    def test_multilabel_serialization(self):
        labels = find_labels('tariffs and battery technology', TOPIC_KEYWORDS)
        encoded = join_labels(labels)
        self.assertIn('Trade, Tariffs & Regulation', json.loads(encoded))
        self.assertEqual(json.loads(encoded), labels)
        self.assertEqual(json.loads(join_labels([])), [])

    def test_sentiment_boundaries_and_missing(self):
        for value in (None, float('nan'), pd.NA, '', ' '):
            self.assertEqual(get_sentiment_score(value), 0)
        for score, expected in [(-.1001,'Negative'),(-.1,'Neutral'),(0,'Neutral'),(.1,'Neutral'),(.1001,'Positive')]:
            self.assertEqual(get_sentiment_label(score), expected)

    def test_newest_and_brief_ties(self):
        df = pd.DataFrame({'title':['old','new','undated'],
            'published':['2026-06-29T14:25:00Z','2026-06-29T18:01:00+02:00','bad'],
            'primary_brand':['BYD','NIO','Other'],
            'primary_topic':['Product Launch','Product Launch','Other']})
        self.assertEqual(sort_latest(df).iloc[0].title, 'new')
        brief = generate_summary(df)
        self.assertIn('(tie)', brief)
        self.assertIn('2026-06-29 16:01 UTC', brief)
        self.assertIn('BYD, NIO', brief)
        self.assertIn('No records', generate_summary(df.iloc[:0]))
        df['published'] = 'invalid'
        self.assertIn('No valid publication dates', generate_summary(df))

    def test_collector_tls_and_metadata(self):
        with patch('src.collectors.news_collector.requests.get') as get:
            get.return_value.content = b'<rss version="2.0"><channel><item><title>BYD</title></item></channel></rss>'
            feed = fetch_feed('https://example.org/rss')
            self.assertNotIn('verify', get.call_args.kwargs)
            self.assertEqual(len(feed.entries), 1)
        from types import SimpleNamespace
        feed = SimpleNamespace(entries=[{'title':'BYD', 'source':{'title':'Publisher', 'href':'https://publisher.test'}}])
        with patch('src.collectors.news_collector.fetch_feed', return_value=feed):
            result = collect_news()
            self.assertEqual(len(result), 7)
            self.assertEqual(result.iloc[0].publisher, 'Publisher')
            self.assertTrue(result.iloc[0].collected_at.endswith('+00:00'))
            self.assertNotEqual(result.iloc[0].source, result.iloc[0].publisher)

    def test_collector_failure_never_overwrites(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory)/'live.csv'
            output.write_text('keep me')
            from types import SimpleNamespace
            feed = SimpleNamespace(entries=[{'title': 'BYD', 'link': 'https://example.org/a'}])
            results = [feed, requests.ConnectionError('fixture failure'), feed, feed, feed, feed, feed]
            with patch('src.collectors.news_collector.fetch_feed', side_effect=results):
                with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                    save_collection(output, overwrite=True)
            self.assertEqual(output.read_text(), 'keep me')
        with self.assertRaisesRegex(ValueError, 'protected'):
            save_collection(ROOT/'data/raw/automotive_news.csv', overwrite=True)


if __name__ == '__main__':
    unittest.main()
