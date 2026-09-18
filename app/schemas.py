from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    normalized_name: str
    country: str | None = None
    city: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    buyer_type: str | None = None
    source: str
    lead_score: float
    lead_score_components: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


class LeadScoreRequest(BaseModel):
    name: str
    country: str | None = None
    city: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    buyer_type: str | None = None


class LeadScoreResponse(BaseModel):
    score: float
    components: dict[str, Any]


class ScrapeRequest(BaseModel):
    url: str
    render_javascript: bool = False
    max_results: int = Field(default=50, ge=1, le=200)
    item_selector: str = "article, li, .company, .company-card, .listing, [class*=company], [class*=listing]"
    name_selector: str = "h1, h2, h3, h4, .name, .company-name, [class*=title]"


class ScrapedLead(BaseModel):
    name: str
    country: str | None = None
    city: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    buyer_type: str | None = None
    source_url: str
    lead_score: float


class ScrapeResponse(BaseModel):
    source_url: str
    render_javascript: bool
    leads: list[ScrapedLead]
    warnings: list[str] = []
