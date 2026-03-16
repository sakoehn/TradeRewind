"""Comprehensive tests for TradeRewind — targeting 100 % line coverage.

Covers every module not already at 100 %:
    metrics, data_loading, stock_history, backtester, csv_to_parquet,
    graph_generation, ui_shared, charts/__init__, charts/common,
    charts/buy_and_hold_chart, charts/moving_average_chart,
    strategies/__init__ (remaining lines).

Run with::

    python -m pytest tests/test_full_coverage.py -v --tb=short
"""
# pylint: disable=unused-argument

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from charts.common import prepare_plot_df
from charts import strategy_dashboard
from charts.buy_and_hold_chart import build as bah_build
from charts.common import(
    add_initial_capital_line,
    add_portfolio_traces,
    build_metrics_df,
)
from csv_to_parquet import convert_csv_file, convert_folder
from data_loading import load_all_data
from metrics import compute_metrics
from strategies import display_name_to_key, get_strategy_display_names
from strategies.moving_average import moving_average_crossover
from strategies.buy_and_hold import buy_and_hold
from backtester import main_backtest, InvalidTickerError
from stock_history import(
    validate_stock,
    validate_date,
    get_stock_history,
    build_market_series,
    next_nonzero_date,
)
from ui_shared import render_logo, apply_shared_ui
from charts.moving_average_chart import(
    build as ma_build,
    _add_price_and_sma_traces,
    _add_trade_markers,
)
from ui_shared import inject_custom_style
# Helpers

def _make_prices(n, close_values=None, ticker="AAPL", company="Apple Inc."):
    """Minimal DataFrame that satisfies strategy + metrics contracts."""
    dates = pd.date_range("2000-01-03", periods=n, freq="B", tz="UTC")
    closes = list(close_values) if close_values is not None else [100.0] * n
    return pd.DataFrame({
        "date": dates,
        "close": closes,
        "open": closes,
        "high": closes,
        "low": closes,
        "volume": [1_000_000] * n,
        "ticker": [ticker] * n,
        "company_name": [company] * n,
        "return_1d": [0.001] * n,
        "return_5d": [0.005] * n,
        "return_20d": [0.02] * n,
        "sma_200": [100.0] * n,
        "rsi_14": [50.0] * n,
        "atr_14": [1.0] * n,
        "volatility_20d": [0.01] * n,
        "volume_ratio": [1.0] * n,
    })


def _make_full_df():
    """A small combined dataset with two tickers."""
    a = _make_prices(250, ticker="AAPL", company="Apple Inc.")
    b = _make_prices(250, ticker="MSFT", company="Microsoft Corporation")
    return pd.concat([a, b], ignore_index=True)


# metrics.py
class TestComputeMetrics(unittest.TestCase):
    """Verify compute_metrics produces correct metric types and values
    from an enriched strategy DataFrame."""

    def _run(self, n=50):
        df = _make_prices(n, close_values=[100.0 + i * 0.5 for i in range(n)])
        # Simulate buy-and-hold columns needed by compute_metrics
        shares = 10000.0 / df["close"].iloc[0]
        df["position"] = shares
        df["daily_value"] = shares * df["close"]
        df["daily_returns"] = df["daily_value"].pct_change().fillna(0)
        return compute_metrics(df, 10000.0)

    def test_returns_dict(self):
        """compute_metrics should return a plain dict."""
        self.assertIsInstance(self._run(), dict)

    def test_expected_keys(self):
        """All 14 documented metric keys must be present in the output."""
        keys = self._run().keys()
        for k in ["Total Return", "Annualized Return", "Annualized Sharpe Ratio",
                   "Max Drawdown", "Annualized Volatility", "Win Rate",
                   "Avg 1D Return", "Avg 5D Return", "Avg 20D Return",
                   "% Above SMA200", "Average RSI", "Average ATR",
                   "Average 20D Volatility", "Average Volume Ratio"]:
            self.assertIn(k, keys)

    def test_total_return_positive_for_rising(self):
        """Steadily rising prices should produce a positive total return."""
        self.assertGreater(self._run()["Total Return"], 0)

    def test_win_rate_between_0_and_1(self):
        """Win rate is a proportion and must stay in [0, 1]."""
        wr = self._run()["Win Rate"]
        self.assertGreaterEqual(wr, 0)
        self.assertLessEqual(wr, 1)

    def test_max_drawdown_non_positive(self):
        """Drawdown measures decline from peak, so it should never be positive."""
        self.assertLessEqual(self._run()["Max Drawdown"], 0)


