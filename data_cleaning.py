# Some tests include testing not passing the wrong path with no csv files to see if we get an error
import pandas as pd
import glob
import os

def load_all_data():

    paths = glob.glob(os.path.join('data', "*.csv"))
    all_stocks = []

    for p in paths:
        df = pd.read_csv(p, parse_dates=["date"])
        all_stocks.append(df)

    if not all_stocks:
        raise ValueError("No CSV files found.")

    combined = pd.concat(all_stocks)
    return combined


if __name__ == "__main__":
    df = load_all_data()
    print(df.head())