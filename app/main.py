from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db, init_db
from app.core.models import Company
from app.schemas import CompanyRead, ImportResult, LeadScoreRequest, LeadScoreResponse
from app.services.importer import calculate_lead_score_breakdown, import_excel, map_columns

app = FastAPI(title="Cashew Market Intelligence API", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/companies", response_model=list[CompanyRead])
def list_companies(
    search: str | None = None,
    country: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Company]:
    query = select(Company).order_by(Company.lead_score.desc(), Company.name).limit(min(limit, 500))
    if search:
        query = query.where(Company.name.ilike(f"%{search}%"))
    if country:
        query = query.where(Company.country.ilike(f"%{country}%"))
    return list(db.scalars(query).all())


@app.get("/leads", response_model=list[CompanyRead])
def list_leads(
    search: str | None = None,
    country: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Company]:
    return list_companies(search=search, country=country, limit=limit, db=db)


@app.post("/leads/score", response_model=LeadScoreResponse)
def score_lead(payload: LeadScoreRequest) -> LeadScoreResponse:
    raw = payload.model_dump()
    mapping = map_columns(raw.keys())
    breakdown = calculate_lead_score_breakdown(raw, mapping)
    return LeadScoreResponse(score=breakdown["score"], components=breakdown)


@app.post("/imports/excel", response_model=ImportResult)
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)) -> ImportResult:
    if not file.filename or Path(file.filename).suffix.lower() not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Upload an .xlsx or .xls file")
    content = await file.read()
    with NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=True) as temporary_file:
        temporary_file.write(content)
        temporary_file.flush()
        try:
            imported, skipped, errors = import_excel(temporary_file.name, db)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    return ImportResult(imported=imported, skipped=skipped, errors=errors)
