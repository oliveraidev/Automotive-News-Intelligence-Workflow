"""Integration checks against the real offline artifacts and Streamlit app."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from src.dashboard.app import ROOT, DATA_PATH, load_data, filter_records, calculate_metrics


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_data()
        cls.app_path = ROOT / 'src/dashboard/app.py'

    def select(self, **kwargs):
        return filter_records(self.df,
            kwargs.get('brands', self.df.primary_brand.unique()),
            kwargs.get('topics', self.df.primary_topic.unique()),
            kwargs.get('sentiments', self.df.sentiment.unique()),
            kwargs.get('query', ''))

    def test_snapshot_and_other_exclusion(self):
        metrics = calculate_metrics(self.df)
        self.assertEqual((metrics['records'], metrics['brands'], metrics['topics']), (679, 8, 18))
        other = self.select(brands=['Other'])
        self.assertEqual(calculate_metrics(other)['brands'], 0)
        self.assertEqual(calculate_metrics(self.select(topics=['Other']))['topics'], 0)
        self.assertAlmostEqual(metrics['positive_share'], 188/679*100)

    def test_filters_and_empty(self):
        self.assertEqual(len(self.select(brands=['BYD'])), 99)
        combined = self.select(brands=['BYD'], topics=['Product Launch'], sentiments=['Positive'])
        self.assertGreater(len(combined), 0)
        self.assertTrue(combined.primary_brand.eq('BYD').all())
        self.assertTrue(combined.primary_topic.eq('Product Launch').all())
        self.assertTrue(combined.sentiment.eq('Positive').all())
        metrics = calculate_metrics(self.select(brands=[]))
        self.assertEqual(metrics['records'], 0)
        self.assertIsNone(metrics['positive_share'])
        self.assertIsNone(metrics['average_polarity'])

    def test_literal_search(self):
        for query in ['[', '(', '.', '+', '*', 'BYD', 'zzzznomatch']:
            with self.subTest(query=query):
                expected = self.df.loc[(self.df.title+' '+self.df.summary).str.lower().map(lambda text: query.lower() in text)]
                self.assertEqual(self.select(query=query).index.tolist(), expected.index.tolist())

    def test_paths_and_missing_artifact(self):
        previous = Path.cwd()
        try:
            with tempfile.TemporaryDirectory(dir=ROOT) as directory:
                os.chdir(directory)
                self.assertEqual(len(load_data()), 679)
                app = AppTest.from_file(str(self.app_path)).run()
                self.assertEqual(len(app.exception), 0)
        finally:
            os.chdir(previous)
        with self.assertRaises(FileNotFoundError):
            load_data(ROOT/'data/processed/does-not-exist.csv')
        from src.dashboard import app as module
        with patch.object(module, 'DATA_PATH', ROOT/'data/processed/does-not-exist.csv'):
            # main catches loader errors; patch function to simulate a missing file.
            with patch.object(module, 'load_data', side_effect=FileNotFoundError('fixture')):
                app = AppTest.from_string('from src.dashboard.app import main\nmain()').run()
                self.assertEqual(len(app.exception), 0)
                self.assertIn('could not be loaded', app.error[0].value)

    def test_streamlit_widgets(self):
        app = AppTest.from_file(str(self.app_path)).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([metric.value for metric in app.metric][:3], ['679','8','18'])
        for query in ['[', '(', '.', '+', '*']:
            app.sidebar.text_input[0].set_value(query).run()
            self.assertEqual(len(app.exception), 0, query)
            self.assertEqual(int(app.metric[0].value), len(self.select(query=query)))
        app.sidebar.text_input[0].set_value('')
        app.sidebar.multiselect[0].set_value(['BYD']).run()
        self.assertEqual(app.metric[0].value, '99')
        app.sidebar.multiselect[0].set_value(['Other']).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[1].value, '0')
        app.sidebar.multiselect[0].set_value([]).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([metric.value for metric in app.metric][-2:], ['N/A','N/A'])


if __name__ == '__main__':
    unittest.main()
