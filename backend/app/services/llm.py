from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
from typing import Any

import httpx
from openai import OpenAI

from app.api.deps import ProviderProxy
from app.core.prompts import (
    CAUSAL_GRAPH_BUILDING_PROMPT,
    CAUSAL_INTERVENTION_PROMPT,
    CORE_ELEMENT_EXTRACTION_PROMPT,
    FACT_EXTRACTION_PROMPT,
    FINAL_WHITEPAPER_PROMPT,
    SEARCH_QUERY_GENERATION_PROMPT,
    SYSTEM_VARIABLE_PROBE_PROMPT,
    WORLDLINE_INTERVENTION_PROMPT,
    WORLDLINE_SIMULATION_PROMPT,
)


def _preferred_proxy_from_env() -> str:
    for key in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _sanitize_proxy_url(proxy_url: str, has_socks_support: bool) -> str:
    if not proxy_url:
        return ""
    lower = proxy_url.lower()
    if lower.startswith("socks://"):
        if has_socks_support:
            return "socks5://" + proxy_url.split("://", 1)[1]
        return ""
    if lower.startswith("socks5://") and not has_socks_support:
        return ""
    return proxy_url


def _client(provider: ProviderProxy) -> OpenAI:
    if not provider or not provider.apiKey:
        raise RuntimeError("LLM Provider API Key is not configured for this stage.")
    timeout_config = httpx.Timeout(60.0, connect=15.0)
    has_socks_support = importlib.util.find_spec("socksio") is not None
    proxy_candidate = _preferred_proxy_from_env()
    proxy_url = _sanitize_proxy_url(proxy_candidate, has_socks_support)
    http_client = httpx.Client(timeout=timeout_config, trust_env=False, proxy=proxy_url or None)
    if provider.baseUrl:
        return OpenAI(api_key=provider.apiKey, base_url=provider.baseUrl, http_client=http_client)
    return OpenAI(api_key=provider.apiKey, http_client=http_client)


def _extract_json(text: str) -> Any:
    raw = text.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    def _cleanup(candidate: str) -> str:
        candidate = candidate.strip().replace("\ufeff", "")
        candidate = candidate.replace("\x00", "")
        candidate = candidate.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
        candidate = re.sub(r"//.*?$", "", candidate, flags=re.MULTILINE)
        candidate = re.sub(r"/\*.*?\*/", "", candidate, flags=re.DOTALL)
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        # Escape stray backslashes that would otherwise break JSON decoding.
        candidate = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", candidate)
        return candidate.strip()

    def _extract_balanced(candidate: str, left: str, right: str) -> str | None:
        start = candidate.find(left)
        if start == -1:
            return None
        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(candidate)):
            ch = candidate[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == left:
                depth += 1
            elif ch == right:
                depth -= 1
                if depth == 0:
                    return candidate[start : idx + 1]
        return None

    candidates = [raw]
    obj = _extract_balanced(raw, "{", "}")
    arr = _extract_balanced(raw, "[", "]")
    if obj:
        candidates.append(obj)
    if arr:
        candidates.append(arr)

    for candidate in candidates:
        cleaned = _cleanup(candidate)
        for attempt in (cleaned, cleaned.replace("'", '"')):
            try:
                return json.loads(attempt)
            except Exception:
                continue
        try:
            py_expr = re.sub(r"\btrue\b", "True", cleaned, flags=re.IGNORECASE)
            py_expr = re.sub(r"\bfalse\b", "False", py_expr, flags=re.IGNORECASE)
            py_expr = re.sub(r"\bnull\b", "None", py_expr, flags=re.IGNORECASE)
            parsed = ast.literal_eval(py_expr)
            if isinstance(parsed, (dict, list)):
                return parsed
        except Exception:
            continue

    # Best-effort fallback: if model emitted multiple standalone JSON objects line-by-line,
    # salvage them into a JSON array to avoid dropping the entire response.
    line_items: list[Any] = []
    for line in raw.splitlines():
        line = _cleanup(line)
        if not line.startswith("{") or not line.endswith("}"):
            continue
        try:
            line_items.append(json.loads(line))
        except Exception:
            continue
    if line_items:
        return line_items

    raise ValueError(f"Invalid JSON from model: {raw[:400]}...")


def _repair_json_with_model(raw_text: str, provider: ProviderProxy) -> str:
    client = _client(provider)
    model = provider.defaultModel or "gpt-4o"
    repair_prompt = (
        "You are a strict JSON repair tool.\n"
        "Task: repair the input into valid JSON only.\n"
        "Rules:\n"
        "1) Keep original semantics and fields.\n"
        "2) Output JSON only, no markdown, no commentary.\n"
        "3) Preserve top-level shape (object/array).\n\n"
        f"INPUT:\n{raw_text}"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": repair_prompt}],
        temperature=0,
        max_tokens=4096,
    )
    return (resp.choices[0].message.content or "").strip()


def _call_json(prompt: str, provider: ProviderProxy) -> Any:
    client = _client(provider)
    model = provider.defaultModel or "gpt-4o"
    last_error: Exception | None = None
    for attempt in range(2):
        current_prompt = prompt
        if attempt == 1:
            current_prompt = (
                f"{prompt}\n\n"
                "[输出约束补充]\n"
                "你的上一次输出不是合法 JSON。请只输出合法 JSON，本次禁止输出任何解释、Markdown 或代码块围栏。"
            )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": current_prompt}],
            temperature=0,
            max_tokens=4096,
        )
        content = (resp.choices[0].message.content or "").strip()
        try:
            return _extract_json(content)
        except Exception as parse_error:
            try:
                repaired = _repair_json_with_model(content, provider)
                return _extract_json(repaired)
            except Exception as repair_error:
                last_error = repair_error
                if attempt == 1:
                    break
                # Retry one more clean generation before failing this stage.
                continue
    raise ValueError(f"Model JSON parse failed after retries: {last_error}")


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _norm_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", value).strip("_")
    return clean[:64] or "node"


