# backend/forecasting.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


def auto_detect_freq(unique_days):
    """
    detect best resample freq by looking at date gaps
    """
    if len(unique_days) < 2:
        return "D"

    # safe sorting
    sorted_vals = np.sort(unique_days).astype("datetime64[D]").astype(int)
    diff = np.diff(sorted_vals)
    if len(diff) == 0:
        return "D"

    avg_gap = diff.mean()

    if avg_gap <= 2:    return "D"   # daily
    if avg_gap <= 12:   return "W"   # weekly
    return "M"                      # monthly default


def forecast_time_series(df, date_col, value_col, periods=6):
    """
    simple regression forecasting
    auto detects frequency (D/W/M)
    returns historical_df, forecast_df
    """

    tmp = df.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp = tmp.dropna(subset=[date_col, value_col])

    if tmp.empty:
        raise ValueError("No usable date/value pairs for forecasting.")

    # detect best freq
    unique_days = tmp[date_col].dt.normalize().unique()
    freq = auto_detect_freq(unique_days)

    agg = tmp.set_index(date_col).resample(freq)[value_col].sum().reset_index().rename(columns={value_col: "y"})

    if len(agg) < 3:
        raise ValueError("Not enough aggregated points to forecast (need >= 3).")

    # regression
    agg["t"] = np.arange(len(agg))
    X = agg[["t"]].values
    y = agg["y"].values
    model = LinearRegression().fit(X, y)

    future_t = np.arange(len(agg), len(agg) + periods).reshape(-1, 1)
    preds = model.predict(future_t)

    last_date = agg[date_col].max()
    future_dates = pd.date_range(start=last_date, periods=periods + 1, freq=freq)[1:]  # skip today

    forecast_df = pd.DataFrame({date_col: future_dates, "prediction": preds})

    return agg, forecast_df
