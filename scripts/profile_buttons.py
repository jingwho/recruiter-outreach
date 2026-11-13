#!/usr/bin/env python3
"""Local-only native XLSX profile links; never verifies people or opens profiles."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


def direct_profile(value):
    """Return a stable direct personal-profile URL, never a search/company URL."""
    try:
        u = urlsplit(value)
        if (u.scheme not in ('http', 'https') or u.username or u.password or u.port
                or not re.fullmatch(r'(?:[a-z]{2,3}\.|www\.)?linkedin\.com', u.hostname or '')
                or not re.fullmatch(r'/in/[^/\s?#]+/?', u.path)):
            return None
        return 'https://www.linkedin.com' + u.path.rstrip('/')
    except (ValueError, TypeError):
        return None


def profile_destination(cell):
    """Read identity from the native hyperlink, not its 'Open profile' label."""
    return cell.hyperlink.target if cell.hyperlink else cell.value


def apply_buttons(sheet, verified_profiles):
    """Change only verified direct profile cells in the existing LinkedIn column.

    verified_profiles is an explicit, private set of identity-verified URLs supplied
    by the caller, not inferred from URL shape. All other cells/statuses stay intact.
    """
    verified = set()
    for url in verified_profiles:
        canonical = direct_profile(url)
        if not canonical:
            raise ValueError('Verified profiles must be direct LinkedIn /in/ URLs')
        verified.add(canonical)
    columns = [c.column for c in sheet[1] if c.value == 'LinkedIn']
    if len(columns) != 1:
        raise ValueError('Expected exactly one LinkedIn header in row 1')
    count = 0
    for row in sheet.iter_rows(min_row=2, min_col=columns[0], max_col=columns[0]):
        cell = row[0]
        target = direct_profile(profile_destination(cell))
        if target and target in verified:
            cell.value = 'Open profile'
            cell.hyperlink = target
            cell.hyperlink.tooltip = target
            cell.font = Font(name='Calibri', size=11, color='FFFFFF', bold=True)
            cell.fill = PatternFill('solid', fgColor='0A66C2')
            cell.alignment = Alignment(horizontal='center', vertical='center')
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='Existing .xlsx tracker')
    parser.add_argument('--output', required=True, help='New local staging path; replace the same tracker after verification')
    parser.add_argument('--sheet', required=True)
    parser.add_argument('--verified-profiles', required=True, help='Private JSON array of identity-verified direct profile URLs')
    args = parser.parse_args()
    if Path(args.output).exists() or Path(args.output).suffix.lower() != '.xlsx':
        parser.error('Output must be a new .xlsx staging path')
    workbook = load_workbook(args.input)
    urls = json.loads(Path(args.verified_profiles).read_text())
    if not isinstance(urls, list) or any(not isinstance(url, str) for url in urls):
        parser.error('Verified profiles must be a JSON array of URL strings')
    count = apply_buttons(workbook[args.sheet], urls)
    workbook.save(args.output)
    print(json.dumps({'profile_buttons': count, 'network_requests': 0}))


if __name__ == '__main__':
    main()
