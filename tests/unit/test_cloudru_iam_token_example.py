#!/usr/bin/env python3
"""SH-1: the IAM response is data on stdin, never generated Python source."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SCRIPT = os.path.join(REPO, "scripts", "sber", "cloudru_iam_token_example.sh")
BASH = shutil.which("bash")


def bash_path(path):
    """Return a path understood by Git Bash and regular Unix bash."""
    path = os.path.abspath(path).replace("\\", "/")
    if len(path) >= 3 and path[1:3] == ":/":
        return "/%s/%s" % (path[0].lower(), path[3:])
    return path


@unittest.skipIf(BASH is None, "bash is unavailable")
class CloudRuIamTokenExample(unittest.TestCase):
    def test_server_response_cannot_become_python_source(self):
        tmp = tempfile.mkdtemp()
        try:
            bindir = os.path.join(tmp, "bin")
            os.makedirs(bindir)
            curl = os.path.join(bindir, "curl")
            with io.open(curl, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("#!/usr/bin/env bash\nprintf '%s' \"$STUB_RESPONSE\"\n")
            os.chmod(curl, 0o755)

            sentinel = os.path.join(tmp, "executed")
            injection = ("''';__import__('pathlib').Path(__import__('os').environ"
                         "['SH1_SENTINEL']).write_text('owned');raw='''")
            response = '{"access_token":"%s","expires_in":3600}' % injection
            env = dict(os.environ,
                       CLOUDRU_KEY_ID="test-key-id",
                       CLOUDRU_KEY_SECRET="test-key-secret",
                       SH1_SENTINEL=sentinel,
                       STUB_RESPONSE=response)

            command = [BASH, "-c", 'PATH="$1:$PATH"; export PATH; exec bash "$2"',
                       "sh1-test", bash_path(bindir), bash_path(SCRIPT)]

            completed = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(os.path.exists(sentinel), "server response executed as Python")
            self.assertIn("token_len: %d" % len(injection), completed.stdout)
            self.assertNotIn("test-key-secret", completed.stdout + completed.stderr)

            secret_body = "not-json-with-sensitive-response-body"
            env["STUB_RESPONSE"] = secret_body
            completed = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("non-json response: JSONDecodeError", completed.stdout)
            self.assertNotIn(secret_body, completed.stdout + completed.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=1))
