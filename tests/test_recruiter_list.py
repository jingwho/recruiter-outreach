import importlib.util
from pathlib import Path
import unittest
import csv
import tempfile
import subprocess
import json
import sys

spec = importlib.util.spec_from_file_location('recruiter_list', Path(__file__).parents[1] / 'scripts/recruiter_list.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def record(**changes):
    row = {'name': 'Alex Example', 'company': 'Example Co', 'profile_url': 'https://www.linkedin.com/in/alex-example', 'category': 'company_contact', 'outreach': 'none', 'do_not_contact': False, 'evidence': [{'claim': 'Current recruiter', 'url': 'https://example.com/team', 'checked_at': '2026-01-01', 'basis': 'indexed'}]}
    row.update(changes)
    return row


class Tests(unittest.TestCase):
    def test_conflicting_location_check_requires_reverification(self):
        first = record(linkedin_location_check={'country_code': 'US'})
        second = record(linkedin_location_check={'country_code': 'GB'})
        result = m.dedupe([first, second])[0]
        self.assertEqual(result['category'], 'needs_checking')
        self.assertIn('linkedin_location_check', result['conflicts'])
        self.assertEqual(len(result['source_records']), 2)

    def test_linkedin_canonicalization(self):
        self.assertEqual(m.canonical_url('https://uk.linkedin.com/in/alex-example/?trk=x'), 'https://www.linkedin.com/in/alex-example')

    def test_nonlinkedin_query_identity_preserved(self):
        self.assertNotEqual(m.canonical_url('https://example.com/person?id=1'), m.canonical_url('https://example.com/person?id=2'))

    def test_same_name_not_identity(self):
        self.assertEqual(len(m.dedupe([record(profile_url=''), record(profile_url='')])), 2)

    def test_conflicting_employer_preserved(self):
        result = m.dedupe([record(), record(company='New Employer')])[0]
        self.assertEqual(result['category'], 'needs_checking')
        self.assertEqual(len(result['source_records']), 2)
        self.assertIn('company', result['conflicts'])

    def test_optout_survives_merge(self):
        result = m.dedupe([record(do_not_contact=True), record()])[0]
        self.assertTrue(result['do_not_contact'])

    def test_uncertain_send_not_reset(self):
        result = m.dedupe([record(outreach='uncertain'), record(outreach='approved')])[0]
        self.assertEqual(result['outreach'], 'uncertain')

    def test_evidence_preserved(self):
        second = record(evidence=[{'claim': 'Historical product role', 'url': 'https://example.com/post', 'checked_at': '2025-12-01', 'basis': 'live'}])
        self.assertEqual(len(m.dedupe([record(), second])[0]['evidence']), 2)

    def test_invalid_evidence_rejected(self):
        with self.assertRaises(ValueError):
            m.validate(record(evidence=[]))

    def test_queries_broad_and_nonlocal(self):
        rows = list(m.queries({'market': 'Austin', 'companies': ['Example Co', ' example co ']}))
        self.assertEqual(len(rows), 11)
        self.assertTrue(any(r['stream'] == 'company_any_location' and 'Austin' not in r['query'] for r in rows))
        self.assertTrue(any(r['stream'] == 'company_local' and 'product' not in r['query'] for r in rows))

    def test_csv_formula_safety(self):
        self.assertEqual(m.safe_cell(' =HYPERLINK("bad")'), '\' =HYPERLINK("bad")')
        self.assertEqual(m.safe_cell('Alex'), 'Alex')

    def test_export_keeps_contact_and_scope_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'records.jsonl'
            output = Path(directory) / 'shortlist.csv'
            source.write_text(json.dumps(record(email='alex@example.com', role_scope='first-line manager', email_status='published')) + '\n')
            result = subprocess.run([sys.executable, str(Path(m.__file__)), 'export', '--detailed', '--input', str(source), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with output.open() as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row['email'], 'alex@example.com')
            self.assertEqual(row['role_scope'], 'first-line manager')
            self.assertEqual(row['email_status'], 'published')

    def test_simple_export_one_status(self):
        row = m.simple_row(record(invitation_status='Sent', outreach='none', relevance='Product recruiter'))
        self.assertEqual(row['Status'], 'Invitation pending')
        self.assertEqual(list(row), m.SIMPLE_FIELDS)
        self.assertNotIn('market_coverage', row)
        self.assertNotIn('outreach', row)

    def test_simple_export_explicit_status(self):
        row = m.simple_row(record(status='Connected', invitation_status='Sent'))
        self.assertEqual(row['Status'], 'Connected')

    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):
            m.canonical_url('https://secret:password@example.com/a')


class CoverageTests(unittest.TestCase):
    def test_generated_is_not_executed(self):
        rows = list(m.query_plan({'market': 'Austin', 'companies': ['Example Co']}))
        report = m.query_report(rows)
        self.assertEqual(report['generated_queries'], 11)
        self.assertEqual(report['executed_queries'], 0)
        self.assertFalse(report['coverage_complete'])

    def test_partial_run_and_blocker(self):
        rows = list(m.query_plan({'market': 'Austin', 'companies': ['Example Co']}))
        rows[0].update(status='executed', attempted_at='2026-01-01', records_examined='3')
        rows[1].update(status='blocked', attempted_at='2026-01-01')
        report = m.query_report(rows)
        self.assertEqual(report['executed_queries'], 1)
        self.assertEqual(report['attempted_queries'], 2)
        self.assertEqual(report['records_examined'], 3)
        self.assertFalse(report['coverage_complete'])

    def test_duplicate_query_ids_rejected(self):
        row = next(m.query_plan({'market': 'Austin', 'companies': []}))
        with self.assertRaises(ValueError):
            m.query_report([row, row])

    def test_execution_requires_evidence_of_attempt(self):
        row = next(m.query_plan({'market': 'Austin', 'companies': []}))
        row['status'] = 'executed'
        with self.assertRaises(ValueError):
            m.query_report([row])

    def test_assessments_separate_and_evidenced(self):
        r = record(assessments={
            'current_employer': {'status': 'supported', 'value': 'Example Co', 'evidence_indices': [0]},
            'management_scope': {'status': 'unknown', 'value': 'Not established', 'evidence_indices': []}})
        self.assertEqual(m.validate(r)['assessments']['management_scope']['status'], 'unknown')
        r['assessments']['management_scope']['status'] = 'supported'
        with self.assertRaises(ValueError):
            m.validate(r)

    def test_conflicting_assessments_preserve_sources(self):
        a = record(assessments={'current_employer': {'status': 'supported', 'value': 'Example Co', 'evidence_indices': [0]}})
        b = record(assessments={'current_employer': {'status': 'unknown', 'value': 'Unverified', 'evidence_indices': []}})
        result = m.dedupe([a, b])[0]
        self.assertEqual(result['assessments']['current_employer']['status'], 'unknown')
        self.assertEqual(result['source_records'][0]['assessments']['current_employer']['status'], 'supported')


if __name__ == '__main__':
    unittest.main()

