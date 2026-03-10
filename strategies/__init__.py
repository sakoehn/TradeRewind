"""Strategy package for TradeRewind.

All strategy modules live here.  Each module exposes one public function
that satisfies the common strategy contract::

    fn(prices: pd.DataFrame, initial_capital: float, df: pd.DataFrame)
        -> pd.DataFrame

Import from this package to keep backtester.py clean:

    from strategies import REGISTRY, run_strategy
"""

from strategies.buy_and_hold import buy_and_hold
from strategies.moving_average import moving_average_crossover

# Strategy registry:
# Maps the human-readable strategy name (lower-cased) to its callable.
# To add a new strategy:
#   1. Create  strategies/my_new_strategy.py  with a public function.
#   2. Import it above.
#   3. Add one entry to REGISTRY below.
# No other file needs to change.

REGISTRY: dict = {
    "buy and hold": buy_and_hold,
    "moving average crossover": moving_average_crossover,
}


def run_strategy(prices, strategy: str, initial_capital: float, full_df):
    """Dispatch to the correct strategy function via REGISTRY.

    Args:
        prices: Date-filtered single-stock DataFrame.
        strategy: Human-readable strategy name (case-insensitive).
        initial_capital: Starting cash in dollars.
        full_df: Full combined dataset passed through to strategies that
            need market-wide context.

    Returns:
        Enriched results DataFrame from the chosen strategy.

    Raises:
        ValueError: If strategy is not present in REGISTRY.
    """
    key = strategy.lower().strip()

    if key not in REGISTRY:
        valid = sorted(REGISTRY.keys())
        raise ValueError(
            f"'{strategy}' is not a valid strategy. "
            f"Choose one of: {valid}"
        )

    return REGISTRY[key](prices, initial_capital, full_df)


__all__ = [
    "REGISTRY",
    "run_strategy",
    "buy_and_hold",
    "moving_average_crossover",
]
