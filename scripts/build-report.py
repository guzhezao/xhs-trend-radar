#!/usr/bin/env python3
"""Validate REPORT_DATA and build a self-contained HTML report."""

from __future__ import annotations

import html
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import parse_qs, urlparse


def fail(message: str) -> None:
    raise ValueError(message)


def require(mapping: dict, key: str, expected_type, path: str):
    value = mapping.get(key)
    if not isinstance(value, expected_type):
        names = getattr(expected_type, "__name__", str(expected_type))
        fail(f"{path}.{key} 必须是 {names}")
    return value


def require_number(mapping: dict, key: str, path: str):
    value = mapping.get(key)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        fail(f"{path}.{key} 必须是数字")
    if value < 0:
        fail(f"{path}.{key} 不能是负数")
    return value


def validate_url(value: str, path: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {
        "xiaohongshu.com",
        "www.xiaohongshu.com",
    }:
        fail(f"{path} 必须是 https://www.xiaohongshu.com 链接")
    if not re.fullmatch(r"/explore/[A-Za-z0-9]+", parsed.path):
        fail(f"{path} 必须使用 /explore/<note_id> 格式")
    token = parse_qs(parsed.query).get("xsec_token", [""])[0]
    if len(token) < 8 or token.startswith("<"):
        fail(f"{path} 缺少搜索页原样提供的 xsec_token")


def validate(data: object) -> dict:
    if not isinstance(data, dict):
        fail("data.json 顶层必须是对象")

    keyword = require(data, "keyword", str, "data")
    if not keyword.strip():
        fail("data.keyword 不能为空")
    require(data, "captured_at", str, "data")
    require(data, "range", str, "data")
    require(data, "sort_note", str, "data")
    require(data, "lede", str, "data")
    kpi = require(data, "kpi", dict, "data")
    require_number(kpi, "max_like", "data.kpi")
    require(kpi, "max_like_note", str, "data.kpi")
    ratio = kpi.get("max_sl_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, (str, int, float)):
        fail("data.kpi.max_sl_ratio 必须是字符串或数字")
    require(kpi, "max_sl_note", str, "data.kpi")
    require_number(kpi, "newest_days", "data.kpi")
    require(kpi, "newest_note", str, "data.kpi")
    require_number(kpi, "window_open", "data.kpi")

    drive_dist = require(data, "drive_dist", dict, "data")
    for key in ("practical", "info", "emotion", "unknown"):
        value = require(drive_dist, key, int, "data.drive_dist")
        if isinstance(value, bool) or value < 0:
            fail(f"data.drive_dist.{key} 必须是非负整数")
    groups = require(data, "groups", dict, "data")
    for key in ("now", "plan"):
        items = require(groups, key, list, "data.groups")
        if not all(isinstance(item, str) for item in items):
            fail(f"data.groups.{key} 的每一项都必须是字符串")
    require(groups, "ref", str, "data.groups")

    target = require(data, "target", int, "data")
    if isinstance(target, bool) or not 1 <= target <= 20:
        fail("data.target 必须是 1 到 20 的整数")

    notes = require(data, "notes", list, "data")
    if not notes:
        fail("data.notes 不能为空")
    if len(notes) > target:
        fail("data.notes 数量不能超过 data.target")

    for index, note in enumerate(notes):
        path = f"data.notes[{index}]"
        if not isinstance(note, dict):
            fail(f"{path} 必须是对象")
        status = require(note, "status", str, path)
        if status not in {"verified", "failed"}:
            fail(f"{path}.status 只能是 verified 或 failed")
        require(note, "title", str, path)
        require(note, "author", str, path)
        if not note["title"].strip() or not note["author"].strip():
            fail(f"{path}.title 与 author 不能为空")
        require_number(note, "like", path)

        if status == "verified":
            require(note, "publish_date", str, path)
            require_number(note, "days_ago", path)
            require_number(note, "save", path)
            require_number(note, "comment", path)
            url = require(note, "url", str, path)
            validate_url(url, f"{path}.url")
            require(note, "judge", dict, path)
        else:
            reason = require(note, "fail_reason", str, path)
            if not reason.strip():
                fail(f"{path}.fail_reason 不能为空")

    if sum(drive_dist.values()) != len(notes):
        fail("data.drive_dist 四项之和必须等于 notes 数量")
    verified_count = sum(note["status"] == "verified" for note in notes)
    if kpi["window_open"] > verified_count:
        fail("data.kpi.window_open 不能超过已验证笔记数")
    return data


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: build-report.py <data.json> <out.html>", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent.parent
    lib_path = root / "assets" / "chart.umd.min.js"
    shell_path = root / "assets" / "report-shell.html"
    data_path = Path(sys.argv[1]).expanduser().resolve()
    out_path = Path(sys.argv[2]).expanduser().resolve()

    if data_path == out_path:
        fail("输入 JSON 与输出 HTML 不能是同一个文件")
    if not data_path.is_file():
        fail(f"找不到数据文件: {data_path}")
    if out_path.suffix.lower() != ".html":
        fail("输出文件扩展名必须是 .html")

    data = validate(json.loads(data_path.read_text(encoding="utf-8")))
    libjs = lib_path.read_text(encoding="utf-8")
    report_shell = shell_path.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = (
        payload.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    title = html.escape(data["keyword"] + " · 小红书热点报告", quote=True)

    for marker in ("__CHARTJS__", "__TITLE__", "__REPORT_DATA__"):
        if report_shell.count(marker) != 1:
            fail(f"模板占位符 {marker} 数量异常")
    rendered = report_shell.replace("__CHARTJS__", libjs)
    rendered = rendered.replace("__TITLE__", title)
    rendered = rendered.replace("__REPORT_DATA__", payload)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=out_path.parent, delete=False, suffix=".tmp"
        ) as temp:
            temp.write(rendered)
            temp_name = temp.name
        os.replace(temp_name, out_path)
        temp_name = None
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)

    print(f"已生成 {out_path}（{len(rendered)} 字节，{len(data['notes'])} 条）")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"生成失败: {exc}", file=sys.stderr)
        raise SystemExit(1)
