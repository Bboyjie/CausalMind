from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

test_db_path = Path("/tmp/wolong_backend_test.db")
if test_db_path.exists():
    test_db_path.unlink()
os.environ["APP_DB_PATH"] = str(test_db_path)
os.environ["CRAWLER_ENABLED"] = "false"
os.environ["LLM_ENABLED"] = "false"

from app.api import routes
from app.db.database import SessionLocal, init_db
from app.workers.huey_app import huey
from app.schemas.dto import (
    CaseFeedbackRequest,
    CreateCaseRequest,
    FactFeedbackRequest,
    SandboxInterveneRequest,
    SandboxInterventionNode,
    WorldlineInterveneRequest,
)


def test_cycle_end_to_end_route_functions():
    init_db()
    huey.immediate = True
    db = SessionLocal()
    try:
        created = routes.create_case(CreateCaseRequest(profile="潍坊 大专 三年经验 程序员 转型"), db)
        case_id = created["data"]["id"]

        strategy = routes.generate_search_strategy(case_id, db)
        assert strategy["data"]["recommended_limit"] == 100

        start = routes.start_collection(case_id, db)
        assert start["message"] == "Collection started"

        status = {}
        for _ in range(4):
            status = routes.collection_status(case_id, db)
        assert status["data"]["status"] == "COMPLETED"
        assert status["data"]["progress"] == 100

        facts = routes.get_facts(case_id, db)
        assert len(facts["data"]) >= 1
        fact_id = facts["data"][0]["id"]

        evidences = routes.get_evidences(case_id, db)
        assert len(evidences["data"]) >= 1

        fact_feedback = routes.submit_fact_feedback(
            case_id, fact_id, FactFeedbackRequest(feedback_type="CONFIRMED", comment="looks good"), db
        )
        assert fact_feedback["message"] == "Feedback received"

        sandbox = routes.get_sandbox(case_id, db)
        assert len(sandbox["data"]["nodes"]) >= 1

        sandbox_result = routes.sandbox_intervene(
            case_id,
            SandboxInterveneRequest(interventions=[SandboxInterventionNode(node_id="n5", new_val=1)]),
            db,
        )
        assert sandbox_result["data"]["affected_nodes"][0]["id"] == "n2"

        context_result = routes.put_context(case_id, {"city": "潍坊", "salary_floor": 7000}, db)
        assert context_result["message"] == "个人语境已注入成功"

        with pytest.raises(HTTPException) as worldline_exc:
            routes.get_worldline(case_id, db)
        assert worldline_exc.value.status_code == 400

        with pytest.raises(HTTPException) as intervene_exc:
            routes.worldline_intervene(case_id, WorldlineInterveneRequest(text="接受外包并降薪"), db)
        assert intervene_exc.value.status_code == 400

        with pytest.raises(HTTPException) as whitepaper_exc:
            routes.get_whitepaper(case_id, db)
        assert whitepaper_exc.value.status_code == 400

        feedback = routes.submit_case_feedback(
            case_id, CaseFeedbackRequest(feedback_type="GENERAL", payload={"rating": 5}), db
        )
        assert feedback["message"] == "反馈已记录"
    finally:
        db.close()
