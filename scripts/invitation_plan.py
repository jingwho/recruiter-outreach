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
