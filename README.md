# TAN-TRADE Buyer Intelligence MVP

Excel-to-PostgreSQL buyer import with a FastAPI API and Streamlit dashboard.

## Start with Docker

```powershell
docker compose up --build
```

Open:

- Dashboard: http://localhost:8501
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Upload an `.xlsx` or `.xls` workbook from the dashboard. The first worksheet is read automatically. Supported header aliases include:

- Company: `company`, `company_name`, `buyer`, `buyer_name`, `business_name`, `name`
- Location: `country`, `city`
- Contact: `email`, `phone`, `whatsapp`
- Profile: `website`, `buyer_type`, `type`, `category`, `industry`

Rows are deduplicated by normalized company name, matching domain, and conservative fuzzy name similarity. Near-duplicates are skipped with a review warning rather than merged automatically. Each imported record stores the original Excel row in `source_row` for traceability. The initial lead score is a transparent completeness score, not an ML prediction; its version, points per signal, and missing-signal reasons are stored with the company. Preview a score with `POST /leads/score`, or list scored records with `GET /leads`.

## Local development

Requires Python 3.11+ and PostgreSQL, or Docker for PostgreSQL.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
uvicorn app.main:app --reload
streamlit run app/dashboard/app.py
```

To import a workbook from the command line:

```powershell
python scripts/import_excel.py path\to\buyers.xlsx
```

## MVP boundaries

This first slice intentionally does not include authentication, fuzzy matching, orders, churn modeling, or LLM recommendations. Those should be added after the import and buyer-review workflow is exercised with real data.
