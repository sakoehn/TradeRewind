"""CLI entry point for TradeRewind.

Run a quick backtest from the command line without launching the Streamlit UI.
Pass ``--strategy`` to choose between available strategies.

Examples::
    python app.py
    python app.py --strategy "Moving Average Crossover" --start 2010-01-01
"""

import argparse

from backtester import main_backtest
from strategies import REGISTRY


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="TradeRewind CLI backtester.")
    parser.add_argument("--stock", default="AAPL", help="Ticker symbol")
    parser.add_argument("--start", default="2016-02-19", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2026-02-19", help="End date YYYY-MM-DD")
    parser.add_argument(
        "--strategy",
        default="Buy and Hold",
        choices=[s.title() for s in REGISTRY],
        help="Strategy name",
    )
    parser.add_argument(
        "--capital", type=float, default=10000.0, help="Initial capital in dollars"
    )
    return parser.parse_args()


def main() -> None:
    """Run the backtest and print results to stdout."""
    args = parse_args()

    results, summary, _ = main_backtest(
        stock=args.stock,
        start_date=args.start,
        end_date=args.end,
        strategy=args.strategy,
        initial_capital=args.capital,
    )

    print(results.head())
    print(summary)


if __name__ == "__main__":
    main()
