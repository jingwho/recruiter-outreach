import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('invitation_plan', Path(__file__).parents[1] / 'scripts/invitation_plan.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class InvitationTests(unittest.TestCase):
    def record(self, **kw):
        return dict({'profile_url':'https://example.com/person', 'category':'company_contact','outreach':'none','status':'Not contacted'}, **kw)

    def test_no_default_authorization(self):
        self.assertFalse(m.eligible_for_invite(self.record(), connection_state='not_connected'))

    def test_explicit_batch_and_clear_state(self):
        self.assertTrue(m.eligible_for_invite(self.record(), authorized=True, connection_state='not_connected'))

    def test_blocked_states(self):
        for state in ['accepted', 'pending', 'unknown']:
            self.assertFalse(m.eligible_for_invite(self.record(), authorized=True, connection_state=state))
        for patch in [{'paused':True}, {'do_not_contact':True}, {'category':'excluded'}, {'status':'Previously contacted'}, {'outreach':'uncertain'}, {'events':[{'type':'prior_contact'}]}]:
            row=self.record(); row.update(patch)
            self.assertFalse(m.eligible_for_invite(row, authorized=True, connection_state='not_connected'))

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
        self.assertEqual(m.next_candidate_action(row, authorized=True, connection_state='not_connected', connect_available=True), 'send_blank_invitation_now')

    def test_immediacy_does_not_override_gates(self):
        self.assertNotEqual(m.next_candidate_action(self.record(), connection_state='not_connected', connect_available=True), 'send_blank_invitation_now')
        for patch in [{'paused':True}, {'outreach':'uncertain'}, {'category':'excluded'}]:
            row=self.record(); row.update(patch)
            self.assertNotEqual(m.next_candidate_action(row, authorized=True, connection_state='not_connected', connect_available=True), 'send_blank_invitation_now')
        self.assertNotEqual(m.next_candidate_action(self.record(), authorized=True, connection_state='pending', connect_available=True), 'send_blank_invitation_now')
        self.assertNotEqual(m.next_candidate_action(self.record(), authorized=True, connection_state='not_connected'), 'send_blank_invitation_now')
