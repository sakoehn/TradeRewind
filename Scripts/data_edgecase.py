import csv
import pandas as pd
import os, glob

"""
 1. Fetches user input (right now just parameters passed in)
        - obtain_info(stock, start=None, end=None, metric=None)
 2. Checks for edge cases on data
        - check for useable date, if not gets date clostest
        - if no date specified, use first and last dates in the dataframe

        - Accepts single ticker/company name or list-like.
        - Supports matching by 'ticker' or 'company_name'.
        - Raises if any requested stock is missing.
        - Returns list of tickers (strings).

        - Accepts single metric or list-like.
        - Ensures each metric is a string and exists in df.columns.
        - Returns list of metric names.
 3.Returns small dataframe of the specific user input

"""


DATA_DIR = '../data/'


def load_one(filepath):
    
    stock = pd.read_csv(filepath)
    stock = stock.set_index('date')
    length = len(stock)
    print(length)
    return length, stock

paths = glob.glob(os.path.join(DATA_DIR, "*.csv"))
check_len = 0
all_stocks = []
for p in paths:
    length, stock = load_one(p)
    all_stocks.append(stock)
    check_len += length
if all_stocks:
    print('combine all')
    df = pd.concat(all_stocks, ignore_index=False)
else:
    df = pd.DataFrame() 


#print(df['company_name'])
for i in df['company_name']:
    if len(i.split(' ')) <= 1:
        print(i)

def validate_date(start, end):
    try:
        if start is None:
            start = df.index[0]
        else:
            start = str(pd.to_datetime(start, format="%Y-%m-%d"))
        if end is None:
            end = df.index[-1]
        else:
            end = str(pd.to_datetime(end, format="%Y-%m-%d"))
    except Exception:
        raise TypeError("Date must be correctly formatted as YYYY-MM-DD")
       
    if start > end:
        raise UserWarning("The start date must be before the end date.")
       
    return start, end


def validate_stock(stocks):
    if stocks is None or stocks == "":
        raise TypeError("Please select at least one stock to analyze.")

    # Normalize to list of strings
    if isinstance(stocks, str):
        stocks = [stocks]
    else:
        stocks = list(stocks)

    valid_tickers = []

    for raw in stocks:
        s = str(raw).strip()
        # Try ticker direct match
        if s in df["ticker"].values:
            valid_tickers.append(s)
            continue

        # Try company_name match (exact)
        matches = df.loc[df["company_name"] == s, "ticker"].unique()
        if len(matches) == 1:
            valid_tickers.append(matches[0])
        elif len(matches) > 1:
            raise ValueError(f"Company name '{s}' maps to multiple tickers: {matches.tolist()}.")
        else:
            raise TypeError(f"Stock '{s}' is not available in the dataframe.")

    return valid_tickers



def validate_metric(metrics):
    if metrics is None or metrics == []:
        raise TypeError("Please select at least one metric to analyze.")

    if isinstance(metrics, str):
        metrics = [metrics]
    else:
        metrics = list(metrics)

    valid_metrics = []
    for m in metrics:
        if not isinstance(m, str):
            raise TypeError("Metric names must be strings.")
        if m not in df.columns:
            raise NameError(f"Metric '{m}' not in dataframe columns.")
        valid_metrics.append(m)

    return valid_metrics

         


def obtain_info(stocks, start=None, end=None, metric=None):
    # 1. Dates
    start_ts, end_ts = validate_date(start, end)
    print("start:", start_ts, " end:", end_ts)

    # 2. Stocks → tickers
    tickers = validate_stock(stocks)
    print("tickers:", tickers)

    # 3. Metrics
    metrics = validate_metric(metric)
    print("metrics:", metrics)

    # 4. Subset dataframe
    mask_date = (df.index >= start_ts) & (df.index <= end_ts)
    mask_stock = df["ticker"].isin(tickers)
    cols = ["ticker", "company_name"] + metrics

    sub = df.loc[mask_date & mask_stock, cols].copy()

    if sub.empty:
        raise ValueError("No data for the requested combination of dates, stocks, and metrics.")

    return sub

