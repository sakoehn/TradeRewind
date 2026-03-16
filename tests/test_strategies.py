"""Tests for the Moving Average Crossover strategy.

Coverage targets
----------------
* strategies/moving_average.py
    - _validate_inputs         : all TypeError / ValueError branches
    - _compute_sma_signals     : window sizes, NaN handling, golden/death cross
    - _simulate_trades         : buy/sell mechanics, portfolio accounting
    - moving_average_crossover : public API, edge cases, mutation guard

* strategies/buy_and_hold.py
    - buy_and_hold             : regression - behaviour must be unchanged

* strategies/__init__.py
    - run_strategy             : dispatch, case-insensitivity, invalid name

* charts/common.py
    - format_summary           : percentage keys, plain floats, non-floats
    - prepare_plot_df          : tz strip, NaN drop, index reset

Run with::

    pytest test_strategies.py -v --tb=short
"""

import math

import pandas as pd
import pytest

from strategies.moving_average import (
    MIN_ROWS_REQUIRED,
    LONG_WINDOW,
    SHORT_WINDOW,
    _compute_sma_signals,
    _simulate_trades,
    _validate_inputs,
    moving_average_crossover,
)
from strategies.buy_and_hold import buy_and_hold
from strategies import run_strategy
from charts.common import format_summary, prepare_plot_df

# Fixtures / helpers
def _make_prices(n: int, close_values=None) -> pd.DataFrame:
    """Return a minimal price DataFrame with *n* rows.

    Args:
        n: Number of rows.
        close_values: Optional list of close prices.  Defaults to 100.0.

    Returns:
        DataFrame with ``date``, ``close``, and the auxiliary columns that
        ``compute_metrics`` requires.
    """
    dates = pd.date_range("2000-01-03", periods=n, freq="B")
    closes = list(close_values) if close_values is not None else [100.0] * n
    assert len(closes) == n

    return pd.DataFrame({
        "date": dates,
        "close": closes,
        "return_1d": [0.0] * n,
        "return_5d": [0.0] * n,
        "return_20d": [0.0] * n,
        "sma_200": [100.0] * n,
        "rsi_14": [50.0] * n,
        "atr_14": [1.0] * n,
        "volatility_20d": [0.01] * n,
        "volume_ratio": [1.0] * n,
    })


def _make_golden_cross_prices(n: int = 300) -> list:
    """Prices that produce exactly one golden cross mid-way through."""
    prices = []
    for i in range(n):
        if i < 150:
            prices.append(200.0 - i * 0.3)
        else:
            prices.append(155.0 + (i - 150) * 0.5)
    return prices

# _validate_inputs
class TestValidateInputs:
    """Unit tests for input validation helper."""
    def test_raises_if_not_dataframe(self):
        with pytest.raises(TypeError, match="pandas DataFrame"):
            _validate_inputs([1, 2, 3], 1000)

    def test_raises_if_empty_dataframe(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_inputs(pd.DataFrame(), 1000)

    def test_raises_if_no_close_column(self):
        with pytest.raises(ValueError, match="'close' column"):
            _validate_inputs(pd.DataFrame({"open": [1, 2, 3]}), 1000)

    def test_raises_if_close_all_nan(self):
        df = pd.DataFrame({"close": [float("nan")] * 5})
        with pytest.raises(ValueError, match="no valid"):
            _validate_inputs(df, 1000)

    def test_raises_if_capital_not_numeric(self):
        with pytest.raises(TypeError, match="numeric"):
            _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), "1000")

    def test_raises_if_capital_zero(self):
        with pytest.raises(ValueError, match="greater than zero"):
            _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), 0)

    def test_raises_if_capital_negative(self):
        with pytest.raises(ValueError, match="greater than zero"):
            _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), -500)

    def test_raises_if_insufficient_rows(self):
        with pytest.raises(ValueError, match="Not enough data"):
            _validate_inputs(_make_prices(LONG_WINDOW), 1000)

    def test_passes_with_minimum_rows(self):
        _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), 1000)

    def test_passes_with_integer_capital(self):
        _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), 5000)

    def test_error_message_contains_counts(self):
        with pytest.raises(ValueError) as exc_info:
            _validate_inputs(_make_prices(50), 1000)
        msg = str(exc_info.value)
        assert str(MIN_ROWS_REQUIRED) in msg
        assert "50" in msg


