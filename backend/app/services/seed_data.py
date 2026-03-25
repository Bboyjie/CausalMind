from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Evidence, Fact, FactAuditAlert, SandboxGraph, Whitepaper, Worldline


DEFAULT_FACTS = [
    {
        "id": "fact_001",
        "content": "潍坊本地缺少大型互联网公司，IT岗位主要集中在传统企业的数字化外包或甲方内部IT。",
        "type": "FACT",
        "evidence_ids": ["doc_12_span_3", "doc_45_span_1"],
        "audit_alerts": [
            {
                "type": "BIAS",
                "message": "可能存在幸存者偏差：发声者多为外包员工，部分隐形的高薪国企岗位较少在公开论坛讨论。",
            }
        ],
        "counter_evidence": "部分初创AI公司最近在潍坊落户（来源: doc_88）",
    },
    {
        "id": "fact_002",
        "content": "三年专科经验跳槽，如果在北上广薪资可达15k，但在该地大概率会被压价至 6k-8k。",
        "type": "INFERENCE",
        "evidence_ids": ["doc_09_span_1"],
        "audit_alerts": [],
        "counter_evidence": None,
    },
    {
        "id": "fact_003",
        "content": "大部分公司不要求微服务或高并发经验，更看重全栈能力（Vue + SpringBoot 独立开发能力）。",
        "type": "FACT",
        "evidence_ids": ["doc_10_span_2"],
        "audit_alerts": [],
        "counter_evidence": None,
    },
    {
        "id": "fact_004",
        "content": "只要你愿意接受996和单休，在当地依然很容易找到工作。",
        "type": "ASSUMPTION",
        "evidence_ids": [],
        "audit_alerts": [
            {
                "type": "RISK",
                "message": "逻辑跳跃：很多贴吧反馈即使接受单休也难以拿到面试机会，存在夸大风险。",
            }
        ],
        "counter_evidence": "多位三年经验开发者表示投出上百份简历仍石沉大海。",
    },
]

DEFAULT_EVIDENCES = [
    {
        "evidence_id": "doc_12_span_3",
        "source_name": "知乎某招聘贴",
        "url": "https://mock.zhihu.com/question/123",
        "content": "...在潍坊找开发工作太难了，基本<mark>没有纯正的互联网大厂，全是在给传统制造企业做外包集成</mark>，工资也就那样...",
    },
    {
        "evidence_id": "doc_45_span_1",
        "source_name": "脉脉职言",
        "url": "https://mock.maimai.cn/news/456",
        "content": "...别提了，<mark>全是化工和农业企业的内包IT</mark>，写一辈子CRUD...",
    },
    {
        "evidence_id": "doc_09_span_1",
        "source_name": "牛客网讨论区",
        "url": "https://mock.nowcoder.com/11",
        "content": "我<mark>三年大专前端，在北京能拿16k，回老家面试最多只给到7.5k</mark>，直接腰斩还要多...",
    },
    {
        "evidence_id": "doc_10_span_2",
        "source_name": "BOSS直聘 JD 分析",
        "url": "#",
        "content": "看了下招聘软件，<mark>要求都是一条龙，前端后端运维一把抓的优先</mark>，高并发没人提。",
    },
]

DEFAULT_SANDBOX = {
    "nodes": [
        {"id": "n1", "name": "大专学历门槛", "status": "fixed", "type": "objective", "val": 1},
        {"id": "n2", "name": "面试邀请率", "status": "variable", "type": "objective", "val": 0.3},
        {"id": "n3", "name": "脱产备考期", "status": "variable", "type": "action", "val": 0},
        {"id": "n4", "name": "期望薪资(>10k)", "status": "variable", "type": "action", "val": 1},
        {"id": "n5", "name": "外包接受度", "status": "variable", "type": "action", "val": 0},
    ],
    "edges": [
        {"source": "n1", "target": "n2", "polarity": "negative", "desc": "学历限制导致简历初审被刷"},
        {"source": "n3", "target": "n2", "polarity": "negative", "desc": "脱产时间越久，HR顾虑越大"},
        {"source": "n4", "target": "n2", "polarity": "negative", "desc": "当地薪资中位数低，高期望致使匹配度下降"},
        {"source": "n5", "target": "n2", "polarity": "positive", "desc": "接受外包能大幅增加流程推进的概率"},
    ],
}

