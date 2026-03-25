from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ProviderProxy, WolongConfig, get_wolong_config
from app.core.response import success
from app.db.database import get_db
from app.models.entities import (
    AuditElementCache,
    Case,
    CaseFeedback,
    CollectionTask,
    Evidence,
    Fact,
    FactAuditAlert,
    FactFeedback,
    SandboxGraph,
    SandboxIntervention,
    SearchStrategy,
    UserContext,
    Whitepaper,
    Worldline,
    WorldlineIntervention,
)
from app.schemas.dto import (
    CreateCaseRequest,
    FactFeedbackRequest,
    SandboxInterveneRequest,
    WorldlineInterveneRequest,
)
from app.services.crawler import normalize_platform_name
from app.services.llm import (
    generate_causal_graph,
    generate_core_elements,
    generate_final_whitepaper,
    generate_search_keywords,
    generate_system_variable_probe,
    generate_worldline_simulation,
)
from app.services.simulation import simulate_sandbox, simulate_worldline
from app.workers.tasks import run_collection

router = APIRouter()


def _utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _resolve_config(config: Any) -> WolongConfig:
    return config if isinstance(config, WolongConfig) else WolongConfig()


def _get_case_or_404(db: Session, case_id: str) -> Case:
    obj = db.get(Case, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="case not found")
    return obj


def _generate_case_id(db: Session) -> str:
    for _ in range(30):
        case_id = f"case_{random.randint(1000, 9999)}"
        if not db.get(Case, case_id):
            return case_id
    return f"case_{int(datetime.now(timezone.utc).timestamp())}"


def _derive_tags(profile: str) -> list[str]:
    if not profile:
        return []
    tokens = [t for t in re.split(r"[\s,，;；/|]+", profile) if t]
    return tokens[:3]


def _fallback_keywords(profile: str) -> list[str]:
    if not profile.strip():
        return ["真实经历 失败教训", "岗位门槛 机会结构", "成本 风险 边界条件"]
    return [
        f"{profile} 真实经历",
        f"{profile} 失败原因",
        f"{profile} 机会门槛",
    ]


def _history_status(db: Session, case_id: str) -> str:
    if db.scalar(select(Whitepaper.id).where(Whitepaper.case_id == case_id).limit(1)):
        return "WHITE_PAPER"
    if db.scalar(select(Worldline.id).where(Worldline.case_id == case_id).limit(1)):
        return "WORLDLINE_EVOLUTION"
    if db.scalar(select(SandboxGraph.id).where(SandboxGraph.case_id == case_id).limit(1)):
        return "CAUSAL_SANDBOX"
    if db.scalar(select(Fact.id).where(Fact.case_id == case_id).limit(1)):
        return "FACT_AUDIT"
    return "CREATED"


def _facts_payload(db: Session, case_id: str) -> list[dict]:
    facts = db.scalars(select(Fact).where(Fact.case_id == case_id).order_by(Fact.fact_id.asc())).all()
    payload = []
    for fact in facts:
        payload.append(
            {
                "id": fact.fact_id,
                "content": fact.content,
                "domain": "市场反馈",
                "logical_property": fact.type,
                "stance_warning": None,
                "evidence_ids": fact.evidence_ids,
            }
        )
    return payload