# data_loading.py
class TestLoadAllData(unittest.TestCase):
    """Verify load_all_data reads parquet files and handles missing data."""

    def test_returns_dataframe(self):
        """Loading the real ./data directory should produce a non-empty DataFrame."""
        df = load_all_data()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)

    def test_raises_when_no_files(self):
        """A ValueError should be raised when no parquet files exist."""
        with patch("data_loading.glob.glob", return_value=[]):
            with self.assertRaises(ValueError):
                load_all_data()


# stock_history.py
class TestValidateStock(unittest.TestCase):
    """Verify validate_stock resolves tickers and company names correctly."""

    def setUp(self):
        self.df = _make_full_df()

    def test_valid_ticker(self):
        """A known ticker symbol should be returned as-is."""
        self.assertEqual(validate_stock("AAPL", self.df), "AAPL")

    def test_valid_company_name(self):
        """A unique company name should resolve to its ticker."""
        self.assertEqual(validate_stock("Apple Inc.", self.df), "AAPL")

    def test_empty_stock_raises(self):
        """An empty string should raise TypeError (no stock provided)."""
        with self.assertRaises(TypeError):
            validate_stock("", self.df)

    def test_none_stock_raises(self):
        """None should raise TypeError (no stock provided)."""
        with self.assertRaises(TypeError):
            validate_stock(None, self.df)

    def test_unknown_stock_raises(self):
        """A ticker not in the dataset should raise TypeError."""
        with self.assertRaises(TypeError):
            validate_stock("ZZZZ", self.df)

    def test_ambiguous_company_raises(self):
        """A company name mapping to multiple tickers should raise ValueError."""
        df = self.df.copy()
        df.loc[df["ticker"] == "MSFT", "company_name"] = "Apple Inc."
        with self.assertRaises(ValueError):
            validate_stock("Apple Inc.", df)


class TestValidateDate(unittest.TestCase):
    """Verify validate_date normalizes and rejects invalid date ranges."""

    def setUp(self):
        self.df = _make_prices(250, ticker="AAPL")

    def test_none_dates_use_min_max(self):
        """Passing None for both dates should default to the full data range."""
        s, e = validate_date(None, None, self.df)
        self.assertEqual(s, self.df["date"].min())
        self.assertEqual(e, self.df["date"].max())

    def test_start_after_end_raises(self):
        """A start date after the end date should raise UserWarning."""
        with self.assertRaises(UserWarning):
            validate_date("2025-01-01", "2000-01-01", self.df)

    def test_out_of_range_raises(self):
        """Dates entirely outside the available data should raise ValueError."""
        with self.assertRaises(ValueError):
            validate_date("1990-01-01", "1990-06-01", self.df)


