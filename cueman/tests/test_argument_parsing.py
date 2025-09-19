from unittest.mock import MagicMock

sys.modules['cueadmin'] = MagicMock()
sys.modules['cueadmin.output'] = MagicMock()
sys.modules['cueadmin.util'] = MagicMock()
sys.modules['opencue'] = MagicMock()
sys.modules['opencue.api'] = MagicMock()
sys.modules['cueadmin.common'] = MagicMock()

import unittest
from unittest.mock import patch
import sys

import cueman.main as cueman_main

def build_parser():
    # Replicate parser construction from cueman_main.main
    import argparse
    parser = argparse.ArgumentParser(description="OpenCueman Job Management Tool",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    return parser

class TestArgumentParsing(unittest.TestCase):

    def test_flag_lf(self):
        with patch.object(sys, 'argv', ['cueman', '-lf', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_flag_lp(self):
        with patch.object(sys, 'argv', ['cueman', '-lp', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_flag_ll(self):
        with patch.object(sys, 'argv', ['cueman', '-ll', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_flag_info(self):
        with patch.object(sys, 'argv', ['cueman', '-info', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_flag_pause(self):
        with patch.object(sys, 'argv', ['cueman', '-pause', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_flag_resume(self):
        with patch.object(sys, 'argv', ['cueman', '-resume', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_flag_term(self):
        with patch.object(sys, 'argv', ['cueman', '-term', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_help_text(self):
        with patch.object(sys, 'argv', ['cueman', '-h']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_version_flag(self):
        with patch.object(sys, 'argv', ['cueman', '--version']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertEqual(cm.exception.code, 0)

    def test_invalid_flag(self):
        with patch.object(sys, 'argv', ['cueman', '--notaflag']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertNotEqual(cm.exception.code, 0)

    def test_missing_required_argument(self):
        with patch.object(sys, 'argv', ['cueman', '-lf']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertNotEqual(cm.exception.code, 0)

    def test_server_and_facility(self):
        with patch.object(sys, 'argv', ['cueman', '-server', 'host1', '-facility', 'FAC']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_combination_pause_resume_conflict(self):
        with patch.object(sys, 'argv', ['cueman', '-pause', 'job1', '-resume', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertEqual(cm.exception.code, 0)

    def test_default_values(self):
        with patch.object(sys, 'argv', ['cueman']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertEqual(cm.exception.code, 0)

    def test_malformed_arguments(self):
        with patch.object(sys, 'argv', ['cueman', '-server']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertNotEqual(cm.exception.code, 0)

    def test_flag_eat(self):
        with patch.object(sys, 'argv', ['cueman', '-eat', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_flag_kill(self):
        with patch.object(sys, 'argv', ['cueman', '-kill', 'job1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

    def test_flag_stagger_missing_args(self):
        with patch.object(sys, 'argv', ['cueman', '-stagger', 'job1', '1']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertNotEqual(cm.exception.code, 0)

    def test_flag_state_multiple(self):
        with patch.object(sys, 'argv', ['cueman', '-state', 'RUNNING', 'FAILED']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertNotEqual(cm.exception.code, 0)

    def test_flag_range_invalid(self):
        with patch.object(sys, 'argv', ['cueman', '-range', 'abc']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertNotEqual(cm.exception.code, 0)

    def test_flag_memory_invalid(self):
        with patch.object(sys, 'argv', ['cueman', '-memory', '10MB']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertNotEqual(cm.exception.code, 0)

    def test_flag_autoeaton_multiple(self):
        with patch.object(sys, 'argv', ['cueman', '-autoeaton', 'job1', 'job2']):
            with self.assertRaises(SystemExit) as cm:
                cueman_main.main(sys.argv)
            self.assertIn(cm.exception.code, [0, 1])

if __name__ == "__main__":
    unittest.main()