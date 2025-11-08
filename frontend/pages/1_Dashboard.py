import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_BASE = st.secrets.get("api_base", "http://127.0.0.1:8000")

# HEADER
st.markdown("<h1 style='text-align:center;'>📊 DASHBOARD</h1>", unsafe_allow_html=True)
st.write("")

st.sidebar.header("Upload & Controls")
uploaded_file = st.sidebar.file_uploader("Upload CSV / Excel / PDF", type=["csv", "xls", "xlsx", "pdf"])

use_llm = st.sidebar.checkbox("Enable LLM summary (may cost tokens)", value=False)
forecast_periods = st.sidebar.slider("Forecast periods (months)", 1, 24, 6)
preview_rows = st.sidebar.slider("Preview rows", 5, 100, 10)

if uploaded_file:
    st.sidebar.info(f"Uploading {uploaded_file.name} to backend...")
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    resp = requests.post(f"{API_BASE}/upload", files=files)
    if resp.status_code != 200:
        st.error("Upload failed.")
        st.stop()
    data = resp.json()
    if "error" in data:
        st.error(data["error"])
        st.stop()

    st.subheader("Dataset preview")
    preview_df = pd.DataFrame(data["preview"])
    st.dataframe(preview_df.head(preview_rows))

    numeric_cols = data.get("numeric", [])
    categorical_cols = data.get("categorical", [])
    datetime_cols = data.get("datetime", [])

    st.sidebar.markdown("### Filters")
    filters = {}
    for cat in categorical_cols:
        vals = preview_df[cat].dropna().unique().tolist()
        sel = st.sidebar.multiselect(f"Filter {cat}", options=sorted(map(str, vals)))
        if sel: filters[cat] = sel

    numeric_filters = {}
    for num in numeric_cols:
        colvals = pd.to_numeric(preview_df[num], errors="coerce")
        mn, mx = float(colvals.min(skipna=True)), float(colvals.max(skipna=True))
        lo, hi = st.sidebar.slider(f"{num} range", min_value=mn, max_value=mx, value=(mn, mx))
        numeric_filters[num] = (lo, hi)

    df_preview = preview_df.copy()

    for c, vals in filters.items():
        df_preview = df_preview[df_preview[c].astype(str).isin(vals)]
    for n, (lo, hi) in numeric_filters.items():
        df_preview[n] = pd.to_numeric(df_preview[n], errors="coerce")
        df_preview = df_preview[(df_preview[n] >= lo) & (df_preview[n] <= hi)]

    st.subheader(f"Filtered preview ({len(df_preview)} rows)")
    st.dataframe(df_preview.head(preview_rows))

    csv_bytes = df_preview.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered CSV", data=csv_bytes, file_name="filtered_data.csv", mime="text/csv")

    st.header("Charts & KPIs")
    if numeric_cols:
        primary_metric = st.selectbox("Primary numeric metric", options=numeric_cols, index=0)
    else:
        primary_metric = None

    if datetime_cols:
        date_col = st.selectbox("Date column", options=datetime_cols, index=0)
    else:
        date_col = None

    if primary_metric:
        total = df_preview[primary_metric].dropna().sum()
        mean = df_preview[primary_metric].dropna().mean()
        st.metric(label=f"Total {primary_metric}", value=f"{total:,.2f}", delta=f"mean {mean:,.2f}")

    chart_type = st.selectbox("Chart type", ["Line / Time series", "Bar (comparison)", "Pie chart", "Scatter"])
    x_col = st.selectbox("X axis", options=list(preview_df.columns), index=0)
    y_col = st.selectbox("Y axis (numeric)", options=numeric_cols if numeric_cols else list(preview_df.columns), index=0)
    color_col = st.selectbox("Color (optional)", options=[None] + list(preview_df.columns))

    if st.button("Generate Chart"):
        plot_df = df_preview.copy()
        if chart_type == "Line / Time series":
            if date_col:
                plot_df[date_col] = pd.to_datetime(plot_df[date_col], errors="coerce")
                fig = px.line(plot_df, x=date_col, y=y_col, color=color_col)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("No date column detected for time series.")
        elif chart_type == "Bar (comparison)":
            agg = plot_df.groupby(x_col)[y_col].sum().reset_index().sort_values(y_col, ascending=False)
            fig = px.bar(agg, x=x_col, y=y_col, color=color_col)
            st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "Pie chart":
            agg = plot_df.groupby(x_col)[y_col].sum().reset_index().sort_values(y_col, ascending=False).head(10)
            fig = px.pie(agg, names=x_col, values=y_col)
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = px.scatter(plot_df, x=x_col, y=y_col, color=color_col)
            st.plotly_chart(fig, use_container_width=True)

    if st.button("Generate Insights"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        resp = requests.post(f"{API_BASE}/insights", files=files, data={"use_llm": str(use_llm)})
        if resp.status_code == 200:
            out = resp.json()
            st.subheader("Rule-based insights")
            for i in out.get("rule_based", []):
                st.markdown(f"- {i}")
            if use_llm:
                st.subheader("LLM summary")
                st.write(out.get("llm") or "No LLM summary returned.")
        else:
            st.error("Insights request failed.")

    st.header("Forecast")
    if st.button("Run Forecast"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        payload = {"periods": forecast_periods}
        resp = requests.post(f"{API_BASE}/forecast", files=files, data=payload)
        if resp.status_code == 200:
            out = resp.json()
            if "error" in out:
                st.error(out["error"])
            else:
                hist = pd.DataFrame(out["historical"])
                fc = pd.DataFrame(out["forecast"])
                date_col_name = hist.columns[0] if not hist.empty else None
                fig = px.line(hist, x=date_col_name, y="y")
                fig.add_scatter(x=fc[date_col_name], y=fc["prediction"], mode="lines+markers", name="Forecast")
                st.plotly_chart(fig, use_container_width=True)
                st.subheader("Forecast table")
                st.dataframe(fc)
                st.download_button("⬇️ Download forecast CSV", data=fc.to_csv(index=False).encode(), file_name="forecast.csv")
        else:
            st.error("Forecast request failed.")

    # ==== AI Agent =====
    st.markdown("---")
    st.subheader("🔍 Ask AI about your data (multilingual, typos OK)")

    agent_query = st.text_area("Type your question or instruction")
    send_file = st.checkbox("Include uploaded file for analysis", value=True)

    if st.button("Run AI Agent"):
        if not agent_query and not (send_file and uploaded_file):
            st.warning("Enter a question or include a file to analyze.")
        else:
            with st.spinner("Thinking..."):
                data = {}
                files = None
                if agent_query:
                    data["text"] = agent_query.strip()
                if send_file and uploaded_file:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                resp = requests.post(f"{API_BASE}/agent/analyze", data=data, files=files)
                if resp.ok:
                    result = resp.json().get("result","")
                    st.markdown("### 🤖 Agent Response")
                    st.write(result)
                else:
                    st.error(f"Request failed: {resp.status_code}")
