import pandas as pd
import sqlite3

from src.data_processing import country_filter_clause, date_range_params


def get_primary_customer_country(transactions: pd.DataFrame) -> pd.DataFrame:
    """Return one primary country per customer, selected by highest revenue."""
    if transactions.empty:
        return pd.DataFrame(columns=['customer_id', 'country'])

    revenue_by_country = (
        transactions.groupby(['customer_id', 'country'], as_index=False)['revenue']
        .sum()
        .sort_values(['customer_id', 'revenue', 'country'], ascending=[True, False, True])
    )
    return revenue_by_country.drop_duplicates('customer_id')[['customer_id', 'country']].reset_index(drop=True)


def load_primary_customer_country(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    countries: tuple = (),
) -> pd.DataFrame:
    country_clause, country_params = country_filter_clause(countries)
    df = pd.read_sql(
        f"""SELECT customer_id, country, revenue
            FROM transactions
            WHERE invoice_date >= ? AND invoice_date < ?
            {country_clause}
            AND customer_id IS NOT NULL""",
        conn,
        params=date_range_params(start_date, end_date) + country_params,
    )
    return get_primary_customer_country(df)


def summarize_segments_by_country(rfm: pd.DataFrame, customer_country: pd.DataFrame) -> pd.DataFrame:
    rfm_country = rfm.merge(customer_country, on='customer_id', how='left')
    country_seg = (
        rfm_country.groupby('country', dropna=False)
        .agg(
            Kunden=('customer_id', 'count'),
            At_Risk=('segment', lambda x: (x == 'At Risk').sum()),
            Champions=('segment', lambda x: (x == 'Champions').sum()),
            Umsatz=('monetary', 'sum'),
        )
        .reset_index()
    )
    country_seg['country'] = country_seg['country'].fillna('Unbekannt')
    country_seg['At_Risk_%'] = country_seg['At_Risk'] / country_seg['Kunden']
    return country_seg.sort_values('At_Risk', ascending=False).reset_index(drop=True)
