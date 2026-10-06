"""Default network budgets include sequential failover and OAuth refreshes.
HTTP phase timeouts and gateway locks are not end-to-end cancellation deadlines.
"""
import ast
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def tree(path):
    return ast.parse((ROOT / path).read_text(encoding="utf-8"))


def seconds(node):
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
        return float(node.args[0].args[1].value)
    raise AssertionError("Unknown timeout expression: " + ast.dump(node))


def defaults():
    config = tree("services/nas_jetson_nano-api/app/config.py")
    fields = {n.target.id: ast.literal_eval(n.value) for n in ast.walk(config)
              if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
              and n.target.id in ("talk_bot_llm_timeout", "talk_bot_image_timeout")}
    gateway = tree("services/llm-gateway/app/main.py")
    timeouts = {}
    for fn in gateway.body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        for call in ast.walk(fn):
            if isinstance(call, ast.Call):
                for kw in call.keywords:
                    if kw.arg == "timeout" and fn.name != "_local_available":
                        timeouts[fn.name] = seconds(kw.value)
    return fields, timeouts


class Hierarchy(unittest.TestCase):
    def test_every_default_provider_chain_fits_bot(self):
        bot, t = defaults()
        oauth = t["_gigachat_access_token"]
        giga = oauth + t["_call_gigachat_locked"]
        chains = {
            "giga": giga,
            "giga then deepseek fallback": giga + t["_call_deepseek"],
            "prefer-local probe then giga fallback": 2 + giga + t["_call_deepseek"],
            "deepseek": t["_call_deepseek"],
            "cloudru": t["_call_cloudru"],
            "local probe and generation": 2 + t["_call_ollama"],
        }
        for label, total in chains.items():
            with self.subTest(chain=label):
                self.assertGreater(bot["talk_bot_llm_timeout"], total)
        generation = 2 * oauth + t["_gigachat_image_locked"] + t["_gigachat_download_file"]
        edit = generation + oauth + t["_gigachat_upload_file"]
        self.assertGreater(bot["talk_bot_image_timeout"], generation)
        self.assertGreater(bot["talk_bot_image_timeout"], edit)

    @unittest.skipUnless(shutil.which("awk"), "awk unavailable")
    def test_curl_gate_catches_nontelegram_and_multiline(self):
        awk = ROOT / "scripts/quality/tg_curl_timeout.awk"
        script = "echo 'curl --verbose prose'\n# curl comment\ncurl -s https://example.test\ncurl -s --max-time 5 https://example.test\ncurl -s \\\n  -m 10 https://example.test\n"
        result = subprocess.run(["awk", "-f", str(awk)], input=script, text=True,
                                capture_output=True, check=True)
        self.assertEqual(result.stdout.count("BAD "), 1, result.stdout)
        self.assertIn("COUNT 3", result.stdout)

    @unittest.skipUnless(shutil.which("awk"), "awk unavailable")
    def test_curl_deadlines_are_per_invocation_and_ssh_is_checked(self):
        cases = [
            ("curl --max-time 5 URL; curl URL", 2, 1),
            ("ssh host 'curl URL'", 1, 1),
            ("ssh host 'curl --max-time 5 URL; curl URL'", 2, 1),
            ("echo 'curl --max-time 5 prose; curl prose'", 0, 0),
            ("curl --max-time 0 URL", 1, 1),
            ("curl --max-time=0.0 URL", 1, 1),
            ("curl -m0 URL", 1, 1),
            ("curl -m5 URL", 1, 0),
            ('result="$(curl URL)"', 1, 1),
        ]
        for source, calls, bad in cases:
            with self.subTest(source=source):
                result = subprocess.run(["awk", "-f", str(ROOT / "scripts/quality/tg_curl_timeout.awk")],
                                        input=source + "\n", text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout.count("BAD "), bad, result.stdout)
                self.assertIn("COUNT " + str(calls), result.stdout)


if __name__ == "__main__":
    unittest.main()
