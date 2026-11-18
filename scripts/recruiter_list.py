#!/usr/bin/env python3
"""Local-only query generation and conservative evidence-preserving CSV export."""
import argparse
import csv
import json
import hashlib
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from datetime import date

CATEGORIES = {'strong_match', 'company_contact', 'needs_checking', 'excluded'}
STATES = {'none', 'drafted', 'approved', 'sent', 'uncertain', 'replied', 'closed'}
EXPORT_FIELDS = ['name', 'company', 'profile_url', 'category', 'recruiter_type',
                 'recruiter_location', 'market_coverage', 'role_scope', 'email',
                 'email_source', 'email_status', 'notes', 'opportunities', 'events',
                 'assessments', 'linkedin_location_check',
                 'outreach', 'do_not_contact', 'evidence', 'conflicts', 'source_records']

SIMPLE_FIELDS = ['Name', 'Company', 'LinkedIn', 'Email', 'Relevance', 'Status', 'Notes', 'Source']

def simple_row(row):
    # Explicit current status is authoritative; legacy invitation fields override
    # old outreach defaults so a confirmed invitation never appears untouched.
    status = row.get('status') or row.get('invitation_status') or {
        'none': 'Not contacted', 'sent': 'Contacted', 'uncertain': 'Needs outcome check',
        'drafted': 'Draft ready', 'approved': 'Ready to send', 'replied': 'Replied',
        'closed': 'Closed'
    }.get(row.get('outreach'), 'Not contacted')
    status = {'Sent': 'Invitation pending', 'Already connected': 'Connected'}.get(status, status)
    if row.get('do_not_contact'):
        status = 'Do not contact'
    elif row.get('category') == 'excluded' and status == 'Not contacted':
        status = 'Excluded'
    evidence = row.get('evidence', [])
    return dict(zip(SIMPLE_FIELDS, [
        row.get('name', ''), row.get('company', ''), row.get('profile_url', ''),
        row.get('email', ''), row.get('relevance', ''), status,
        row.get('notes', ''), '; '.join(dict.fromkeys(e['url'] for e in evidence))]))

ASSESSMENT_KEYS = {'current_employer', 'pm_experience', 'management_scope', 'vacancy_status'}
ASSESSMENT_STATUSES = {'supported', 'unknown', 'conflicting', 'not_applicable'}
QUERY_FIELDS = ['query_id', 'stream', 'company', 'query', 'status', 'attempted_at', 'records_examined', 'notes']
QUERY_STATES = {'planned', 'executed', 'blocked', 'skipped'}

RANK = {v: i for i, v in enumerate(['none', 'drafted', 'approved', 'sent', 'uncertain', 'replied', 'closed'])}


def canonical_url(value):
    if not value:
        return ''
    u = urlsplit(value)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
        raise ValueError('Profile URL must be an absolute HTTP(S) URL without credentials')
    host = u.hostname.lower()
    path = u.path.rstrip('/')
    if host == 'linkedin.com' or host.endswith('.linkedin.com'):
        host = 'www.linkedin.com'
        if path.startswith('/in/'):
            path = '/in/' + path.split('/')[2]
    # Query parameters can identify people outside LinkedIn; preserve them.
    query = '' if host == 'www.linkedin.com' else u.query
    netloc = host + (f':{u.port}' if u.port else '')
    return urlunsplit(('https', netloc, path, query, ''))


def validate(record):
    for key in ('name', 'company', 'profile_url', 'category', 'outreach'):
        if not isinstance(record.get(key), str):
            raise ValueError(f'{key} must be a string')
    if not record['name'].strip() or not record['company'].strip():
        raise ValueError('name and company cannot be blank')
    canonical_url(record['profile_url'])
    if record['category'] not in CATEGORIES or record['outreach'] not in STATES:
        raise ValueError('Invalid category or outreach status')
    if not isinstance(record.get('do_not_contact'), bool):
        raise ValueError('do_not_contact must be boolean')
    evidence = record.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        raise ValueError('At least one evidence record is required')
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError('Evidence must be an object')
        for key in ('claim', 'url', 'checked_at', 'basis'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'Evidence {key} must be a nonempty string')
        date.fromisoformat(item['checked_at'])
        canonical_url(item['url'])
        if item['basis'] not in ('live', 'indexed', 'user_supplied'):
            raise ValueError('Invalid evidence basis')
    assessments = record.get('assessments', {})
    if not isinstance(assessments, dict) or set(assessments) - ASSESSMENT_KEYS:
        raise ValueError('Invalid assessment dimensions')
    for key, assessment in assessments.items():
        if not isinstance(assessment, dict) or assessment.get('status') not in ASSESSMENT_STATUSES:
            raise ValueError(f'Invalid assessment status for {key}')
        if not isinstance(assessment.get('value'), str):
            raise ValueError(f'Assessment value must be a string for {key}')
        indices = assessment.get('evidence_indices', [])
        if not isinstance(indices, list) or any(type(i) is not int or i < 0 or i >= len(evidence) for i in indices):
            raise ValueError(f'Invalid evidence reference for {key}')
        if assessment['status'] in ('supported', 'conflicting') and not indices:
            raise ValueError(f'{key} requires supporting evidence')
    return record


