import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from tracker_review import read_tracker, review, timestamp, literal_profile

NOW = timestamp('2026-11-18T15:00:00Z')
URL = 'https://www.linkedin.com/in/synthetic-example'


def record(status='Not contacted', **extra):
    return {'row': 2, 'profile_url': URL, 'values':
            dict({'Name': 'Synthetic Example', 'LinkedIn': URL, 'Status': status, 'Notes': 'Keep'}, **extra)}


class ReviewTests(unittest.TestCase):
    def test_unchanged_is_quiet_and_inputs_untouched(self):
        old = [record()]; new = copy.deepcopy(old); before = copy.deepcopy(new)
        self.assertEqual(review(new, old, NOW)['review_items'], [])
        self.assertEqual(new, before)

    def test_changed_preserves_manual_status_and_note(self):
        old = [record()]; new = [record('Connected', Notes='Owner edit')]
        result = review(new, old, NOW)['review_items'][0]
        self.assertEqual(result['status'], 'Connected')
        self.assertEqual(result['changes']['Notes']['after'], 'Owner edit')
        self.assertIsNone(result['due_at'])

    def test_canonical_link_changes_do_not_create_false_delta(self):
        old = record(); old['values']['LinkedIn'] = 'https://linkedin.com/in/synthetic-example/?trk=x'
        self.assertEqual(review([record()], [old], NOW)['review_items'], [])

    def test_native_excel_links_and_no_input_write(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'tracker.xlsx'; w = Workbook(); w.active.title='Recruiters'
            w.active.append(['Name', 'LinkedIn', 'Status', 'Notes'])
            w.active.append(['Synthetic Example', 'Open profile', 'Connected', 'User edit'])
            w.active['B2'].hyperlink = URL
            w.save(path); before = path.read_bytes()
            rows = read_tracker(path)
            self.assertEqual(rows[0]['profile_url'], URL)
            self.assertEqual(rows[0]['values']['Notes'], 'User edit')
            self.assertEqual(path.read_bytes(), before)

    def test_no_inferred_send_date(self):
        row = record('Invitation pending')
        result = review([row], [row], NOW)['review_items'][0]
        self.assertIn('pending_without_confirmed_send_time', result['reasons'])
        self.assertIsNone(result['due_at'])

    def test_exact_72_hours_and_checked_suppression(self):
        row = record('Invitation pending', **{'Confirmed sent at': '2026-11-15T09:00:00-06:00'})
        item = review([row], [row], NOW)['review_items'][0]
        self.assertEqual(item['due_at'], '2026-11-18T15:00:00+00:00')
        row['values']['Last checked at'] = '2026-11-18T15:00:00Z'
        self.assertEqual(review([row], [row], NOW)['review_items'], [])

    def test_not_due_and_connected_never_due(self):
        row = record('Invitation pending', **{'Confirmed sent at': '2026-11-15T15:00:01Z'})
        self.assertEqual(review([row], [row], NOW)['review_items'], [])
        row['values']['Status'] = 'Connected'; row['values']['Confirmed sent at'] = '2026-11-01T00:00:00Z'
        self.assertEqual(review([row], [row], NOW)['review_items'], [])

    def test_invalid_future_and_naive_dates_fail_closed(self):
        for sent in ['yesterday', '2026-11-15T15:00:00', '2027-01-01T00:00:00Z']:
            row = record('Invitation pending', **{'Confirmed sent at': sent})
            item = review([row], [row], NOW)['review_items'][0]
            self.assertIn('invalid_or_inconsistent_timestamp', item['reasons'])
            self.assertIsNone(item['due_at'])

    def test_duplicates_and_missing_ids_not_due(self):
        row = record('Invitation pending', **{'Confirmed sent at': '2026-11-01T00:00:00Z'})
        for old, new in [([row], [row, row]), ([row, row], [row])]:
            for item in review(new, old, NOW)['review_items']:
                self.assertIn('duplicate_profile_review_required', item['reasons'])
                self.assertIsNone(item['due_at'])
        row['profile_url'] = None
        self.assertIsNone(review([row], [], NOW)['review_items'][0]['due_at'])

    def test_new_and_removed_are_not_outreach(self):
        self.assertEqual(review([record()], [], NOW)['review_items'][0]['reasons'], ['new_record'])
        self.assertEqual(review([], [record()], NOW)['review_items'][0]['reasons'], ['removed_record_review_only'])

    def test_csv_cli_and_existing_output_protection(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'tracker.csv'; output = Path(d)/'review.json'
            with source.open('w', newline='') as f:
                writer=csv.writer(f); writer.writerow(['Name','LinkedIn','Status']); writer.writerow(['Example',URL,'Connected'])
            cmd=[sys.executable,str(Path(__file__).parents[1]/'scripts/tracker_review.py'),
                 '--current',str(source),'--previous',str(source),'--now',NOW.isoformat(),'--output',str(output)]
            first=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertEqual(json.loads(output.read_text())['review_items'],[])
            before=output.read_bytes()
            self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertEqual(output.read_bytes(),before)
            output.unlink()
            i=cmd.index('--previous'); del cmd[i:i+2]
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            self.assertFalse(json.loads(output.read_text())['baseline_present'])
            self.assertEqual(json.loads(output.read_text())['review_items'],[])

    def test_literal_hyperlink_formula_without_evaluation(self):
        self.assertEqual(literal_profile(f'=HYPERLINK("{URL}","Open profile")'), URL)
        for value in ['=HYPERLINK(A1,"Open profile")', '=HYPERLINK("https://evil.test/in/x","Open")', '=HYPERLINK("https://linkedin.com/in/a"&A1,"Open")', '=WEBSERVICE("https://evil.test")']:
            self.assertIsNone(literal_profile(value))
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'tracker.xlsx'; w=Workbook(); w.active.title='Recruiters'
            w.active.append(['Name','LinkedIn','Status'])
            w.active.append(['Example', f'=HYPERLINK("{URL}","Open profile")', 'Connected'])
            w.save(path)
            self.assertEqual(read_tracker(path)[0]['profile_url'], URL)

    def test_bad_headers_and_formula_link_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.csv'; p.write_text('Name,LinkedIn,Status,Status\nx,x,x,x\n')
            with self.assertRaises(ValueError): read_tracker(p)
            p.write_text('Name,LinkedIn,Status\nx,=HYPERLINK(),Connected\n')
            self.assertIsNone(read_tracker(p)[0]['profile_url'])