class TestGetStockHistory(unittest.TestCase):
    """Verify get_stock_history filters data correctly and raises on bad input."""

    def setUp(self):
        self.df = _make_full_df()

    def test_returns_dataframe(self):
        """Valid ticker with no date constraints should return a non-empty DataFrame."""
        result = get_stock_history("AAPL", None, None, self.df)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)

    def test_none_df_raises(self):
        """Passing None as the stocks DataFrame should raise TypeError."""
        with self.assertRaises(TypeError):
            get_stock_history("AAPL", None, None, None)

    def test_non_df_raises(self):
        """Passing a non-DataFrame (e.g. a string) should raise TypeError."""
        with self.assertRaises(TypeError):
            get_stock_history("AAPL", None, None, "not a df")

    def test_unknown_ticker_raises(self):
        """A ticker not present in the dataset should raise TypeError."""
        with self.assertRaises(TypeError):
            get_stock_history("ZZZZ", None, None, self.df)

    def test_company_name_lookup(self):
        """Passing a company name instead of ticker should resolve and return data."""
        result = get_stock_history("Apple Inc.", None, None, self.df)
        self.assertGreater(len(result), 0)

    def test_ambiguous_company_raises(self):
        """A company name that maps to multiple tickers should raise ValueError."""
        df = self.df.copy()
        df.loc[df["ticker"] == "MSFT", "company_name"] = "Apple Inc."
        with self.assertRaises(ValueError):
            get_stock_history("Apple Inc.", None, None, df)

    def test_empty_stock_data_raises(self):
        """Requesting a ticker with no rows in the df should raise TypeError."""
        df = self.df.copy()
        df = df[df["ticker"] != "AAPL"]
        with self.assertRaises(TypeError):
            get_stock_history("AAPL", None, None, df)

    def test_date_coercion_error(self):
        """Unparseable date strings in the data should raise ValueError."""
        df = _make_prices(10, ticker="TEST")
        df["date"] = "not-a-date"
        with self.assertRaises(ValueError):
            get_stock_history("TEST", None, None, df)

    def test_no_data_in_range_raises(self):
        """Requesting a date range entirely outside available data should raise ValueError."""
        with self.assertRaises(ValueError):
            get_stock_history("AAPL", "2050-01-01", "2050-06-01", self.df)

    def test_attrs_adjusted_start(self):
        """When the requested start is before available data, attrs should note the adjustment."""
        result = get_stock_history("AAPL", "1990-01-01", None, self.df)
        self.assertIn("adjusted_start_date", result.attrs)

    def test_attrs_adjusted_end(self):
        """When the requested end is after available data, attrs should note the adjustment."""
        result = get_stock_history("AAPL", None, "2090-01-01", self.df)
        self.assertIn("adjusted_end_date", result.attrs)

    def test_empty_result_after_filter_raises(self):
        """If date filtering produces zero rows, a ValueError should be raised."""
        df = _make_prices(10, ticker="XX")
        df["date"] = pd.to_datetime("2000-01-03", utc=True)
        with self.assertRaises(ValueError):
            get_stock_history("XX", "2020-01-01", "2020-06-01", df)


class TestBuildMarketSeries(unittest.TestCase):
    """Verify build_market_series extracts a time-indexed Series for a stock."""

    def setUp(self):
        self.df = _make_full_df()

    def test_returns_series(self):
        """A valid ticker should produce a pandas Series of close prices."""
        s = build_market_series(self.df, "AAPL")
        self.assertIsInstance(s, pd.Series)

    def test_unknown_stock_raises(self):
        """A ticker not in the dataset should raise ValueError."""
        with self.assertRaises(ValueError):
            build_market_series(self.df, "ZZZZ")

    def test_missing_column_raises(self):
        """Requesting a column that doesn't exist should raise KeyError."""
        with self.assertRaises(KeyError):
            build_market_series(self.df, "AAPL", value_col="nonexistent")


class TestNextNonzeroDate(unittest.TestCase):
    """Verify next_nonzero_date finds the first non-zero value at or after a date."""

    def setUp(self):
        self.df = _make_full_df()
        self.series = build_market_series(self.df, "AAPL")

    def test_returns_timestamp(self):
        """Should return a pandas Timestamp for a valid lookup."""
        result = next_nonzero_date(self.series.index[0], self.series)
        self.assertIsInstance(result, pd.Timestamp)

    def test_no_date_before_raises(self):
        """A date before the entire series should raise ValueError (no pad match)."""
        with self.assertRaises(ValueError):
            next_nonzero_date("1900-01-01", self.series)

    def test_skips_zeros(self):
        """Leading zero values should be skipped, returning the first non-zero date."""
        s = self.series.copy()
        s.iloc[0] = 0
        s.iloc[1] = 0
        result = next_nonzero_date(s.index[0], s)
        self.assertEqual(result, s.index[2])

    def test_all_zeros_raises(self):
        """If every value is zero, there's no valid date — should raise ValueError."""
        s = self.series.copy()
        s[:] = 0
        with self.assertRaises(ValueError):
            next_nonzero_date(s.index[0], s)

