import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import studio_core


class EngineModeTests(TestCase):
    def test_python_invocation(self):
        with patch.object(studio_core.sys, "frozen", False, create=True):
            self.assertEqual(studio_core.engine_prefix(), [sys.executable, "-m", "gallery_dl"])

    def test_frozen_invocation(self):
        with patch.object(studio_core.sys, "frozen", True, create=True):
            self.assertEqual(studio_core.engine_prefix(), [sys.executable, "--engine"])
            self.assertEqual(studio_core.default_output_directory(), Path(sys.executable).resolve().parent)
