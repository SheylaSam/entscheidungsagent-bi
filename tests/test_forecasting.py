# tests/test_forecasting.py
import pandas as pd
from src.forecasting import prepare_monthly_series, forecast_revenue

def make_monthly_series():
    dates = pd.date_range('2010-01-01', periods=24, freq='MS')
    return pd.DataFrame({'ds': dates, 'y': range(24)})

def test_forecast_returns_future_rows():
    series = make_monthly_series()
    result = forecast_revenue(series, periods=3)
    assert len(result) == 24 + 3

def test_forecast_has_required_columns():
    series = make_monthly_series()
    result = forecast_revenue(series, periods=3)
    assert {'ds', 'yhat', 'yhat_lower', 'yhat_upper'}.issubset(result.columns)

def test_forecast_future_dates_are_after_training():
    series = make_monthly_series()
    result = forecast_revenue(series, periods=3)
    last_train = series['ds'].max()
    future = result[result['ds'] > last_train]
    assert len(future) == 3
