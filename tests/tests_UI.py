"""Tests for the Streamlit UI in home_page.py using mocking.

This script uses unittest.mock to simulate user interactions
and verify the behavior of the Streamlit app.

Run with::

    python tests_UI.py
"""

import unittest
from unittest.mock import patch, MagicMock
import home_page

class TestStreamlitUI(unittest.TestCase):
    @patch("home_page.st")
    def test_navigation_buttons(self, mock_streamlit):
        """Test navigation buttons on the home page."""
        # Mock Streamlit functions
        mock_streamlit.button.side_effect = [True, False, True, False]
        mock_streamlit.switch_page = MagicMock()

        # Simulate clicking the "Go to stock information page" button
        home_page.st.button("Go to stock information page")
        mock_streamlit.switch_page.assert_called_with("pages/stocks_info.py")

        # Simulate clicking the "Go to strategy information page" button
        home_page.st.button("Go to strategy information page")
        mock_streamlit.switch_page.assert_called_with("pages/backtester_info.py")

    @patch("home_page.st")
    def test_backtest_valid_inputs(self, mock_streamlit):
        """Test the backtest functionality with valid inputs."""
        # Mock Streamlit inputs
        mock_streamlit.text_input.side_effect = ["AAPL", "2020-01-01", "2021-01-01"]
        mock_streamlit.selectbox.return_value = "Buy and Hold"
        mock_streamlit.number_input.return_value = 10000.0
        mock_streamlit.button.return_value = True

        # Mock backtest function
        with patch("home_page.main_backtest") as mock_backtest:
            mock_backtest.return_value = ("results", "summary", "fig")

            # Run the Streamlit app
            home_page.submit_button = True
            home_page.st.button("Run backtest")

            # Verify backtest results
            mock_backtest.assert_called_with(
                stock="AAPL",
                start_date="2020-01-01",
                end_date="2021-01-01",
                strategy="Buy and Hold",
                initial_capital=10000.0,
            )

    @patch("home_page.st")
    def test_backtest_invalid_inputs(self, mock_streamlit):
        """Test the backtest functionality with invalid inputs."""
        # Test with missing stock ticker
        mock_streamlit.text_input.side_effect = ["", "2020-01-01", "2021-01-01"]
        mock_streamlit.button.return_value = True

        with patch("home_page.st.error") as mock_error:
            home_page.submit_button = True
            home_page.st.button("Run backtest")
            mock_error.assert_called_with("Please enter a stock ticker or company name (e.g., AAPL).")

        # Test with invalid date format
        mock_streamlit.text_input.side_effect = ["AAPL", "invalid-date", "2021-01-01"]
        with patch("home_page.st.error") as mock_error:
            home_page.submit_button = True
            home_page.st.button("Run backtest")
            mock_error.assert_called_with(
                "Start date must be in the format YYYY-MM-DD (e.g., 2020-01-01)."
            )

if __name__ == "__main__":
    unittest.main()
    