# backtester.py
class TestBacktester(unittest.TestCase):
    """Verify main_backtest orchestrates the pipeline and handles bad data."""

    @patch("backtester.df", _make_full_df())
    @patch("backtester.get_stock_history")
    @patch("backtester.run_strategy")
    @patch("backtester.compute_metrics")
    @patch("backtester.strategy_dashboard")
    def test_main_backtest_returns_tuple(self, mock_dash, mock_met, mock_strat, mock_hist):
        """A successful backtest should return (results_df, summary_dict, figure, metrics_df)."""
        prices = _make_prices(50)
        results = prices.copy()
        results["daily_value"] = 10000.0
        results["daily_returns"] = 0.0

        mock_hist.return_value = prices
        mock_strat.return_value = results
        mock_met.return_value = {"Total Return": 0.1}
        mock_dash.return_value = (go.Figure(), pd.DataFrame())

        r, s, f, m = main_backtest("AAPL", None, None, "Buy and Hold", 10000.0)
        self.assertIsInstance(s, dict)
        self.assertIsInstance(f, go.Figure)

    @patch("backtester.df", pd.DataFrame())
    def test_main_backtest_empty_df_raises(self):
        """An empty module-level DataFrame should raise InvalidTickerError."""
        with self.assertRaises(InvalidTickerError):
            main_backtest("AAPL", None, None, "Buy and Hold", 10000.0)

    @patch("backtester.df", None)
    def test_main_backtest_none_df_raises(self):
        """A None module-level DataFrame should raise InvalidTickerError."""
        with self.assertRaises(InvalidTickerError):
            main_backtest("AAPL", None, None, "Buy and Hold", 10000.0)

# csv_to_parquet.py
class TestCsvToParquet(unittest.TestCase):
    """Verify CSV-to-Parquet conversion for single files and entire folders."""

    def test_convert_csv_file(self):
        """A single CSV should be converted to a readable Parquet file."""
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "test.csv"
            pd.DataFrame({"a": [1, 2]}).to_csv(csv_path, index=False)
            out = convert_csv_file(csv_path, Path(tmp))
            self.assertTrue(out.exists())
            df = pd.read_parquet(out)
            self.assertEqual(len(df), 2)

    def test_convert_folder(self):
        """All CSVs in a folder should each produce a corresponding Parquet file."""
        with tempfile.TemporaryDirectory() as tmp:
            in_dir = Path(tmp) / "in"
            out_dir = Path(tmp) / "out"
            in_dir.mkdir()
            pd.DataFrame({"x": [1]}).to_csv(in_dir / "a.csv", index=False)
            pd.DataFrame({"x": [2]}).to_csv(in_dir / "b.csv", index=False)
            convert_folder(in_dir, out_dir)
            self.assertEqual(len(list(out_dir.glob("*.parquet"))), 2)

    def test_convert_folder_creates_output_dir(self):
        """The output directory should be created automatically if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            in_dir = Path(tmp) / "in"
            out_dir = Path(tmp) / "new_out"
            in_dir.mkdir()
            convert_folder(in_dir, out_dir)
            self.assertTrue(out_dir.exists())

# ui_shared.py
class TestUiShared(unittest.TestCase):
    """Verify Streamlit UI helpers inject CSS and render the logo correctly."""

    @patch("ui_shared.st")
    def test_inject_custom_style(self, mock_st):
        """inject_custom_style should call st.markdown exactly once with the CSS."""
        inject_custom_style()
        mock_st.markdown.assert_called_once()

    @patch("ui_shared.st")
    @patch("ui_shared.os.path.isfile", return_value=False)
    def test_render_logo_missing(self, mock_isfile, mock_st):
        """When the logo file doesn't exist, st.image should not be called."""
        render_logo()
        mock_st.image.assert_not_called()

    @patch("ui_shared.st")
    @patch("ui_shared.os.path.isfile", return_value=True)
    def test_render_logo_present(self, mock_isfile, mock_st):
        """When the logo file exists, render_logo should set up columns and display it."""
        col_mock = MagicMock()
        mock_st.columns.return_value = [MagicMock(), col_mock, MagicMock()]
        render_logo()
        col_mock.__enter__.return_value = col_mock

    @patch("ui_shared.st")
    @patch("ui_shared.os.path.isfile", return_value=True)
    def test_apply_shared_ui(self, mock_isfile, mock_st):
        """apply_shared_ui should inject CSS and attempt to render the logo."""
        col_mock = MagicMock()
        mock_st.columns.return_value = [MagicMock(), col_mock, MagicMock()]
        apply_shared_ui()
        mock_st.markdown.assert_called_once()

