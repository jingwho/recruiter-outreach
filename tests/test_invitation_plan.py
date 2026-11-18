import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timezone
GEO = {"country_codes": ["US"]}
RUN = "synthetic-run-2"
NOW = datetime(2026, 11, 18, 16, tzinfo=timezone.utc)
spec = importlib.util.spec_from_file_location('invitation_plan', Path(__file__).parents[1] / 'scripts/invitation_plan.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class InvitationTests(unittest.TestCase):
    def record(self, **kw):
        return dict({'profile_url':'https://www.linkedin.com/in/synthetic-person', 'linkedin_location_check': {'profile_url': 'https://www.linkedin.com/in/synthetic-person', 'basis': 'full_linkedin_profile', 'status': 'verified', 'run_id': RUN, 'observed_at': '2026-11-18T15:59:00Z', 'location_text': 'Austin, Texas, United States', 'country_code': 'US', 'locality': 'Austin'}, 'category':'company_contact','outreach':'none','status':'Not contacted'}, **kw)

    def test_no_default_authorization(self):
        self.assertFalse(m.eligible_for_invite(self.record(), connection_state='not_connected'))

    def test_explicit_batch_and_clear_state(self):
        self.assertTrue(m.eligible_for_invite(self.record(), authorized=True, target_geography=GEO, current_run=RUN, now=NOW, connection_state='not_connected'))

    def test_blocked_states(self):
        for state in ['accepted', 'pending', 'unknown']:
            self.assertFalse(m.eligible_for_invite(self.record(), authorized=True, target_geography=GEO, current_run=RUN, now=NOW, connection_state=state))
        for patch in [{'paused':True}, {'do_not_contact':True}, {'category':'excluded'}, {'status':'Previously contacted'}, {'outreach':'uncertain'}, {'events':[{'type':'prior_contact'}]}]:
            row=self.record(); row.update(patch)
            self.assertFalse(m.eligible_for_invite(row, authorized=True, target_geography=GEO, current_run=RUN, now=NOW, connection_state='not_connected'))

    def test_due_exactly_72_hours_and_not_scheduled(self):
        p=m.acceptance_check_plan('https://example.com/person', '2026-03-07T12:00:00-06:00', confirmed=True)
        self.assertEqual(p['due_at'], '2026-03-10T18:00:00+00:00')
        self.assertEqual(p['schedule_status'], 'not_scheduled')

    def test_dedupe_and_confirmation(self):
        p=m.acceptance_check_plan('https://example.com/person', '2026-01-01T00:00:00Z', confirmed=True)
        self.assertIsNone(m.acceptance_check_plan('https://example.com/person', '2026-01-01T00:00:00+00:00', confirmed=True, existing_keys=[p['check_key']]))
        with self.assertRaises(ValueError): m.acceptance_check_plan('https://example.com/person', '2026-01-01T00:00:00Z')
        with self.assertRaises(ValueError): m.acceptance_check_plan('https://example.com/person', '2026-01-01T00:00:00', confirmed=True)

    def test_unknown_not_pending(self):
        self.assertEqual(m.observed_connection_status('accepted'), 'Connected')
        self.assertEqual(m.observed_connection_status('pending'), 'Invitation pending')
        self.assertEqual(m.observed_connection_status('inaccessible'), 'Connection unknown')

    def test_search_result_absence_requires_full_profile(self):
        self.assertEqual(m.profile_invite_action()['action'], 'open_verified_full_profile')

    def test_no_direct_connect_requires_intro_menu(self):
        self.assertEqual(m.profile_invite_action(full_profile_verified=True)['action'], 'inspect_intro_more_menu')
        self.assertEqual(m.profile_invite_action(full_profile_verified=True, menu_opened=True, menu_connect=True)['action'], 'connect_available')
        self.assertEqual(m.profile_invite_action(full_profile_verified=True, direct_connect=True)['action'], 'connect_available')

    def test_menu_failure_is_unverified_not_skipped(self):
        for blocker in ['menu timeout', 'menu cannot open', 'email verification required', 'platform restriction']:
            result = m.profile_invite_action(full_profile_verified=True, blocker=blocker)
            self.assertEqual(result['availability'], 'unverified')
            self.assertEqual(result['status'], 'Not contacted')
            self.assertEqual(result['blocker'], blocker)
        self.assertEqual(m.profile_invite_action(full_profile_verified=True, menu_opened=True)['availability'], 'unavailable')

    def test_verified_authorized_candidate_is_immediate_without_enrichment(self):
        row = self.record(vacancy_status='unknown', email=None, apollo_enriched=False)
        self.assertEqual(m.next_candidate_action(row, authorized=True, target_geography=GEO, current_run=RUN, now=NOW, connection_state='not_connected', connect_available=True), 'send_blank_invitation_now')

    def test_immediacy_does_not_override_gates(self):
        self.assertNotEqual(m.next_candidate_action(self.record(), connection_state='not_connected', connect_available=True), 'send_blank_invitation_now')
        for patch in [{'paused':True}, {'outreach':'uncertain'}, {'category':'excluded'}]:
            row=self.record(); row.update(patch)
            self.assertNotEqual(m.next_candidate_action(row, authorized=True, target_geography=GEO, current_run=RUN, now=NOW, connection_state='not_connected', connect_available=True), 'send_blank_invitation_now')
        self.assertNotEqual(m.next_candidate_action(self.record(), authorized=True, target_geography=GEO, current_run=RUN, now=NOW, connection_state='pending', connect_available=True), 'send_blank_invitation_now')
        self.assertNotEqual(m.next_candidate_action(self.record(), authorized=True, target_geography=GEO, current_run=RUN, now=NOW, connection_state='not_connected'), 'send_blank_invitation_now')


class LocationGateTests(unittest.TestCase):
    def row(self):
        return InvitationTests().record()

    def gate(self, row, **kw):
        return m.location_gate(row, **dict(dict(target_geography=GEO, current_run=RUN, now=NOW), **kw))

    def test_direct_us_profile_passes(self):
        self.assertTrue(self.gate(self.row())['eligible'])

    def test_foreign_us_market_does_not_pass(self):
        row = self.row()
        row.update(market_coverage='US', company_location='Austin', recruiter_location='Austin')
        row['linkedin_location_check'].update(country_code='GB', location_text='London, England')
        self.assertFalse(self.gate(row)['eligible'])

    def test_missing_or_inaccessible_location_fails(self):
        for patch in [None, {}, {'status': 'blocked'}, {'country_code': None}, {'location_text': ''}]:
            row = self.row()
            if patch is None:
                del row['linkedin_location_check']
            else:
                row['linkedin_location_check'].update(patch)
                if not patch: row['linkedin_location_check'] = {}
            self.assertFalse(self.gate(row)['eligible'])

    def test_search_snippet_and_headquarters_fail(self):
        for basis in ['indexed', 'company_page', 'job_posting', 'directory', 'user_supplied']:
            row = self.row()
            row['linkedin_location_check']['basis'] = basis
            self.assertFalse(self.gate(row)['eligible'])

    def test_rerun_requires_new_profile_check(self):
        row = self.row()
        self.assertFalse(self.gate(row, current_run='synthetic-run-3')['eligible'])

    def test_bad_timestamps_fail(self):
        for timestamp in [None, '', 'nonsense', '2026-11-18T16:01:00Z', '2026-11-16T15:00:00Z', '2026-11-18T15:59:00']:
            row = self.row()
            row['linkedin_location_check']['observed_at'] = timestamp
            self.assertFalse(self.gate(row)['eligible'])

    def test_geography_and_run_cannot_default_to_approval(self):
        for patch in [{'target_geography': None}, {'target_geography': {}}, {'current_run': None}, {'target_geography': {'country_codes': 'US'}}, {'target_geography': {'country_codes': ['US'], 'localities': 'Austin'}}]:
            self.assertFalse(self.gate(self.row(), **patch)['eligible'])

    def test_city_scope_is_separate_from_country_scope(self):
        row = self.row()
        row['linkedin_location_check'].update(locality='Seattle', location_text='Seattle, Washington, United States')
        self.assertTrue(self.gate(row)['eligible'])
        self.assertFalse(self.gate(row, target_geography={'country_codes': ['US'], 'localities': ['Austin']})['eligible'])

    def test_profile_identity_cannot_be_substituted(self):
        for url in ['https://www.linkedin.com/in/someone-else', 'https://example.com/in/synthetic-person', 'https://www.linkedin.com/company/synthetic-person', 'https://www.linkedin.com.evil.example/in/synthetic-person', 'https://user@linkedin.com/in/synthetic-person']:
            row = self.row()
            row['linkedin_location_check']['profile_url'] = url
            self.assertFalse(self.gate(row)['eligible'])

    def test_immediate_send_cannot_bypass_location(self):
        row = self.row()
        row['linkedin_location_check']['country_code'] = 'IE'
        self.assertFalse(m.eligible_for_invite(row, authorized=True, connection_state='not_connected', target_geography=GEO, current_run=RUN, now=NOW))
        self.assertNotEqual(m.next_candidate_action(row, authorized=True, connection_state='not_connected', connect_available=True, target_geography=GEO, current_run=RUN, now=NOW), 'send_blank_invitation_now')
