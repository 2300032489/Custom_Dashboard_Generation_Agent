# backend/data_processing.py
import io
import pandas as pd

def load_file(uploaded_file):
    """
    uploaded_file: fastapi UploadFile object
    returns: pandas DataFrame
    Supports csv, xls, xlsx, and optionally pdf (if tabula-py installed & Java present)
    """
    filename = getattr(uploaded_file, "filename", None) or getattr(uploaded_file, "name", "")
    filename = filename.lower()
    content = uploaded_file.file.read()
    uploaded_file.file.seek(0)
    if filename.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    if filename.endswith((".xls", ".xlsx")):
        return pd.read_excel(io.BytesIO(content))
    if filename.endswith(".pdf"):
        # optional: use tabula if available
        try:
            import tabula
            tmp_path = "/tmp/uploaded_pdf.pdf"
            with open(tmp_path, "wb") as f:
                f.write(content)
            tables = tabula.read_pdf(tmp_path, pages="all", multiple_tables=True)
            if tables:
                df = pd.concat(tables, ignore_index=True)
                return df
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()
    raise ValueError("Unsupported file type. Allowed: .csv, .xls, .xlsx, .pdf")

def detect_column_types(df):
    """
    Detect numeric, categorical, datetime columns.
    Returns: numeric_cols, categorical_cols, datetime_cols, normalized_df
    """
    df = df.copy()
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    datetime_cols = []
    for col in df.columns:
        if col in numeric_cols:
            continue
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            # if many values parse to datetime, treat as datetime column
            if parsed.notna().sum() >= max(2, 0.5 * len(parsed)):
                df[col] = parsed
                datetime_cols.append(col)
        except Exception:
            continue
    categorical_cols = [c for c in df.columns if c not in numeric_cols + datetime_cols]
    return numeric_cols, categorical_cols, datetime_cols, df