def dedupe(records):
    output, seen = [], {}
    for raw in records:
        item = json.loads(json.dumps(validate(raw)))
        item['profile_url'] = canonical_url(item['profile_url'])
        key = item['profile_url']
        if not key or key not in seen:
            item['source_records'] = [raw]
            output.append(item)
            if key:
                seen[key] = item
            continue
        target = seen[key]
        target['source_records'].append(raw)
        for evidence in item['evidence']:
            if evidence not in target['evidence']:
                target['evidence'].append(evidence)
        conflicts = target.setdefault('conflicts', [])
        for field in ('name', 'company', 'category', 'email', 'assessments', 'linkedin_location_check'):
            if target.get(field) != item.get(field):
                if field not in conflicts:
                    conflicts.append(field)
        if conflicts:
            target['category'] = 'needs_checking'
        if 'assessments' in conflicts:
            # Source records retain original evidence-index relationships.
            target['assessments'] = {key: {'status': 'unknown', 'value': 'Conflicting or incomplete merged assessments; review source records', 'evidence_indices': []} for key in ASSESSMENT_KEYS}
        target['do_not_contact'] |= item['do_not_contact']
        target['outreach'] = max((target['outreach'], item['outreach']), key=RANK.get)
    return output


def safe_cell(value):
    """Neutralize spreadsheet formulas in exports of untrusted source text."""
    value = str(value)
    if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')):
        return "'" + value
    return value


def write_csv(path, fields, rows):
    with Path(path).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({key: safe_cell(row.get(key, '')) for key in fields})


def queries(config):
    market = config.get('market', '')
    companies = config.get('companies', [])
    if not isinstance(market, str) or not market.strip() or not isinstance(companies, list):
        raise ValueError('Config requires market string and companies list')
    titles = ['recruiter', 'talent acquisition', 'talent partner', 'sourcer']
    seen = set()
    quote = lambda s: '"' + s.replace('"', ' ').strip() + '"'
    for company in companies:
        if not isinstance(company, str) or not company.strip():
            raise ValueError('Company entries must be nonempty strings')
        normalized = ' '.join(company.split()).casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        for title in titles:
            base = f'site:linkedin.com/in {quote(company)} {quote(title)}'
            yield {'stream': 'company_local', 'company': company, 'query': base + ' ' + quote(market)}
            yield {'stream': 'company_any_location', 'company': company, 'query': base}
    yield {'stream': 'specialist', 'company': '', 'query': f'site:linkedin.com/in "product management" recruiter {quote(market)}'}
    yield {'stream': 'hiring_posts', 'company': '', 'query': f'site:linkedin.com/posts "product manager" hiring {quote(market)}'}
    yield {'stream': 'agency', 'company': '', 'query': f'"product management" recruiters team {quote(market)} -site:linkedin.com'}


def query_plan(config):
    for row in queries(config):
        yield dict(row, query_id=hashlib.sha256(row['query'].encode()).hexdigest()[:16],
                   status='planned', attempted_at='', records_examined='', notes='')


def query_report(rows):
    counts = {state: 0 for state in sorted(QUERY_STATES)}
    ids = set()
    records = 0
    for row in rows:
        query_id = row.get('query_id')
        if not query_id or query_id in ids:
            raise ValueError('Query IDs must be present and unique')
        ids.add(query_id)
        status = row.get('status')
        if status not in QUERY_STATES:
            raise ValueError('Invalid query status')
        attempted = row.get('attempted_at', '')
        if status in ('executed', 'blocked'):
            if not attempted:
                raise ValueError('Executed/blocked queries require attempted_at')
            date.fromisoformat(attempted)
        elif attempted:
            raise ValueError('Unattempted queries must not have attempted_at')
        examined = row.get('records_examined', '')
        if status == 'executed':
            if not str(examined).isdigit():
                raise ValueError('Executed queries require nonnegative records_examined')
            records += int(examined)
        elif examined not in ('', None):
            raise ValueError('Record counts belong only to executed queries')
        counts[status] += 1
    return {'generated_queries': len(ids), 'executed_queries': counts['executed'],
            'attempted_queries': counts['executed'] + counts['blocked'],
            'status_counts': counts, 'records_examined': records,
            'coverage_complete': counts['planned'] + counts['blocked'] + counts['skipped'] == 0 and bool(ids)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    q = sub.add_parser('queries')
    q.add_argument('--config', required=True)
    q.add_argument('--output', required=True)
    e = sub.add_parser('export')
    e.add_argument('--input', required=True)
    e.add_argument('--output', required=True)
    e.add_argument('--detailed', action='store_true', help='Export audit fields as JSON; default is a concise human-readable sheet')
    r = sub.add_parser('coverage')
    r.add_argument('--input', required=True)
    r.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        source = args.config if args.command == 'queries' else args.input
        if Path(source).resolve() == Path(args.output).resolve():
            raise ValueError('Output must not overwrite input')
        if Path(args.output).exists():
            raise ValueError('Output already exists; choose a new filename')
        if args.command == 'queries':
            rows = list(query_plan(json.loads(Path(args.config).read_text())))
            write_csv(args.output, QUERY_FIELDS, rows)
            print(json.dumps({'queries': len(rows), 'network_requests': 0}))
        elif args.command == 'coverage':
            with Path(args.input).open(newline='', encoding='utf-8') as f:
                report = query_report(list(csv.DictReader(f)))
            Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report))
        else:
            raw = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
            rows = dedupe(raw)
            fields = EXPORT_FIELDS if args.detailed else SIMPLE_FIELDS
            csv_rows = ([{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()} for row in rows] if args.detailed else [simple_row(row) for row in rows])
            write_csv(args.output, fields, csv_rows)
            print(json.dumps({'source_records': len(raw), 'distinct_records': len(rows), 'duplicates_collapsed': len(raw)-len(rows), 'network_requests': 0}))
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    main()

