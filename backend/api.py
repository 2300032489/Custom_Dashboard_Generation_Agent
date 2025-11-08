# backend/api.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from .data_processing import load_file, detect_column_types
from .insights import generate_rule_based_insights, generate_llm_summary
from .forecasting import forecast_time_series
from .agent.gemini_agent import analyze_text_or_table  # ← NEW
import pandas as pd
import tempfile
import uvicorn

app = FastAPI(title="Custom Dashboard Generator API")

# CORS for Streamlit frontend local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Backend is running"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        df = load_file(file)
    except Exception as e:
        return {"error": f"Failed to load file: {e}"}
    numeric, categorical, datetime_cols, df_clean = detect_column_types(df)
    preview = df_clean.head(50).fillna("").to_dict(orient="records")
    return {
        "columns": df_clean.columns.tolist(),
        "numeric": numeric,
        "categorical": categorical,
        "datetime": datetime_cols,
        "preview": preview,
        "rows": len(df_clean)
    }

@app.post("/insights")
async def insights(file: UploadFile = File(...), use_llm: bool = Form(False)):
    try:
        df = load_file(file)
    except Exception as e:
        return {"error": f"Failed to load file: {e}"}
    numeric, categorical, datetime_cols, df_clean = detect_column_types(df)
    rule_insights = generate_rule_based_insights(df_clean, numeric, categorical, datetime_cols)
    llm_text = None
    if use_llm:
        llm_text = generate_llm_summary(df_clean)
    return {"rule_based": rule_insights, "llm": llm_text}

@app.post("/forecast")
async def forecast(
    file: UploadFile = File(...),
    periods: int = Form(6),
    date_col: str = Form(None),
    value_col: str = Form(None)
):
    try:
        df = load_file(file)
    except Exception as e:
        return {"error": f"Failed to load file: {e}"}
    numeric, categorical, datetime_cols, df_clean = detect_column_types(df)
    if not date_col and datetime_cols:
        date_col = datetime_cols[0]
    if not value_col and numeric:
        value_col = numeric[0]
    if not date_col or not value_col:
        return {"error": "Need a date column and a numeric column to forecast."}
    try:
        hist, forecast_df = forecast_time_series(df_clean, date_col, value_col, periods=periods)
        return {
            "historical": hist.to_dict(orient="records"),
            "forecast": forecast_df.to_dict(orient="records")
        }
    except Exception as e:
        return {"error": f"Forecast failed: {e}"}

# ---------- NEW: Gemini agent endpoint ----------
@app.post("/agent/analyze")
async def agent_analyze(
    text: str = Form(None),
    file: UploadFile = File(None)
):
    """
    Multilingual, grammar-tolerant analysis endpoint.
    Send either 'text' OR 'file' (CSV/XLS/XLSX/PDF).
    """
    file_name = None
    file_bytes = None
    if file is not None:
        file_name = file.filename
        file_bytes = await file.read()
    result = analyze_text_or_table(
        user_input_text=text,
        file_name=file_name,
        file_bytes=file_bytes
    )
    return {"result": result}
# ------------------------------------------------

# If running backend directly
if __name__ == "__main__":
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=True)
