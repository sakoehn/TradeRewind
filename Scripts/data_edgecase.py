"""Edge-case data utilities for TradeRewind (legacy CSV-based script).

Provides helpers for:

1. Loading CSV stock files into a combined DataFrame.
2. Snapping dates to the nearest non-zero value (``next_nonzero_date``).
3. Validating user-supplied dates, stocks, and metric names.
4. Returning a filtered sub-DataFrame (``obtain_info``).

Note: The main pipeline now uses Parquet files via ``data_loading.py``.
This script is kept for reference and legacy CSV workflows.
"""

import os
import glob

import pandas as pd


DATA_DIR = '../data/'

def load_one(filepath: str):
    """Load a single CSV stock file and return its row count and DataFrame.

    Args:
        filepath: Path to the CSV file to load.

    Returns:
        Tuple of (row_count, DataFrame) with ``date`` as the index.
    """
    stock = pd.read_csv(filepath)
    stock = stock.set_index('date')
    length = len(stock)
    print(length)
    return length, stock


paths = glob.glob(os.path.join(DATA_DIR, "*.csv"))
check_len = 0
all_stocks = []
for _p in paths:
    _length, _stock = load_one(_p)
    all_stocks.append(_stock)
    check_len += _length

if all_stocks:
    print('combine all')
    combined_df = pd.concat(all_stocks, ignore_index=False)
else:
    combined_df = pd.DataFrame()

for _name in combined_df.get('company_name', []):
    if len(_name.split(' ')) <= 1:
        print(_name)


def next_nonzero_date(date, column: str, data=None):
    """Snap to the previous index date then walk forward to a non-zero value.

    Args:
        date: Target date (string or Timestamp).
        column: Column name to check for non-zero values.
        data: DataFrame to search (defaults to the module-level ``combined_df``).

    Returns:
        The first index date at or after ``date`` where ``column`` is non-zero.

    Raises:
        ValueError: If no non-zero value is found on or after ``date``.
    """
    if data is None:
        data = combined_df

    timestamp = pd.to_datetime(date)
    pos = data.index.get_loc(timestamp, method="pad")
    idx = pos if isinstance(pos, int) else pos.start

    while idx < len(data.index) and data.iloc[idx][column] == 0:
        idx += 1

    if idx >= len(data.index):
        raise ValueError(
            f"No non-zero value found for {column} on or after {date}"
        )

    return data.index[idx]


def validate_date(start, end):
    """Validate and normalise start/end date strings.

    Args:
        start: Start date string (YYYY-MM-DD) or ``None`` to use earliest.
        end: End date string (YYYY-MM-DD) or ``None`` to use latest.

    Returns:
        Tuple of (start, end) as normalised strings.

    Raises:
        TypeError: If either date is not in YYYY-MM-DD format.
        UserWarning: If start is after end.
    """
    try:
        start = combined_df.index[0] if start is None else str(
            pd.to_datetime(start, format="%Y-%m-%d")
        )
        end = combined_df.index[-1] if end is None else str(
            pd.to_datetime(end, format="%Y-%m-%d")
        )
    except Exception as exc:
        raise TypeError(
            "Date must be correctly formatted as YYYY-MM-DD"
        ) from exc

    if start > end:
        raise UserWarning("The start date must be before the end date.")

    return start, end


def validate_stock(stocks):
    """Validate one or more stock identifiers against the loaded data.

    Args:
        stocks: Ticker string, company name string, or list of either.

    Returns:
        List of validated ticker strings.

    Raises:
        TypeError: If ``stocks`` is empty or a ticker is not found.
        ValueError: If a company name maps to multiple tickers.
    """
    if stocks is None or stocks == "":
        raise TypeError("Please select at least one stock to analyze.")

    if isinstance(stocks, str):
        stocks = [stocks]
    else:
        stocks = list(stocks)

    valid_tickers = []

    for raw in stocks:
        ticker_str = str(raw).strip()
        if ticker_str in combined_df["ticker"].values:
            valid_tickers.append(ticker_str)
            continue

        matches = combined_df.loc[
            combined_df["company_name"] == ticker_str, "ticker"
        ].unique()

        if len(matches) == 1:
            valid_tickers.append(matches[0])
        elif len(matches) > 1:
            raise ValueError(
                f"Company name '{ticker_str}' maps to multiple tickers: "
                f"{matches.tolist()}."
            )
        else:
            raise TypeError(
                f"Stock '{ticker_str}' is not available in the dataframe."
            )

    return valid_tickers


def validate_metric(metrics):
    """Validate one or more metric names against the loaded DataFrame columns.

    Args:
        metrics: Metric name string or list of metric name strings.

    Returns:
        List of validated metric name strings.

    Raises:
        TypeError: If ``metrics`` is empty or a metric name is not a string.
        NameError: If a metric name is not found in the DataFrame columns.
    """
    if metrics is None or metrics == []:
        raise TypeError("Please select at least one metric to analyze.")

    if isinstance(metrics, str):
        metrics = [metrics]
    else:
        metrics = list(metrics)

    valid_metrics = []
    for metric in metrics:
        if not isinstance(metric, str):
            raise TypeError("Metric names must be strings.")
        if metric not in combined_df.columns:
            raise NameError(f"Metric '{metric}' not in dataframe columns.")
        valid_metrics.append(metric)

    return valid_metrics


def obtain_info(stocks, start=None, end=None, metric=None):
    """Return a filtered sub-DataFrame for the requested stocks, dates, metrics.

    Args:
        stocks: Ticker(s) or company name(s) to include.
        start: Start date string (YYYY-MM-DD) or ``None``.
        end: End date string (YYYY-MM-DD) or ``None``.
        metric: Metric column name(s) to include.

    Returns:
        Filtered DataFrame containing only the requested rows and columns.

    Raises:
        ValueError: If the resulting subset is empty.
    """
    start_ts, end_ts = validate_date(start, end)
    tickers = validate_stock(stocks)
    metric_cols = validate_metric(metric)

    stock_mask = combined_df["ticker"].isin(tickers)
    df_sub = combined_df.loc[stock_mask]

    ref_col = metric_cols[0]
    start_ts = next_nonzero_date(start_ts, ref_col, data=df_sub)
    end_ts = next_nonzero_date(end_ts, ref_col, data=df_sub)

    mask_date = (combined_df.index >= start_ts) & (combined_df.index <= end_ts)
    output_cols = ["ticker", "company_name"] + metric_cols
    sub = combined_df.loc[mask_date & stock_mask, output_cols].copy()

    if sub.empty:
        raise ValueError(
            "No data for the requested combination of dates, stocks, and metrics."
        )

    return sub
