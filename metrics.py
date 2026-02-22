import numpy as np

import numpy as np

def compute_metrics(df, initial_capital):

    df = df.copy()
    df = df.dropna(subset=["daily_value", "daily_returns"])

    daily_returns = df["daily_returns"]

    # Returns
    total_return = (df["daily_value"].iloc[-1] / initial_capital) - 1

    annualized_return = (1 + total_return) ** (252 / len(df)) - 1

    annualized_sharpe_ratio = (
        daily_returns.mean() /
        daily_returns.std()
    ) * np.sqrt(252)

    max_drawdown = (
        df["daily_value"] /
        df["daily_value"].cummax() - 1
    ).min()

    annual_volatility = daily_returns.std() * np.sqrt(252)

    win_rate = (daily_returns > 0).mean()

    # Calculating other metrics from the daily metrics from the dataset
    avg_return_1d = df["return_1d"].mean()
    avg_return_5d = df["return_5d"].mean()
    avg_return_20d = df["return_20d"].mean()
    pct_above_sma_200 = (df["close"] > df["sma_200"]).mean()
    avg_rsi = df["rsi_14"].mean()
    avg_atr = df["atr_14"].mean()
    avg_volatility_20d = df["volatility_20d"].mean()
    avg_volume_ratio = df["volume_ratio"].mean()


    return {
        #Metrics we calculated
        "Total Return": total_return,
        "Annualized Return": annualized_return,
        "Annualized Sharpe Ratio":  annualized_sharpe_ratio,
        "Max Drawdown": max_drawdown,
        "Annualized Volatility": annual_volatility,
        "Win Rate": win_rate,

        #Metrics from the dataset 
        "Avg 1D Return": avg_return_1d,
        "Avg 5D Return": avg_return_5d,
        "Avg 20D Return": avg_return_20d,
        "% Above SMA200": pct_above_sma_200,
        "Average RSI": avg_rsi,
        "Average ATR": avg_atr,
        "Average 20D Volatility": avg_volatility_20d,
        "Average Volume Ratio": avg_volume_ratio
    }