def generate_search_keywords(profile: str, provider: ProviderProxy) -> list[str]:
    prompt = (
        f"{SEARCH_QUERY_GENERATION_PROMPT}\n\n"
        f"[用户背景与困境]:\n{profile}"
    )
    data = _call_json(prompt, provider)
    if isinstance(data, dict) and "keywords" in data:
        return [str(x).strip() for x in _as_list(data.get("keywords")) if str(x).strip()]
    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    raise ValueError("Unexpected keyword format from model.")


def generate_knowledge_cards(
    evidences: list[dict],
    provider: ProviderProxy,
    user_initial_prompt: str = "",
) -> list[dict]:
    prompt = (
        f"{FACT_EXTRACTION_PROMPT}\n\n"
        f"[用户初始决策情景]:\n{user_initial_prompt}\n\n"
        f"[爬取到的文本片段及对应的 evidence_id]:\n{json.dumps(evidences, ensure_ascii=False)}"
    )
    data = _call_json(prompt, provider)
    cards = data.get("knowledge_cards") if isinstance(data, dict) else data
    normalized: list[dict] = []
    for idx, item in enumerate(_as_list(cards), start=1):
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "id": _norm_text(item.get("id")),
                "content": _norm_text(item.get("content")),
                "domain": _norm_text(item.get("domain")) or "市场反馈",
                "logical_property": _norm_text(item.get("logical_property")) or "FACT",
                "stance_warning": _norm_text(item.get("stance_warning")) or None,
                "evidence_ids": [str(x).strip() for x in _as_list(item.get("evidence_ids")) if str(x).strip()],
            }
        )
    return normalized


def generate_core_elements(knowledge_cards: list[dict], provider: ProviderProxy) -> list[dict]:
    prompt = (
        f"{CORE_ELEMENT_EXTRACTION_PROMPT}\n\n"
        f"[knowledge_cards]:\n{json.dumps(knowledge_cards, ensure_ascii=False)}"
    )
    data = _call_json(prompt, provider)
    elements = data.get("elements_graph") if isinstance(data, dict) else data
    normalized: list[dict] = []
    for idx, item in enumerate(_as_list(elements), start=1):
        if not isinstance(item, dict):
            continue
        reflections = []
        for r in _as_list(item.get("cognitive_reflections")):
            if not isinstance(r, dict):
                continue
            reflections.append(
                {
                    "target_fact": _norm_text(r.get("target_fact")),
                    "flaw_type": _norm_text(r.get("flaw_type")) or "隐藏假设",
                    "critique": _norm_text(r.get("critique")),
                }
            )
        normalized.append(
            {
                "id": _norm_text(item.get("id")) or f"el_{idx:03d}",
                "element_name": _norm_text(item.get("element_name")) or f"核心元素{idx}",
                "category": _norm_text(item.get("category")) or "核心评价指标",
                "bound_facts": [str(x).strip() for x in _as_list(item.get("bound_facts")) if str(x).strip()],
                "cognitive_reflections": reflections,
            }
        )
    return normalized


