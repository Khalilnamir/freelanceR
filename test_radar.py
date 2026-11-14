import io
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from radar import init_db, insert_signal, fetch_all, update_signal, score_signal, outreach_draft, parse_feed, export_csv, export_snapshot, import_snapshot

SAMPLE_RSS = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item><title>La banque ABC lance une nouvelle plateforme data Snowflake</title>
<link>https://example.org/article/abc</link>
<description>Projet de migration dbt et Snowflake</description><pubDate>Sat, 14 Nov 2026 08:00:00 GMT</pubDate>
<source>Media Exemple</source></item></channel></rss>'''

class RadarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'test.sqlite3'
        init_db(self.db)
    def tearDown(self):
        self.temp.cleanup()
    def test_rss_and_dedupe(self):
        item = parse_feed(SAMPLE_RSS)[0]
        self.assertEqual(item['publisher'], 'Media Exemple')
        self.assertEqual(item['published'], '2026-11-14')
        self.assertTrue(insert_signal(item, self.db))
        self.assertFalse(insert_signal(item, self.db))
        self.assertEqual(len(fetch_all(self.db)), 1)
    def test_score_explainable(self):
        score, pos, typ, detail = score_signal('Nouvelle plateforme Data Snowflake et dbt pour la banque')
        self.assertGreaterEqual(score, 60)
        self.assertEqual(pos, 'Data Platform')
        self.assertIn('snowflake', detail)
    def test_backup_and_restore(self):
        item = parse_feed(SAMPLE_RSS)[0]
        insert_signal(item, self.db)
        original = fetch_all(self.db)[0]
        update_signal(original['id'], {'company': 'ABC', 'do_not_contact': 1}, self.db)
        snapshot = export_snapshot(self.db)
        another_db = Path(self.temp.name) / 'restored.sqlite3'
        result = import_snapshot(snapshot, another_db)
        self.assertEqual(result['added'], 1)
        restored = fetch_all(another_db)[0]
        self.assertEqual(restored['company'], 'ABC')
        self.assertEqual(restored['do_not_contact'], 1)
        self.assertEqual(import_snapshot(snapshot, another_db)['skipped'], 1)

    def test_contact_save_and_draft(self):
        item = parse_feed(SAMPLE_RSS)[0]
        insert_signal(item, self.db)
        x = fetch_all(self.db)[0]
        update_signal(x['id'], {'company':'ABC','contact_name':'Alex Martin',
                                 'do_not_contact':1, 'status':'À contacter'}, self.db)
        x = fetch_all(self.db)[0]
        self.assertEqual(x['company'], 'ABC')
        self.assertEqual(x['do_not_contact'], 1)
        subj, body = outreach_draft(x)
        self.assertIn('ABC', subj)
        self.assertIn('Alex Martin', body)
        self.assertIn('stop', body.lower())
        self.assertIn('company', export_csv([x]))

if __name__ == '__main__':
    unittest.main()
