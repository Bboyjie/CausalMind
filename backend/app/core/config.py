from __future__ import annotations

import os
from pathlib import Path


def _bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "t"}


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_ENABLED = _bool(os.getenv("LLM_ENABLED", "true"), default=True)

HUEY_DB_PATH = os.getenv("HUEY_DB_PATH", str(DATA_DIR / "huey.db"))

CRAWLER_REPO_PATH = os.getenv("CRAWLER_REPO_PATH", str(PROJECT_ROOT.parent / "external" / "MediaCrawler"))
CRAWLER_PLATFORMS = [p.strip() for p in os.getenv("CRAWLER_PLATFORMS", "xhs,zhihu").split(",") if p.strip()]
CRAWLER_LOGIN_TYPE = os.getenv("CRAWLER_LOGIN_TYPE", "qrcode")
CRAWLER_HEADLESS = _bool(os.getenv("CRAWLER_HEADLESS", "false"), default=False)
CRAWLER_GET_COMMENT = _bool(os.getenv("CRAWLER_GET_COMMENT", "true"), default=True)
CRAWLER_MAX_NOTES = int(os.getenv("CRAWLER_MAX_NOTES", "30"))
CRAWLER_CONCURRENCY = int(os.getenv("CRAWLER_CONCURRENCY", "1"))
CRAWLER_ENABLED = _bool(os.getenv("CRAWLER_ENABLED", "true"), default=True)
