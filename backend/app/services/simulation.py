from __future__ import annotations

from app.api.deps import ProviderProxy
from app.services.llm import generate_causal_intervention, generate_worldline_intervention


def simulate_sandbox(
    interventions: list[dict],
    text: str,
    profile: str,
    graph: dict,
    provider: ProviderProxy | None = None,
) -> dict:
    if provider:
        try:
            result = generate_causal_intervention(
                causal_graph_snapshot=graph,
                user_intervention_text=text or str(interventions),
                user_initial_prompt=profile,
                provider=provider,
            )
            return {
                "affected_nodes": result.get("affected_nodes", []),
                "logic_explanation": result.get("logic_explanation", ""),
                "risk_warning": result.get("risk_warning", ""),
            }
        except Exception as e:
            print(f"Sandbox simulate LLM fallback: {e}")

    # Lightweight fallback when no provider available.
    trend = "up" if text else "flat"
    val = 0.6 if text else 0.5
    target = "n2"
    return {
        "affected_nodes": [{"id": target or "n1", "new_val": val, "trend": trend}],
        "logic_explanation": "未配置模型，返回规则引擎推演结果。",
        "risk_warning": "",
    }


def simulate_worldline(
    text: str,
    profile: str,
    current_worldline: dict,
    graph: dict,
    provider: ProviderProxy | None = None,
) -> dict:
    if not provider or not provider.apiKey:
        raise RuntimeError("世界线干预未配置可用模型，请先在设置中完成 worldline 阶段模型配置。")
    return generate_worldline_intervention(
        current_worldline=current_worldline,
        user_intervention_text=text,
        causal_graph=graph,
        provider=provider,
        user_initial_prompt=profile,
    )
