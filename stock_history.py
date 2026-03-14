"""
    Returns a subset of the full data that only includes the stock information wanted by the user.
"""
import pandas as pd
from data_loading import load_all_data


def validate_stock(stock, stocks_df):
    """
    Validate a stock identifier against the dataframe.

    - If `stock` is a ticker present in stocks_df['ticker'], return it.
    - If `stock` matches a company_name uniquely, return its ticker.
    - Otherwise, raise an error.
    """
    if not stock:
        raise TypeError("Please provide a stock to analyze.")

    stock_str = str(stock).strip()

    if stock_str in stocks_df["ticker"].values:
        return stock_str

    matches = stocks_df.loc[
        stocks_df["company_name"] == stock_str,
        "ticker",
    ].unique()

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        msg = (
            f"Company name '{stock_str}' maps to multiple tickers: "
            f"{matches.tolist()}"
        )
        raise ValueError(msg)

    raise TypeError(
        f"Stock '{stock_str}' is not available in the dataframe."
    )


def validate_date(start, end, stock_df):
    """
    Validate and normalize start/end against the available date range
    of a single-stock dataframe.
    """
    stock_df = stock_df.copy()

    # Ensure timezone-aware UTC datetimes
    stock_df["date"] = pd.to_datetime(stock_df["date"], utc=True)

    min_date = stock_df["date"].min()
    max_date = stock_df["date"].max()

    # Convert start/end to UTC tz-aware
    start_ts = pd.to_datetime(start, utc=True) if start else min_date
    end_ts = pd.to_datetime(end, utc=True) if end else max_date

    if start_ts > end_ts:
        raise UserWarning("The start date must be before the end date.")

    if end_ts < min_date or start_ts > max_date:
        msg = (
            "The available date range for this stock is from "
            f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
        )
        raise ValueError(msg)

    return start_ts, end_ts


def get_stock_history(stock, start=None, end=None, stocks_df=None):
    """
    Return a date-filtered history for a stock from the combined dataframe.
    """
    if stocks_df is None or not isinstance(stocks_df, pd.DataFrame):
        raise TypeError("A valid dataframe must be provided.")

    if stock in stocks_df["ticker"].values:
        ticker = stock
    else:
        matches = stocks_df.loc[
            stocks_df["company_name"] == stock,
            "ticker",
        ].unique()

        if len(matches) == 1:
            ticker = matches[0]
        elif len(matches) > 1:
            msg = (
                f"Company name '{stock}' maps to multiple tickers: "
                f"{matches.tolist()}"
            )
            raise ValueError(msg)
        else:
            raise TypeError(f"Stock '{stock}' not found.")

    stock_df = stocks_df[stocks_df["ticker"] == ticker].copy()
    if stock_df.empty:
        raise ValueError(f"No data found for stock '{ticker}'.")

    stock_df["date"] = pd.to_datetime(
        stock_df["date"],
        utc=True,
        errors="coerce",
    )

    if stock_df["date"].isna().any():
        raise ValueError("Some dates could not be converted to datetime.")

    start_ts, end_ts = validate_date(start, end, stock_df)

    subset = stock_df[
        (stock_df["date"] >= start_ts) & (stock_df["date"] <= end_ts)
    ].copy()

    if subset.empty:
        raise ValueError("No data available for the requested date range.")

    subset.reset_index(drop=True, inplace=True)

    return subset


def build_market_series(stocks_df, stock, value_col="close"):
    """
    Build a time-indexed Series for a single stock's values,
    used by next_nonzero_date.
    """
    stock_df = stocks_df[stocks_df["ticker"] == stock].copy()
    if stock_df.empty:
        raise ValueError(f"No data found for stock '{stock}'.")

    stock_df["date"] = pd.to_datetime(stock_df["date"], utc=True)
    stock_df = stock_df.sort_values("date").set_index("date")

    if value_col not in stock_df.columns:
        raise KeyError(f"Column '{value_col}' not found for stock '{stock}'.")

    return stock_df[value_col]


def next_nonzero_date(date, market_series):
    """
    Given a target date and a time-indexed Series (market_series),
    return the first index at or after that date with a non-zero value.
    """
    target_ts = pd.to_datetime(date, utc=True)

    indexer = market_series.index.get_indexer(
        [target_ts],
        method="pad",
    )
    if indexer.size == 0 or indexer[0] == -1:
        msg = f"No date at or before {date} found in index."
        raise ValueError(msg)

    idx = int(indexer[0])

    while idx < len(market_series.index) and market_series.iloc[idx] == 0:
        idx += 1

    if idx >= len(market_series.index):
        msg = f"No non-zero value found on or after {date}"
        raise ValueError(msg)

    return market_series.index[idx]


if __name__ == "__main__":
    ALL_STOCKS_DF = load_all_data()

    STOCK_HISTORY = get_stock_history(
        "AAPL",
        pd.Timestamp("2016-02-19"),
        pd.Timestamp("2026-02-19"),
        ALL_STOCKS_DF,
    )
    print(STOCK_HISTORY.head())

    AAPL_SERIES = build_market_series(
        ALL_STOCKS_DF,
        "AAPL",
        value_col="close",
    )
    NEXT_NONZERO = next_nonzero_date("2016-02-19", AAPL_SERIES)
    print("Next non-zero date for AAPL close:", NEXT_NONZERO)
