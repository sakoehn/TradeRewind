"""Strategy package for TradeRewind.

All strategy modules live here.  Each module exposes one public function
that satisfies the common strategy contract::

    fn(prices: pd.DataFrame, initial_capital: float, df: pd.DataFrame)
        -> pd.DataFrame

Import from this package to keep backtester.py clean:

    from strategies import REGISTRY, run_strategy, get_strategy_display_names
"""

from typing import Dict, List

from strategies.buy_and_hold import buy_and_hold
from strategies.moving_average import moving_average_crossover

# Strategy registry:
# Maps the internal key (lower-cased) to its callable.
# To add a new strategy:
#   1. Create  strategies/my_new_strategy.py  with a public function.
#   2. Import it above.
#   3. Add one entry to REGISTRY and one to DISPLAY_NAMES below.
#   4. Optionally add STRATEGY_INFO for a home-page callout.
# No other file needs to change (compare_tickers and home_page use these).

REGISTRY: dict = {
    "buy and hold": buy_and_hold,
    "moving average crossover": moving_average_crossover,
}

# Display names for UI (dropdowns, titles). Key = same as REGISTRY key.
DISPLAY_NAMES: Dict[str, str] = {
    "buy and hold": "Buy and Hold",
    "moving average crossover": "Moving Average Crossover",
}

# Optional: info text shown on home page when this strategy is selected.
# Key = same as REGISTRY key. Omit if no callout needed.
STRATEGY_INFO: Dict[str, str] = {
    "moving average crossover": (
        "**Moving Average Crossover (50 / 200 day)**  \n"
        "Buys when the 50-day SMA crosses above the 200-day SMA *(Golden "
        "Cross)* and sells when it crosses below *(Death Cross)*.  \n"
        "Requires **at least 201 trading days** (~1 year) of data. "
        "Widen your date range if you see an error."
    ),
}


def get_strategy_display_names() -> List[str]:
    """Return display names for all registered strategies (sorted). For UI dropdowns."""
    return sorted(DISPLAY_NAMES.values())


def display_name_to_key(display_name: str) -> str:
    """Return the REGISTRY key for a given display name (case-insensitive match)."""
    d = display_name.strip()
    for key, name in DISPLAY_NAMES.items():
        if name.lower() == d.lower():
            return key
    return d.lower()


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
    "DISPLAY_NAMES",
    "REGISTRY",
    "STRATEGY_INFO",
    "buy_and_hold",
    "display_name_to_key",
    "get_strategy_display_names",
    "moving_average_crossover",
    "run_strategy",
]
