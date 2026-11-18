#!/usr/bin/env python3
"""Offline tracker comparison. Never edits inputs, verifies connections or sends."""
import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from profile_buttons import direct_profile, profile_destination


def timestamp(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('Timestamp must include timezone')
    return result.astimezone(timezone.utc)


def literal_profile(value):
    """Accept a URL or a literal Excel HYPERLINK without evaluating formulas."""
    if isinstance(value, str) and value.startswith('='):
        match = re.fullmatch(r'=HYPERLINK\(\s*"([^"\r\n]+)"\s*,\s*"(?:[^"]|"")*"\s*\)', value, re.IGNORECASE)
        return direct_profile(match.group(1)) if match else None
    return direct_profile(value)


def read_tracker(path, sheet='Recruiters'):
    """Read values faithfully; Excel native links retain their actual target."""
    path = Path(path)
    if path.suffix.lower() == '.xlsx':
        from openpyxl import load_workbook
        book = load_workbook(path, data_only=False)
        try:
            ws = book[sheet]
            rows = list(ws.iter_rows())
            if not rows:
                raise ValueError('Tracker is empty')
            headers = [c.value for c in rows[0]]
            data = [[profile_destination(c) if h == 'LinkedIn' else c.value
                     for h, c in zip(headers, row)] for row in rows[1:]]
        finally:
            book.close()
    elif path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.reader(stream))
        if not rows:
            raise ValueError('Tracker is empty')
        headers, data = rows[0], rows[1:]
    else:
        raise ValueError('Tracker must be .xlsx or .csv')
    if any(not isinstance(h, str) or not h for h in headers) or len(set(headers)) != len(headers):
        raise ValueError('Headers must be nonempty and unique')
    if not {'Name', 'LinkedIn', 'Status'} <= set(headers):
        raise ValueError('Required headers: Name, LinkedIn, Status')
    result = []
    for number, row in enumerate(data, 2):
        if all(v is None or v == '' for v in row):
            continue
        if len(row) != len(headers):
            raise ValueError(f'Row {number} has a different width from the header')
        record = {key: '' if value is None else str(value) for key, value in zip(headers, row)}
        result.append({'row': number, 'values': record,
                       'profile_url': literal_profile(record['LinkedIn'])})
    return result


def review(current, previous, now):
    """Compare known profile identities, never merge by name or infer send dates.

    Optional dates require explicit timezone offsets. A confirmed send is supplied
    in Confirmed sent at, not inferred from Status or a note. Last checked at at or
    after the 72-hour due time means the initial acceptance check was completed.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must include timezone')
    now = now.astimezone(timezone.utc)
    counts = [Counter(r['profile_url'] for r in rows if r['profile_url'])
              for rows in (current, previous)]
    prior = {r['profile_url']: r for r in previous if r['profile_url']}
    items = []
    for entry in current:
        values, url = entry['values'], entry['profile_url']
        reasons, changes = [], {}
        if not url:
            reasons.append('missing_or_invalid_profile')
        elif any(c[url] > 1 for c in counts):
            reasons.append('duplicate_profile_review_required')
        else:
            before = prior.get(url)
            if before is None:
                reasons.append('new_record')
            else:
                for key in sorted(values.keys() | before['values'].keys()):
                    old, new = before['values'].get(key, ''), values.get(key, '')
                    if key == 'LinkedIn':
                        old, new = literal_profile(old), literal_profile(new)
                    if old != new:
                        changes[key] = {'before': old, 'after': new}
                if changes:
                    reasons.append('changed_record')
        due_at = None
        if values['Status'] == 'Invitation pending':
            sent = values.get('Confirmed sent at', '')
            if not sent:
                reasons.append('pending_without_confirmed_send_time')
            else:
                try:
                    sent_at = timestamp(sent)
                    checked = timestamp(values['Last checked at']) if values.get('Last checked at') else None
                    if sent_at > now or (checked and (checked > now or checked < sent_at)):
                        raise ValueError('Inconsistent timestamp')
                    due = sent_at + timedelta(hours=72)
                    if due <= now and (checked is None or checked < due):
                        # Ambiguous identities never get a due action.
                        if url and all(c[url] == 1 for c in counts[:1]) and counts[1][url] <= 1:
                            due_at = due.isoformat()
                            reasons.append('acceptance_check_due_not_scheduled')
                except (ValueError, TypeError, OverflowError):
                    reasons.append('invalid_or_inconsistent_timestamp')
        if reasons:
            items.append({'row': entry['row'], 'name': values['Name'], 'profile_url': url,
                          'status': values['Status'], 'reasons': reasons, 'changes': changes,
                          'due_at': due_at})
    # Deletions are review-only. Do not resurrect removed people or contact them.
    for entry in previous:
        url = entry['profile_url']
        if url and not counts[0][url] and counts[1][url] == 1:
            items.append({'row': None, 'name': entry['values']['Name'], 'profile_url': url,
                          'status': entry['values']['Status'], 'reasons': ['removed_record_review_only'],
                          'changes': {}, 'due_at': None})
    return {'mode': 'read_only_review', 'network_requests': 0, 'invitations_sent': 0,
            'checks_scheduled': 0, 'current_records': len(current), 'review_items': items}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--current', required=True)
    p.add_argument('--previous', help='Optional earlier private tracker snapshot; omit for initial ambiguity/due review')
    p.add_argument('--sheet', default='Recruiters')
    p.add_argument('--now', required=True, help='ISO 8601 timestamp with timezone')
    p.add_argument('--output', required=True, help='New private .json review path, not a replacement tracker')
    a = p.parse_args()
    if Path(a.output).suffix.lower() != '.json':
        p.error('Output must be .json')
    try:
        current = read_tracker(a.current, a.sheet)
        previous = read_tracker(a.previous, a.sheet) if a.previous else current
        result = review(current, previous, timestamp(a.now))
        result['baseline_present'] = bool(a.previous)
        # Exclusive creation protects both inputs and any previous report.
        with open(a.output, 'x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except (ValueError, OSError, KeyError) as exc:
        p.error(str(exc))
    print(json.dumps({'review_items': len(result['review_items']), 'tracker_modified': False}))


if __name__ == '__main__':
    main()
