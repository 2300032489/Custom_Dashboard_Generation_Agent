# backend/insights.py
import os
from sklearn.linear_model import LinearRegression
import pandas as pd

def generate_rule_based_insights(df, numeric_cols, cat_cols, datetime_cols, max_items=4):
    """
    Produce textual insights from dataframe using simple rules.
    """
    insights = []
    if df.empty:
        return insights
    # numeric summaries
    for col in numeric_cols[:max_items]:
        s = df[col].dropna()
        if s.empty:
            continue
        insights.append(f"**{col}** — mean: {s.mean():.2f}, median: {s.median():.2f}, min: {s.min():.2f}, max: {s.max():.2f}")
    # top categories
    for col in cat_cols[:max_items]:
        top = df[col].value_counts().nlargest(3)
        items = "; ".join([f"{idx} ({cnt})" for idx, cnt in top.items()])
        insights.append(f"**{col}** — top values: {items}")
    # trend detection (if date + numeric present)
    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        num_col = numeric_cols[0]
        series = df.dropna(subset=[date_col, num_col]).sort_values(date_col)
        if len(series) >= 3:
            # LR trend
            X = (series[date_col].astype("int64") // 10**9).values.reshape(-1,1)
            y = series[num_col].values
            lr = LinearRegression().fit(X, y)
            slope = lr.coef_[0]
            if slope > 0:
                insights.append(f"**Trend:** {num_col} shows an upward trend over {date_col}.")
            elif slope < 0:
                insights.append(f"**Trend:** {num_col} shows a downward trend over {date_col}.")
            else:
                insights.append(f"**Trend:** {num_col} shows no clear trend over {date_col}.")
    return insights

def generate_llm_summary(df, sample_rows=20):
    """
    Optional: generate an LLM summary.
    This function will try OpenAI if OPENAI_API_KEY is set, otherwise
    looks for GEMINI_API_KEY (placeholder). The Gemini integration code is commented
    and requires Google's gen AI client. Replace with your preferred provider code.
    """
    # Quick guard: if small dataset, create a CSV snippet prompt
    snippet = df.head(sample_rows).to_csv(index=False)
    prompt = f"Provide a short summary (3 bullets) and 3 suggested actions for this dataset. Sample:\n\n{snippet}"

    # Try OpenAI if available
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            openai.api_key = openai_key
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                max_tokens=300
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"LLM call (OpenAI) failed: {e}"

    # Placeholder for Gemini — you can uncomment & adapt if you install google.generativeai
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            # Example using google.generativeai (install google-generative-ai)
            # import google.generativeai as genai
            # genai.configure(api_key=gemini_key)
            # conversation = genai.chat.create(model="gemini-pro", input=prompt)
            # return conversation last message text
            return "Gemini integration enabled but code is commented. Install google-generative-ai and adapt the client call as shown in comments."
        except Exception as e:
            return f"LLM call (Gemini) failed: {e}"

    return "LLM not configured. Set OPENAI_API_KEY or GEMINI_API_KEY to enable text summaries."
