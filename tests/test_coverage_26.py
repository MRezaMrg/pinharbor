"""Coverage confidence, authentication, session and bilingual regressions."""
from pathlib import Path
import os
import sys
import tempfile
import unittest

from studio_core import (QueueEntry, dump_session, load_session, build_command,
                         assess_board_coverage, parse_output_event)
from download_runtime import ProcessController
from ui_language import set_language, language, tr


class CoverageTests(unittest.TestCase):
    def test_distinguishes_pins_from_files(self):
        self.assertEqual(assess_board_coverage(25, 45, 25, 0), "partial")
        self.assertEqual(assess_board_coverage(45, 45, 25, 20), "done")
        self.assertEqual(assess_board_coverage(45, 0, 25, 20), "done")
        self.assertEqual(assess_board_coverage(25, 45, 0, 0), "empty")
        self.assertEqual(assess_board_coverage(0, 45, 25, 0), "partial")
        self.assertEqual(assess_board_coverage(45, 45, 1, 0), "done")

    def test_tracking_does_not_limit_pagination(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = build_command('https://www.pinterest.com/rezamnteo/web-ui-design/', Path(tmp), Path(tmp)/'config.json')
            self.assertIn('prepare:PINHARBOR_SEEN|{id}', cmd)
            self.assertIn('--Print', cmd)
            self.assertNotIn('--range', cmd)
            self.assertNotIn('--abort', cmd)
            self.assertNotIn('--cookies-from-browser', cmd)
            cmd_with_login = build_command('pinterest.com/rezamnteo/web-ui-design/', Path(tmp), Path(tmp)/'config.json', browser='edge')
            self.assertEqual(cmd_with_login[cmd_with_login.index('--cookies-from-browser') + 1], 'edge')

    def test_seen_event_and_subprocess_dedup(self):
        self.assertEqual(parse_output_event('PINHARBOR_SEEN|112233\n'), ('seen','112233'))
        source = ';'.join(["print('PINHARBOR_SEEN|101')", "print('PBS_OK|a.jpg')",
                           "print('PINHARBOR_SEEN|101')", "print('PBS_SKIP|a.jpg')",
                           "print('PINHARBOR_SEEN|102')", "print('PBS_OK|b.jpg')"])
        events = []
        result = ProcessController().run([sys.executable, '-u', '-c', source], os.environ.copy(),
                                         lambda *a: events.append(a))
        self.assertEqual((result.ok, result.skipped, result.discovered), (2, 1, 2))
        self.assertEqual(sum(e[0]=='seen' for e in events), 3)

    def test_session_upgrade_preserves_legacy_and_new_coverage(self):
        e = QueueEntry('pinterest.com/a/board', status='partial', discovered=25, expected=45, new=25)
        loaded = load_session(dump_session([e]))[0]
        self.assertEqual((loaded.status, loaded.discovered, loaded.expected), ('partial',25,45))
        legacy = '{"format":"PBS-session","version":1,"boards":[{"url":"pinterest.com/a/board","status":"done","new":4}]}'
        back = load_session(legacy)[0]
        self.assertEqual((back.discovered, back.expected, back.new), (0,0,4))


class LanguageTests(unittest.TestCase):
    def tearDown(self):
        set_language('fa')

    def test_english_labels_and_dynamic_messages(self):
        set_language('en')
        self.assertEqual(tr('کتابخانه رسانه‌ها'), 'Library')
        self.assertEqual(tr('نیازمند بررسی'), 'Needs review')
        self.assertIn('45', tr('45 بورد معتبر شناسایی شد · می‌توانید مستقیم دانلود کنید یا به صف اضافه کنید.'))
        self.assertEqual(tr('PinHarbor'), 'PinHarbor')

    def test_default_persian_and_invalid_code(self):
        set_language('fa')
        self.assertEqual(tr('دانلود از لینک‌ها'), 'دانلود از لینک‌ها')
        set_language('bogus')
        self.assertEqual(language(), 'fa')


if __name__ == '__main__':
    unittest.main()
