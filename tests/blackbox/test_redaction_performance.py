"""Synthetic timeout regressions for long nonmatching log tokens."""
from pathlib import Path
import subprocess
import sys
import unittest

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / 'services/blackbox'
CHILD = '''
import sys
sys.path.insert(0, sys.argv[1])
from blackbox.redact import mask_secrets, mask_family_text
from blackbox.collector_events import scrub_text
name = sys.argv[2]
payload = 'A' * 131072
if name == 'mask_family_text':
    payload = chr(0x044f) + payload + chr(0x044f)
function = {'mask_secrets': mask_secrets, 'mask_family_text': mask_family_text,
            'scrub_text': scrub_text}[name]
assert function(payload) == payload
print('OK')
'''


class RedactionPerformanceRegressionTest(unittest.TestCase):
    def check_bounded(self, name):
        try:
            result = subprocess.run(
                [sys.executable, '-B', '-c', CHILD, str(PACKAGE_ROOT), name],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, timeout=5)
        except subprocess.TimeoutExpired:
            self.fail('%s exceeded 5 seconds on a synthetic 128 KiB token' % name)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertEqual(result.stdout.strip(), 'OK')

    def test_mask_secrets_large_nonmatching_token(self):
        self.check_bounded('mask_secrets')

    def test_scrub_text_large_nonmatching_token(self):
        self.check_bounded('scrub_text')

    def test_family_text_large_single_token(self):
        self.check_bounded('mask_family_text')


if __name__ == '__main__':
    unittest.main()
