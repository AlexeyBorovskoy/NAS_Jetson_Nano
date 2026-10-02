"""CQ-18: host .env settings must reach the container explicitly.

Static inspection avoids importing services or reading real credentials.
Run directly (preflight/CI) or with pytest.
"""
import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker/compose"
# Container layout and operational capabilities are deliberately fixed here.
# Changing these requires matching mounts, image contents or an access review.
API_DEFAULTS = {
    "API_PORT": "Image command, published port and healthcheck are fixed at 8099.",
    "LOG_FILE": "Fixed destination inside the mounted log directory.",
    "REPORT_CMD": "Matches the single read-only script bind mount.",
    "BACKUP_CMD": "Legacy host path; forwarding cannot supply the missing script mount.",
    "RESTARTABLE_CONTAINERS": "Reviewed restart allowlist; not widened through host .env.",
    "TELEGRAM_STATE_FILE": "State stays inside the mounted log directory.",
    "DL_SSD_DIR": "aria2 container layout, paired with its downloads mount.",
    "DL_HDD_DIR": "aria2 container layout, paired with its downloads mount.",
    "DL_SSD_STAT_PATH": "Matches the read-only /dl/ssd bind mount.",
    "DL_HDD_STAT_PATH": "Matches the read-only /dl/hdd bind mount.",
    "DL_LEDGER_FILE": "Ledger stays inside the mounted log directory.",
    "TALK_ALERT_STATE_FILE": "Matches the read-only monitor state mount.",
}
GATEWAY_DEFAULTS = {}


def api_settings():
    tree = ast.parse((ROOT / "services/nas_jetson_nano-api/app/config.py").read_text(encoding="utf-8"))
    settings = next(node for node in tree.body
                    if isinstance(node, ast.ClassDef) and node.name == "Settings")
    return {node.target.id.upper() for node in settings.body
            if isinstance(node, ast.AnnAssign)}


def gateway_settings():
    tree = ast.parse((ROOT / "services/llm-gateway/app/main.py").read_text(encoding="utf-8"))
    return {node.args[0].value for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and ast.unparse(node.func) in ("os.getenv", "os.environ.get")
            and node.args and isinstance(node.args[0], ast.Constant)}


def compose_environment(service):
    text = (COMPOSE / ("docker-compose." + service + ".yml")).read_text(encoding="utf-8")
    # These single-service files use a mapping. Scope to environment, so a
    # similarly named key in labels/build/etc cannot hide a missing setting.
    block = text.split("    environment:\n", 1)[1]
    block = re.split(r"^    \S", block, maxsplit=1, flags=re.M)[0]
    return set(re.findall(r"^      ([A-Z][A-Z0-9_]*):", block, re.M))


def coverage_errors(settings, environment, defaults):
    return {
        "missing": settings - environment - defaults.keys(),
        "stale_defaults": defaults.keys() - settings,
        "redundant_defaults": defaults.keys() & environment,
        "unexplained_defaults": {key for key, reason in defaults.items() if not reason.strip()},
    }


class SettingsComposeTest(unittest.TestCase):
    def test_api_settings_are_explicit(self):
        errors = coverage_errors(api_settings(), compose_environment("nas_jetson_nano-api"), API_DEFAULTS)
        self.assertFalse(any(errors.values()), errors)

    def test_gateway_settings_are_explicit(self):
        errors = coverage_errors(gateway_settings(), compose_environment("llm-gateway"), GATEWAY_DEFAULTS)
        self.assertFalse(any(errors.values()), errors)

    def test_missing_image_timeout_is_detected(self):
        env = compose_environment("nas_jetson_nano-api") - {"TALK_BOT_IMAGE_TIMEOUT"}
        errors = coverage_errors(api_settings(), env, API_DEFAULTS)
        self.assertIn("TALK_BOT_IMAGE_TIMEOUT", errors["missing"])

    def test_new_setting_requires_a_decision(self):
        errors = coverage_errors(api_settings() | {"FUTURE_TIMEOUT"},
                                 compose_environment("nas_jetson_nano-api"), API_DEFAULTS)
        self.assertIn("FUTURE_TIMEOUT", errors["missing"])

    def test_forwarded_settings_reference_the_host_variable(self):
        aliases = {"API_LOG_LEVEL": "NAS_JETSON_NANO_API_LOG_LEVEL",
                   "JWT_SECRET": "NAS_JETSON_NANO_API_JWT_SECRET",
                   "JWT_TTL_HOURS": "NAS_JETSON_NANO_API_JWT_TTL_HOURS"}
        for service, settings, defaults in (
            ("nas_jetson_nano-api", api_settings(), API_DEFAULTS),
            ("llm-gateway", gateway_settings(), GATEWAY_DEFAULTS),
        ):
            text = (COMPOSE / ("docker-compose." + service + ".yml")).read_text(encoding="utf-8")
            fixed = {"EXPECTED_CONTAINERS", "LOCAL_SERVICES"} if service == "nas_jetson_nano-api" else set()
            for key in settings - defaults.keys() - fixed:
                source = aliases.get(key, key)
                pattern = r"(?m)^      " + key + r": \$\{" + source + r"(?::-[^}\n]*)?\}$"
                with self.subTest(service=service, setting=key):
                    self.assertRegex(text, pattern)


if __name__ == "__main__":
    unittest.main()