DEFAULT_WORLDLINE = {
    "timeline": ["T + 6个月", "T + 1年", "T + 3年"],
    "paths": [
        {
            "type": "baseline",
            "color": "info",
            "nodes": [
                {"time": "T + 6个月", "desc": "耗尽积蓄，仍未获得满意的开发岗Offer", "triggers": ["未主动降薪", "未改变求职地域"]},
                {"time": "T + 1年", "desc": "开始妥协，进入潍坊某传统制造厂IT部", "triggers": ["资金链断裂"]},
            ],
        },
        {
            "type": "best_case",
            "color": "success",
            "nodes": [
                {"time": "T + 6个月", "desc": "通过低薪外包入行，积累了第一套成熟的微服务实施经验", "triggers": ["接受首年薪资折损(仅6-8k)"]},
                {"time": "T + 1年", "desc": "跳板成功，跳槽至本地数字农业核心企业", "triggers": ["沉淀了完整的项目架构经验"]},
            ],
        },
        {
            "type": "worst_case",
            "color": "danger",
            "nodes": [
                {"time": "T + 6个月", "desc": "持续空窗，技术栈生疏，产生求职焦虑", "triggers": ["拒绝所有低于预期的外包和传统厂"]},
                {"time": "T + 3年", "desc": "彻底转行退出IT业", "triggers": ["脱离IT圈子过久"]},
            ],
        },
    ],
}

DEFAULT_WHITEPAPER = {
    "main_conflict": "当前脱产备考导致的‘应届生身份流失’与‘潍坊本地偏好即插即用熟练工’之间的结构性矛盾。",
    "critical_warnings": ["脱产期限若超过6个月，简历被初筛淘汰的概率将呈指数级上升。"],
    "mvp_actions": [
        {
            "id": "act_1",
            "title": "测试水温：盲投3份本地最差的外包岗位",
            "objective": "验证本地HR对‘三年专科空窗期’的真实压价底线，而不是继续在家闭门造车。",
            "cost": "只需2天时间试错",
            "status": "pending",
        },
        {
            "id": "act_2",
            "title": "更新个人语境：预设下底线薪水",
            "objective": "明确‘接受降薪先入行’的决心点，防止焦虑蔓延。",
            "cost": "内心博弈1天",
            "status": "pending",
        },
    ],
    "unknowns": ["潍坊本地几家头部制造企业的内部IT是否会在Q3释放校招/社招补录名额？（建议实地打听或托人脉摸排）"],
}


def ensure_case_seed_data(db: Session, case_id: str) -> None:
    has_fact = db.scalar(select(Fact.id).where(Fact.case_id == case_id).limit(1))
    if not has_fact:
        for item in DEFAULT_FACTS:
            fact = Fact(
                fact_id=item["id"],
                case_id=case_id,
                content=item["content"],
                type=item["type"],
                evidence_ids=item["evidence_ids"],
                counter_evidence=item["counter_evidence"],
            )
            db.add(fact)
            db.flush()
            for alert in item["audit_alerts"]:
                db.add(FactAuditAlert(fact_row_id=fact.id, type=alert["type"], message=alert["message"]))

    has_evidence = db.scalar(select(Evidence.id).where(Evidence.case_id == case_id).limit(1))
    if not has_evidence:
        for item in DEFAULT_EVIDENCES:
            db.add(
                Evidence(
                    evidence_id=item["evidence_id"],
                    case_id=case_id,
                    source_name=item["source_name"],
                    url=item["url"],
                    content=item["content"],
                )
            )

    graph = db.scalar(select(SandboxGraph).where(SandboxGraph.case_id == case_id).limit(1))
    if not graph:
        db.add(SandboxGraph(case_id=case_id, nodes=DEFAULT_SANDBOX["nodes"], edges=DEFAULT_SANDBOX["edges"]))
    elif not graph.nodes:
        graph.nodes = DEFAULT_SANDBOX["nodes"]
        graph.edges = DEFAULT_SANDBOX["edges"]

    worldline = db.scalar(select(Worldline).where(Worldline.case_id == case_id).limit(1))
    if not worldline:
        db.add(Worldline(case_id=case_id, timeline=DEFAULT_WORLDLINE["timeline"], paths=DEFAULT_WORLDLINE["paths"]))
    elif not worldline.timeline or not worldline.paths:
        worldline.timeline = DEFAULT_WORLDLINE["timeline"]
        worldline.paths = DEFAULT_WORLDLINE["paths"]

    whitepaper = db.scalar(select(Whitepaper).where(Whitepaper.case_id == case_id).limit(1))
    if not whitepaper:
        db.add(
            Whitepaper(
                case_id=case_id,
                main_conflict=DEFAULT_WHITEPAPER["main_conflict"],
                critical_warnings=DEFAULT_WHITEPAPER["critical_warnings"],
                mvp_actions=DEFAULT_WHITEPAPER["mvp_actions"],
                unknowns=DEFAULT_WHITEPAPER["unknowns"],
            )
        )
    elif not whitepaper.main_conflict:
        whitepaper.main_conflict = DEFAULT_WHITEPAPER["main_conflict"]
        whitepaper.critical_warnings = DEFAULT_WHITEPAPER["critical_warnings"]
        whitepaper.mvp_actions = DEFAULT_WHITEPAPER["mvp_actions"]
        whitepaper.unknowns = DEFAULT_WHITEPAPER["unknowns"]