# _compute_sma_signals
class TestComputeSmaSignals:
    """Unit tests for SMA and signal computation."""

    def test_sma_50_nan_before_window(self):
        result = _compute_sma_signals(_make_prices(300).copy())
        assert result["sma_50"].iloc[:SHORT_WINDOW - 1].isna().all()
        assert not math.isnan(result["sma_50"].iloc[SHORT_WINDOW - 1])

    def test_sma_200_nan_before_window(self):
        result = _compute_sma_signals(_make_prices(300).copy())
        assert result["sma_200"].iloc[:LONG_WINDOW - 1].isna().all()
        assert not math.isnan(result["sma_200"].iloc[LONG_WINDOW - 1])

    def test_sma_correct_for_constant_price(self):
        df = _make_prices(300, close_values=[50.0] * 300)
        result = _compute_sma_signals(df.copy())
        assert (result["sma_50"].dropna() == 50.0).all()
        assert (result["sma_200"].dropna() == 50.0).all()

    def test_signal_zero_for_flat_prices(self):
        result = _compute_sma_signals(_make_prices(300).copy())
        assert (result["signal"] == 0).all()

    def test_signal_one_for_rising_prices(self):
        prices = list(range(1, 301))
        df = _make_prices(300, close_values=prices)
        result = _compute_sma_signals(df.copy())
        assert (result["signal"].iloc[250:] == 1).all()

    def test_trade_detects_buy(self):
        prices = _make_golden_cross_prices()
        df = _make_prices(len(prices), close_values=prices)
        result = _compute_sma_signals(df.copy())
        assert len(result[result["trade"] == 1]) >= 1

    def test_trade_detects_sell(self):
        n = 350
        prices = [100.0 + i * 0.5 if i < 200 else 200.0 - (i - 200) * 2.0
                  for i in range(n)]
        df = _make_prices(n, close_values=prices)
        result = _compute_sma_signals(df.copy())
        assert len(result[result["trade"] == -1]) >= 1

    def test_trade_zero_for_flat_prices(self):
        df = _make_prices(300, close_values=[100.0] * 300)
        result = _compute_sma_signals(df.copy())
        assert (result["trade"] == 0).all()

