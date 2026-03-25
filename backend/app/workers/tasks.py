from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.api.deps import CrawlerPlatformConfig, WolongConfig
from app.core.config import CRAWLER_ENABLED
from app.db.database import SessionLocal
from app.models.entities import (
    Case,
    CollectionTask,
    Evidence,
    Fact,
    FactAuditAlert,
    SandboxGraph,
    SearchStrategy,
    Whitepaper,
    Worldline,
    UserContext,
)
from app.services.crawler import (
    build_evidence_items,
    infer_item_kind,
    normalize_platform_name,
    parse_jsonl_files,
    run_media_crawler,
)
from app.services.llm import (
    generate_causal_graph,
    generate_core_elements,
    generate_final_whitepaper,
    generate_knowledge_cards,
    generate_search_keywords,
    generate_worldline_simulation,
)
from app.workers.huey_app import huey


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _update_task(db, task: CollectionTask, **kwargs) -> None:
    for key, value in kwargs.items():
        setattr(task, key, value)
    db.add(task)
    db.commit()


def _fallback_keywords(profile: str) -> list[str]:
    if not profile.strip():
        return ["就业 真实经验 失败教训", "岗位要求 薪资结构 机会门槛"]
    return [
        f"{profile} 真实经历",
        f"{profile} 失败原因",
        f"{profile} 薪资 与 门槛",
    ]


def _meta_path(case_id: str) -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "crawler" / case_id / "run_meta.json"


