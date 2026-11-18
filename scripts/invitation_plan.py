"""Pure planning helpers; never access LinkedIn, send, schedule or edit a tracker."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from urllib.parse import urlsplit


def _profile_identity(url):
    if not isinstance(url, str):
        return None
    try:
        u = urlsplit(url)
        parts = u.path.strip('/').split('/')
        if (u.scheme != 'https' or u.username or u.password or u.port or
                not (u.hostname == 'linkedin.com' or (u.hostname or '').endswith('.linkedin.com')) or
                len(parts) != 2 or parts[0] != 'in' or not parts[1]):
            return None
        return parts[1]
    except ValueError:
        return None


def location_gate(record, *, target_geography=None, current_run=None, now=None):
    """Validate host-recorded direct profile evidence; never fetch or infer location.

    Must be called with the current run ID, not a stored prior run ID. Evidence
    must be refreshed on the person's full LinkedIn profile in every run and
    immediately before an invite. This is a validation helper, not proof the
    host actually opened LinkedIn or permission to send.
    """
    blocked = lambda reason: {'eligible': False, 'reason': reason}
    if not isinstance(target_geography, dict) or not isinstance(current_run, str) or not current_run.strip():
        return blocked('missing_geography_or_current_run')
    countries = target_geography.get('country_codes')
    localities = target_geography.get('localities', [])
    if (not isinstance(countries, list) or not countries or
            any(not isinstance(c, str) or len(c) != 2 or not c.isalpha() or c != c.upper() for c in countries) or
            not isinstance(localities, list) or any(not isinstance(c, str) or not c.strip() for c in localities)):
        return blocked('invalid_geography')
    evidence = record.get('linkedin_location_check')
    if not isinstance(evidence, dict):
        return blocked('profile_location_unverified')
    identity = _profile_identity(record.get('profile_url'))
    if not identity or _profile_identity(evidence.get('profile_url')) != identity:
        return blocked('profile_identity_mismatch')
    if (evidence.get('basis') != 'full_linkedin_profile' or
            evidence.get('run_id') != current_run or evidence.get('status') != 'verified'):
        return blocked('current_direct_profile_check_required')
    if not isinstance(evidence.get('location_text'), str) or not evidence['location_text'].strip():
        return blocked('profile_location_missing')
    try:
        observed = datetime.fromisoformat(evidence['observed_at'].replace('Z', '+00:00'))
        current = now if now is not None else datetime.now(timezone.utc)
        if (observed.utcoffset() is None or current.utcoffset() is None or
                not timedelta(0) <= current - observed <= timedelta(hours=24)):
            return blocked('profile_check_stale_or_invalid')
    except (KeyError, ValueError, TypeError, AttributeError):
        return blocked('profile_check_stale_or_invalid')
    if evidence.get('country_code') not in countries:
        return blocked('outside_or_unknown_country')
    # Localities are explicit normalized values from the observed personal
    # location, never company headquarters, job locations or market coverage.
    if localities and evidence.get('locality') not in localities:
        return blocked('outside_or_unknown_locality')
    return {'eligible': True, 'reason': 'current_profile_location_matches'}


def eligible_for_invite(record, *, authorized=False, connection_state='unknown',
                        target_geography=None, current_run=None, now=None):
    """Fail closed unless current UI and private history permit a new invitation."""
    if not authorized or connection_state != 'not_connected':
        return False
    if record.get('do_not_contact') or record.get('paused') or record.get('category') == 'excluded':
        return False
    if record.get('status', 'Not contacted') != 'Not contacted':
        return False
    if record.get('outreach', 'none') != 'none' or record.get('events'):
        return False
    if not location_gate(record, target_geography=target_geography,
                         current_run=current_run, now=now)['eligible']:
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
                          connect_available=False, target_geography=None,
                          current_run=None, now=None):
    """Pure per-person decision, with no batch/enrichment/vacancy timing gate.

    Host must execute a returned invitation before researching the next candidate;
    this helper itself performs no UI, sending or scheduling.
    """
    if eligible_for_invite(record, authorized=authorized, connection_state=connection_state,
                           target_geography=target_geography, current_run=current_run, now=now) and connect_available:
        return 'send_blank_invitation_now'
    return 'resolve_eligibility_or_record_blocker'