def _json_signature(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_source_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw or raw == "#" or raw.lower().startswith("javascript:"):
        return ""
    return raw if re.match(r"^https?://", raw, flags=re.IGNORECASE) else f"https://{raw}"


def _infer_parent_id_from_content(content: str) -> str:
    text = (content or "").strip()
    if not text:
        return ""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            for key in ("note_id", "aweme_id", "video_id", "dynamic_id", "article_id", "post_id"):
                value = obj.get(key)
                if value is None:
                    continue
                parent_id = str(value).strip()
                if parent_id:
                    return parent_id
    except Exception:
        pass
    return ""


def _fallback_post_url(platform: str, parent_id: str) -> str:
    if not parent_id:
        return ""
    pf = normalize_platform_name(platform)
    if pf == "xhs":
        return f"https://www.xiaohongshu.com/explore/{parent_id}"
    if pf == "dy":
        return f"https://www.douyin.com/video/{parent_id}"
    if pf == "zhihu":
        return f"https://www.zhihu.com/search?type=content&q={quote(parent_id)}"
    if pf == "wb":
        return f"https://s.weibo.com/weibo?q={quote(parent_id)}"
    if pf == "bili":
        return f"https://search.bilibili.com/all?keyword={quote(parent_id)}"
    if pf == "tieba":
        return f"https://tieba.baidu.com/f?kw={quote(parent_id)}"
    return ""


def _platform_search_url(platform: str, content: str) -> str:
    snippet = re.sub(r"\s+", " ", (content or "").strip())[:40]
    if not snippet:
        return ""
    q = quote(snippet)
    pf = normalize_platform_name(platform)
    if pf == "xhs":
        return f"https://www.xiaohongshu.com/search_result?keyword={q}"
    if pf == "zhihu":
        return f"https://www.zhihu.com/search?type=content&q={q}"
    if pf == "dy":
        return f"https://www.douyin.com/search/{q}"
    if pf == "wb":
        return f"https://s.weibo.com/weibo?q={q}"
    if pf == "bili":
        return f"https://search.bilibili.com/all?keyword={q}"
    if pf == "tieba":
        return f"https://tieba.baidu.com/f?kw={q}"
    return f"https://www.google.com/search?q={q}"


def _resolve_evidence_url(url: str, source_name: str, content: str) -> str:
    normalized = _normalize_source_url(url)
    if normalized:
        return normalized

    embedded_url = re.search(r"https?://[^\s\"'>]+", content or "")
    if embedded_url:
        normalized = _normalize_source_url(embedded_url.group(0))
        if normalized:
            return normalized

    parent_id = _infer_parent_id_from_content(content)
    fallback_post = _fallback_post_url(source_name, parent_id)
    if fallback_post:
        return fallback_post

    return _platform_search_url(source_name, content)


def _delete_case_rows(db: Session, case_id: str) -> None:
    fact_rows = db.scalars(select(Fact).where(Fact.case_id == case_id)).all()
    fact_row_ids = [row.id for row in fact_rows]
    for row in db.scalars(select(FactFeedback).where(FactFeedback.case_id == case_id)).all():
        db.delete(row)
    if fact_row_ids:
        for alert in db.scalars(select(FactAuditAlert).where(FactAuditAlert.fact_row_id.in_(fact_row_ids))).all():
            db.delete(alert)
    for row in fact_rows:
        db.delete(row)
    for row in db.scalars(select(Evidence).where(Evidence.case_id == case_id)).all():
        db.delete(row)
    for row in db.scalars(select(CollectionTask).where(CollectionTask.case_id == case_id)).all():
        db.delete(row)
    for row in db.scalars(select(SearchStrategy).where(SearchStrategy.case_id == case_id)).all():
        db.delete(row)
    for row in db.scalars(select(SandboxIntervention).where(SandboxIntervention.case_id == case_id)).all():
        db.delete(row)
    for row in db.scalars(select(WorldlineIntervention).where(WorldlineIntervention.case_id == case_id)).all():
        db.delete(row)
    row = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    if row:
        db.delete(row)
    row = db.scalar(select(UserContext).where(UserContext.case_id == case_id).limit(1))
    if row:
        db.delete(row)
    row = db.scalar(select(Worldline).where(Worldline.case_id == case_id).limit(1))
    if row:
        db.delete(row)
    row = db.scalar(select(Whitepaper).where(Whitepaper.case_id == case_id).limit(1))
    if row:
        db.delete(row)
    row = db.scalar(select(AuditElementCache).where(AuditElementCache.case_id == case_id).limit(1))
    if row:
        db.delete(row)
    for row in db.scalars(select(CaseFeedback).where(CaseFeedback.case_id == case_id)).all():
        db.delete(row)

    case_row = db.get(Case, case_id)
    if case_row:
        db.delete(case_row)
    db.commit()


def _delete_case_files(case_id: str) -> None:
    crawler_dir = Path(__file__).resolve().parents[2] / "data" / "crawler" / case_id
    if crawler_dir.exists() and crawler_dir.is_dir():
        shutil.rmtree(crawler_dir, ignore_errors=True)


def _worldline_baselines() -> dict:
    return {
        "confidence_scheme": "high_medium_low",
        "constraints": [
            "禁止输出伪精确概率",
            "高冲突证据时优先提示补充信息",
        ],
    }


def _heuristic_graph_from_cards(cards: list[dict]) -> dict:
    nodes = []
    edges = []
    for idx, card in enumerate(cards[:8], start=1):
        text = str(card.get("content", "")).strip()[:32] or f"变量{idx}"
        nodes.append(
            {
                "id": f"n{idx}",
                "name": text,
                "status": "variable",
                "type": "objective",
                "val": 0.5,
            }
        )
    for idx in range(1, len(nodes)):
        edges.append(
            {
                "source": nodes[idx - 1]["id"],
                "target": nodes[idx]["id"],
                "polarity": "positive",
                "desc": "经验链路推断",
            }
        )
    return {"nodes": nodes, "edges": edges}


def _fallback_probe_questions(nodes: list[dict]) -> list[dict]:
    questions = []
    for node in nodes[:4]:
        name = str(node.get("name", "关键变量"))
        questions.append(
            {
                "node_id": str(node.get("id", "unknown")),
                "probe_question": f"当前在“{name}”上的真实状态是什么？请尽量量化描述。",
                "why_it_matters": "该变量是世界线收敛的关键初始存量，缺失会导致推演偏差。",
            }
        )
    return questions


def _fallback_worldline() -> dict:
    return {
        "timeline": ["T+6个月", "T+1年", "T+3年"],
        "paths": [
            {
                "type": "baseline",
                "color": "info",
                "nodes": [
                    {"time": "T+6个月", "desc": "维持当前策略，缓慢推进", "triggers": ["未引入新干预"]},
                    {"time": "T+1年", "desc": "结构改善有限，仍需补充关键变量", "triggers": ["变量信息不足"]},
                ],
            }
        ],
    }


def _fallback_whitepaper(profile: str) -> dict:
    return {
        "main_conflict": profile[:80] or "当前信息不足，无法准确定位主要矛盾。",
        "critical_warnings": ["证据链和变量状态不足时，不应进行高强度下注。"],
        "mvp_actions": [
            {
                "id": "A1",
                "title": "补全关键变量并验证",
                "objective": "先完成变量探针问答，再做世界线推演。",
                "cost": "2天",
                "status": "pending",
            }
        ],
        "unknowns": ["缺少关键变量的当前状态。"],
        "contradiction_transformation": {},
    }


def _collection_meta(case_id: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "data" / "crawler" / case_id / "run_meta.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_collection_meta(case_id: str, patch: dict[str, Any]) -> None:
    path = Path(__file__).resolve().parents[2] / "data" / "crawler" / case_id / "run_meta.json"
    base = _collection_meta(case_id)

    def _merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        merged = dict(left)
        for key, value in right.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = _merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    merged = _merge(base if isinstance(base, dict) else {}, patch if isinstance(patch, dict) else {})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")


def _norm_text_key(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").strip().lower())


def _bind_fact_ids(bound_facts: list[str], fact_by_id: dict[str, dict[str, Any]]) -> list[str]:
    if not bound_facts:
        return []
    content_index = {fid: _norm_text_key(str(f.get("content", ""))) for fid, f in fact_by_id.items()}
    result: list[str] = []
    for text in bound_facts:
        raw = str(text or "").strip()
        if not raw:
            continue
        if raw in fact_by_id and raw not in result:
            result.append(raw)
            continue
        key = _norm_text_key(raw)
        if not key:
            continue
        matched_id = None
        for fid, content_key in content_index.items():
            if key == content_key or key in content_key or content_key in key:
                matched_id = fid
                break
        if not matched_id:
            best_score = 0.0
            best_id = None
            for fid, content_key in content_index.items():
                if not content_key:
                    continue
                score = SequenceMatcher(None, key, content_key).ratio()
                if score > best_score:
                    best_score = score
                    best_id = fid
            if best_id and best_score >= 0.58:
                matched_id = best_id
        if matched_id and matched_id not in result:
            result.append(matched_id)
    return result


def _chunk_items(items: list[dict], chunk_size: int, overlap: int = 0) -> list[list[dict]]:
    if not items:
        return []
    chunk_size = max(1, min(int(chunk_size or 1), 200))
    overlap = max(0, int(overlap or 0))
    overlap = min(overlap, max(0, chunk_size - 1))
    chunks: list[list[dict]] = []
    start = 0
    while start < len(items):
        end = min(len(items), start + chunk_size)
        chunk = items[start:end]
        if chunk:
            chunks.append(chunk)
        if end >= len(items):
            break
        if overlap > 0:
            start = end - overlap
        else:
            start = end
    return chunks


@router.post("/cases")
def create_case(payload: CreateCaseRequest, db: Session = Depends(get_db)):
    case_id = _generate_case_id(db)
    case = Case(id=case_id, profile=payload.profile, status="CREATED")
    db.add(case)
    db.commit()
    db.refresh(case)
    return success(
        data={"id": case.id, "profile": case.profile, "status": case.status, "created_at": _utc_iso(case.created_at)},
        message="success",
    )


@router.get("/cases/history")
def list_cases_history(db: Session = Depends(get_db)):
    cases = db.scalars(select(Case).order_by(Case.created_at.desc())).all()
    data = []
    for case in cases:
        data.append(
            {
                "id": case.id,
                "title": case.profile or case.id,
                "status": _history_status(db, case.id),
                "created_at": _utc_iso(case.created_at),
                "tags": _derive_tags(case.profile or ""),
            }
        )
    return success(data=data, message=None)


@router.post("/llm/test")
def test_llm_connection(provider: ProviderProxy):
    from app.services.llm import _client

    try:
        client = _client(provider)
        resp = client.chat.completions.create(
            model=provider.defaultModel or "gpt-4o",
            messages=[{"role": "user", "content": "Return the word OK"}],
            max_tokens=5,
            temperature=0,
        )
        if resp.choices:
            return success(message="连接成功")
        raise HTTPException(status_code=400, detail="无响应")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")


@router.post("/cases/{case_id}/search-strategy")
def generate_search_strategy(
    case_id: str,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    provider = cfg.get_provider_for_stage("collection")
    if not provider or not provider.apiKey:
        keywords = _fallback_keywords(case.profile or "")
    else:
        try:
            keywords = generate_search_keywords(case.profile or "", provider)
        except Exception:
            keywords = _fallback_keywords(case.profile or "")

    plan = SearchStrategy(case_id=case_id, keywords=keywords, recommended_limit=100)
    case.status = "STRATEGY_READY"
    db.add(plan)
    db.commit()
    return success(data={"keywords": keywords, "recommended_limit": 100}, message=None)


@router.post("/cases/{case_id}/start-collection")
def start_collection(
    case_id: str,
    db: Session = Depends(get_db),
    payload: dict = Body(default={}),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    latest_task = db.scalar(
        select(CollectionTask).where(CollectionTask.case_id == case_id).order_by(CollectionTask.id.desc()).limit(1)
    )
    if latest_task and latest_task.status in {"RUNNING", "PENDING"}:
        return success(message="Collection started")

    ui_keywords: list[str] = []
    if isinstance(payload, dict):
        candidate_keywords = payload.get("keywords")
        if isinstance(candidate_keywords, list):
            ui_keywords = [str(k).strip() for k in candidate_keywords if str(k).strip()]
    if ui_keywords:
        strategy = db.scalar(
            select(SearchStrategy).where(SearchStrategy.case_id == case_id).order_by(SearchStrategy.id.desc()).limit(1)
        )
        if strategy:
            strategy.keywords = ui_keywords
            strategy.recommended_limit = max(strategy.recommended_limit or 0, 100)
        else:
            db.add(SearchStrategy(case_id=case_id, keywords=ui_keywords, recommended_limit=100))
        db.commit()

    task = CollectionTask(case_id=case_id, status="PENDING", progress=0)
    case.status = "COLLECTING"
    db.add(task)
    db.commit()

    merged_config = cfg.model_dump()
    ui_config = payload.get("config", {}) if isinstance(payload, dict) else {}
    if "platforms" in ui_config:
        merged_config["crawlerPlatforms"] = ui_config["platforms"]
    if isinstance(ui_config.get("extraction"), dict):
        merged_config["extraction"] = ui_config["extraction"]

    run_collection(case_id, merged_config)
    return success(message="Collection started")


@router.get("/cases/{case_id}/collection-status")
def collection_status(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    task = db.scalar(select(CollectionTask).where(CollectionTask.case_id == case_id).order_by(CollectionTask.id.desc()).limit(1))
    if not task:
        raise HTTPException(status_code=400, detail="collection not started")
    meta = _collection_meta(case_id)
    crawler_config = meta.get("requested", {}) if isinstance(meta, dict) else {}
    crawler_observed = meta.get("observed", {}) if isinstance(meta, dict) else {}
    crawler_reconciliation = meta.get("reconciliation", {}) if isinstance(meta, dict) else {}

    if task.status == "COMPLETED":
        return success(
            data={
                "status": "COMPLETED",
                "progress": 100,
                "current_platform": task.current_platform,
                "filtering_progress": task.filtering_progress,
                "filtering_status": task.filtering_status,
                "total_scraped": task.total_scraped or 0,
                "filtered": {
                    "ads": task.filtered_ads or 0,
                    "duplicates": task.filtered_duplicates or 0,
                    "emotional_venting": task.filtered_emotional_venting or 0,
                },
                "valid_sources": task.valid_sources or 0,
                "extracted_facts": task.extracted_facts or 0,
                "crawler_config": crawler_config,
                "crawler_observed": crawler_observed,
                "crawler_reconciliation": crawler_reconciliation,
                "crawler_steps": meta.get("steps", []) if isinstance(meta, dict) else [],
            },
            message=None,
        )
    return success(
        data={
            "status": "COLLECTING",
            "progress": task.progress,
            "current_platform": task.current_platform,
            "filtering_progress": task.filtering_progress,
            "filtering_status": task.filtering_status,
            "extracted_facts": task.extracted_facts or 0,
            "crawler_config": crawler_config,
            "crawler_observed": crawler_observed,
            "crawler_reconciliation": crawler_reconciliation,
            "crawler_steps": meta.get("steps", []) if isinstance(meta, dict) else [],
        },
        message=None,
    )


@router.get("/cases/{case_id}/facts")
def get_facts(case_id: str, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    facts = db.scalars(select(Fact).where(Fact.case_id == case_id).order_by(Fact.fact_id.asc())).all()
    all_evidences = db.scalars(select(Evidence).where(Evidence.case_id == case_id)).all()
    evidence_map: dict[str, dict[str, str]] = {}
    for e in all_evidences:
        evidence_map[str(e.evidence_id)] = {
            "url": _resolve_evidence_url(str(e.url), str(e.source_name), str(e.content)),
            "source_name": str(e.source_name),
        }

    result = []
    for fact in facts:
        alerts = db.scalars(select(FactAuditAlert).where(FactAuditAlert.fact_row_id == fact.id)).all()
        sources = [evidence_map[eid] for eid in fact.evidence_ids if eid in evidence_map]
        result.append(
            {
                "id": fact.fact_id,
                "content": fact.content,
                "type": fact.type,
                "evidence_ids": fact.evidence_ids,
                "sources": sources,
                "audit_alerts": [{"type": a.type, "message": a.message} for a in alerts],
                "counter_evidence": fact.counter_evidence,
            }
        )
    return success(data=result, message=None)


@router.get("/cases/{case_id}/audit-elements")
def get_audit_elements(
    case_id: str,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    _get_case_or_404(db, case_id)
    provider = cfg.get_provider_for_stage("audit")
    fact_rows = db.scalars(select(Fact).where(Fact.case_id == case_id).order_by(Fact.fact_id.asc())).all()
    cards = [
        {
            "id": f.fact_id,
            "content": f.content,
            "domain": "市场反馈",
            "logical_property": f.type,
            "stance_warning": None,
            "evidence_ids": f.evidence_ids,
        }
        for f in fact_rows
    ]
    if not cards:
        return success(data=[], message=None)
    fact_by_id: dict[str, dict[str, Any]] = {
        str(card["id"]): {
            "content": str(card.get("content", "")),
            "evidence_ids": [str(x) for x in card.get("evidence_ids", [])],
            "type": str(card.get("logical_property", "FACT")),
        }
        for card in cards
    }
    evidence_rows = db.scalars(select(Evidence).where(Evidence.case_id == case_id)).all()
    evidence_map = {
        str(e.evidence_id): {"url": str(e.url), "source_name": str(e.source_name)}
        for e in evidence_rows
    }

    cards_signature = _json_signature(cards)
    cache_row = db.scalar(select(AuditElementCache).where(AuditElementCache.case_id == case_id).limit(1))
    elements: list[dict] = []
    if (
        cache_row
        and str(cache_row.facts_signature) == cards_signature
        and isinstance(cache_row.elements_graph, list)
        and cache_row.elements_graph
    ):
        elements = cache_row.elements_graph
    else:
        if provider:
            try:
                extraction_cfg = getattr(cfg, "extraction", None)
                map_chunk_size = max(8, int(getattr(extraction_cfg, "chunk_size", 24) or 24))
                map_chunk_overlap = int(getattr(extraction_cfg, "chunk_overlap", 0) or 0)
                map_chunks = _chunk_items(cards, map_chunk_size, map_chunk_overlap)

                if len(map_chunks) <= 1:
                    elements = generate_core_elements(cards, provider)
                else:
                    map_elements: list[dict] = []
                    for chunk in map_chunks:
                        partial = generate_core_elements(chunk, provider)
                        if partial:
                            map_elements.extend(partial)

                    if map_elements:
                        reduce_cards: list[dict] = []
                        for idx, item in enumerate(map_elements, start=1):
                            if not isinstance(item, dict):
                                continue
                            bound_facts = [str(x).strip() for x in item.get("bound_facts", []) if str(x).strip()]
                            reduce_cards.append(
                                {
                                    "id": f"map_el_{idx:04d}",
                                    "content": (
                                        f"核心元素:{item.get('element_name', '')};"
                                        f"分类:{item.get('category', '')};"
                                        f"绑定事实:{'；'.join(bound_facts[:3]) if bound_facts else '无'}"
                                    ),
                                    "domain": "系统元素",
                                    "logical_property": "FACT",
                                    "stance_warning": None,
                                    "evidence_ids": [],
                                }
                            )
                        if len(reduce_cards) > 1:
                            try:
                                elements = generate_core_elements(reduce_cards, provider)
                            except Exception as reduce_err:
                                print("Core element reduce pass failed:", reduce_err)
                                elements = map_elements
                        else:
                            elements = map_elements
            except Exception as e:
                print("Core element generation failed:", e)
        if not elements and cache_row and isinstance(cache_row.elements_graph, list) and cache_row.elements_graph:
            # Degrade gracefully to stale cache instead of empty page.
            elements = cache_row.elements_graph
        if not elements:
            # Keep the audit page usable even without an available model.
            for idx, card in enumerate(cards, start=1):
                elements.append(
                    {
                        "id": f"el_{idx:03d}",
                        "element_name": f"元素{idx}",
                        "category": "核心评价指标",
                        "bound_fact_ids": [card.get("id")],
                        "bound_facts": [card.get("content", "")],
                        "cognitive_reflections": [],
                    }
                )
        if cache_row:
            cache_row.facts_signature = cards_signature
            cache_row.elements_graph = elements
        else:
            db.add(
                AuditElementCache(
                    case_id=case_id,
                    facts_signature=cards_signature,
                    elements_graph=elements,
                )
            )
        db.commit()

    ui_cards = []
    for item in elements:
        reflections = item.get("cognitive_reflections", []) if isinstance(item, dict) else []
        alerts = []
        for r in reflections:
            if not isinstance(r, dict):
                continue
            alerts.append(
                {
                    "type": str(r.get("flaw_type") or "反思"),
                    "message": str(r.get("critique") or ""),
                }
            )
        bound_facts = [str(x) for x in item.get("bound_facts", []) if str(x).strip()]
        bound_fact_ids = _bind_fact_ids(bound_facts, fact_by_id)
        direct_ids = [str(x) for x in item.get("bound_fact_ids", []) if str(x).strip()]
        for fid in direct_ids:
            if fid in fact_by_id and fid not in bound_fact_ids:
                bound_fact_ids.append(fid)
        bound_evidence_ids: list[str] = []
        bound_types: list[str] = []
        for fid in bound_fact_ids:
            bound_evidence_ids.extend([str(x) for x in fact_by_id.get(fid, {}).get("evidence_ids", [])])
            bound_types.append(str(fact_by_id.get(fid, {}).get("type", "FACT")))
        dedup_evidence_ids: list[str] = []
        seen_evidence: set[str] = set()
        for eid in bound_evidence_ids:
            if eid in seen_evidence:
                continue
            seen_evidence.add(eid)
            dedup_evidence_ids.append(eid)
        sources = [evidence_map[eid] for eid in dedup_evidence_ids if eid in evidence_map]
        element_type = "FACT"
        if bound_types:
            priority = {"ASSUMPTION": 3, "INFERENCE": 2, "RISK": 2, "FACT": 1}
            element_type = sorted(bound_types, key=lambda t: priority.get(str(t).upper(), 0), reverse=True)[0]
        fact_preview = "；".join(bound_facts[:3]) if bound_facts else "（无）"
        content = (
            f"核心元素：{item.get('element_name', '')}\n"
            f"分类：{item.get('category', '')}\n"
            f"绑定信息池条目：{len(bound_fact_ids)} 条\n"
            f"绑定事实：{fact_preview}"
        )
        ui_cards.append(
            {
                "id": item.get("id"),
                "content": content,
                "type": element_type,
                "evidence_ids": dedup_evidence_ids,
                "sources": sources,
                "bound_fact_ids": bound_fact_ids,
                "bound_facts": bound_facts,
                "element_name": item.get("element_name"),
                "category": item.get("category"),
                "audit_alerts": alerts,
                "counter_evidence": None,
            }
        )
    return success(data=ui_cards, message=None)


@router.get("/cases/{case_id}/evidences")
def get_evidences(case_id: str, db: Session = Depends(get_db), ids: str | None = None):
    _get_case_or_404(db, case_id)
    query = select(Evidence).where(Evidence.case_id == case_id)
    if ids:
        evidence_ids = [i.strip() for i in ids.split(",")]
        query = query.where(Evidence.evidence_id.in_(evidence_ids))

    items = db.scalars(query.order_by(Evidence.evidence_id.asc())).all()
    return success(
        data=[
            {
                "evidence_id": e.evidence_id,
                "source_name": e.source_name,
                "url": _resolve_evidence_url(str(e.url), str(e.source_name), str(e.content)),
                "content": e.content,
            }
            for e in items
        ],
        message=None,
    )


@router.post("/cases/{case_id}/facts/{fact_id}/feedback")
def submit_fact_feedback(case_id: str, fact_id: str, payload: FactFeedbackRequest, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    fact = db.scalar(select(Fact).where(Fact.case_id == case_id, Fact.fact_id == fact_id).limit(1))
    if not fact:
        raise HTTPException(status_code=404, detail="fact not found")
    db.add(
        FactFeedback(
            case_id=case_id,
            fact_id=fact_id,
            feedback_type=payload.feedback_type or payload.type or "GENERAL",
            comment=payload.comment,
        )
    )
    db.commit()
    return success(message="Feedback received")


@router.get("/cases/{case_id}/sandbox")
def get_sandbox(
    case_id: str,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    if graph and graph.nodes:
        meta = _collection_meta(case_id).get("model_outputs", {})
        return success(
            data={
                "nodes": graph.nodes,
                "edges": graph.edges,
                "causal_topology": meta.get("causal_topology", {}),
                "counterfactual_insight": meta.get("counterfactual_insight", ""),
            },
            message=None,
        )

    cards = _facts_payload(db, case_id)
    if not cards:
        raise HTTPException(status_code=400, detail="事实资料不足，无法生成因果逻辑")
    element_provider = cfg.get_provider_for_stage("audit") or cfg.get_provider_for_stage("sandbox")
    sandbox_provider = cfg.get_provider_for_stage("sandbox")
    if not element_provider or not sandbox_provider:
        graph_data = _heuristic_graph_from_cards(cards)
    else:
        try:
            elements_graph = generate_core_elements(cards, element_provider)
            graph_data = generate_causal_graph(elements_graph, sandbox_provider, user_initial_prompt=case.profile or "")
        except Exception:
            graph_data = _heuristic_graph_from_cards(cards)

    if not graph:
        graph = SandboxGraph(case_id=case_id, nodes=graph_data["nodes"], edges=graph_data["edges"])
        db.add(graph)
    else:
        graph.nodes = graph_data["nodes"]
        graph.edges = graph_data["edges"]
    db.commit()
    _write_collection_meta(
        case_id,
        {
            "model_outputs": {
                "causal_topology": graph_data.get("causal_topology", {}),
                "counterfactual_insight": graph_data.get("counterfactual_insight", ""),
            }
        },
    )
    return success(
        data={
            "nodes": graph.nodes,
            "edges": graph.edges,
            "causal_topology": graph_data.get("causal_topology", {}),
            "counterfactual_insight": graph_data.get("counterfactual_insight", ""),
        },
        message=None,
    )


@router.post("/cases/{case_id}/sandbox/regenerate")
def regenerate_sandbox(
    case_id: str,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    cards = _facts_payload(db, case_id)
    if not cards:
        raise HTTPException(status_code=400, detail="事实资料不足，无法生成因果逻辑")

    element_provider = cfg.get_provider_for_stage("audit") or cfg.get_provider_for_stage("sandbox")
    sandbox_provider = cfg.get_provider_for_stage("sandbox")
    if not element_provider or not sandbox_provider:
        graph_data = _heuristic_graph_from_cards(cards)
    else:
        try:
            elements_graph = generate_core_elements(cards, element_provider)
            graph_data = generate_causal_graph(elements_graph, sandbox_provider, user_initial_prompt=case.profile or "")
        except Exception:
            graph_data = _heuristic_graph_from_cards(cards)

    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    if not graph:
        graph = SandboxGraph(case_id=case_id, nodes=graph_data["nodes"], edges=graph_data["edges"])
        db.add(graph)
    else:
        graph.nodes = graph_data["nodes"]
        graph.edges = graph_data["edges"]
    db.commit()
    _write_collection_meta(
        case_id,
        {
            "model_outputs": {
                "causal_topology": graph_data.get("causal_topology", {}),
                "counterfactual_insight": graph_data.get("counterfactual_insight", ""),
            }
        },
    )
    return success(
        data={
            "nodes": graph.nodes,
            "edges": graph.edges,
            "causal_topology": graph_data.get("causal_topology", {}),
            "counterfactual_insight": graph_data.get("counterfactual_insight", ""),
        },
        message="沙盘逻辑重铸成功",
    )


@router.post("/cases/{case_id}/sandbox/intervene")
def sandbox_intervene(
    case_id: str,
    payload: SandboxInterveneRequest,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    graph_data = {"nodes": graph.nodes, "edges": graph.edges} if graph else {}

    result = simulate_sandbox(
        [x.model_dump() for x in payload.interventions],
        payload.text,
        case.profile,
        graph_data,
        cfg.get_provider_for_stage("sandbox"),
    )
    db.add(
        SandboxIntervention(
            case_id=case_id,
            payload=payload.model_dump(),
            affected_nodes=result["affected_nodes"],
            logic_explanation=result["logic_explanation"],
            risk_warning=result["risk_warning"],
        )
    )
    db.commit()
    return success(data=result, message=None)


@router.get("/cases/{case_id}/worldline/probe")
def get_worldline_probe(
    case_id: str,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    provider = cfg.get_provider_for_stage("worldline")
    if not graph or not graph.nodes:
        raise HTTPException(status_code=400, detail="请先生成因果图谱")
    if not provider or not provider.apiKey:
        raise HTTPException(status_code=400, detail="worldline 阶段未配置可用模型，无法生成变量探针问题")
    try:
        questions = generate_system_variable_probe(
            user_initial_prompt=case.profile,
            causal_graph_snapshot={"nodes": graph.nodes, "edges": graph.edges},
            provider=provider,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"变量探针生成失败: {e}") from e
    return success(data={"questions": questions}, message=None)


@router.put("/cases/{case_id}/context")
def put_context(case_id: str, payload: dict[str, Any] = Body(default={}), db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    row = db.scalar(select(UserContext).where(UserContext.case_id == case_id).limit(1))
    if row:
        row.context_payload = payload
    else:
        db.add(UserContext(case_id=case_id, context_payload=payload))
    db.commit()
    return success(message="个人语境已注入成功")


@router.get("/cases/{case_id}/worldline")
def get_worldline(
    case_id: str,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    model_outputs = _collection_meta(case_id).get("model_outputs", {})
    worldline = db.scalar(select(Worldline).where(Worldline.case_id == case_id).limit(1))
    if worldline and worldline.timeline:
        return success(
            data={
                "timeline": worldline.timeline,
                "paths": worldline.paths,
                "worldlines": model_outputs.get("worldlines", []),
                "model_generated": bool(model_outputs.get("worldline_model_generated", True)),
                "model": model_outputs.get("worldline_model", ""),
                "generated_at": model_outputs.get("worldline_generated_at", ""),
            },
            message=None,
        )

    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    if not graph or not graph.nodes:
        raise HTTPException(status_code=400, detail="前置条件缺失：请先完成因果图谱构建")

    ctx_row = db.scalar(select(UserContext).where(UserContext.case_id == case_id).limit(1))
    context_payload = ctx_row.context_payload if ctx_row else {}
    if not context_payload:
        return success(data={"timeline": [], "paths": [], "worldlines": []}, message=None)
    provider = cfg.get_provider_for_stage("worldline")
    if not provider or not provider.apiKey:
        raise HTTPException(status_code=400, detail="worldline 阶段未配置可用模型，无法进行真实世界线推演")
    try:
        wl_data = generate_worldline_simulation(
            user_initial_prompt=case.profile,
            causal_graph_snapshot={"nodes": graph.nodes, "edges": graph.edges},
            user_verified_status=context_payload,
            real_world_baselines=_worldline_baselines(),
            provider=provider,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"世界线推演失败: {e}") from e

    if not worldline:
        worldline = Worldline(case_id=case_id, timeline=wl_data["timeline"], paths=wl_data["paths"])
        db.add(worldline)
    else:
        worldline.timeline = wl_data["timeline"]
        worldline.paths = wl_data["paths"]
    db.commit()
    _write_collection_meta(
        case_id,
        {
            "model_outputs": {
                "worldlines": wl_data.get("worldlines", []),
                "worldline_model_generated": True,
                "worldline_model": provider.defaultModel or "gpt-4o",
                "worldline_generated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    return success(
        data={
            "timeline": worldline.timeline,
            "paths": worldline.paths,
            "worldlines": wl_data.get("worldlines", []),
            "model_generated": True,
            "model": provider.defaultModel or "gpt-4o",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        message=None,
    )


@router.post("/cases/{case_id}/worldline/regenerate")
def regenerate_worldline(
    case_id: str,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    if not graph or not graph.nodes:
        raise HTTPException(status_code=400, detail="前置条件缺失：请先完成因果图谱构建")

    ctx_row = db.scalar(select(UserContext).where(UserContext.case_id == case_id).limit(1))
    context_payload = ctx_row.context_payload if ctx_row else {}
    if not context_payload:
        raise HTTPException(status_code=400, detail="请先完成变量探针问答并注入个人语境")
    provider = cfg.get_provider_for_stage("worldline")
    if not provider or not provider.apiKey:
        raise HTTPException(status_code=400, detail="worldline 阶段未配置可用模型，无法重铸世界线")
    try:
        wl_data = generate_worldline_simulation(
            user_initial_prompt=case.profile,
            causal_graph_snapshot={"nodes": graph.nodes, "edges": graph.edges},
            user_verified_status=context_payload,
            real_world_baselines=_worldline_baselines(),
            provider=provider,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"世界线重铸失败: {e}") from e

    worldline = db.scalar(select(Worldline).where(Worldline.case_id == case_id).limit(1))
    if not worldline:
        worldline = Worldline(case_id=case_id, timeline=wl_data["timeline"], paths=wl_data["paths"])
        db.add(worldline)
    else:
        worldline.timeline = wl_data["timeline"]
        worldline.paths = wl_data["paths"]
    db.commit()
    _write_collection_meta(
        case_id,
        {
            "model_outputs": {
                "worldlines": wl_data.get("worldlines", []),
                "worldline_model_generated": True,
                "worldline_model": provider.defaultModel or "gpt-4o",
                "worldline_generated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    return success(
        data={
            "timeline": worldline.timeline,
            "paths": worldline.paths,
            "worldlines": wl_data.get("worldlines", []),
            "model_generated": True,
            "model": provider.defaultModel or "gpt-4o",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        message="世界线推演重铸成功",
    )


@router.post("/cases/{case_id}/worldline/intervene")
def worldline_intervene(
    case_id: str,
    payload: WorldlineInterveneRequest,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    worldline = db.scalar(select(Worldline).where(Worldline.case_id == case_id).limit(1))
    if not worldline:
        raise HTTPException(status_code=400, detail="请先完成世界线推演，再执行世界线干预")
    provider = cfg.get_provider_for_stage("worldline")
    if not provider or not provider.apiKey:
        raise HTTPException(status_code=400, detail="worldline 阶段未配置可用模型，无法执行世界线干预")

    try:
        result = simulate_worldline(
            payload.text or "",
            case.profile,
            {"timeline": worldline.timeline, "paths": worldline.paths},
            {"nodes": graph.nodes, "edges": graph.edges} if graph else {},
            provider,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"世界线干预失败: {e}") from e
    db.add(
        WorldlineIntervention(
            case_id=case_id,
            text=payload.text or "",
            new_paths=result["new_paths"],
            logic_explanation=result["logic_explanation"],
            risk_warning=result["risk_warning"],
        )
    )
    db.commit()
    return success(data=result, message=None)


@router.get("/cases/{case_id}/whitepaper")
def get_whitepaper(
    case_id: str,
    db: Session = Depends(get_db),
    config: WolongConfig = Depends(get_wolong_config),
):
    cfg = _resolve_config(config)
    case = _get_case_or_404(db, case_id)
    row = db.scalar(select(Whitepaper).where(Whitepaper.case_id == case_id).limit(1))
    model_outputs = _collection_meta(case_id).get("model_outputs", {})
    if row and row.main_conflict and model_outputs.get("whitepaper_model_generated") is True:
        return success(
            data={
                "main_conflict": row.main_conflict,
                "critical_warnings": row.critical_warnings,
                "mvp_actions": row.mvp_actions,
                "unknowns": row.unknowns,
                "contradiction_transformation": model_outputs.get("contradiction_transformation", {}),
                "model_generated": True,
                "model": model_outputs.get("whitepaper_model", ""),
                "generated_at": model_outputs.get("whitepaper_generated_at", ""),
            },
            message=None,
        )

    provider = cfg.get_provider_for_stage("worldline")
    if not provider or not provider.apiKey:
        raise HTTPException(status_code=400, detail="worldline 阶段未配置可用模型，无法生成真实白皮书")

    facts = db.scalars(select(Fact).where(Fact.case_id == case_id)).all()
    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    worldline = db.scalar(select(Worldline).where(Worldline.case_id == case_id).limit(1))
    ctx_row = db.scalar(select(UserContext).where(UserContext.case_id == case_id).limit(1))
    if not graph or not worldline:
        raise HTTPException(status_code=400, detail="请先完成因果图与世界线推演")

    snapshot = {
        "facts": [f.to_dict() for f in facts],
        "causal_graph_snapshot": {"nodes": graph.nodes, "edges": graph.edges},
        "worldline": {"timeline": worldline.timeline, "paths": worldline.paths},
        "user_context": ctx_row.context_payload if ctx_row else {},
    }
    try:
        wp_data = generate_final_whitepaper(
            system_deduction_snapshot=snapshot,
            user_current_dilemma=case.profile,
            provider=provider,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"白皮书生成失败: {e}") from e

    if not row:
        row = Whitepaper(case_id=case_id, main_conflict="", critical_warnings=[], mvp_actions=[], unknowns=[])
        db.add(row)
    row.main_conflict = wp_data.get("main_conflict", "")
    row.critical_warnings = wp_data.get("critical_warnings", [])
    row.mvp_actions = wp_data.get("mvp_actions", [])
    row.unknowns = wp_data.get("unknowns", [])
    db.commit()
    _write_collection_meta(
        case_id,
        {
            "model_outputs": {
                "contradiction_transformation": wp_data.get("contradiction_transformation", {}),
                "whitepaper_model_generated": True,
                "whitepaper_model": provider.defaultModel or "gpt-4o",
                "whitepaper_generated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    return success(
        data={
            **wp_data,
            "model_generated": True,
            "model": provider.defaultModel or "gpt-4o",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        message=None,
    )


@router.post("/cases/{case_id}/feedbacks")
def submit_case_feedback(case_id: str, payload: Any = Body(...), db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    if isinstance(payload, dict):
        payload_dict = payload
    elif hasattr(payload, "model_dump"):
        payload_dict = payload.model_dump()
    else:
        payload_dict = {"raw": str(payload)}
    feedback_type = payload_dict.get("feedback_type", payload_dict.get("reason", "GENERAL"))
    db.add(CaseFeedback(case_id=case_id, feedback_type=feedback_type, payload=payload_dict))
    db.commit()
    return success(message="反馈已记录")


@router.delete("/cases/{case_id}")
def delete_case(case_id: str, force: bool = True, db: Session = Depends(get_db)):
    _get_case_or_404(db, case_id)
    latest_task = db.scalar(
        select(CollectionTask).where(CollectionTask.case_id == case_id).order_by(CollectionTask.id.desc()).limit(1)
    )
    if latest_task and latest_task.status == "RUNNING" and not force:
        raise HTTPException(status_code=409, detail="当前案例仍在采集中，请稍后删除")
    _delete_case_rows(db, case_id)
    _delete_case_files(case_id)
    return success(message="案例已删除")
