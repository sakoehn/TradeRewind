"""Utilities for loading all stock data from Parquet files into a single DataFrame."""

import glob
import os
import pandas as pd


def load_all_data() -> pd.DataFrame:
    """Load all Parquet files from the ./data directory and concatenate them.

    Raises:
        ValueError: If no Parquet files are found.

    Returns:
        Combined DataFrame of all loaded Parquet files.
    """
    parquet_paths = glob.glob(os.path.join("data", "*.parquet"))
    all_stocks = []

    for parquet_path in parquet_paths:
        parquet_df = pd.read_parquet(parquet_path)
        all_stocks.append(parquet_df)

    if not all_stocks:
        raise ValueError("No Parquet files found.")

    combined_df = pd.concat(all_stocks)
    return combined_df


def main():
    """Run a simple demonstration of loading data and printing the head."""
    all_stocks_df = load_all_data()
    print(all_stocks_df.head())


if __name__ == "__main__":
    main()
