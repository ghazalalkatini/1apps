import io
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_excel import generate_excel, tag


def cells(workbook, sheet):
    with ZipFile(io.BytesIO(workbook)) as archive:
        xml = ET.fromstring(archive.read(f'xl/worksheets/sheet{sheet}.xml'))
    return {cell.get('r'): cell for cell in xml.iter(tag('c'))}


class ExcelExportTests(unittest.TestCase):
    def setUp(self):
        self.project = json.loads((ROOT / 'tests' / 'demo_records.json').read_text(encoding='utf-8'))

    def test_populates_both_views_and_flags_unknown_cost(self):
        workbook = generate_excel(self.project)
        for sheet, col in ((1, 'P'), (2, 'F')):
            data = cells(workbook, sheet)
            self.assertEqual(data[col + '2'].findtext(tag('v')), '1250')
            self.assertEqual(data[col + '3'].findtext(tag('v')), '360')
            self.assertNotIn(col + '4', data)
        brief = cells(workbook, 4)
        self.assertEqual(brief['B9'].findtext(tag('v')), '1610')
        self.assertIn('Partial', ''.join(brief['B10'].itertext()))
        self.assertIn('coverage_per_box', ''.join(text for cell in cells(workbook, 3).values() for text in cell.itertext()))

    def test_conflicting_and_foreign_prices_do_not_enter_project_subtotal(self):
        self.project['products'][0]['attributes']['unit_price']['evidence'] = 'CONFLICT'
        self.project['products'][1]['currency'] = 'USD'
        self.project['products'][2]['attributes']['unit_price'].update(
            value=0, evidence='CLIENT-PROVIDED', source_ids=['card-3'])
        workbook = generate_excel(self.project)
        schedule = cells(workbook, 1)
        self.assertNotIn('P2', schedule)
        self.assertEqual(schedule['P3'].findtext(tag('v')), '360')
        self.assertEqual(schedule['P4'].findtext(tag('v')), '0')
        self.assertEqual(cells(workbook, 4)['B9'].findtext(tag('v')), '0')

    def test_approval_and_literal_text(self):
        with self.assertRaisesRegex(ValueError, 'project approval'):
            generate_excel(self.project, final=True)
        self.project['approval_state'] = 'Approved'
        self.project['audience'] = 'B2C'
        self.project['products'][0]['product_name'] = '=1+1'
        workbook = generate_excel(self.project, final=True)
        name = cells(workbook, 2)['B2']
        self.assertEqual(name.get('t'), 'inlineStr')
        self.assertEqual(''.join(name.itertext()), '=1+1')
        self.assertIn('Final', ''.join(cells(workbook, 4)['B6'].itertext()))


if __name__ == '__main__':
    unittest.main()
