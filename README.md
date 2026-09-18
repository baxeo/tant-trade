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

The Vercel deployment serves a lightweight browser dashboard at `/` and the API under `/api`. For persistent production data on Vercel, set `DATABASE_URL` to a managed PostgreSQL database; the automatic SQLite fallback is only for local development or temporary previews.

Upload a `.csv`, `.xlsx`, or `.xls` file from the dashboard. For Excel, the first worksheet is read automatically. Supported header aliases include:

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

This first slice intentionally does not include authentication, orders, churn modeling, or LLM recommendations. Those should be added after the import and buyer-review workflow is exercised with real data.

## Dashboard walkthrough

1. Open `http://localhost:8501` locally, or your deployed dashboard URL.
2. Check the sidebar status. `API connected` means the dashboard can read and import data.
3. Upload `sample_data/buyers_sample.csv` and click **Import workbook**.
4. Use **Search**, **Country**, and **Minimum score** to narrow the buyer list.
5. Read **Priority leads** first. A score of 75 or more indicates strong data completeness signals; it is not a conversion guarantee.
6. Select a buyer to inspect contact details and the score explanation.
7. Use **Download filtered buyers** to export the current table as CSV.

The sample file is fictional and safe for testing. It includes high, medium, low, incomplete, and near-duplicate records. Uploading it twice demonstrates the duplicate review warnings.
