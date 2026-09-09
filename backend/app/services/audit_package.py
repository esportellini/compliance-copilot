from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.pre_approval import PreApprovalRequest
from app.models.product import FinancialProduct
from app.models.user import User

DISCLAIMER = "Educational/demo artifact. It is not legal, regulatory, financial, or investment advice."


def build_audit_package(db: Session, request: PreApprovalRequest) -> dict:
    requester = db.get(User, request.requester_id)
    product = db.get(FinancialProduct, request.product_id) if request.product_id else None
    query = request.source_query
    answer = query.answer if query else None
    events = db.query(AuditLog).filter_by(entity="pre_approval_requests", entity_id=request.id).order_by(AuditLog.created_at).all()
    return {
        "header": {"request_id": request.id, "generated_at": datetime.now(timezone.utc).isoformat(), "status": request.status},
        "request": {
            "requester": requester.email if requester else f"user:{request.requester_id}",
            "product": request.product_label,
            "identifier": product.identifier if product else None,
            "operation": request.operation_type,
            "amount": request.estimated_amount,
            "created_at": request.created_at.isoformat(),
            "due_at": request.due_at.isoformat() if request.due_at else None,
        },
        "initial_analysis": {
            "source_query_id": request.source_query_id,
            "question": query.question if query else None,
            "decision": request.copilot_initial_decision,
            "risk": answer.risk_level if answer else None,
            "next_action": answer.next_action if answer else None,
            "rule_provenance": (answer.rule_provenance or []) if answer else [],
        },
        "documentary_evidence": [
            {"document": source.document_name, "version": source.document_version, "section": source.section_title, "page": source.page_number, "excerpt": source.excerpt, "relevance": source.score}
            for source in (answer.sources if answer else [])
        ],
        "human_workflow": {
            "review_started_at": request.review_started_at.isoformat() if request.review_started_at else None,
            "reviewer": request.reviewer,
            "comments": [{"author": comment.author_name, "body": comment.body, "created_at": comment.created_at.isoformat()} for comment in request.comments],
            "final_opinion": request.compliance_opinion,
            "status": request.status,
            "decided_at": request.decided_at.isoformat() if request.decided_at else None,
        },
        "audit_events": [{"type": event.event_type, "actor": event.actor_label, "message": event.message, "created_at": event.created_at.isoformat(), "meta": event.meta or {}} for event in events],
        "disclaimer": DISCLAIMER,
    }


def render_audit_package_pdf(package: dict) -> bytes:
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title=f"Compliance Copilot Audit Package #{package['header']['request_id']}")
    story = [Paragraph("Compliance Copilot", styles["Title"]), Paragraph(f"Audit Package #{package['header']['request_id']}", styles["Heading2"]), Spacer(1, 5 * mm)]
    request = package["request"]
    rows = [["Status", package["header"]["status"]], ["Requester", request["requester"]], ["Product", request["product"] or "-"], ["Identifier", request["identifier"] or "-"], ["Operation", request["operation"]], ["Amount", str(request["amount"] or "-")], ["Created", request["created_at"]], ["Due", request["due_at"] or "-"]]
    table = Table(rows, colWidths=[38 * mm, 120 * mm]); table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#d9ded7")), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f2ed")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]))
    story.extend([table, Spacer(1, 6 * mm), Paragraph("Initial automated analysis", styles["Heading2"]), Paragraph(escape(str(package["initial_analysis"]["decision"] or "-")), styles["BodyText"])])
    for rule in package["initial_analysis"]["rule_provenance"]:
        story.append(Paragraph(escape(f"{rule['name']} — {rule['rule_key']} v{rule['version']} · priority {rule['priority']}"), styles["BodyText"]))
    story.extend([Spacer(1, 4 * mm), Paragraph("Documentary evidence", styles["Heading2"])])
    for source in package["documentary_evidence"]:
        story.append(Paragraph(escape(f"{source['document']} v{source['version'] or '-'} · {source['section'] or '-'} · p. {source['page'] or '-'}"), styles["Heading3"]))
        story.append(Paragraph(escape(source["excerpt"]), styles["BodyText"]))
    workflow = package["human_workflow"]
    story.extend([
        Spacer(1, 4 * mm),
        Paragraph("Human workflow", styles["Heading2"]),
        Paragraph(escape(f"Reviewer: {workflow['reviewer'] or '-'} · Final status: {workflow['status']}"), styles["BodyText"]),
        Paragraph(escape(f"Final opinion: {workflow['final_opinion'] or '-'}"), styles["BodyText"]),
    ])
    for comment in package["human_workflow"]["comments"]:
        story.append(Paragraph(escape(f"{comment['author']}: {comment['body']}"), styles["BodyText"]))
    story.extend([PageBreak(), Paragraph("Related audit events", styles["Heading2"])])
    for event in package["audit_events"]:
        story.append(Paragraph(escape(f"{event['created_at']} · {event['type']} · {event['message']}"), styles["BodyText"]))
    story.extend([Spacer(1, 8 * mm), Paragraph(escape(package["disclaimer"]), styles["Italic"])])
    doc.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
    return buffer.getvalue()


def _page_number(canvas, doc):
    canvas.saveState(); canvas.setFont("Helvetica", 8); canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}"); canvas.restoreState()
