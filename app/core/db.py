from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    from app.core import models

    Base.metadata.create_all(bind=engine)
    _ensure_company_score_components()


def _ensure_company_score_components() -> None:
    """Keep existing MVP databases compatible until Alembic is introduced."""
    columns = {column["name"] for column in inspect(engine).get_columns("companies")}
    if "lead_score_components" in columns:
        return
    column_type = "JSONB" if engine.dialect.name == "postgresql" else "JSON"
    default_value = "'{}'::jsonb" if engine.dialect.name == "postgresql" else "'{}'"
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE companies "
                f"ADD COLUMN lead_score_components {column_type} NOT NULL DEFAULT {default_value}"
            )
        )
