#consider testing when wrong dates are passed, or when the stock is not in the dataset, or when the strategy is not valid
import sys
print(sys.executable)

from data_loading import load_all_data
from strategies import buy_and_hold
from metrics import compute_metrics
from stock_history import get_stock_history
from graph_generation import strategy_dashboard



df = load_all_data()

def run_strategy(prices, strategy, initial_capital, df):

    if strategy.lower() == "buy and hold":
        return buy_and_hold(prices, initial_capital, df)
    else:
        raise ValueError("Please select a valid strategy")
    

def main_backtest(stock, start_date, end_date, strategy, initial_capital):

    # Getting stock data
    prices = get_stock_history(stock, start_date, end_date, df)

    # Running the strategy
    results = run_strategy(prices, strategy, initial_capital, df)

    # Computing the metrics
    summary = compute_metrics(results, initial_capital)
    
    strategy_dashboard(results, summary, initial_capital)

    return results, summary



if __name__ == "__main__":
    # Example usage
    results, summary = main_backtest(
        stock="AAPL",
        start_date="2016-02-19",
        end_date="2026-02-19",
        strategy="Buy and Hold",
        initial_capital=1000
    )

    print(results.head())
    print(summary)