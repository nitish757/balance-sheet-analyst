import os
import streamlit as st
import pandas as pd
import plotly.express as px
from parser import extract_tables_from_pdf

# -----------------------------
# Streamlit UI Setup
# -----------------------------
st.set_page_config(page_title="Balance Sheet Analyzer", layout="wide")
st.title("📊 Balance Sheet Analyzer")
st.write("Upload Reliance Annual Report PDF → Extract Financials → Visualize → Ask AI")

uploaded = st.file_uploader("Upload PDF", type=["pdf"])

# -----------------------------
# Helpers
# -----------------------------

def find_metric(df, keys):
    if df is None or df.empty:
        return pd.DataFrame()

    col = df.columns[0]
    for k in keys:
        match = df[df[col].astype(str).str.contains(k, case=False, na=False)]
        if not match.empty:
            return match
    return pd.DataFrame()


def get_value(row):
    if row is None or row.empty:
        return None

    for col in row.columns[1:]:
        try:
            return float(row.iloc[0][col])
        except:
            continue
    return None


def plot(metrics, values, title):
    df = pd.DataFrame({"Metric": metrics, "Value": values})
    fig = px.bar(df, x="Metric", y="Value", title=title)
    st.plotly_chart(fig, width="stretch")


def table_to_text(df):
    if df is None or df.empty:
        return ""
    lines = []
    for _, r in df.head(50).iterrows():
        text = ", ".join(str(x) for x in r.dropna())
        if any(ch.isdigit() for ch in text):
            lines.append(text)
    return "\n".join(lines)


def ai_answer(q, context):
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        return "⚠️ Offline mode (no API key)\nCompany appears financially stable and profitable."

    from openai import OpenAI
    client = OpenAI(api_key=key)

    prompt = f"""
    Use only the financial data below to answer:

    {context}

    Question: {q}
    Be concise and analytical.
    """

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return resp.choices[0].message.content.strip()


# -----------------------------
# Main
# -----------------------------
if uploaded:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded.getbuffer())

    st.info("⏳ Extracting financial tables…")
    bs, pl = extract_tables_from_pdf("temp.pdf")

    st.subheader("📘 Balance Sheet Extract")
    st.dataframe(bs, width="stretch")

    st.subheader("📕 Profit & Loss Extract")
    st.dataframe(pl, width="stretch")

    KEYS_ASSETS = ["Total Assets"]
    KEYS_LIAB = ["Total Liabilities"]
    KEYS_REV = ["Revenue", "Turnover", "Income from Operations"]
    KEYS_PROF = ["Net Profit", "Profit for the year", "PAT"]

    assets = get_value(find_metric(bs, KEYS_ASSETS))
    liab = get_value(find_metric(bs, KEYS_LIAB))
    rev = get_value(find_metric(pl, KEYS_REV))
    prof = get_value(find_metric(pl, KEYS_PROF))

    if assets and liab:
        st.subheader("🏦 Assets vs Liabilities")
        plot(["Assets", "Liabilities"], [assets, liab], "Assets vs Liabilities")

    if rev and prof:
        st.subheader("💰 Revenue vs Profit")
        plot(["Revenue", "Profit"], [rev, prof], "Revenue vs Profit")
        st.success(f"📈 Profit Margin: **{prof/rev:.2%}**")

    st.markdown("---")
    st.subheader("🤖 Ask AI About Performance")
    q = st.text_input("Your question:")

    if q:
        context = table_to_text(bs) + "\n" + table_to_text(pl)
        st.write("### ✅ Response")
        st.write(ai_answer(q, context))

else:
    st.info("📂 Upload the annual report PDF to get started.")