def _edge_polarity(mechanism: str) -> str:
    negative_markers = ("下降", "减少", "抑制", "拖慢", "恶化", "流失", "负")
    return "negative" if any(token in mechanism for token in negative_markers) else "positive"


def generate_causal_graph(
    elements_graph: list[dict],
    provider: ProviderProxy,
    user_initial_prompt: str = "",
) -> dict:
    prompt = (
        f"{CAUSAL_GRAPH_BUILDING_PROMPT}\n\n"
        f"[user_initial_prompt]:\n{user_initial_prompt}\n\n"
        f"[elements_graph]:\n{json.dumps(elements_graph, ensure_ascii=False)}"
    )
    data = _call_json(prompt, provider)

    if isinstance(data, dict) and "nodes" in data and "edges" in data:
        return {
            "nodes": _as_list(data.get("nodes")),
            "edges": _as_list(data.get("edges")),
            "causal_topology": data.get("causal_topology", {}),
            "counterfactual_insight": _norm_text(data.get("counterfactual_insight")),
        }

    direct_edges = _as_list(data.get("direct_causal_edges") if isinstance(data, dict) else [])
    topology = data.get("causal_topology", {}) if isinstance(data, dict) else {}
    insight = _norm_text(data.get("counterfactual_insight")) if isinstance(data, dict) else ""

    names: list[str] = []
    for el in elements_graph:
        if isinstance(el, dict):
            name = _norm_text(el.get("element_name"))
            if name:
                names.append(name)
    for edge in direct_edges:
        if not isinstance(edge, dict):
            continue
        names.extend([_norm_text(edge.get("source")), _norm_text(edge.get("target"))])
    deduped = []
    seen = set()
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(name)

    node_map: dict[str, str] = {}
    nodes: list[dict] = []
    for idx, name in enumerate(deduped, start=1):
        node_id = f"n{idx}_{_slug(name)}"
        node_map[name] = node_id
        nodes.append(
            {
                "id": node_id,
                "name": name,
                "status": "variable",
                "type": "objective",
                "val": 0.5,
            }
        )

    edges: list[dict] = []
    for item in direct_edges:
        if not isinstance(item, dict):
            continue
        src_name = _norm_text(item.get("source"))
        dst_name = _norm_text(item.get("target"))
        mechanism = _norm_text(item.get("mechanism")) or "因果作用"
        if not src_name or not dst_name:
            continue
        if src_name not in node_map:
            node_id = f"n{len(nodes)+1}_{_slug(src_name)}"
            node_map[src_name] = node_id
            nodes.append({"id": node_id, "name": src_name, "status": "variable", "type": "objective", "val": 0.5})
        if dst_name not in node_map:
            node_id = f"n{len(nodes)+1}_{_slug(dst_name)}"
            node_map[dst_name] = node_id
            nodes.append({"id": node_id, "name": dst_name, "status": "variable", "type": "objective", "val": 0.5})
        edges.append(
            {
                "source": node_map[src_name],
                "target": node_map[dst_name],
                "polarity": _edge_polarity(mechanism),
                "desc": mechanism,
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "causal_topology": topology if isinstance(topology, dict) else {},
        "counterfactual_insight": insight,
    }


def generate_system_variable_probe(
    user_initial_prompt: str,
    causal_graph_snapshot: dict,
    provider: ProviderProxy,
) -> list[dict]:
    causal_graph_nodes = _as_list(causal_graph_snapshot.get("nodes") if isinstance(causal_graph_snapshot, dict) else [])
    prompt = (
        f"{SYSTEM_VARIABLE_PROBE_PROMPT}\n\n"
        f"[user_initial_prompt]:\n{user_initial_prompt}\n\n"
        f"[causal_graph_snapshot]:\n{json.dumps(causal_graph_snapshot, ensure_ascii=False)}\n\n"
        f"[causal_graph_nodes]:\n{json.dumps(causal_graph_nodes, ensure_ascii=False)}"
    )
    data = _call_json(prompt, provider)
    missing = data.get("missing_variables") if isinstance(data, dict) else data
    normalized: list[dict] = []
    for item in _as_list(missing):
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "node_id": _norm_text(item.get("node_id")) or "unknown_node",
                "probe_question": _norm_text(item.get("probe_question")),
                "why_it_matters": _norm_text(item.get("why_it_matters")),
            }
        )
    return normalized


