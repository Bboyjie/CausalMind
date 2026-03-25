from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, utcnow


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SearchStrategy(Base):
    __tablename__ = "search_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    recommended_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CollectionTask(Base):
    __tablename__ = "collection_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="RUNNING", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Phase 1: Scraping
    current_platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    total_scraped: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Phase 2: LLM Filtering
    filtering_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    filtering_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filtered_ads: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filtered_duplicates: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filtered_emotional_venting: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_sources: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_facts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Fact(Base):
    __tablename__ = "facts"
    __table_args__ = (UniqueConstraint("case_id", "fact_id", name="uq_fact_case_fact_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fact_id: Mapped[str] = mapped_column(String(64), nullable=False)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    counter_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.fact_id,
            "content": self.content,
            "type": self.type,
            "evidence_ids": self.evidence_ids,
            "counter_evidence": self.counter_evidence,
        }


class FactAuditAlert(Base):
    __tablename__ = "fact_audit_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fact_row_id: Mapped[int] = mapped_column(Integer, ForeignKey("facts.id"), index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class AuditElementCache(Base):
    __tablename__ = "audit_element_caches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), unique=True, index=True)
    facts_signature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    elements_graph: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Evidence(Base):
    __tablename__ = "evidences"
    __table_args__ = (UniqueConstraint("case_id", "evidence_id", name="uq_evidence_case_evidence_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FactFeedback(Base):
    __tablename__ = "fact_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    fact_id: Mapped[str] = mapped_column(String(64), index=True)
    feedback_type: Mapped[str] = mapped_column(String(32), default="GENERAL", nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SandboxGraph(Base):
    __tablename__ = "sandbox_graphs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), unique=True, index=True)
    nodes: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    edges: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SandboxIntervention(Base):
    __tablename__ = "sandbox_interventions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    affected_nodes: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    logic_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    risk_warning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserContext(Base):
    __tablename__ = "user_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), unique=True, index=True)
    context_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Worldline(Base):
    __tablename__ = "worldlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), unique=True, index=True)
    timeline: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    paths: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WorldlineIntervention(Base):
    __tablename__ = "worldline_interventions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    new_paths: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    logic_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    risk_warning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Whitepaper(Base):
    __tablename__ = "whitepapers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), unique=True, index=True)
    main_conflict: Mapped[str] = mapped_column(Text, nullable=False)
    critical_warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    mvp_actions: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    unknowns: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CaseFeedback(Base):
    __tablename__ = "case_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), ForeignKey("cases.id"), index=True)
    feedback_type: Mapped[str] = mapped_column(String(32), default="GENERAL", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=utcnow)
