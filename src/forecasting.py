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
    return monthly


def forecast_revenue(series: pd.DataFrame, periods: int = 3) -> pd.DataFrame:
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    model.fit(series)
    future = model.make_future_dataframe(periods=periods, freq='MS')
    forecast = model.predict(future)
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]


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