def _worldline_type(line_name: str) -> str:
    lower = line_name.lower()
    if "beta" in lower or "破局" in line_name:
        return "best_case"
    if "gamma" in lower or "崩溃" in line_name or "恶化" in line_name:
        return "worst_case"
    return "baseline"


def generate_worldline_simulation(
    user_initial_prompt: str,
    causal_graph_snapshot: dict,
    user_verified_status: dict,
    real_world_baselines: dict,
    provider: ProviderProxy,
) -> dict:
    prompt = (
        f"{WORLDLINE_SIMULATION_PROMPT}\n\n"
        f"[user_initial_prompt]:\n{user_initial_prompt}\n\n"
        f"[causal_graph_snapshot]:\n{json.dumps(causal_graph_snapshot, ensure_ascii=False)}\n\n"
        f"[user_verified_status]:\n{json.dumps(user_verified_status, ensure_ascii=False)}\n\n"
        f"[real_world_baselines]:\n{json.dumps(real_world_baselines, ensure_ascii=False)}"
    )
    data = _call_json(prompt, provider)

    if isinstance(data, dict) and "timeline" in data and "paths" in data:
        result = {
            "worldlines": _as_list(data.get("worldlines")),
            "timeline": [str(x) for x in _as_list(data.get("timeline")) if str(x).strip()],
            "paths": _as_list(data.get("paths")),
        }
        if not result["timeline"] or not result["paths"]:
            raise ValueError("Worldline output is empty.")
        return result

    worldlines = _as_list(data.get("worldlines") if isinstance(data, dict) else [])
    timeline: list[str] = []
    paths: list[dict] = []
    for line in worldlines:
        if not isinstance(line, dict):
            continue
        line_name = _norm_text(line.get("line_name")) or "Alpha-惯性线"
        evolution = line.get("timeline_evolution", {}) if isinstance(line.get("timeline_evolution"), dict) else {}
        nodes = []
        for k, v in evolution.items():
            time_label = str(k).replace("T_plus_", "T+").replace("_years", "年").replace("_year", "年")
            desc = _norm_text(v)
            timeline.append(time_label)
            nodes.append(
                {
                    "time": time_label,
                    "desc": desc,
                    "triggers": [
                        _norm_text(line.get("core_strategy")),
                        _norm_text(line.get("dominant_loop")),
                    ],
                }
            )
        paths.append(
            {
                "type": _worldline_type(line_name),
                "color": "info",
                "branch_name": line_name,
                "nodes": nodes,
            }
        )

    dedup_timeline = []
    seen = set()
    for t in timeline:
        if t and t not in seen:
            seen.add(t)
            dedup_timeline.append(t)

    result = {"worldlines": worldlines, "timeline": dedup_timeline, "paths": paths}
    if not result["timeline"] or not result["paths"]:
        raise ValueError("Worldline output is empty.")
    return result


