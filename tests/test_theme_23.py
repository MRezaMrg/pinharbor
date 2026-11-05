"""Tests for font fallback, burgundy glass design, and safe upgrade payload."""
from pathlib import Path
import unittest

from ui_theme import STYLE_SHEET, PALETTE, choose_font, available_fonts
from upgrade_existing import APP_FILES
from release_manifest import SOURCE_FILES

ROOT = Path(__file__).resolve().parents[1]


class FontFallbackTests(unittest.TestCase):
    def test_vazirmatn_wins_when_installed(self):
        self.assertEqual(choose_font(["Tahoma", "Vazirmatn", "Segoe UI"]), "Vazirmatn")

    def test_user_preference_wins(self):
        self.assertEqual(choose_font(["Tahoma", "Vazirmatn"], "Tahoma"), "Tahoma")

    def test_missing_choice_recovers_without_missing_font(self):
        self.assertEqual(choose_font(["Noto Sans Arabic", "Tahoma"], "Missing Font"), "Noto Sans Arabic")

    def test_case_insensitive_family_selection(self):
        self.assertEqual(choose_font(["Vazirmatn"], "VAZIRMATN"), "Vazirmatn")

    def test_empty_database_fallback(self):
        self.assertEqual(choose_font([]), "Tahoma")

    def test_only_offer_installed_families(self):
        self.assertEqual(available_fonts(["Arial", "Verdana", "Vazirmatn"]), ["Vazirmatn", "Arial"])


class VisualContracts(unittest.TestCase):
    def test_color_palette_is_single_source_of_truth(self):
        self.assertEqual(PALETTE["burgundy"], "#721F43")
        self.assertEqual(PALETTE["rose"], "#F0B6CB")
        self.assertEqual(PALETTE["black"], "#120A11")

    def test_glass_has_partial_opacity_and_keyboard_focus(self):
        self.assertIn('QFrame#panel', STYLE_SHEET)
        self.assertIn('rgba(72, 35, 58, 176)', STYLE_SHEET)
        self.assertIn('QFrame#hero', STYLE_SHEET)
        self.assertIn('QPushButton:focus', STYLE_SHEET)
        self.assertIn('QLineEdit:focus', STYLE_SHEET)
        self.assertIn('QPushButton:disabled', STYLE_SHEET)
        self.assertIn('QScrollBar:vertical', STYLE_SHEET)

    def test_no_previous_teal_color_left_in_gui(self):
        src = (ROOT / 'pinterest_studio.py').read_text(encoding='utf-8')
        for previous in ('#6DDCD0', '#64D8CF', '#73DED5', '#7ADBE5'):
            self.assertNotIn(previous, src + STYLE_SHEET)
        self.assertIn('AmbientCanvas', src)
        self.assertIn('font_panel, font_layout', src)

    def test_font_files_not_bundled_and_not_required(self):
        self.assertFalse(any(p.suffix.lower() in ('.ttf', '.otf', '.woff', '.woff2') for p in ROOT.rglob('*')))
        self.assertIn('ui_theme.py', APP_FILES)
        self.assertIn('tests/test_theme_23.py', SOURCE_FILES)
        self.assertNotIn('tests/test_theme_23.py', APP_FILES)


if __name__ == '__main__':
    unittest.main()


def _luminance(hex_color: str) -> float:
    components = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in components]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class ContrastTests(unittest.TestCase):
    def test_main_text_aa(self):
        self.assertGreaterEqual(_contrast(PALETTE['text'], PALETTE['ink']), 4.5)

    def test_muted_text_aa(self):
        self.assertGreaterEqual(_contrast(PALETTE['muted'], PALETTE['black']), 4.5)

    def test_rose_on_black_aa(self):
        self.assertGreaterEqual(_contrast(PALETTE['rose'], PALETTE['black']), 4.5)
