import pdfplumber
import pandas as pd

BALANCE_TAG = "Consolidated Balance Sheet"
PL_TAG = "Consolidated Statement of Profit and Loss"


def extract_tables_from_pdf(pdf_path):
    balance_pages = []
    pl_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""

            if BALANCE_TAG in text:
                balance_pages.extend(pdf.pages[i:i+3])
            if PL_TAG in text:
                pl_pages.extend(pdf.pages[i:i+3])

    return clean_table(extract_from_pages(balance_pages)), clean_table(extract_from_pages(pl_pages))


def extract_from_pages(pages):
    tables = []
    for pg in pages:
        extracted = pg.extract_tables()
        if extracted:
            tables.extend(extracted)
    return tables


def clean_table(tables):
    rows = []
    for t in tables:
        for r in t:
            rows.append(r)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.dropna(how="all", axis=1).dropna(how="all")

    # Header row cleanup
    header = df.iloc[0].tolist()
    header = ["Column" if h is None or str(h).strip() == "" else str(h).strip() for h in header]

    df = df[1:]
    df.columns = header
    df = df[df.iloc[:, 0].notna()].reset_index(drop=True)

    # ✅ Deduplicate columns safely
    df.columns = _dedupe(df.columns)

    # Convert numeric-like text to float where possible
    df = df.map(convert_num)

    return df


def _dedupe(cols):
    seen = {}
    new_cols = []
    for col in cols:
        if col not in seen:
            seen[col] = 0
            new_cols.append(col)
        else:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
    return new_cols


def convert_num(x):
    if isinstance(x, str):
        x = x.replace(",", "").replace("(", "-").replace(")", "").strip()
        try:
            return float(x)
        except:
            return x
    return x
