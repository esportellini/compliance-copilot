"""Relatórios agregados — respeitam RBAC por papel."""
import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Role
from app.db.session import get_db
from app.models.copilot import CopilotAnswer, CopilotQuery, SourceReference
from app.models.document import PolicyDocument
from app.models.pre_approval import PreApprovalRequest
from app.models.rule import ComplianceRule
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


def _date_range(days: int = 30):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start, end


def _base_query_filter(q, user: User):
    """Empregados enxergam apenas suas próprias consultas."""
    if Role(user.role) == Role.EMPLOYEE:
        q = q.filter(CopilotQuery.user_id == user.id)
    return q


@router.get("/summary")
def summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, end = _date_range(days)

    # consultas por decisão
    base = _base_query_filter(db.query(CopilotQuery), user)
    period = base.filter(CopilotQuery.created_at.between(start, end))

    total_queries = period.count()

    by_decision_raw = (
        db.query(CopilotAnswer.decision, func.count().label("n"))
        .join(CopilotQuery, CopilotAnswer.query_id == CopilotQuery.id)
        .filter(CopilotQuery.created_at.between(start, end))
    )
    if Role(user.role) == Role.EMPLOYEE:
        by_decision_raw = by_decision_raw.filter(CopilotQuery.user_id == user.id)
    by_decision = {d: n for d, n in by_decision_raw.group_by(CopilotAnswer.decision).all()}

    # por risco
    by_risk_raw = (
        db.query(CopilotAnswer.risk_level, func.count().label("n"))
        .join(CopilotQuery, CopilotAnswer.query_id == CopilotQuery.id)
        .filter(CopilotQuery.created_at.between(start, end))
    )
    if Role(user.role) == Role.EMPLOYEE:
        by_risk_raw = by_risk_raw.filter(CopilotQuery.user_id == user.id)
    by_risk = {r: n for r, n in by_risk_raw.group_by(CopilotAnswer.risk_level).all()}

    # consultas por dia
    daily_raw = (
        db.query(
            func.date_trunc("day", CopilotQuery.created_at).label("day"),
            func.count().label("n"),
        )
        .filter(CopilotQuery.created_at.between(start, end))
    )
    if Role(user.role) == Role.EMPLOYEE:
        daily_raw = daily_raw.filter(CopilotQuery.user_id == user.id)
    queries_by_day = [
        {"date": str(r.day.date()), "count": r.n}
        for r in daily_raw.group_by("day").order_by("day").all()
    ]

    # inconclusivas
    inconclusive = by_decision.get("INCONCLUSIVE", 0)
    pct_inconclusive = round(inconclusive / total_queries * 100, 1) if total_queries else 0

    return {
        "period_days": days,
        "total_queries": total_queries,
        "by_decision": by_decision,
        "by_risk": by_risk,
        "queries_by_day": queries_by_day,
        "inconclusive_count": inconclusive,
        "inconclusive_pct": pct_inconclusive,
    }


@router.get("/top-products")
def top_products(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, _ = _date_range(days)
    q = (
        db.query(CopilotQuery.product_type, func.count().label("n"))
        .filter(
            CopilotQuery.created_at >= start,
            CopilotQuery.product_type.isnot(None),
        )
    )
    if Role(user.role) == Role.EMPLOYEE:
        q = q.filter(CopilotQuery.user_id == user.id)
    rows = q.group_by(CopilotQuery.product_type).order_by(func.count().desc()).limit(limit).all()
    return [{"product_type": r[0], "count": r[1]} for r in rows]


@router.get("/pre-approvals-by-status")
def pre_approvals_by_status(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, _ = _date_range(days)
    q = db.query(PreApprovalRequest.status, func.count().label("n")).filter(
        PreApprovalRequest.created_at >= start
    )
    if Role(user.role) == Role.EMPLOYEE:
        q = q.filter(PreApprovalRequest.requester_id == user.id)
    rows = q.group_by(PreApprovalRequest.status).all()
    return {r[0]: r[1] for r in rows}


@router.get("/top-documents")
def top_documents(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Documentos mais citados como fonte pelo Copilot."""
    start, _ = _date_range(days)
    rows = (
        db.query(SourceReference.document_name, func.count().label("n"))
        .join(CopilotAnswer, SourceReference.answer_id == CopilotAnswer.id)
        .join(CopilotQuery, CopilotAnswer.query_id == CopilotQuery.id)
        .filter(CopilotQuery.created_at >= start)
        .group_by(SourceReference.document_name)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )
    return [{"document_name": r[0], "count": r[1]} for r in rows]


@router.get("/top-rules")
def top_rules(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Regras mais aplicadas (extraídas do campo JSONB matched_rules)."""
    start, _ = _date_range(days)
    answers = (
        db.query(CopilotAnswer.matched_rules)
        .join(CopilotQuery, CopilotAnswer.query_id == CopilotQuery.id)
        .filter(CopilotQuery.created_at >= start, CopilotAnswer.matched_rules.isnot(None))
        .all()
    )
    counter: dict[str, int] = {}
    for (rules,) in answers:
        if isinstance(rules, list):
            for r in rules:
                counter[r] = counter.get(r, 0) + 1
    sorted_rules = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:20]
    return [{"rule": k, "count": v} for k, v in sorted_rules]


@router.get("/export/csv")
def export_summary_csv(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, end = _date_range(days)
    q = (
        db.query(CopilotQuery, CopilotAnswer)
        .outerjoin(CopilotAnswer, CopilotAnswer.query_id == CopilotQuery.id)
        .filter(CopilotQuery.created_at.between(start, end))
    )
    if Role(user.role) == Role.EMPLOYEE:
        q = q.filter(CopilotQuery.user_id == user.id)
    rows = q.order_by(CopilotQuery.created_at.desc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "data", "pergunta", "tipo_produto", "valor", "decisao", "risco", "confianca", "revisao_humana"])
    for query, answer in rows:
        writer.writerow([
            query.id,
            query.created_at.strftime("%Y-%m-%d %H:%M") if query.created_at else "",
            query.question[:120],
            query.product_type or "",
            query.amount or "",
            answer.decision if answer else "",
            answer.risk_level if answer else "",
            f"{answer.confidence:.0%}" if answer else "",
            "Sim" if (answer and answer.requires_human_review) else "Não",
        ])

    buf.seek(0)
    fname = f"relatorio_consultas_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
