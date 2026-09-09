import csv
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_compliance, require_global_view
from app.core.identifiers import normalize_identifier
from app.db.session import get_db
from app.models.restricted import RestrictedListItem
from app.models.user import User
from app.services.audit import log_event

router = APIRouter(prefix="/restricted-list", tags=["restricted-list"])
HEADERS = ["identifier", "name", "reason", "active"]
MAX_BYTES = 1_000_000
MAX_ROWS = 1_000


class ImportRow(BaseModel):
    line: int
    identifier: str
    name: str
    reason: str | None = None
    active: bool
    action: str


class ImportPreview(BaseModel):
    filename: str
    rows: list[ImportRow]


def _error(line: int, message: str) -> dict:
    return {"line": line, "message": message}


def _parse(content: bytes, filename: str, db: Session) -> ImportPreview:
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="CSV excede 1 MB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail=[_error(1, "Arquivo deve usar UTF-8")]) from exc
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames != HEADERS:
        raise HTTPException(status_code=422, detail=[_error(1, f"Header esperado: {','.join(HEADERS)}")])
    existing = {item.identifier: item for item in db.query(RestrictedListItem).all()}
    seen: set[str] = set()
    rows: list[ImportRow] = []
    errors: list[dict] = []
    try:
        raw_rows = list(reader)
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail=[_error(reader.line_num, "Linha CSV malformada")]) from exc
    if len(raw_rows) > MAX_ROWS:
        raise HTTPException(status_code=413, detail="CSV excede 1000 linhas")
    for line, raw in enumerate(raw_rows, 2):
        if None in raw:
            errors.append(_error(line, "Linha CSV possui colunas extras")); continue
        identifier = normalize_identifier(raw.get("identifier"))
        name = (raw.get("name") or "").strip()
        active_text = (raw.get("active") or "").strip().lower()
        if not identifier:
            errors.append(_error(line, "identifier vazio")); continue
        if identifier in seen:
            errors.append(_error(line, "identifier duplicado após normalização")); continue
        seen.add(identifier)
        if not name:
            errors.append(_error(line, "name vazio")); continue
        if active_text not in {"true", "false"}:
            errors.append(_error(line, "active deve ser true ou false")); continue
        active = active_text == "true"
        reason = (raw.get("reason") or "").strip() or None
        current = existing.get(identifier)
        if current is None:
            action = "ADD"
        elif (current.name, current.reason, current.active) == (name, reason, active):
            action = "NO_CHANGE"
        elif current.active and not active:
            action = "DEACTIVATE"
        else:
            action = "UPDATE"
        rows.append(ImportRow(line=line, identifier=identifier, name=name, reason=reason, active=active, action=action))
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return ImportPreview(filename=Path(filename).name[:255], rows=rows)


@router.get("")
def list_items(db: Session = Depends(get_db), _: User = Depends(require_global_view)):
    return db.query(RestrictedListItem).order_by(RestrictedListItem.identifier).all()


@router.post("/import/preview", response_model=ImportPreview)
async def preview_import(file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(require_compliance)):
    return _parse(await file.read(), file.filename or "restricted-list.csv", db)


@router.post("/import/apply")
def apply_import(payload: ImportPreview, db: Session = Depends(get_db), actor: User = Depends(require_compliance)):
    identifiers = [normalize_identifier(row.identifier) for row in payload.rows]
    if None in identifiers or len(set(identifiers)) != len(identifiers):
        raise HTTPException(status_code=422, detail="Preview contém identifiers inválidos ou duplicados")
    existing = {item.identifier: item for item in db.query(RestrictedListItem).filter(RestrictedListItem.identifier.in_(identifiers)).all()}
    added = updated = deactivated = unchanged = 0
    for row in payload.rows:
        identifier = normalize_identifier(row.identifier)
        current = existing.get(identifier)
        if current is None:
            current = RestrictedListItem(identifier=identifier, name=row.name.strip(), reason=row.reason, active=row.active)
            db.add(current); existing[identifier] = current; added += 1
        elif (current.name, current.reason, current.active) == (row.name.strip(), row.reason, row.active):
            unchanged += 1
        else:
            if current.active and not row.active: deactivated += 1
            current.name, current.reason, current.active = row.name.strip(), row.reason, row.active
            updated += 1
    log_event(db, "RESTRICTED_LIST_IMPORTED", f"Lista restrita importada: {len(payload.rows)} linhas", user_id=actor.id, actor_label=actor.email, entity="restricted_list_items", meta={"filename": Path(payload.filename).name[:255], "total_rows": len(payload.rows), "added": added, "updated": updated, "deactivated": deactivated, "unchanged": unchanged})
    db.commit()
    return {"total_rows": len(payload.rows), "added": added, "updated": updated, "deactivated": deactivated, "unchanged": unchanged}


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db), _: User = Depends(require_global_view)):
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(HEADERS)
    for item in db.query(RestrictedListItem).order_by(RestrictedListItem.identifier).all():
        writer.writerow([item.identifier, item.name, item.reason or "", str(item.active).lower()])
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=restricted-list.csv"})
