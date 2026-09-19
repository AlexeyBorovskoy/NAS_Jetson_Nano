"""Unit tests for smart routing and image presets (no network, no secrets).

Run from repo root (Windows):
  python -m pytest tests/llm_gateway/test_smart_routing.py -q
or:
  python tests/llm_gateway/test_smart_routing.py
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GW = ROOT / "services" / "llm-gateway"
sys.path.insert(0, str(GW))


def _reload_main(env: dict):
    """Apply env and reimport app.main."""
    os.environ.update({k: str(v) for k, v in env.items()})
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    return importlib.import_module("app.main")


class TestSmartRouting(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]

    def test_simple_prompt_uses_lite_model(self):
        """Simple prompts should use GigaChat-2 (Lite)."""
        m = _reload_main({
            "LLM_PROVIDER": "gigachat",
            "GIGACHAT_MODEL": "GigaChat-2",
        })
        # _is_complex_prompt returns False for simple text
        self.assertFalse(m._is_complex_prompt("привет, как дела?"))
        self.assertFalse(m._is_complex_prompt("что приготовить из курицы?"))
        self.assertFalse(m._is_complex_prompt("расскажи анекдот"))

    def test_docker_prompt_uses_max_model(self):
        """Docker-related prompts should trigger Max model."""
        m = _reload_main({
            "LLM_PROVIDER": "gigachat",
            "GIGACHAT_MODEL": "GigaChat-2",
        })
        self.assertTrue(m._is_complex_prompt("docker container"))
        self.assertTrue(m._is_complex_prompt("docker compose down"))
        self.assertTrue(m._is_complex_prompt("container failed"))

    def test_error_prompt_uses_max_model(self):
        """Error-related prompts should trigger Max model."""
        m = _reload_main({
            "LLM_PROVIDER": "gigachat",
            "GIGACHAT_MODEL": "GigaChat-2",
        })
        # "error" is in _COMPLEX_PATTERNS
        self.assertTrue(m._is_complex_prompt("error 502"))
        self.assertTrue(m._is_complex_prompt("immich error"))
        self.assertTrue(m._is_complex_prompt("ошибк"))

    def test_diagnostics_prompt_uses_max_model(self):
        """Diagnostics prompts should trigger Max model."""
        m = _reload_main({
            "LLM_PROVIDER": "gigachat",
            "GIGACHAT_MODEL": "GigaChat-2",
        })
        # Patterns must match what's in _COMPLEX_PATTERNS (Cyrillic)
        self.assertTrue(m._is_complex_prompt("температур"))
        self.assertTrue(m._is_complex_prompt("бэкап"))
        self.assertTrue(m._is_complex_prompt("восстанови"))

    def test_health_exposes_smart_routing(self):
        """Health endpoint should expose smart routing config."""
        m = _reload_main({
            "LLM_PROVIDER": "gigachat",
            "GIGACHAT_BASE_URL": "https://api.giga.chat/v1",
            "GIGACHAT_MODEL": "GigaChat-2",
        })
        from fastapi.testclient import TestClient
        client = TestClient(m.app)
        h = client.get("/health").json()
        self.assertTrue(h["smart_routing_enabled"])
        self.assertEqual(h["gigachat_model"], "GigaChat-2")
        self.assertEqual(h["gigachat_model_complex"], "GigaChat-2-Max")


class TestImagePresets(unittest.TestCase):
    def test_new_presets_exist(self):
        """All new family presets should be present."""
        m = _reload_main({})
        presets = m.IMAGE_PRESETS
        expected_new = [
            "birthday_card",
            "family_collage",
            "child_drawing",
            "postcard",
            "meme",
        ]
        for preset in expected_new:
            self.assertIn(preset, presets, f"Missing preset: {preset}")
            self.assertIsInstance(presets[preset], str)
            self.assertGreater(len(presets[preset]), 0)

    def test_existing_presets_untouched(self):
        """Existing presets should remain unchanged."""
        m = _reload_main({})
        presets = m.IMAGE_PRESETS
        for existing in ["anime", "cartoon", "artistic"]:
            self.assertIn(existing, presets)

    def test_presets_have_descriptions(self):
        """All presets should have meaningful descriptions."""
        m = _reload_main({})
        for name, desc in m.IMAGE_PRESETS.items():
            self.assertGreater(len(desc), 20,
                               f"Preset '{name}' description too short")
            # Should contain style/activity keywords
            self.assertTrue(
                any(kw in desc.lower() for kw in ["нарисуй", "стиль", "по мотивам"]),
                f"Preset '{name}' lacks descriptive content"
            )


class TestSavePathRestriction(unittest.TestCase):
    """W0.1 — audit_new G01: save_path cannot escape IMAGE_OUTPUT_ROOT."""

    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)
        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                del sys.modules[key]

    def _normalize(self, p: Path) -> str:
        """Normalize path for cross-platform comparison."""
        return str(p).replace("\\", "/")

    def test_normal_filename_allowed(self):
        """Simple filename should be allowed."""
        m = _reload_main({})
        result = m._sanitize_save_path("photo.jpg")
        self.assertTrue(self._normalize(result).endswith("/photo.jpg"))

    def test_path_traversal_sanitized_by_name(self):
        """Path traversal is neutralized by .name — result is safe basename."""
        m = _reload_main({})
        for traversal in [
            "../../etc/passwd",
            "../../../data/llm_usage.json",
            "/etc/shadow",
        ]:
            result = m._sanitize_save_path(traversal)
            # .name extracts only the filename — traversal is neutralized
            self.assertEqual(result.name, "passwd" if "passwd" in traversal
                             else "llm_usage.json" if "llm_usage" in traversal
                             else "shadow")
            # Result must be under IMAGE_OUTPUT_ROOT
            try:
                result.relative_to(m._IMAGE_OUTPUT_ROOT.resolve())
            except ValueError:
                self.fail(f"Path {traversal} resolved outside IMAGE_OUTPUT_ROOT")

    def test_dot_dot_rejected(self):
        """'.' and '..' as names should be rejected (400 or 403)."""
        m = _reload_main({})
        from fastapi import HTTPException
        for name in [".", ".."]:
            with self.assertRaises(HTTPException) as ctx:
                m._sanitize_save_path(name)
            # 400 for ".", 403 for ".." (resolve fails relative_to) — both are safe
            self.assertIn(ctx.exception.status_code, (400, 403),
                          f"'{name}' should be 400 or 403, got {ctx.exception.status_code}")

    def test_empty_name_rejected(self):
        """Empty name should be rejected (400)."""
        m = _reload_main({})
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            m._sanitize_save_path("")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_null_byte_rejected(self):
        """Null bytes in name should be rejected."""
        m = _reload_main({})
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            m._sanitize_save_path("photo\x00.jpg")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_none_returns_empty_path(self):
        """None save_path should return empty Path (no save)."""
        m = _reload_main({})
        result = m._sanitize_save_path(None)
        self.assertEqual(result, Path(""))

    def test_output_root_is_fixed(self):
        """IMAGE_OUTPUT_ROOT should be /data/images by default."""
        m = _reload_main({})
        self.assertIn("data/images", self._normalize(m._IMAGE_OUTPUT_ROOT))

    def test_custom_output_root(self):
        """Custom IMAGE_OUTPUT_ROOT should be respected."""
        m = _reload_main({"IMAGE_OUTPUT_ROOT": "/custom/output"})
        self.assertEqual(self._normalize(m._IMAGE_OUTPUT_ROOT), "/custom/output")


if __name__ == "__main__":
    unittest.main()
