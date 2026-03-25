from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from app.core.config import (
    CRAWLER_CONCURRENCY,
    CRAWLER_HEADLESS,
    CRAWLER_LOGIN_TYPE,
    CRAWLER_REPO_PATH,
)


_PLATFORM_ALIASES: dict[str, str] = {
    "xhs": "xhs",
    "xiaohongshu": "xhs",
    "dy": "dy",
    "douyin": "dy",
    "ks": "ks",
    "kuaishou": "ks",
    "bili": "bili",
    "bilibili": "bili",
    "wb": "wb",
    "weibo": "wb",
    "tieba": "tieba",
    "zhihu": "zhihu",
}


def normalize_platform_name(name: str) -> str:
    return _PLATFORM_ALIASES.get((name or "").strip().lower(), (name or "").strip().lower())


def _sanitize_proxy_env(env: dict[str, str]) -> None:
    has_socksio = importlib.util.find_spec("socksio") is not None
    proxy_keys = ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy")
    for key in proxy_keys:
        value = env.get(key)
        if not value:
            continue
        lower = value.strip().lower()
        if lower.startswith("socks://"):
            if has_socksio:
                env[key] = "socks5://" + value.split("://", 1)[1]
            else:
                env.pop(key, None)
        elif lower.startswith("socks5://") and not has_socksio:
            env.pop(key, None)


def run_media_crawler(
    keyword: str,
    case_id: str,
    platform: str,
    max_notes: int,
    get_comments: bool,
    max_comments_count_singlenotes: int = 10,
) -> list[Path]:
    repo = Path(CRAWLER_REPO_PATH).resolve()
    if not repo.exists():
        raise FileNotFoundError(f"MediaCrawler repo not found at {repo}")

    platform_code = normalize_platform_name(platform)
    out_root = Path(__file__).resolve().parents[2] / "data" / "crawler" / case_id
    out_root.mkdir(parents=True, exist_ok=True)
    output_files: list[Path] = []
    platform_path = out_root / platform_code / "jsonl"
    before_files = set(platform_path.glob("*.jsonl")) if platform_path.exists() else set()
    start_ts = time.time()

    cmd = [
        sys.executable,
        str(repo / "main.py"),
        "--platform",
        platform_code,
        "--lt",
        CRAWLER_LOGIN_TYPE,
        "--type",
        "search",
        "--keywords",
        keyword,
        "--save_data_option",
        "jsonl",
        "--save_data_path",
        str(out_root),
        "--headless",
        "true" if CRAWLER_HEADLESS else "false",
        "--get_comment",
        "true" if get_comments else "false",
        "--max_comments_count_singlenotes",
        str(max(1, int(max_comments_count_singlenotes))),
        "--max_concurrency_num",
        str(CRAWLER_CONCURRENCY),
    ]
    
    env = os.environ.copy()
    env["CRAWLER_MAX_NOTES"] = str(max_notes)
    _sanitize_proxy_env(env)

    proc = subprocess.run(cmd, cwd=str(repo), check=False, env=env)
    if proc.returncode != 0:
        print(f"MediaCrawler exited with code {proc.returncode} on platform={platform_code}, keyword={keyword}")

    if platform_path.exists():
        after_files = set(platform_path.glob("*.jsonl"))
        new_files = sorted(path for path in after_files if path not in before_files)
        if not new_files and proc.returncode == 0:
            changed_files = sorted(path for path in after_files if path.stat().st_mtime >= start_ts - 1)
            if changed_files:
                new_files = changed_files
        output_files.extend(new_files)

    return output_files


def parse_jsonl_files(files: list[Path], file_offsets: dict[str, int] | None = None) -> list[dict]:
    items: list[dict] = []
    for file in files:
        try:
            platform = file.parts[-3] if len(file.parts) >= 3 else "unknown"
            offset_key = str(file.resolve())
            start_offset = 0
            if file_offsets is not None:
                start_offset = max(0, int(file_offsets.get(offset_key, 0)))
            with file.open("rb") as f:
                f.seek(start_offset)
                payload = f.read()
                if file_offsets is not None:
                    file_offsets[offset_key] = f.tell()
            for line in payload.decode("utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and "__platform" not in obj:
                        obj["__platform"] = platform
                    items.append(obj)
                except json.JSONDecodeError:
                    continue
        except FileNotFoundError:
            continue
    return items


def infer_item_kind(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return "post"
    comment_keys = ("comment_id", "root_comment_id", "parent_comment_id", "reply_comment_id")
    if any(item.get(key) for key in comment_keys):
        return "comment"
    obj_type = str(item.get("type", "")).lower()
    if "comment" in obj_type:
        return "comment"
    if item.get("note_id") and item.get("content") and not (
        item.get("title") or item.get("desc") or item.get("note_url") or item.get("url")
    ):
        return "comment"
    return "post"


def _pick_first_text(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def build_evidence_items(raw_items: list[dict], platform: str) -> list[dict]:
    evidences: list[dict] = []
    for item in raw_items:
        kind = infer_item_kind(item)
        title = _pick_first_text(item, ("title", "name", "subject"))
        body = _pick_first_text(item, ("content", "desc", "text", "summary"))
        url = _pick_first_text(
            item,
            (
                "note_url",
                "url",
                "link",
                "detail_url",
                "post_url",
                "article_url",
                "aweme_url",
                "video_url",
                "jump_url",
                "share_url",
            ),
        )
        text = (title + "\n" + body).strip() if (title and body) else (title or body)
        if not text:
            text = json.dumps(item, ensure_ascii=False)
        evidences.append(
            {
                "source_name": normalize_platform_name(platform),
                "url": url or "#",
                "content": text,
                "kind": kind,
            }
        )
    return evidences
