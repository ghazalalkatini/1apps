import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_records import validate

class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.demo = json.loads((ROOT / 'tests' / 'demo_records.json').read_text())
    def test_known_subtotal_and_partial_total(self):
        r = validate(self.demo)
        self.assertEqual(r['known_subtotal'], '1610')
        self.assertTrue(r['total_incomplete'])
        self.assertEqual(r['issues'], [])
    def test_missing_not_fabricated(self):
        a = self.demo['products'][1]['attributes']
        for field in ('wattage', 'certification', 'lead_time'):
            self.assertIsNone(a[field]['value'])
            self.assertEqual(a[field]['evidence'], 'MISSING')
    def test_reject_missing_with_value(self):
        d = copy.deepcopy(self.demo)
        d['products'][1]['attributes']['wattage']['value'] = 60
        self.assertTrue(any('MISSING must have null' in x for x in validate(d)['issues']))
    def test_reject_unapproved_signoff(self):
        d = copy.deepcopy(self.demo)
        d['products'][0]['approval_status'] = 'Approved'
        self.assertTrue(any('human signoff' in x for x in validate(d)['issues']))
    def test_reject_unknown_source(self):
        d = copy.deepcopy(self.demo)
        d['products'][0]['attributes']['width_cm']['source_ids'] = ['made-up']
        self.assertTrue(any('unknown source' in x for x in validate(d)['issues']))

if __name__ == '__main__':
    unittest.main()
