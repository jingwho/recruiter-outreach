import sys
from pathlib import Path
from io import BytesIO
import unittest
from openpyxl import Workbook, load_workbook
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from profile_buttons import apply_buttons, direct_profile, profile_destination

class ProfileButtonsTests(unittest.TestCase):
    def test_only_verified_profiles_and_preserved_tracker(self):
        w = Workbook(); s = w.active
        s.append(['Name', 'LinkedIn', 'Status', 'Notes'])
        s.append(['Example', 'https://www.linkedin.com/in/synthetic-person/?trk=foo', 'Invitation pending', 'User note'])
        s.append(['Other', 'https://www.linkedin.com/in/unverified-person', 'Not contacted', 'Keep'])
        s.append(['Search', 'https://www.linkedin.com/search/results/people/?keywords=Example', 'Not contacted', 'Unverified'])
        other = w.create_sheet('History'); other['A1'] = 'Preserve history'
        self.assertEqual(apply_buttons(s, ['https://linkedin.com/in/synthetic-person']), 1)
        self.assertEqual(s['B2'].value, 'Open profile')
        self.assertEqual(s['B2'].fill.fgColor.rgb, '000A66C2')
        self.assertIsNone(s['B3'].hyperlink)
        self.assertIsNone(s['B4'].hyperlink)
        self.assertEqual(s['C2'].value, 'Invitation pending')
        self.assertEqual(s['D2'].value, 'User note')
        f = BytesIO(); w.save(f); f.seek(0); reread = load_workbook(f)
        self.assertEqual(profile_destination(reread.active['B2']), 'https://www.linkedin.com/in/synthetic-person')
        self.assertEqual(reread['History']['A1'].value, 'Preserve history')
        self.assertEqual(apply_buttons(reread.active, ['https://linkedin.com/in/synthetic-person']), 1)

    def test_reject_search_and_unsafe_urls(self):
        for url in ['https://linkedin.com/search/results/people/', 'https://linkedin.com/company/example', 'https://linkedin.com/in/a/posts', 'https://linkedin.com.evil.test/in/a', 'javascript:alert(1)', 'https://user:pass@linkedin.com/in/a', 'https://linkedin.com:444/in/a', '=HYPERLINK("bad")', None]:
            self.assertIsNone(direct_profile(url), url)
        w=Workbook(); w.active.append(['LinkedIn'])
        with self.assertRaises(ValueError): apply_buttons(w.active, ['https://linkedin.com/search/results/people/'])