def generate_causal_intervention(
    causal_graph_snapshot: dict,
    user_intervention_text: str,
    user_initial_prompt: str,
    provider: ProviderProxy,
) -> dict:
    prompt = (
        f"{CAUSAL_INTERVENTION_PROMPT}\n\n"
        f"[user_initial_prompt]:\n{user_initial_prompt}\n\n"
        f"[causal_graph_snapshot]:\n{json.dumps(causal_graph_snapshot, ensure_ascii=False)}\n\n"
        f"[user_intervention_text]:\n{user_intervention_text}\n\n"
        f"[causal_graph]:\n{json.dumps(causal_graph_snapshot, ensure_ascii=False)}"
    )
    data = _call_json(prompt, provider)
    if not isinstance(data, dict):
        raise ValueError("Unexpected intervention output format.")

    graph_nodes = _as_list(causal_graph_snapshot.get("nodes") if isinstance(causal_graph_snapshot, dict) else [])
    id_set = {str(n.get("id")) for n in graph_nodes if isinstance(n, dict)}
    name_to_id = {
        _norm_text(n.get("name")): _norm_text(n.get("id"))
        for n in graph_nodes
        if isinstance(n, dict) and _norm_text(n.get("name")) and _norm_text(n.get("id"))
    }
    val_by_id = {
        _norm_text(n.get("id")): float(n.get("val", 0.5))
        for n in graph_nodes
        if isinstance(n, dict) and _norm_text(n.get("id"))
    }

    ripple_effects = _as_list(data.get("ripple_effects"))
    trend_to_val = {
        "UP": 0.7,
        "DOWN": 0.3,
        "FLUCTUATING": 0.5,
        "STABLE": None,
    }
    affected_nodes: list[dict] = []
    for item in ripple_effects:
        if not isinstance(item, dict):
            continue
        raw_node = _norm_text(item.get("node_id"))
        if not raw_node:
            continue
        resolved_id = raw_node if raw_node in id_set else name_to_id.get(raw_node, "")
        if not resolved_id:
            continue
        trend = _norm_text(item.get("trend")).upper() or "STABLE"
        mapped = trend_to_val.get(trend)
        new_val = val_by_id.get(resolved_id, 0.5) if mapped is None else mapped
        affected_nodes.append(
            {
                "id": resolved_id,
                "new_val": max(0.0, min(1.0, float(new_val))),
                "trend": trend.lower(),
                "impact_degree": _norm_text(item.get("impact_degree")),
                "delay_type": _norm_text(item.get("delay_type")),
            }
        )

    if affected_nodes:
        return {
            "affected_nodes": affected_nodes,
            "logic_explanation": _norm_text(data.get("causal_deduction") or data.get("logic_explanation")),
            "risk_warning": _norm_text(data.get("dialectical_risk") or data.get("risk_warning")),
        }

    # Legacy compatibility fallback.
    if "affected_nodes" in data:
        return {
            "affected_nodes": _as_list(data.get("affected_nodes")),
            "logic_explanation": _norm_text(data.get("causal_deduction") or data.get("logic_explanation")),
            "risk_warning": _norm_text(data.get("dialectical_risk") or data.get("risk_warning")),
        }

    fallback_affected = [
        {
            "id": _norm_text(graph_nodes[0].get("id")) if graph_nodes and isinstance(graph_nodes[0], dict) else "n1",
            "new_val": 0.5,
            "trend": "stable",
        }
    ]
    return {
        "affected_nodes": fallback_affected,
        "logic_explanation": _norm_text(data.get("causal_deduction")),
        "risk_warning": _norm_text(data.get("dialectical_risk")),
    }


def generate_worldline_intervention(
    current_worldline: dict,
    user_intervention_text: str,
    causal_graph: dict,
    provider: ProviderProxy,
    user_initial_prompt: str = "",
) -> dict:
    prompt = (
        f"{WORLDLINE_INTERVENTION_PROMPT}\n\n"
        f"[user_initial_prompt]:\n{user_initial_prompt}\n\n"
        f"[current_worldline]:\n{json.dumps(current_worldline, ensure_ascii=False)}\n\n"
        f"[user_intervention_text]:\n{user_intervention_text}\n\n"
        f"[causal_graph]:\n{json.dumps(causal_graph, ensure_ascii=False)}"
    )
    data = _call_json(prompt, provider)
    if not isinstance(data, dict):
        raise ValueError("Unexpected worldline intervention output format.")

    if "new_paths" in data:
        return {
            "new_paths": _as_list(data.get("new_paths")),
            "logic_explanation": _norm_text(data.get("causal_logic_explanation") or data.get("logic_explanation")),
            "risk_warning": _norm_text(data.get("dialectical_risk") or data.get("risk_warning")),
        }

    # Backward compatibility for older intervention-like outputs.
    ripple_effects = _as_list(data.get("ripple_effects"))
    new_paths = [
        {
            "type": "custom",
            "color": "primary",
            "branch_name": _norm_text(data.get("intervention_summary")) or "Intervention",
            "nodes": [
                {
                    "time": "T+1",
                    "desc": _norm_text(item.get("node_id")),
                    "triggers": [f"{_norm_text(item.get('trend'))} / {_norm_text(item.get('impact_degree'))}"],
                }
                for item in ripple_effects
                if isinstance(item, dict)
            ],
        }
    ]
    return {
        "new_paths": new_paths,
        "logic_explanation": _norm_text(data.get("causal_deduction")),
        "risk_warning": _norm_text(data.get("dialectical_risk")),
    }


