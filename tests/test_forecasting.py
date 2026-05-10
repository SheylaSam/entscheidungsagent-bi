# tests/test_forecasting.py
import pandas as pd
from src.forecasting import prepare_monthly_series, forecast_revenue, run_backtest

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

def test_backtest_returns_metrics():
    series = make_monthly_series()
    result = run_backtest(series, holdout_months=3)
    assert result is not None
    assert {'actuals', 'forecast', 'mape', 'mae'}.issubset(result.keys())
    assert len(result['actuals']) == 3
    assert len(result['forecast']) == 3
    assert result['mape'] >= 0
    assert result['mae'] >= 0

def test_backtest_returns_none_for_insufficient_data():
    short = pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=4, freq='MS'), 'y': range(4)})
    result = run_backtest(short, holdout_months=3)
    assert result is None

def test_backtest_requires_six_training_months():
    short = pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=8, freq='MS'), 'y': range(8)})
    result = run_backtest(short, holdout_months=3)
    assert result is None
