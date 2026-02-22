def buy_and_hold(prices, initial_capital, df):

    df = prices.copy()

    first_price = df["close"].iloc[0]
    shares = initial_capital / first_price

    # Strategy computations
    df["position"] = shares
    df["price"] = df["close"]
    df["daily_value"] = df["position"] * df["price"]
    df["daily_returns"] = df["daily_value"].pct_change().fillna(0)
    df["profit_to_date"] = df["daily_value"] - initial_capital
    df["drawdown"] = df["daily_value"] / df["daily_value"].cummax() - 1

    return df