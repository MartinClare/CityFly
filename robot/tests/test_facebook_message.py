"""Unit tests for Facebook teaser message formatting."""

from __future__ import annotations

import unittest

from hk_city.facebook_publish import (
    DEFAULT_FACEBOOK_MAX_PER_RUN,
    _is_legacy_boilerplate_caption,
    _max_per_run_from_env,
    build_teaser_message,
)


class FacebookMessageTests(unittest.TestCase):
    def test_build_teaser_uses_hook_and_invite(self) -> None:
        meta = {
            "headline": "將軍澳南新盤開售",
            "pillar": "property",
            "facebook": {"visual_thesis": "供應堆積，議價空間拉大。"},
        }
        msg = build_teaser_message(meta)
        self.assertIn("供應堆積", msg)
        self.assertIn("規劃圖之外", msg)
        self.assertLess(len(msg), 280)

    def test_legacy_caption_detected(self) -> None:
        old = "某題\n\n生意、投資觀察、建造，邊度有窗口？"
        self.assertTrue(_is_legacy_boilerplate_caption(old))
        self.assertFalse(_is_legacy_boilerplate_caption("編輯寫嘅短 hook\n\n如果新站救唔到個區，仲有邊樣先救到？"))

    def test_editor_caption_preserved(self) -> None:
        from hk_city.facebook_publish import _message

        custom = "自定義帖文\n\n如果新站救唔到個區，仲有邊樣先救到？"
        meta = {"facebook": {"caption": custom}}
        self.assertEqual(_message(meta), custom)

    def test_default_max_per_run(self) -> None:
        self.assertEqual(DEFAULT_FACEBOOK_MAX_PER_RUN, 2)


class FacebookEnvTests(unittest.TestCase):
    def test_max_per_run_env(self) -> None:
        import os

        key = "FACEBOOK_MAX_PER_RUN"
        prev = os.environ.get(key)
        try:
            os.environ.pop(key, None)
            self.assertEqual(_max_per_run_from_env(), 2)
            os.environ[key] = "0"
            self.assertEqual(_max_per_run_from_env(), 0)
            os.environ[key] = "5"
            self.assertEqual(_max_per_run_from_env(), 5)
        finally:
            if prev is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev


if __name__ == "__main__":
    unittest.main()
