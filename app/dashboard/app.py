import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="TAN-TRADE Intelligence", page_icon="🥜", layout="wide")
st.title("TAN-TRADE Buyer Intelligence")
st.caption("Find the next buyer worth your attention.")

with st.sidebar:
    st.header("Workspace")
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=3)
        health_response.raise_for_status()
        st.success("API connected")
    except requests.RequestException:
        st.error("API unavailable")

    st.subheader("Import buyers")
    workbook = st.file_uploader("Choose an Excel workbook", type=["xlsx", "xls"])
    if workbook and st.button("Import workbook", type="primary", use_container_width=True):
        with st.spinner("Importing and scoring buyers..."):
            response = requests.post(
                f"{API_URL}/imports/excel",
                files={"file": (workbook.name, workbook.getvalue(), workbook.type)},
                timeout=60,
            )
        if response.ok:
            result = response.json()
            st.success(f"Imported {result['imported']} companies; skipped {result['skipped']}.")
            if result["errors"]:
                st.warning("\n".join(result["errors"][:5]))
            st.rerun()
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        st.error(f"Import failed: {detail}")

st.subheader("Buyer pipeline")
filter_column, country_column, score_column, limit_column = st.columns([2, 1, 1, 1])
search = filter_column.text_input("Search", placeholder="Company name")
country = country_column.text_input("Country", placeholder="Tanzania")
minimum_score = score_column.slider("Minimum score", min_value=0, max_value=100, value=0, step=5)
limit = limit_column.selectbox("Rows", [25, 50, 100, 250], index=2)

try:
    response = requests.get(
        f"{API_URL}/leads",
        params={"search": search, "country": country, "limit": limit},
        timeout=10,
    )
    response.raise_for_status()
    companies = [company for company in response.json() if company["lead_score"] >= minimum_score]
except requests.RequestException as error:
    st.error(f"Could not load buyers: {error}")
    st.stop()

first_column, second_column, third_column, fourth_column = st.columns(4)
first_column.metric("Buyers", len(companies))
second_column.metric("Priority leads", sum(item["lead_score"] >= 75 for item in companies))
third_column.metric("Average score", f"{sum(item['lead_score'] for item in companies) / len(companies):.0f}" if companies else "0")
fourth_column.metric("Countries", len({item["country"] for item in companies if item["country"]}))

if companies:
    table = pd.DataFrame(companies)
    table["priority"] = table["lead_score"].apply(
        lambda score: "High" if score >= 75 else "Medium" if score >= 50 else "Low"
    )
    table = table.sort_values(["lead_score", "name"], ascending=[False, True])
    st.dataframe(
        table[["priority", "name", "country", "city", "buyer_type", "email", "website", "lead_score", "source"]],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download filtered buyers",
        data=table.drop(columns=["lead_score_components"]).to_csv(index=False).encode("utf-8"),
        file_name="tan-trade-buyers.csv",
        mime="text/csv",
    )

    st.subheader("Buyer detail")
    selected_name = st.selectbox("Select a company", table["name"].tolist())
    selected_company = next(item for item in companies if item["name"] == selected_name)
    detail_column, score_column = st.columns([2, 1])
    detail_column.markdown(
        f"**{selected_company['name']}**  \n"
        f"{selected_company.get('buyer_type') or 'Buyer type not recorded'} in "
        f"{selected_company.get('country') or 'country not recorded'}"
    )
    detail_column.write(selected_company.get("email") or "No email recorded")
    detail_column.write(selected_company.get("website") or "No website recorded")
    score_column.metric("Lead score", f"{selected_company['lead_score']:.0f}/100")

    st.subheader("Score explanation")
    components = selected_company.get("lead_score_components", {}).get("components", {})
    if components:
        score_rows = [
            {"signal": name.replace("_", " ").title(), "points": detail["points"], "reason": detail["reason"]}
            for name, detail in components.items()
            if name != "base"
        ]
        st.dataframe(pd.DataFrame(score_rows), use_container_width=True, hide_index=True)
else:
    st.info("No buyers match these filters. Upload an Excel workbook from the sidebar or lower the minimum score.")