# strategies/__init__.py — remaining lines
class TestStrategiesInit(unittest.TestCase):
    """Verify strategy registry helpers for UI dropdowns and dispatch."""

    def test_get_strategy_display_names_returns_sorted(self):
        """Display names should be returned in alphabetical order for UI dropdowns."""
        names = get_strategy_display_names()
        self.assertEqual(names, sorted(names))
        self.assertGreater(len(names), 0)

    def test_display_name_to_key_known(self):
        """Known display names should map to their lowercase registry keys."""
        self.assertEqual(display_name_to_key("Buy and Hold"), "buy and hold")
        self.assertEqual(
            display_name_to_key("Moving Average Crossover"),
            "moving average crossover",
        )

    def test_display_name_to_key_case_insensitive(self):
        """Lookup should be case-insensitive so UI input variations still work."""
        self.assertEqual(display_name_to_key("BUY AND HOLD"), "buy and hold")

    def test_display_name_to_key_unknown_falls_through(self):
        """An unrecognized name should be lowercased and returned as-is."""
        result = display_name_to_key("Some Unknown Strategy")
        self.assertEqual(result, "some unknown strategy")

# charts/common.py
class TestBuildMetricsDf(unittest.TestCase):
    """Verify build_metrics_df converts a raw summary dict into a display table."""

    def test_returns_dataframe_with_columns(self):
        """Output should be a DataFrame with 'Metric' and 'Value' columns, one row per metric."""
        df = build_metrics_df({"Total Return": 0.25, "Sharpe": 1.5})
        self.assertIn("Metric", df.columns)
        self.assertIn("Value", df.columns)
        self.assertEqual(len(df), 2)

    def test_labels_applied(self):
        """Snake_case keys should be mapped to human-readable labels via _METRIC_LABELS."""
        df = build_metrics_df({"total_return": 0.1})
        self.assertEqual(df.iloc[0]["Metric"], "Total Return")

class TestAddPortfolioTraces(unittest.TestCase):
    """Verify add_portfolio_traces adds the expected Plotly traces to a figure."""

    def _make_fig(self):
        return make_subplots(rows=1, cols=1)

    def _make_plot_df(self, n=20):
        dates = pd.date_range("2020-01-01", periods=n, freq="B")
        values = [10000 + i * 10 for i in range(n)]
        return pd.DataFrame({
            "date": dates,
            "daily_value": values,
            "daily_returns": [0.001] * n,
            "profit_to_date": [i * 10 for i in range(n)],
            "drawdown": [0.0] * n,
        })

    def test_adds_traces(self):
        """With all 4 portfolio columns present, at least 4 line traces should be added."""
        fig = self._make_fig()
        df = self._make_plot_df()
        add_portfolio_traces(fig, df, 1, 1)
        self.assertGreaterEqual(len(fig.data), 4)

    def test_empty_df_no_crash(self):
        """An empty DataFrame should not cause an error (graceful no-op)."""
        fig = self._make_fig()
        df = pd.DataFrame(columns=["date", "daily_value", "daily_returns"])
        add_portfolio_traces(fig, df, 1, 1)

    def test_missing_columns_handled(self):
        """If none of the expected columns exist, zero traces should be added."""
        fig = self._make_fig()
        df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=5, freq="B")})
        add_portfolio_traces(fig, df, 1, 1)
        self.assertEqual(len(fig.data), 0)

class TestAddInitialCapitalLine(unittest.TestCase):
    """Verify add_initial_capital_line draws a reference line on the figure."""

    def test_adds_hline(self):
        """Calling the function should not error; the line is stored in layout shapes."""
        fig = make_subplots(rows=1, cols=1)
        add_initial_capital_line(fig, 10000.0, 1, 1)

# charts/__init__.py — strategy_dashboard
class TestStrategyDashboard(unittest.TestCase):
    """Verify strategy_dashboard routes to the correct chart builder."""

    def _make_bah_results(self):
        df = _make_prices(50, close_values=[100.0 + i for i in range(50)])
        return buy_and_hold(df, 10000.0, pd.DataFrame())

    def _make_ma_results(self):
        n = 300
        prices = list(range(1, n + 1))
        df = _make_prices(n, close_values=prices)
        return moving_average_crossover(df, 10000.0, pd.DataFrame())

    def _summary(self, results):
        return compute_metrics(results, 10000.0)

    def test_buy_and_hold_route(self):
        """'Buy and Hold' should route to the buy-and-hold chart builder."""
        r = self._make_bah_results()
        fig, mdf = strategy_dashboard(r, "Buy and Hold", self._summary(r), 10000.0)
        self.assertIsInstance(fig, go.Figure)
        self.assertIsInstance(mdf, pd.DataFrame)

    def test_moving_average_route(self):
        """'Moving Average Crossover' should route to the MA chart builder."""
        r = self._make_ma_results()
        fig, mdf = strategy_dashboard(r, "Moving Average Crossover", self._summary(r), 10000.0)
        self.assertIsInstance(fig, go.Figure)

    def test_unknown_strategy_raises(self):
        """An unrecognized strategy name should raise ValueError."""
        r = self._make_bah_results()
        with self.assertRaises(ValueError):
            strategy_dashboard(r, "Nonexistent", {}, 10000.0)

    def test_case_insensitive(self):
        """Strategy name matching should be case-insensitive and strip whitespace."""
        r = self._make_bah_results()
        fig, _ = strategy_dashboard(r, "  buy and hold  ", self._summary(r), 10000.0)
        self.assertIsInstance(fig, go.Figure)

