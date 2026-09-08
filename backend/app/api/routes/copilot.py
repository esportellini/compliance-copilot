from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Role
from app.db.session import get_db
from app.models.copilot import CopilotAnswer, CopilotQuery
from app.models.user import User
from app.schemas.copilot import (
    CopilotAnswerOut,
    CopilotHistoryDetail,
    CopilotHistoryItem,
    CopilotQueryRequest,
    SourceOut,
)
from app.schemas.enums import Decision, RiskLevel
from app.services.copilot import CopilotInput, run_query

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/query", response_model=CopilotAnswerOut)
def query_copilot(
    payload: CopilotQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inp = CopilotInput(
        user_id=user.id,
        question=payload.question,
        product_type=payload.product_type,
        product_id=payload.product_id,
        product_name_hint=payload.product_name_hint,
        amount=payload.amount,
        objective=payload.objective,
    )
    result = run_query(inp, db)
    return CopilotAnswerOut(
        query_id=result.query_id,
        decision=Decision(result.decision),
        answer=result.answer,
        justification=result.justification,
        sources=[SourceOut(**s) for s in result.sources],
        confidence=result.confidence,
        risk_level=RiskLevel(result.risk_level),
        next_action=result.next_action,
        requires_human_review=result.requires_human_review,
        matched_rules=result.matched_rules,
        out_of_scope=result.out_of_scope,
    )


@router.get("/history", response_model=list[CopilotHistoryItem])
def history(
    decision: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    product_type: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    q = db.query(CopilotQuery)

    # empregados veem apenas as próprias consultas
    if Role(user.role) == Role.EMPLOYEE:
        q = q.filter(CopilotQuery.user_id == user.id)

    if product_type:
        q = q.filter(CopilotQuery.product_type == product_type)

    if date_from:
        try:
            q = q.filter(CopilotQuery.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(CopilotQuery.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    rows = q.order_by(CopilotQuery.created_at.desc()).limit(300).all()

    result = []
    for row in rows:
        ans = row.answer
        if decision and (not ans or ans.decision != decision):
            continue
        if risk_level and (not ans or ans.risk_level != risk_level):
            continue
        result.append(CopilotHistoryItem(
            id=row.id,
            question=row.question,
            product_type=row.product_type,
            amount=row.amount,
            decision=ans.decision if ans else "INCONCLUSIVE",
            risk_level=ans.risk_level if ans else "MEDIUM",
            confidence=ans.confidence if ans else 0.0,
            requires_human_review=ans.requires_human_review if ans else False,
            created_at=row.created_at,
        ))
    return result


@router.get("/history/{query_id}", response_model=CopilotHistoryDetail)
def history_detail(
    query_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(CopilotQuery, query_id)
    if not row:
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    if Role(user.role) == Role.EMPLOYEE and row.user_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    ans = row.answer
    if not ans:
        raise HTTPException(status_code=404, detail="Resposta não disponível")

    return CopilotHistoryDetail(
        id=row.id,
        question=row.question,
        product_type=row.product_type,
        product_id=row.product_id,
        amount=row.amount,
        objective=row.objective,
        created_at=row.created_at,
        answer=CopilotAnswerOut(
            query_id=row.id,
            decision=Decision(ans.decision),
            answer=ans.answer,
            justification=ans.justification,
            sources=[
                SourceOut(
                    document_id=s.document_id,
                    chunk_id=s.chunk_id,
                    document_name=s.document_name,
                    excerpt=s.excerpt,
                    score=s.score,
                    page_number=s.page_number,
                    section_title=s.section_title,
                )
                for s in ans.sources
            ],
            confidence=ans.confidence,
            risk_level=RiskLevel(ans.risk_level),
            next_action=ans.next_action,
            requires_human_review=ans.requires_human_review,
            matched_rules=ans.matched_rules or [],
        ),
    )