def _safe_write_meta(case_id: str, payload: dict[str, Any]) -> None:
    path = _meta_path(case_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _uniq_list(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = str(value).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _pick_first_text(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _item_parent_id(item: dict[str, Any]) -> str:
    candidates = ("note_id", "aweme_id", "video_id", "dynamic_id", "article_id", "post_id")
    for key in candidates:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _fallback_url_by_platform(platform: str, parent_id: str) -> str:
    if not parent_id:
        return ""
    pf = normalize_platform_name(platform)
    if pf == "xhs":
        return f"https://www.xiaohongshu.com/explore/{parent_id}"
    if pf == "dy":
        return f"https://www.douyin.com/video/{parent_id}"
    if pf == "zhihu":
        return f"https://www.zhihu.com/search?type=content&q={parent_id}"
    if pf == "wb":
        return f"https://s.weibo.com/weibo?q={parent_id}"
    if pf == "bili":
        return f"https://search.bilibili.com/all?keyword={parent_id}"
    if pf == "tieba":
        return f"https://tieba.baidu.com/f?kw={parent_id}"
    return ""


def _distribute_budget(total: int, slots: int) -> list[int]:
    slots = max(1, int(slots))
    total = max(0, int(total))
    if total == 0:
        return [0] * slots
    base = total // slots
    remainder = total % slots
    return [base + (1 if idx < remainder else 0) for idx in range(slots)]


def _estimate_tokens(text: str) -> int:
    compact = (text or "").strip()
    if not compact:
        return 1
    return max(1, len(compact) // 4)


def _build_evidence_chunks(
    evidence_payload: list[dict[str, Any]],
    chunk_size: int,
    chunk_overlap: int,
    max_chunk_tokens: int,
) -> list[list[dict[str, Any]]]:
    if not evidence_payload:
        return []

    chunk_size = max(1, min(int(chunk_size or 12), 200))
    chunk_overlap = max(0, int(chunk_overlap or 0))
    chunk_overlap = min(chunk_overlap, max(0, chunk_size - 1))
    max_chunk_tokens = max(0, int(max_chunk_tokens or 0))

    # Keep post + comments (same URL) together as much as possible.
    unit_order: list[str] = []
    unit_map: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_payload:
        raw_key = str(item.get("url") or "").strip()
        if not raw_key or raw_key == "#":
            raw_key = str(item.get("evidence_id") or "").strip() or "unknown"
        if raw_key not in unit_map:
            unit_map[raw_key] = []
            unit_order.append(raw_key)
        unit_map[raw_key].append(item)
    units = [unit_map[key] for key in unit_order]

    def _tokens(items: list[dict[str, Any]]) -> int:
        return sum(_estimate_tokens(str(item.get("content", ""))) for item in items)

    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_tokens = 0

    for unit in units:
        unit_len = len(unit)
        unit_tokens = _tokens(unit)

        # Split oversized logical units.
        if unit_len > chunk_size or (max_chunk_tokens > 0 and unit_tokens > max_chunk_tokens):
            if current:
                chunks.append(current)
                current = []
                current_tokens = 0

            start = 0
            while start < unit_len:
                sub: list[dict[str, Any]] = []
                sub_tokens = 0
                idx = start
                while idx < unit_len:
                    item = unit[idx]
                    token_cost = _estimate_tokens(str(item.get("content", "")))
                    if sub and (len(sub) >= chunk_size or (max_chunk_tokens > 0 and sub_tokens + token_cost > max_chunk_tokens)):
                        break
                    sub.append(item)
                    sub_tokens += token_cost
                    idx += 1
                    if len(sub) >= chunk_size:
                        break
                if not sub:
                    sub = [unit[start]]
                    idx = start + 1
                chunks.append(sub)
                if chunk_overlap > 0 and idx < unit_len:
                    start = max(start + 1, idx - chunk_overlap)
                else:
                    start = idx
            continue

        would_overflow_size = current and (len(current) + unit_len > chunk_size)
        would_overflow_tokens = max_chunk_tokens > 0 and current and (current_tokens + unit_tokens > max_chunk_tokens)
        if would_overflow_size or would_overflow_tokens:
            chunks.append(current)
            if chunk_overlap > 0:
                current = list(current[-chunk_overlap:])
                current_tokens = _tokens(current)
            else:
                current = []
                current_tokens = 0

        current.extend(unit)
        current_tokens += unit_tokens

    if current:
        chunks.append(current)
    return chunks


@huey.task()
def run_collection(case_id: str, config_data: dict) -> None:
    db = SessionLocal()
    try:
        config = WolongConfig(**config_data) if config_data else WolongConfig()
        collection_provider = config.get_provider_for_stage("collection")
        audit_provider = config.get_provider_for_stage("audit")
        sandbox_provider = config.get_provider_for_stage("sandbox")
        worldline_provider = config.get_provider_for_stage("worldline")

        task = db.scalar(select(CollectionTask).where(CollectionTask.case_id == case_id).order_by(CollectionTask.id.desc()))
        if not task:
            task = CollectionTask(case_id=case_id, status="RUNNING", progress=0)
            db.add(task)
            db.commit()

        _update_task(db, task, status="RUNNING", progress=8)

        strategy = db.scalar(
            select(SearchStrategy).where(SearchStrategy.case_id == case_id).order_by(SearchStrategy.id.desc()).limit(1)
        )
        case_row = db.get(Case, case_id)
        profile = case_row.profile if case_row else ""
        if strategy and strategy.keywords:
            keywords = strategy.keywords
        else:
            try:
                keywords = generate_search_keywords(profile, collection_provider) if collection_provider else _fallback_keywords(profile)
            except Exception:
                keywords = _fallback_keywords(profile)

        raw_items: list[dict] = []
        crawler_meta: dict[str, Any] = {
            "requested": {
                "keywords": [k for k in keywords if str(k).strip()],
                "platforms": [],
                "total_steps": 0,
                "extraction": {},
            },
            "steps": [],
            "observed": {
                "raw_items_total": 0,
                "post_items_total": 0,
                "comment_items_total": 0,
                "evidence_total": 0,
                "post_evidences_total": 0,
                "comment_evidences_total": 0,
            },
            "reconciliation": {},
        }
        extraction_cfg = config.extraction if getattr(config, "extraction", None) else None
        chunk_size_cfg = int(getattr(extraction_cfg, "chunk_size", 12) or 12)
        chunk_overlap_cfg = int(getattr(extraction_cfg, "chunk_overlap", 0) or 0)
        max_chunk_tokens_cfg = int(getattr(extraction_cfg, "max_chunk_tokens", 0) or 0)
        crawler_meta["requested"]["extraction"] = {
            "chunk_size": chunk_size_cfg,
            "chunk_overlap": chunk_overlap_cfg,
            "max_chunk_tokens": max_chunk_tokens_cfg,
        }
        if CRAWLER_ENABLED:
            crawler_platforms = config.crawlerPlatforms
            if not crawler_platforms:
                from app.core.config import CRAWLER_GET_COMMENT, CRAWLER_MAX_NOTES, CRAWLER_PLATFORMS

                fallback_platforms = CRAWLER_PLATFORMS or ["xhs", "zhihu"]
                crawler_platforms = [
                    CrawlerPlatformConfig(
                        name=name,
                        max_notes=CRAWLER_MAX_NOTES,
                        get_comments=CRAWLER_GET_COMMENT,
                        max_comments_count_singlenotes=10,
                    )
                    for name in fallback_platforms
                ]

            crawler_meta["requested"]["platforms"] = [
                {
                    "name": normalize_platform_name(p.name),
                    "max_notes": int(p.max_notes),
                    "get_comments": bool(p.get_comments),
                    "max_comments_count_singlenotes": int(p.max_comments_count_singlenotes),
                }
                for p in crawler_platforms
            ]
            active_keywords = [k.strip() for k in keywords if str(k).strip()]
            total_steps = max(1, len(crawler_platforms) * max(1, len(active_keywords)))
            crawler_meta["requested"]["total_steps"] = total_steps
            completed_steps = 0
            jsonl_offsets: dict[str, int] = {}
            for platform in crawler_platforms:
                platform_name = normalize_platform_name(platform.name)
                remaining_posts_budget = max(1, int(platform.max_notes))
                comment_count_by_post: dict[str, int] = defaultdict(int)
                keyword_caps = _distribute_budget(remaining_posts_budget, len(active_keywords))
                _update_task(db, task, current_platform=platform_name.upper())
                for keyword_idx, keyword in enumerate(active_keywords):
                    allocated_cap = keyword_caps[keyword_idx] if keyword_idx < len(keyword_caps) else 0
                    step_budget = min(remaining_posts_budget, max(0, int(allocated_cap)))
                    if remaining_posts_budget <= 0:
                        completed_steps += 1
                        crawler_meta["steps"].append(
                            {
                                "platform": platform_name,
                                "keyword": keyword,
                                "max_notes": int(platform.max_notes),
                                "allocated_cap": step_budget,
                                "max_notes_remaining": 0,
                                "get_comments": bool(platform.get_comments),
                                "max_comments_count_singlenotes": int(platform.max_comments_count_singlenotes),
                                "jsonl_files": 0,
                                "raw_items": 0,
                                "post_items": 0,
                                "comment_items": 0,
                                "skipped": "platform_max_notes_reached",
                            }
                        )
                        progress = 8 + int(30 * (completed_steps / total_steps))
                        _update_task(db, task, progress=progress)
                        continue
                    if step_budget <= 0:
                        completed_steps += 1
                        crawler_meta["steps"].append(
                            {
                                "platform": platform_name,
                                "keyword": keyword,
                                "max_notes": int(platform.max_notes),
                                "allocated_cap": 0,
                                "max_notes_remaining": remaining_posts_budget,
                                "get_comments": bool(platform.get_comments),
                                "max_comments_count_singlenotes": int(platform.max_comments_count_singlenotes),
                                "jsonl_files": 0,
                                "raw_items": 0,
                                "post_items": 0,
                                "comment_items": 0,
                                "skipped": "keyword_budget_zero",
                            }
                        )
                        progress = 8 + int(30 * (completed_steps / total_steps))
                        _update_task(db, task, progress=progress)
                        continue
                    try:
                        files = run_media_crawler(
                            keyword,
                            case_id,
                            platform_name,
                            step_budget,
                            platform.get_comments,
                            platform.max_comments_count_singlenotes,
                        )
                        parsed_items = parse_jsonl_files(files, jsonl_offsets)
                        selected_items: list[dict] = []
                        selected_post_ids: set[str] = set()
                        post_candidates: list[dict] = []
                        comment_candidates: list[dict] = []
                        for item in parsed_items:
                            if infer_item_kind(item) == "comment":
                                if platform.get_comments:
                                    comment_candidates.append(item)
                            else:
                                post_candidates.append(item)

                        added_posts = 0
                        added_comments = 0
                        for item in post_candidates:
                            if added_posts >= step_budget:
                                break
                            selected_items.append(item)
                            added_posts += 1
                            parent_id = _item_parent_id(item)
                            if parent_id:
                                selected_post_ids.add(parent_id)

                        if platform.get_comments and selected_post_ids:
                            for item in comment_candidates:
                                parent_id = _item_parent_id(item)
                                if not parent_id or parent_id not in selected_post_ids:
                                    continue
                                if comment_count_by_post[parent_id] >= int(platform.max_comments_count_singlenotes):
                                    continue
                                comment_count_by_post[parent_id] += 1
                                selected_items.append(item)
                                added_comments += 1

                        parsed_items = selected_items
                        raw_items.extend(parsed_items)
                        remaining_posts_budget = max(0, remaining_posts_budget - added_posts)
                        crawler_meta["steps"].append(
                            {
                                "platform": platform_name,
                                "keyword": keyword,
                                "max_notes": int(platform.max_notes),
                                "allocated_cap": step_budget,
                                "max_notes_remaining": remaining_posts_budget,
                                "get_comments": bool(platform.get_comments),
                                "max_comments_count_singlenotes": int(platform.max_comments_count_singlenotes),
                                "jsonl_files": len(files),
                                "raw_items": len(parsed_items),
                                "post_items": added_posts,
                                "comment_items": added_comments,
                            }
                        )
                    except Exception as e:
                        print(f"Crawler error on {platform_name} - '{keyword}': {e}")
                        crawler_meta["steps"].append(
                            {
                                "platform": platform_name,
                                "keyword": keyword,
                                "max_notes": int(platform.max_notes),
                                "allocated_cap": step_budget,
                                "max_notes_remaining": remaining_posts_budget,
                                "get_comments": bool(platform.get_comments),
                                "max_comments_count_singlenotes": int(platform.max_comments_count_singlenotes),
                                "jsonl_files": 0,
                                "raw_items": 0,
                                "post_items": 0,
                                "comment_items": 0,
                                "error": str(e),
                            }
                        )
                    completed_steps += 1
                    progress = 8 + int(30 * (completed_steps / total_steps))
                    _update_task(db, task, progress=progress)

        crawler_meta["observed"]["raw_items_total"] = len(raw_items)
        crawler_meta["observed"]["post_items_total"] = sum(int(step.get("post_items", 0) or 0) for step in crawler_meta["steps"])
        crawler_meta["observed"]["comment_items_total"] = sum(
            int(step.get("comment_items", 0) or 0) for step in crawler_meta["steps"]
        )
        requested_post_cap = sum(int(p.get("max_notes", 0) or 0) for p in crawler_meta["requested"].get("platforms", []))
        comment_toggle_respected = all(
            bool(step.get("get_comments", False)) or int(step.get("comment_items", 0) or 0) == 0
            for step in crawler_meta["steps"]
        )
        crawler_meta["reconciliation"] = {
            "requested_post_cap_total": requested_post_cap,
            "observed_posts_within_cap": crawler_meta["observed"]["post_items_total"] <= requested_post_cap if requested_post_cap else True,
            "comment_toggle_respected": comment_toggle_respected,
        }
        _safe_write_meta(case_id, crawler_meta)
        _update_task(db, task, progress=40, current_platform="DONE", filtering_status="PREPARING")

        for row in db.scalars(select(Evidence).where(Evidence.case_id == case_id)).all():
            db.delete(row)
        db.commit()

        seen_hashes: set[str] = set()
        filtered_ads = 0
        filtered_duplicates = 0
        filtered_emotional = 0
        valid_sources = 0
        comment_evidences = 0
        post_evidences = 0
        parent_url_map: dict[str, str] = {}
        url_fields = (
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
        )
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            platform = normalize_platform_name(str(item.get("__platform") or item.get("platform") or item.get("source") or "unknown"))
            parent_id = _item_parent_id(item)
            if not parent_id:
                continue
            found_url = _pick_first_text(item, url_fields)
            if not found_url:
                continue
            parent_url_map[f"{platform}:{parent_id}"] = found_url
        for item in raw_items:
            platform = item.get("__platform") or item.get("platform") or item.get("source") or "unknown"
            for evidence in build_evidence_items([item], platform):
                content = evidence["content"]
                content_hash = _hash_text(content)
                if content_hash in seen_hashes:
                    filtered_duplicates += 1
                    continue
                seen_hashes.add(content_hash)
                if "广告" in content or "推广" in content:
                    filtered_ads += 1
                    continue
                if "垃圾" in content or "吐槽" in content:
                    filtered_emotional += 1
                    continue
                valid_sources += 1
                kind = str(evidence.get("kind") or "post")
                if kind == "comment":
                    comment_evidences += 1
                else:
                    post_evidences += 1
                evidence_prefix = "c" if kind == "comment" else "doc"
                resolved_url = str(evidence.get("url") or "").strip()
                if not resolved_url or resolved_url == "#":
                    platform_name = normalize_platform_name(str(platform))
                    parent_id = _item_parent_id(item)
                    if parent_id:
                        resolved_url = parent_url_map.get(f"{platform_name}:{parent_id}", "")
                        if not resolved_url:
                            resolved_url = _fallback_url_by_platform(platform_name, parent_id)
                if not resolved_url:
                    resolved_url = "#"
                db.add(
                    Evidence(
                        evidence_id=f"{evidence_prefix}_{valid_sources:04d}_span_1",
                        case_id=case_id,
                        source_name=evidence["source_name"],
                        url=resolved_url,
                        content=evidence["content"],
                    )
                )
        if valid_sources == 0:
            valid_sources = 1
            post_evidences = 1
            db.add(
                Evidence(
                    evidence_id="doc_1_span_1",
                    case_id=case_id,
                    source_name="system_fallback",
                    url="#",
                    content=profile or "暂无可用外部证据，系统将以用户输入作为临时事实源。",
                )
            )
        db.commit()
        crawler_meta["observed"]["evidence_total"] = valid_sources
        crawler_meta["observed"]["post_evidences_total"] = post_evidences
        crawler_meta["observed"]["comment_evidences_total"] = comment_evidences
        _safe_write_meta(case_id, crawler_meta)
        _update_task(db, task, progress=55, filtering_status="PROCESSING")

        evidence_rows = db.scalars(select(Evidence).where(Evidence.case_id == case_id)).all()
        evidence_payload = [
            {
                "evidence_id": row.evidence_id,
                "content": row.content,
                "source": row.source_name,
                "url": row.url,
            }
            for row in evidence_rows
        ]

        for row in db.scalars(select(Fact).where(Fact.case_id == case_id)).all():
            db.delete(row)
        db.commit()

        valid_evidence_ids = {str(row.evidence_id) for row in evidence_rows}
        first_pass_cards: list[dict] = []
        if audit_provider and evidence_payload:
            chunks = _build_evidence_chunks(
                evidence_payload=evidence_payload,
                chunk_size=chunk_size_cfg,
                chunk_overlap=chunk_overlap_cfg,
                max_chunk_tokens=max_chunk_tokens_cfg,
            )
            crawler_meta["observed"]["extraction_chunks"] = len(chunks)
            for idx, chunk in enumerate(chunks, start=1):
                try:
                    cards = generate_knowledge_cards(chunk, audit_provider, user_initial_prompt=profile)
                    chunk_ids = [str(item.get("evidence_id", "")).strip() for item in chunk]
                    chunk_ids = [eid for eid in chunk_ids if eid in valid_evidence_ids]
                    for card in cards:
                        raw_ids = [str(x).strip() for x in card.get("evidence_ids", []) if str(x).strip()]
                        normalized_ids = [eid for eid in raw_ids if eid in valid_evidence_ids]
                        if not normalized_ids and chunk_ids:
                            normalized_ids = chunk_ids[:3]
                        card["evidence_ids"] = _uniq_list(normalized_ids)
                    first_pass_cards.extend(cards)
                except Exception as e:
                    print(f"Knowledge card extraction failed on chunk {idx}: {e}. chunk_size={len(chunk)}")
                    # Retry with single-item micro-batches to reduce complete chunk loss when one response is malformed.
                    for item in chunk:
                        try:
                            cards = generate_knowledge_cards([item], audit_provider, user_initial_prompt=profile)
                            single_id = str(item.get("evidence_id", "")).strip()
                            for card in cards:
                                raw_ids = [str(x).strip() for x in card.get("evidence_ids", []) if str(x).strip()]
                                normalized_ids = [eid for eid in raw_ids if eid in valid_evidence_ids]
                                if not normalized_ids and single_id in valid_evidence_ids:
                                    normalized_ids = [single_id]
                                card["evidence_ids"] = _uniq_list(normalized_ids)
                            first_pass_cards.extend(cards)
                        except Exception as single_err:
                            print(
                                f"Knowledge card extraction single-item fallback failed on chunk {idx}: "
                                f"evidence_id={item.get('evidence_id')}, err={single_err}"
                            )
                pct = int((idx / max(1, len(chunks))) * 100)
                _update_task(
                    db,
                    task,
                    filtering_progress=pct,
                    progress=55 + int((idx / max(1, len(chunks))) * 20),
                )

        knowledge_cards: list[dict] = first_pass_cards
        if audit_provider and len(first_pass_cards) > 1:
            merge_input = []
            first_pass_id_to_evidence: dict[str, list[str]] = {}
            for idx, card in enumerate(first_pass_cards, start=1):
                fp_id = f"kc_fp_{idx:04d}"
                first_pass_id_to_evidence[fp_id] = _uniq_list([str(x) for x in card.get("evidence_ids", [])])
                merge_input.append({"evidence_id": fp_id, "content": card.get("content", "")})
            try:
                merged_cards = generate_knowledge_cards(merge_input, audit_provider, user_initial_prompt=profile)
                expanded_cards: list[dict] = []
                for card in merged_cards:
                    refs = [str(x).strip() for x in card.get("evidence_ids", []) if str(x).strip()]
                    expanded_ids: list[str] = []
                    for ref in refs:
                        if ref in first_pass_id_to_evidence:
                            expanded_ids.extend(first_pass_id_to_evidence[ref])
                        elif ref in valid_evidence_ids:
                            expanded_ids.append(ref)
                    card["evidence_ids"] = _uniq_list([eid for eid in expanded_ids if eid in valid_evidence_ids])
                    expanded_cards.append(card)
                if expanded_cards:
                    knowledge_cards = expanded_cards
            except Exception as e:
                print(f"Knowledge card merge pass failed: {e}")

        if not knowledge_cards:
            knowledge_cards = [
                {
                    "id": "kc_001",
                    "content": profile or "用户尚未提供足够证据，当前仅能建立初始问题陈述。",
                    "domain": "市场反馈",
                    "logical_property": "ASSUMPTION",
                    "stance_warning": "证据不足",
                    "evidence_ids": [],
                }
            ]

        # Deduplicate noisy or repeated model cards before persistence.
        deduped_cards: list[dict] = []
        seen_content_hashes: set[str] = set()
        for card in knowledge_cards:
            content = str(card.get("content", "")).strip()
            if not content:
                continue
            content_hash = _hash_text(content)
            if content_hash in seen_content_hashes:
                continue
            seen_content_hashes.add(content_hash)
            deduped_cards.append(card)
        knowledge_cards = deduped_cards or knowledge_cards

        existing_fact_ids = {
            str(fid)
            for fid in db.scalars(select(Fact.fact_id).where(Fact.case_id == case_id)).all()
            if str(fid).strip()
        }
        used_fact_ids: set[str] = set(existing_fact_ids)
        processed_fact_ids: list[str] = []
        warning_by_fact_id: dict[str, str] = {}
        default_evidence_id = evidence_rows[0].evidence_id if evidence_rows else None
        for idx, card in enumerate(knowledge_cards, start=1):
            base_fact_id = str(card.get("id") or "").strip() or f"fact_{idx:03d}"
            fact_id = base_fact_id
            suffix = 2
            while fact_id in used_fact_ids:
                fact_id = f"{base_fact_id}_{suffix}"
                suffix += 1
            used_fact_ids.add(fact_id)
            fact_evidence_ids = [str(x).strip() for x in card.get("evidence_ids", []) if str(x).strip()]
            fact_evidence_ids = _uniq_list([eid for eid in fact_evidence_ids if eid in valid_evidence_ids])
            if not fact_evidence_ids and default_evidence_id:
                fact_evidence_ids = [default_evidence_id]
            processed_fact_ids.append(fact_id)
            if card.get("stance_warning"):
                warning_by_fact_id[fact_id] = str(card["stance_warning"])

            stmt = sqlite_insert(Fact).values(
                fact_id=fact_id,
                case_id=case_id,
                content=card.get("content", ""),
                type=card.get("logical_property", "FACT"),
                evidence_ids=fact_evidence_ids,
                counter_evidence=None,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["case_id", "fact_id"],
                set_={
                    "content": card.get("content", ""),
                    "type": card.get("logical_property", "FACT"),
                    "evidence_ids": fact_evidence_ids,
                    "counter_evidence": None,
                },
            )
            db.execute(stmt)

        fact_rows = (
            db.scalars(select(Fact).where(Fact.case_id == case_id, Fact.fact_id.in_(processed_fact_ids))).all()
            if processed_fact_ids
            else []
        )
        fact_row_ids = [row.id for row in fact_rows]
        if fact_row_ids:
            for alert in db.scalars(select(FactAuditAlert).where(FactAuditAlert.fact_row_id.in_(fact_row_ids))).all():
                db.delete(alert)

        fact_by_fact_id = {str(row.fact_id): row for row in fact_rows}
        for fact_id, warning in warning_by_fact_id.items():
            row = fact_by_fact_id.get(fact_id)
            if not row:
                continue
            db.add(
                FactAuditAlert(
                    fact_row_id=row.id,
                    type="BIAS",
                    message=warning,
                )
            )

        inserted_facts = len(processed_fact_ids)
        db.commit()

        _update_task(
            db,
            task,
            progress=80,
            filtering_status="COMPLETED",
            filtering_progress=100,
            extracted_facts=inserted_facts,
        )

        elements_graph: list[dict] = []
        if knowledge_cards and (audit_provider or sandbox_provider):
            element_provider = audit_provider or sandbox_provider
            try:
                elements_graph = generate_core_elements(knowledge_cards, element_provider)
            except Exception as e:
                print(f"Core element extraction failed: {e}")

        graph = {"nodes": [], "edges": [], "causal_topology": {}, "counterfactual_insight": ""}
        if elements_graph and sandbox_provider:
            try:
                graph = generate_causal_graph(elements_graph, sandbox_provider, user_initial_prompt=profile)
            except Exception as e:
                print(f"Causal graph generation failed: {e}")
        if not graph.get("nodes"):
            graph["nodes"] = [
                {
                    "id": f"n{idx+1}",
                    "name": str(card.get("content", ""))[:24] or f"变量{idx+1}",
                    "status": "variable",
                    "type": "objective",
                    "val": 0.5,
                }
                for idx, card in enumerate(knowledge_cards[:6])
            ]
            graph["edges"] = [
                {
                    "source": graph["nodes"][idx]["id"],
                    "target": graph["nodes"][idx + 1]["id"],
                    "polarity": "positive",
                    "desc": "关联推断",
                }
                for idx in range(max(0, len(graph["nodes"]) - 1))
            ]

        graph_row = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id))
        if graph_row:
            graph_row.nodes = graph.get("nodes", [])
            graph_row.edges = graph.get("edges", [])
        else:
            db.add(SandboxGraph(case_id=case_id, nodes=graph.get("nodes", []), edges=graph.get("edges", [])))
        db.commit()

        snapshot = {
            "profile": profile,
            "knowledge_cards": knowledge_cards,
            "elements_graph": elements_graph,
            "causal_graph_snapshot": graph,
        }

        worldline_result = {"timeline": [], "paths": [], "worldlines": []}
        ctx_row = db.scalar(select(UserContext).where(UserContext.case_id == case_id).limit(1))
        verified_status = ctx_row.context_payload if ctx_row else {}
        if worldline_provider and verified_status:
            try:
                worldline_result = generate_worldline_simulation(
                    user_initial_prompt=profile,
                    causal_graph_snapshot=snapshot.get("causal_graph_snapshot", {}),
                    user_verified_status=verified_status,
                    real_world_baselines={"confidence_scheme": "high_medium_low"},
                    provider=worldline_provider,
                )
            except Exception as e:
                print(f"Worldline simulation failed: {e}")

        if worldline_result.get("timeline") and worldline_result.get("paths"):
            wl_row = db.scalar(select(Worldline).where(Worldline.case_id == case_id))
            if wl_row:
                wl_row.timeline = worldline_result.get("timeline", [])
                wl_row.paths = worldline_result.get("paths", [])
            else:
                db.add(
                    Worldline(
                        case_id=case_id,
                        timeline=worldline_result.get("timeline", []),
                        paths=worldline_result.get("paths", []),
                    )
                )
            db.commit()

        whitepaper = {"main_conflict": "", "critical_warnings": [], "mvp_actions": [], "unknowns": []}
        if worldline_provider and worldline_result.get("paths"):
            try:
                whitepaper = generate_final_whitepaper(
                    system_deduction_snapshot={
                        **snapshot,
                        "worldline": worldline_result,
                    },
                    user_current_dilemma=profile,
                    provider=worldline_provider,
                )
            except Exception as e:
                print(f"Whitepaper generation failed: {e}")

        wp_row = db.scalar(select(Whitepaper).where(Whitepaper.case_id == case_id))
        if wp_row:
            wp_row.main_conflict = whitepaper.get("main_conflict", "")
            wp_row.critical_warnings = whitepaper.get("critical_warnings", [])
            wp_row.mvp_actions = whitepaper.get("mvp_actions", [])
            wp_row.unknowns = whitepaper.get("unknowns", [])
        else:
            db.add(
                Whitepaper(
                    case_id=case_id,
                    main_conflict=whitepaper.get("main_conflict", ""),
                    critical_warnings=whitepaper.get("critical_warnings", []),
                    mvp_actions=whitepaper.get("mvp_actions", []),
                    unknowns=whitepaper.get("unknowns", []),
                )
            )
        db.commit()

        crawler_meta["observed"]["filtered_ads"] = filtered_ads
        crawler_meta["observed"]["filtered_duplicates"] = filtered_duplicates
        crawler_meta["observed"]["filtered_emotional"] = filtered_emotional
        crawler_meta["observed"]["valid_sources"] = valid_sources
        crawler_meta["observed"]["extracted_facts"] = inserted_facts
        worldline_generated = bool(worldline_result.get("timeline") and worldline_result.get("paths"))
        whitepaper_generated = bool(whitepaper.get("main_conflict"))
        crawler_meta["model_outputs"] = {
            "elements_graph": elements_graph,
            "causal_topology": graph.get("causal_topology", {}),
            "counterfactual_insight": graph.get("counterfactual_insight", ""),
            "worldlines": worldline_result.get("worldlines", []),
            "worldline_model_generated": worldline_generated,
            "worldline_model": (worldline_provider.defaultModel if worldline_provider else ""),
            "worldline_generated_at": datetime.now(timezone.utc).isoformat() if worldline_generated else "",
            "contradiction_transformation": whitepaper.get("contradiction_transformation", {}),
            "whitepaper_model_generated": whitepaper_generated,
            "whitepaper_model": (worldline_provider.defaultModel if worldline_provider else ""),
            "whitepaper_generated_at": datetime.now(timezone.utc).isoformat() if whitepaper_generated else "",
        }
        _safe_write_meta(case_id, crawler_meta)

        _update_task(
            db,
            task,
            status="COMPLETED",
            progress=100,
            total_scraped=crawler_meta["observed"]["post_items_total"],
            filtered_ads=filtered_ads,
            filtered_duplicates=filtered_duplicates,
            filtered_emotional_venting=filtered_emotional,
            valid_sources=valid_sources,
            finished_at=datetime.now(timezone.utc),
        )
        case_row = db.get(Case, case_id)
        if case_row:
            case_row.status = "FACT_AUDIT"
            db.add(case_row)
            db.commit()
    finally:
        db.close()
