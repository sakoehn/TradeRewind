# This will be our main entry point for running everything. 
# No major tests needed for this one. May be forgetting a parameter would be a test, like passing fewer parameters than expected 

from backtester import main_backtest

results, summary = main_backtest(
    stock="AAPL",
    start_date="2016-02-19",
    end_date="2026-02-19",
    strategy="Buy and Hold",
    initial_capital=10000
)

print(results.head())
print(summary)