def generate_final_whitepaper(
    system_deduction_snapshot: dict,
    user_current_dilemma: str,
    provider: ProviderProxy,
) -> dict:
    prompt = (
        f"{FINAL_WHITEPAPER_PROMPT}\n\n"
        f"[system_deduction_snapshot]:\n{json.dumps(system_deduction_snapshot, ensure_ascii=False)}\n\n"
        f"[user_current_dilemma]:\n{user_current_dilemma}"
    )
    data = _call_json(prompt, provider)
    if not isinstance(data, dict):
        raise ValueError("Unexpected whitepaper output format.")

    actions = []
    for idx, action in enumerate(_as_list(data.get("mvp_actions")), start=1):
        if not isinstance(action, dict):
            continue
        actions.append(
            {
                "id": _norm_text(action.get("id")) or f"A{idx}",
                "title": _norm_text(action.get("title")) or f"行动{idx}",
                "objective": _norm_text(action.get("rationale") or action.get("objective")),
                "cost": _norm_text(action.get("estimated_days")) or "3天",
                "status": "pending",
            }
        )

    trans = data.get("contradiction_transformation", {}) if isinstance(data.get("contradiction_transformation"), dict) else {}
    unknowns = []
    for key in ("next_stage_contradiction", "dialectical_insight", "trigger_condition"):
        value = _norm_text(trans.get(key))
        if value:
            unknowns.append(value)

    result = {
        "main_conflict": _norm_text(data.get("principal_contradiction") or data.get("main_conflict")),
        "critical_warnings": [str(x) for x in _as_list(data.get("critical_warnings")) if str(x).strip()],
        "mvp_actions": actions,
        "unknowns": unknowns,
        "contradiction_transformation": trans if isinstance(trans, dict) else {},
        "raw_whitepaper": data,
    }
    if not result["main_conflict"]:
        raise ValueError("Whitepaper output missing main_conflict.")
    if not result["mvp_actions"]:
        raise ValueError("Whitepaper output missing mvp_actions.")
    return result


# Compatibility wrappers used by existing route/task modules.
def generate_facts(evidences: list[dict], provider: ProviderProxy) -> list[dict]:
    cards = generate_knowledge_cards(evidences, provider, user_initial_prompt="")
    converted = []
    for idx, card in enumerate(cards, start=1):
        audit_alerts = []
        if card.get("stance_warning"):
            audit_alerts.append({"type": "BIAS", "message": str(card["stance_warning"])})
        converted.append(
            {
                "id": card.get("id") or f"fact_{idx:03d}",
                "content": card.get("content", ""),
                "type": card.get("logical_property", "FACT"),
                "evidence_ids": card.get("evidence_ids", []),
                "counter_evidence": None,
                "audit_alerts": audit_alerts,
                "domain": card.get("domain"),
            }
        )
    return converted


def generate_sandbox_graph(profile: str, facts: list[dict], provider: ProviderProxy) -> dict:
    knowledge_cards = [
        {
            "id": f.get("id"),
            "content": f.get("content"),
            "domain": f.get("domain", "市场反馈"),
            "logical_property": f.get("type", "FACT"),
            "stance_warning": None,
            "evidence_ids": f.get("evidence_ids", []),
        }
        for f in facts
        if isinstance(f, dict)
    ]
    elements = generate_core_elements(knowledge_cards, provider)
    graph = generate_causal_graph(elements, provider, user_initial_prompt=profile)
    graph["elements_graph"] = elements
    return graph


def generate_worldline(profile: str, facts: list[dict], sandbox_graph: dict, context: dict, provider: ProviderProxy) -> dict:
    snapshot = {
        "user_initial_prompt": profile,
        "facts": facts,
        "causal_graph_snapshot": sandbox_graph,
    }
    baselines = {
        "confidence_scheme": "high_medium_low",
        "note": "No pseudo precise probability allowed.",
    }
    return generate_worldline_simulation(profile, snapshot, context or {}, baselines, provider)


def generate_whitepaper(facts: list[dict], worldline: dict, provider: ProviderProxy) -> dict:
    snapshot = {
        "facts": facts,
        "worldline": worldline,
    }
    return generate_final_whitepaper(snapshot, "", provider)
