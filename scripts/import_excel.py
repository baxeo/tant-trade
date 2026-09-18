import argparse

from app.core.db import SessionLocal, init_db
from app.services.importer import import_excel


parser = argparse.ArgumentParser(description="Import buyer companies from an Excel workbook")
parser.add_argument("path")
args = parser.parse_args()

init_db()
with SessionLocal() as session:
    imported, skipped, errors = import_excel(args.path, session)

print(f"Imported: {imported}; skipped: {skipped}")
for error in errors:
    print(f"Warning: {error}")