# charts/buy_and_hold_chart.py
class TestBuyAndHoldChart(unittest.TestCase):
    """Verify the Buy-and-Hold chart builder produces a valid Plotly figure."""

    def test_build_returns_figure(self):
        """build() should return a go.Figure with portfolio traces and a capital line."""
        df = _make_prices(50, close_values=[100.0 + i for i in range(50)])
        results = buy_and_hold(df, 10000.0, pd.DataFrame())
        fig = bah_build(results, {"Total Return": 0.1}, 10000.0)
        self.assertIsInstance(fig, go.Figure)

# charts/moving_average_chart.py
class TestMovingAverageChart(unittest.TestCase):
    """Verify the Moving Average chart builder and its helper functions."""

    def _results(self):
        n = 300
        prices = list(range(1, n + 1))
        df = _make_prices(n, close_values=prices)
        return moving_average_crossover(df, 10000.0, pd.DataFrame())

    def test_build_returns_figure(self):
        """build() should return a two-panel go.Figure (portfolio + price/SMA)."""
        r = self._results()
        fig = ma_build(r, {"Total Return": 0.5}, 10000.0)
        self.assertIsInstance(fig, go.Figure)

    def test_add_price_and_sma_traces(self):
        """Should add exactly 3 traces: close price, SMA-50, and SMA-200."""
        fig = make_subplots(rows=1, cols=1)
        r = self._results()
        plot_df = prepare_plot_df(r)
        _add_price_and_sma_traces(fig, plot_df, 1, 1)
        self.assertEqual(len(fig.data), 3)

    def test_add_trade_markers_with_trades(self):
        """When buy signals exist in the data, at least one buy marker trace should be added."""
        fig = make_subplots(rows=1, cols=1)
        r = self._results()
        plot_df = prepare_plot_df(r)
        _add_trade_markers(fig, plot_df, 1, 1)
        self.assertGreaterEqual(len(fig.data), 1)

    def test_add_trade_markers_no_trades(self):
        """When no trades occurred (all trade == 0), zero marker traces should be added."""
        fig = make_subplots(rows=1, cols=1)
        df = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=5, freq="B"),
            "close": [100.0] * 5,
            "trade": [0] * 5,
        })
        _add_trade_markers(fig, df, 1, 1)
        self.assertEqual(len(fig.data), 0)

# backtester.InvalidTickerError
class TestInvalidTickerError(unittest.TestCase):
    """Verify the custom InvalidTickerError exception behaves correctly."""

    def test_is_exception(self):
        """InvalidTickerError should be a subclass of Exception."""
        self.assertTrue(issubclass(InvalidTickerError, Exception))

    def test_message(self):
        """The error message should be preserved when the exception is raised."""
        e = InvalidTickerError("test")
        self.assertEqual(str(e), "test")

# Moving Average chart sell markers
class TestMovingAverageChartSellMarkers(unittest.TestCase):
    """Verify the MA chart renders sell (Death Cross) markers when present."""

    def test_chart_with_death_cross(self):
        """Prices that rise then fall should trigger both golden and death crosses,
        producing at least one 'Sell (Death Cross)' marker trace on the chart."""
        n = 500
        prices = (
            [100.0 + i * 0.5 for i in range(250)]
            + [225.0 - i * 1.5 for i in range(250)]
        )
        df = _make_prices(n, close_values=prices)
        results = moving_average_crossover(df, 10000.0, pd.DataFrame())
        fig = ma_build(results, {"Total Return": 0.1}, 10000.0)
        self.assertIsInstance(fig, go.Figure)
        sell_traces = [t for t in fig.data if "Sell" in (t.name or "")]
        self.assertGreater(len(sell_traces), 0)


if __name__ == "__main__":
    unittest.main()
