"""Regression tests for article instruction-leak detection."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hk_city.article_leak import (  # noqa: E402
    assemble_article_markdown,
    looks_like_instruction_leak,
    looks_like_worksheet,
    parse_article_json,
)


CLEAN_OPENING = """# 觀塘工廈區再規劃

將舊工廈變成混合用途，唔係一句口號咁簡單。

## 規劃局點睇

規劃署上周公布諮詢文件，列明三個發展節點同預計人口承載。

## 街坊關心咩

交通同噪音係兩個最常見問題，區議會會再開會聽意見。

## 下一步

公眾諮詢會持續六星期，之後才會定稿。
"""


class ArticleLeakTests(unittest.TestCase):
    def test_rejects_english_planning(self) -> None:
        bad = "We need write Hong Kong Cantonese magazine piece about tech.\n\n# Title\n\nbody"
        self.assertTrue(looks_like_instruction_leak(bad))
        self.assertTrue(looks_like_worksheet(bad))

    def test_rejects_chinese_meta(self) -> None:
        bad = "用户想要一篇關於樓市的特稿，我需要仔細看一下要求。\n\n# 樓市\n\n正文"
        self.assertTrue(looks_like_instruction_leak(bad))

    def test_accepts_clean_magazine_copy(self) -> None:
        self.assertFalse(looks_like_instruction_leak(CLEAN_OPENING))
        self.assertFalse(looks_like_worksheet(CLEAN_OPENING))

    def test_worksheet_scaffold_two_heads(self) -> None:
        ws = "## 機會\n\nfoo\n\n## 窗口\n\nbar"
        self.assertTrue(looks_like_worksheet(ws))

    def test_assemble_markdown(self) -> None:
        md = assemble_article_markdown("標題", "一句 dek", "## 小標\n\n正文。")
        self.assertIn("# 標題", md)
        self.assertIn("一句 dek", md)
        self.assertIn("## 小標", md)

    def test_parse_article_json(self) -> None:
        payload = json.dumps({"title": "T", "dek": "D", "body": "正文"}, ensure_ascii=False)
        data = parse_article_json(payload)
        self.assertIsNotNone(data)
        self.assertEqual(data["title"], "T")


if __name__ == "__main__":
    unittest.main()
