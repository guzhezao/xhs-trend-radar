#!/usr/bin/env python3
"""Smoke tests for the cross-platform report builder."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build-report.py"


def synthetic_data() -> dict:
    return {
        "keyword": "合成测试 </title><script>bad()</script>",
        "captured_at": "2099-01-01 12:00",
        "range": "合成时间范围",
        "range_days": 30,
        "sort_note": "合成数据，不代表平台结果",
        "account": "测试账号定位",
        "target": 2,
        "lede": "这是<b>合成数据</b><script>bad()</script>，不含真实用户内容。",
        "kpi": {
            "max_like": 1200,
            "max_like_note": "合成笔记 A",
            "max_sl_ratio": "0.50",
            "max_sl_note": "第 01 条",
            "newest_days": 2,
            "newest_note": "合成笔记 A",
            "window_open": 1,
        },
        "drive_dist": {"practical": 1, "info": 0, "emotion": 0, "unknown": 1},
        "groups": {"now": ["合成笔记 A"], "plan": [], "ref": "合成兜底条目"},
        "notes": [
            {
                "status": "verified",
                "title": "合成笔记 A </script><script>bad()</script>",
                "author": "合成作者 A",
                "publish_date": "2098-12-30",
                "days_ago": 2,
                "like": 1200,
                "save": 600,
                "comment": 30,
                "tags": ["合成标签"],
                "url": "https://www.xiaohongshu.com/explore/000000000000000000000001?xsec_token=synthetic-token-not-real&xsec_source=pc_search",
                "judge": {
                    "stage": "窗口开着",
                    "drive": "实用",
                    "barrier": "可直接做",
                    "relevance": "强相关",
                },
                "suggestion": "仅用于测试",
            },
            {
                "status": "failed",
                "title": "合成笔记 B",
                "author": "合成作者 B",
                "like": 300,
                "fail_reason": "合成失败原因",
                "judge": {},
            },
        ],
        "footer": {},
    }


class BuildReportTest(unittest.TestCase):
    def run_builder(self, data: dict):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        data_path = root / "synthetic.json"
        out_path = root / "report.html"
        data_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(BUILDER), str(data_path), str(out_path)],
            text=True,
            capture_output=True,
            check=False,
        )
        return temp, out_path, result

    def test_builds_offline_report_and_escapes_script_breakout(self):
        temp, out_path, result = self.run_builder(synthetic_data())
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = out_path.read_text(encoding="utf-8")
        self.assertNotIn("__REPORT_DATA__", rendered)
        self.assertNotIn("fonts.googleapis.com", rendered)
        self.assertNotIn("</title><script>bad()", rendered)
        self.assertNotIn("</script><script>bad()", rendered)
        self.assertIn("<\\/script><script>bad()", rendered)

    def test_rejects_verified_note_without_signed_url(self):
        data = synthetic_data()
        data["notes"][0]["url"] = "https://www.xiaohongshu.com/explore/000000000000000000000001"
        temp, out_path, result = self.run_builder(data)
        self.addCleanup(temp.cleanup)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(out_path.exists())
        self.assertIn("xsec_token", result.stderr)

    def test_unix_wrapper_delegates_to_python_builder(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        data_path = root / "synthetic.json"
        out_path = root / "report.html"
        data_path.write_text(json.dumps(synthetic_data(), ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / "build-report.sh"), str(data_path), str(out_path)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(out_path.is_file())


if __name__ == "__main__":
    unittest.main()
