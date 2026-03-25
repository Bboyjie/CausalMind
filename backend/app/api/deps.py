from __future__ import annotations

import base64
import json
import urllib.parse
from typing import Any

from fastapi import Header, HTTPException
from pydantic import BaseModel


class ProviderProxy(BaseModel):
    id: str = ""
    name: str = ""
    baseUrl: str = ""
    apiKey: str = ""
    defaultModel: str = ""


class StageAssignmentsProxy(BaseModel):
    collection: str = ""
    audit: str = ""
    sandbox: str = ""
    worldline: str = ""


class CrawlerPlatformConfig(BaseModel):
    name: str
    max_notes: int = 50
    get_comments: bool = False
    max_comments_count_singlenotes: int = 10


class ExtractionConfig(BaseModel):
    chunk_size: int = 12
    chunk_overlap: int = 0
    max_chunk_tokens: int = 0


class WolongConfig(BaseModel):
    providers: list[ProviderProxy] = []
    stageAssignments: StageAssignmentsProxy = StageAssignmentsProxy()
    crawlerPlatforms: list[CrawlerPlatformConfig] = []
    extraction: ExtractionConfig = ExtractionConfig()

    def get_provider_for_stage(self, stage: str) -> ProviderProxy | None:
        """Returns the configured Provider for a given stage ('collection', 'audit', 'sandbox', 'worldline')"""
        target_id = getattr(self.stageAssignments, stage, None)
        if not target_id:
            return None
        for p in self.providers:
            if p.id == target_id:
                return p
        return None


def get_wolong_config(x_wolong_config: str | None = Header(None)) -> WolongConfig:
    """FastAPI Dependency to parse the Base64 encoded JSON config from the frontend."""
    if not x_wolong_config:
        return WolongConfig()
    try:
        decoded_bytes = base64.b64decode(x_wolong_config)
        decoded_string = urllib.parse.unquote(decoded_bytes.decode("utf-8"))
        data = json.loads(decoded_string)
        return WolongConfig(**data)
    except Exception as e:
        print(f"Failed to parse X-Wolong-Config header: {e}")
        return WolongConfig()
