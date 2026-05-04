import os
import pandas as pd
import sqlite3
import cmdstanpy

# Prophet bundles a stub cmdstan-2.33.1 directory that is often incomplete.
# Fall back to the system-installed CmdStan when that happens.
try:
    cmdstanpy.cmdstan_path()
except ValueError:
    _user_cmdstan = os.path.expanduser("~/.cmdstan")
    if os.path.isdir(_user_cmdstan):
        _versions = sorted(os.listdir(_user_cmdstan), reverse=True)
        if _versions:
            cmdstanpy.set_cmdstan_path(os.path.join(_user_cmdstan, _versions[0]))

from prophet import Prophet


def prepare_monthly_series(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    countries: tuple = (),
) -> pd.DataFrame:
    placeholders = ','.join(['?' for _ in countries])
    sql = (
        "SELECT invoice_date, revenue FROM transactions"
        f" WHERE invoice_date >= ? AND invoice_date <= ?"
        f" AND country IN ({placeholders})"
    )
    params = (start_date, end_date + ' 23:59:59') + countries
    df = pd.read_sql(sql, conn, params=params, parse_dates=['invoice_date'])
    monthly = (
        df.set_index('invoice_date')
        .resample('MS')['revenue']
        .sum()
        .reset_index()
        .rename(columns={'invoice_date': 'ds', 'revenue': 'y'})
    )
    # Drop the last month if it's incomplete so Prophet doesn't learn a false drop
    if len(monthly) > 0:
        last_month_end = monthly['ds'].iloc[-1] + pd.offsets.MonthEnd(1)
        if pd.Timestamp(end_date) < last_month_end:
            monthly = monthly.iloc[:-1]
    return monthly


def forecast_revenue(series: pd.DataFrame, periods: int = 3) -> pd.DataFrame:
    # yearly_seasonality=2 → fourier_order=2 (4 params) instead of default 10 (20 params)
    # prevents overfitting on short series (~24 monthly data points)
    model = Prophet(yearly_seasonality=2, weekly_seasonality=False, daily_seasonality=False)
    model.fit(series)
    future = model.make_future_dataframe(periods=periods, freq='MS')
    forecast = model.predict(future)
    forecast['yhat'] = forecast['yhat'].clip(lower=0)
    forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
    cols = ['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'trend']
    if 'yearly' in forecast.columns:
        cols.append('yearly')
    return forecast[cols]


def load_forecast(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    countries: tuple = (),
    periods: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (monthly_actuals, forecast_df)."""
    series = prepare_monthly_series(conn, start_date, end_date, countries)
    forecast = forecast_revenue(series, periods=periods)
    return series, forecast


def run_backtest(series: pd.DataFrame, holdout_months: int = 3) -> dict | None:
    """Train on all-but-last N months, forecast N months, return metrics."""
    if len(series) <= holdout_months + 2:
        return None
    train = series.iloc[:-holdout_months].copy()
    test = series.iloc[-holdout_months:].copy().reset_index(drop=True)
    model = Prophet(yearly_seasonality=2, weekly_seasonality=False, daily_seasonality=False)
    model.fit(train)
    future = model.make_future_dataframe(periods=holdout_months, freq='MS')
    fc = model.predict(future)
    preds = fc.tail(holdout_months)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].reset_index(drop=True)
    # clip actuals to avoid division by near-zero
    mape = ((test['y'] - preds['yhat']).abs() / test['y'].clip(lower=1)).mean()
    mae = (test['y'] - preds['yhat']).abs().mean()
    return {'actuals': test, 'forecast': preds, 'mape': mape, 'mae': mae}
