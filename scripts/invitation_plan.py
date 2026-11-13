"""Pure planning helpers; never access LinkedIn, send, schedule or edit a tracker."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256


def eligible_for_invite(record, *, authorized=False, connection_state='unknown'):
    """Fail closed unless current UI and private history permit a new invitation."""
    if not authorized or connection_state != 'not_connected':
        return False
    if record.get('do_not_contact') or record.get('paused') or record.get('category') == 'excluded':
        return False
    if record.get('status', 'Not contacted') != 'Not contacted':
        return False
    if record.get('outreach', 'none') != 'none' or record.get('events'):
        return False
    return bool(record.get('profile_url')) and record.get('category') in ('strong_match', 'company_contact')


def acceptance_check_plan(profile_url, confirmed_sent_at, *, confirmed=False, existing_keys=()):
    """Return an unscheduled 72-hour check plan; actual scheduler must confirm setup."""
    if not confirmed:
        raise ValueError('A confirmed invitation send is required')
    if not profile_url or not confirmed_sent_at:
        raise ValueError('Profile and confirmed send timestamp are required')
    sent = datetime.fromisoformat(confirmed_sent_at.replace('Z', '+00:00'))
    if sent.tzinfo is None or sent.utcoffset() is None:
        raise ValueError('Send timestamp must include its timezone')
    sent = sent.astimezone(timezone.utc)
    key = sha256((profile_url + '|' + sent.isoformat()).encode()).hexdigest()
    if key in existing_keys:
        return None
    return {'check_key': key, 'profile_url': profile_url, 'sent_at': sent.isoformat(),
            'due_at': (sent + timedelta(days=3)).isoformat(), 'schedule_status': 'not_scheduled'}


def observed_connection_status(observation):
    return {'accepted': 'Connected', 'pending': 'Invitation pending'}.get(observation, 'Connection unknown')


def profile_invite_action(*, full_profile_verified=False, direct_connect=False,
                          menu_opened=False, menu_connect=False, blocker=None):
    """Classify observed full-profile UI, never search-result Follow/absence.

    Does not grant eligibility or authorize a send; use existing scope/history gates.
    A technical inspection failure must remain Not contacted and unverified.
    """
    if blocker:
        return {'action': 'blocked', 'status': 'Not contacted',
                'availability': 'unverified', 'blocker': blocker}
    if not full_profile_verified:
        return {'action': 'open_verified_full_profile', 'availability': 'unverified'}
    if direct_connect:
        return {'action': 'connect_available', 'availability': 'verified'}
    if not menu_opened:
        return {'action': 'inspect_intro_more_menu', 'availability': 'unverified'}
    if menu_connect:
        return {'action': 'connect_available', 'availability': 'verified'}
    return {'action': 'record_verified_unavailable', 'status': 'Not contacted',
            'availability': 'unavailable'}


def next_candidate_action(record, *, authorized=False, connection_state='unknown',
                          connect_available=False):
    """Pure per-person decision, with no batch/enrichment/vacancy timing gate.

    Host must execute a returned invitation before researching the next candidate;
    this helper itself performs no UI, sending or scheduling.
    """
    if eligible_for_invite(record, authorized=authorized, connection_state=connection_state) and connect_available:
        return 'send_blank_invitation_now'
    return 'resolve_eligibility_or_record_blocker'
