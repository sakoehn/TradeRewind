import pandas as pd

def validate_stock(stock, df):

    if not stock:
        raise TypeError("Please provide a stock to analyze.")

    s = str(stock).strip()

    if s in df["ticker"].values:
        return s

    matches = df.loc[df["company_name"] == s, "ticker"].unique()
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        raise ValueError(f"Company name '{s}' maps to multiple tickers: {matches.tolist()}")
    else:
        raise TypeError(f"Stock '{s}' is not available in the dataframe.")

def validate_date(start, end, stockDf):

    stockDf = stockDf.copy()

    # Fixing any issues with timezones
    stockDf['date'] = pd.to_datetime(stockDf['date'], utc=True)

    minDate = stockDf['date'].min()
    maxDate = stockDf['date'].max()

    # Convert start/end to UTC tz-aware
    start_ts = pd.to_datetime(start, utc=True) if start else minDate
    end_ts   = pd.to_datetime(end, utc=True)   if end else maxDate

    if start_ts > end_ts:
        raise UserWarning("The start date must be before the end date.")

    if end_ts < minDate or start_ts > maxDate:
        raise ValueError(
            f"The available date range for this stock is from {minDate.strftime('%Y-%m-%d')} to {maxDate.strftime('%Y-%m-%d')}"
        )

    return start_ts, end_ts

def get_stock_history(stock, start=None, end=None, df=None):


    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("A valid dataframe must be provided.")

    if stock in df['ticker'].values:
        ticker = stock
    else:
        matches = df.loc[df['company_name'] == stock, 'ticker'].unique()
        if len(matches) == 1:
            ticker = matches[0]
        elif len(matches) > 1:
            raise ValueError(f"Company name '{stock}' maps to multiple tickers: {matches.tolist()}")
        else:
            raise TypeError(f"Stock '{stock}' not found.")

    stock_df = df[df['ticker'] == ticker].copy()
    if stock_df.empty:
        raise ValueError(f"No data found for stock '{ticker}'.")

    stock_df['date'] = pd.to_datetime(stock_df['date'], utc=True, errors='coerce')

    if stock_df['date'].isna().any():
        raise ValueError("Some dates could not be converted to datetime.")

    start_ts = pd.to_datetime(start, utc=True) if start else stock_df['date'].min()
    end_ts   = pd.to_datetime(end, utc=True) if end else stock_df['date'].max()

    if start_ts > end_ts:
        raise UserWarning("Start date must be before end date.")

    subset = stock_df[(stock_df['date'] >= start_ts) & (stock_df['date'] <= end_ts)].copy()

    if subset.empty:
        raise ValueError("No data available for the requested date range.")

    subset.reset_index(drop=True, inplace=True)

    return subset

if __name__ == "__main__":
    # test
    from data_loading import load_all_data

    df = load_all_data()
    stock_history = get_stock_history("AAPL", pd.Timestamp("2016-02-19"), pd.Timestamp("2026-02-19"), df)
    print(stock_history.head())