# _simulate_trades
class TestSimulateTrades:
    """Unit tests for trade simulation and portfolio accounting."""

    def _flat_df(self, n: int = 300):
        df = _make_prices(n)
        return _compute_sma_signals(df)

    def test_starts_at_initial_capital_with_no_trade(self):
        result = _simulate_trades(self._flat_df(), 5000.0)
        assert result["daily_value"].iloc[0] == pytest.approx(5000.0)

    def test_all_cash_when_no_buy_signal(self):
        result = _simulate_trades(self._flat_df(), 1000.0)
        assert (result["position"] == 0.0).all()
        assert (result["cash"] == 1000.0).all()

    def test_buy_moves_cash_to_shares(self):
        prices = _make_golden_cross_prices()
        df = _compute_sma_signals(_make_prices(len(prices), close_values=prices))
        result = _simulate_trades(df, 10000.0)
        buy_day = result[result["trade"] == 1].index[0]
        assert result["cash"].iloc[buy_day] == pytest.approx(0.0, abs=1e-6)
        assert result["position"].iloc[buy_day] > 0

    def test_sell_moves_shares_to_cash(self):
        n = 400
        prices = [100.0 + i * 0.5 if i < 220 else 210.0 - (i - 220) * 2.0
                  for i in range(n)]
        df = _compute_sma_signals(_make_prices(n, close_values=prices))
        result = _simulate_trades(df, 10000.0)
        sells = result[result["trade"] == -1]
        if not sells.empty:
            sell_day = sells.index[0]
            assert result["position"].iloc[sell_day] == pytest.approx(0.0, abs=1e-6)
            assert result["cash"].iloc[sell_day] > 0

    def test_daily_value_equals_cash_plus_equity(self):
        prices = _make_golden_cross_prices()
        df = _compute_sma_signals(_make_prices(len(prices), close_values=prices))
        result = _simulate_trades(df, 10000.0)
        expected = result["cash"] + result["position"] * result["price"]
        pd.testing.assert_series_equal(
            result["daily_value"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False, rtol=1e-9,
        )

    def test_profit_to_date_correct(self):
        prices = _make_golden_cross_prices()
        df = _compute_sma_signals(_make_prices(len(prices), close_values=prices))
        result = _simulate_trades(df, 10000.0)
        expected = result["daily_value"] - 10000.0
        pd.testing.assert_series_equal(
            result["profit_to_date"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )

    def test_drawdown_non_positive(self):
        prices = _make_golden_cross_prices()
        df = _compute_sma_signals(_make_prices(len(prices), close_values=prices))
        result = _simulate_trades(df, 10000.0)
        assert (result["drawdown"] <= 0).all()

    def test_drawdown_zero_at_all_time_high(self):
        prices = list(range(1, 301))
        df = _compute_sma_signals(_make_prices(300, close_values=prices))
        result = _simulate_trades(df, 10000.0)
        assert result["drawdown"].max() == pytest.approx(0.0, abs=1e-9)



# moving_average_crossover (public API)
class TestMovingAverageCrossover:
    """End-to-end tests for the public strategy function."""

    def test_returns_dataframe(self):
        assert isinstance(
            moving_average_crossover(_make_prices(MIN_ROWS_REQUIRED), 10000.0, pd.DataFrame()),
            pd.DataFrame,
        )

    def test_output_has_required_columns(self):
        required = {
            "sma_50", "sma_200", "signal", "trade",
            "cash", "position", "price",
            "daily_value", "daily_returns", "profit_to_date", "drawdown",
        }
        result = moving_average_crossover(
            _make_prices(MIN_ROWS_REQUIRED), 10000.0, pd.DataFrame()
        )
        assert required.issubset(set(result.columns))

    def test_raises_insufficient_data(self):
        with pytest.raises(ValueError, match="Not enough data"):
            moving_average_crossover(_make_prices(LONG_WINDOW), 10000.0, pd.DataFrame())

    def test_raises_empty_dataframe(self):
        with pytest.raises(ValueError, match="empty"):
            moving_average_crossover(pd.DataFrame(), 10000.0, pd.DataFrame())

    def test_raises_missing_close(self):
        df = pd.DataFrame({"open": [1.0] * MIN_ROWS_REQUIRED})
        with pytest.raises(ValueError, match="'close' column"):
            moving_average_crossover(df, 10000.0, pd.DataFrame())

    def test_raises_non_positive_capital(self):
        with pytest.raises(ValueError, match="greater than zero"):
            moving_average_crossover(_make_prices(MIN_ROWS_REQUIRED), 0.0, pd.DataFrame())

    def test_raises_non_numeric_capital(self):
        with pytest.raises(TypeError, match="numeric"):
            moving_average_crossover(_make_prices(MIN_ROWS_REQUIRED), "big", pd.DataFrame())

    def test_no_crossover_stays_in_cash_original(self):
        df = _make_prices(300, close_values=[100.0] * 300)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert result["daily_value"].values == pytest.approx(10000.0)

    def test_golden_cross_invests_capital(self):
        prices = _make_golden_cross_prices()
        df = _make_prices(len(prices), close_values=prices)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert (result["position"] > 0).any()

    def test_first_daily_return_is_zero(self):
        result = moving_average_crossover(
            _make_prices(MIN_ROWS_REQUIRED), 1000.0, pd.DataFrame()
        )
        assert result["daily_returns"].iloc[0] == pytest.approx(0.0)

    def test_output_length_matches_input(self):
        n = MIN_ROWS_REQUIRED + 50
        result = moving_average_crossover(_make_prices(n), 1000.0, pd.DataFrame())
        assert len(result) == n

    def test_input_not_mutated(self):
        df = _make_prices(MIN_ROWS_REQUIRED)
        original_cols = set(df.columns)
        moving_average_crossover(df, 1000.0, pd.DataFrame())
        assert set(df.columns) == original_cols

    def test_portfolio_value_always_positive(self):
        prices = _make_golden_cross_prices()
        df = _make_prices(len(prices), close_values=prices)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert (result["daily_value"] > 0).all()

    def test_multiple_crossovers(self):
        n = 600
        prices = [
            100.0 + (i % 300) * 0.4 if (i % 300) < 150
            else 160.0 - ((i % 300) - 150) * 0.4
            for i in range(n)
        ]
        df = _make_prices(n, close_values=prices)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert (result["trade"] != 0).sum() >= 2

    def test_second_golden_cross_reinvests(self):
        prices = (
            [100.0 + i * 0.5 for i in range(230)]
            + [215.0 - i * 1.5 for i in range(100)]
            + [65.0 + i * 0.6 for i in range(200)]
        )
        df = _make_prices(len(prices), close_values=prices)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert len(result[result["trade"] == 1]) >= 2

    def test_unused_df_argument_ignored(self):
        result = moving_average_crossover(
            _make_prices(MIN_ROWS_REQUIRED), 1000.0, pd.DataFrame({"x": [1]})
        )
        assert isinstance(result, pd.DataFrame)

# buy_and_hold — full coverage
class TestBuyAndHold:
    """Tests for buy_and_hold: core behaviour, output contract, key formulas."""

    def test_position_constant(self):
        """Buy-and-hold holds the same number of shares every day."""
        prices_df = _make_prices(50)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        num_different_positions = result["position"].nunique()
        assert num_different_positions == 1

    def test_daily_value_equals_shares_times_price(self):
        """Portfolio value each day should equal shares held times price that day."""
        close_prices = [10.0 + i for i in range(50)]
        prices_df = _make_prices(50, close_values=close_prices)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        expected_value = result["position"] * result["close"]
        pd.testing.assert_series_equal(
            result["daily_value"].reset_index(drop=True),
            expected_value.reset_index(drop=True),
            check_names=False,
        )

    def test_flat_prices_zero_profit(self):
        """If the price never changes, profit should be zero."""
        flat_prices = [100.0] * 50
        prices_df = _make_prices(50, close_values=flat_prices)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        profit_series = result["profit_to_date"]
        assert profit_series.values == pytest.approx(0.0)

    def test_returns_dataframe(self):
        """buy_and_hold should return a pandas DataFrame."""
        prices_df = _make_prices(10)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        assert isinstance(result, pd.DataFrame)

    def test_output_has_all_required_columns(self):
        """Result should include position, price, daily_value, daily_returns, profit_to_date, drawdown."""
        prices_df = _make_prices(10)
        initial_capital = 5000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        required_column_names = {
            "position", "price", "daily_value", "daily_returns",
            "profit_to_date", "drawdown",
        }
        result_columns = set(result.columns)
        assert required_column_names.issubset(result_columns)

    def test_price_equals_close(self):
        """The 'price' column should match the 'close' column."""
        close_prices = [50.0 + i for i in range(20)]
        prices_df = _make_prices(20, close_values=close_prices)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        pd.testing.assert_series_equal(
            result["price"], result["close"], check_names=False
        )

    def test_daily_value_first_day_equals_initial_capital(self):
        """On the first day we invest all cash, so portfolio value equals initial capital."""
        prices_df = _make_prices(10, close_values=[50.0] * 10)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        first_day_value = result["daily_value"].iloc[0]
        assert first_day_value == pytest.approx(initial_capital)

    def test_daily_returns_first_row_zero(self):
        """The first day has no previous day to compare, so daily return is zero."""
        prices_df = _make_prices(10)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        first_day_return = result["daily_returns"].iloc[0]
        assert first_day_return == pytest.approx(0.0)

    def test_profit_to_date_equals_daily_value_minus_capital(self):
        """Profit to date is current portfolio value minus what we started with."""
        close_prices = [100.0 + i * 2 for i in range(20)]
        prices_df = _make_prices(20, close_values=close_prices)
        initial_capital = 5000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        expected_profit = result["daily_value"] - initial_capital
        pd.testing.assert_series_equal(
            result["profit_to_date"].reset_index(drop=True),
            expected_profit.reset_index(drop=True),
            check_names=False,
        )

    def test_drawdown_non_positive(self):
        """Drawdown is never positive; it measures how far we are below the peak."""
        falling_prices = [100.0 - i for i in range(30)]
        prices_df = _make_prices(30, close_values=falling_prices)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        drawdown_series = result["drawdown"]
        assert (drawdown_series <= 0).all()

    def test_input_not_mutated(self):
        """Calling buy_and_hold should not change the input DataFrame's columns."""
        prices_df = _make_prices(10)
        columns_before = set(prices_df.columns)
        initial_capital = 1000.0
        buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        columns_after = set(prices_df.columns)
        assert columns_before == columns_after

    def test_rising_prices_positive_profit_at_end(self):
        """If prices go up over time, we should have positive profit at the end."""
        rising_prices = [100.0 + i * 5 for i in range(20)]
        prices_df = _make_prices(20, close_values=rising_prices)
        initial_capital = 10000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        final_profit = result["profit_to_date"].iloc[-1]
        assert final_profit > 0

# strategies.run_strategy dispatch
class TestRunStrategy:
    """Tests for the registry-based dispatch in strategies/__init__.py."""

    def test_dispatches_buy_and_hold(self):
        result = run_strategy(_make_prices(50), "Buy and Hold", 1000.0, pd.DataFrame())
        assert "position" in result.columns

    def test_dispatches_ma_crossover_mixed_case(self):
        df = _make_prices(MIN_ROWS_REQUIRED)
        for name in [
            "Moving Average Crossover",
            "moving average crossover",
            "MOVING AVERAGE CROSSOVER",
        ]:
            result = run_strategy(df, name, 1000.0, pd.DataFrame())
            assert "sma_50" in result.columns

    def test_raises_on_invalid_strategy(self):
        with pytest.raises(ValueError, match="not a valid strategy"):
            run_strategy(_make_prices(50), "Unknown Strategy", 1000.0, pd.DataFrame())

    def test_raises_on_empty_strategy_name(self):
        with pytest.raises(ValueError):
            run_strategy(_make_prices(50), "", 1000.0, pd.DataFrame())

# charts.common
class TestFormatSummary:
    """Tests for the format_summary utility."""
    def test_return_key_formatted_as_percentage(self):
        result = format_summary({"Total Return": 0.25})
        assert result["Total Return"] == "25.00%"

    def test_percent_symbol_key_formatted_as_percentage(self):
        result = format_summary({"% Above SMA200": 0.6})
        assert result["% Above SMA200"] == "60.00%"

    def test_plain_float_two_decimal_places(self):
        result = format_summary({"Sharpe Ratio": 1.2345})
        assert result["Sharpe Ratio"] == "1.23"

    def test_non_float_converted_to_string(self):
        result = format_summary({"Win Rate": "N/A"})
        assert result["Win Rate"] == "N/A"

    def test_integer_value_converted_to_string(self):
        result = format_summary({"Count": 42})
        assert result["Count"] == "42"


class TestPreparePlotDf:
    """Tests for the prepare_plot_df utility."""

    def test_strips_timezone(self):
        df = _make_prices(MIN_ROWS_REQUIRED)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df["daily_value"] = 1000.0
        df["daily_returns"] = 0.0
        result = prepare_plot_df(df)
        assert result["date"].dt.tz is None

    def test_drops_nan_daily_value_rows(self):
        df = _make_prices(10)
        df["daily_value"] = [float("nan")] * 3 + [1000.0] * 7
        df["daily_returns"] = 0.0
        result = prepare_plot_df(df)
        assert len(result) == 7

    def test_resets_index(self):
        df = _make_prices(10)
        df["daily_value"] = 1000.0
        df["daily_returns"] = 0.0
        df = df.iloc[5:]  # intentionally broken index
        result = prepare_plot_df(df)
        assert list(result.index) == list(range(len(result)))
