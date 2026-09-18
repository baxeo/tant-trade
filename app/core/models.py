from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Float, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(120), index=True)
    city: Mapped[str | None] = mapped_column(String(120))
    website: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(80))
    buyer_type: Mapped[str | None] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(120), default="excel")
    source_row: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    lead_score: Mapped[float] = mapped_column(Float, default=0)
    lead_score_components: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
