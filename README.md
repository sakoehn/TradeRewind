# Trade Rewind
#### Authors: Arlette Ngabonzima, Priyal Jain, Sophia Koehn, Scott Fry

[![Coverage Status](https://coveralls.io/repos/github/sakoehn/TradeRewind/badge.svg)](https://coveralls.io/github/sakoehn/TradeRewind)
[![build_test](https://github.com/sakoehn/TradeRewind/actions/workflows/build-test.yml/badge.svg)](https://github.com/sakoehn/TradeRewind/actions/workflows/build-test.yml)


## Project Type
------------------
Interactive Tool

## Project Overview
-------------------
TradeRewind is an interactive tool designed to empower users to explore and validate stock trading strategies using historical market data. By leveraging backtesting techniques, users can simulate trades, analyze performance metrics, and visualize results to make informed financial decisions. The tool is tailored for both novice and experienced traders, offering an intuitive interface for strategy testing without the risk of real-world losses. With features like single-stock analysis, multi-stock comparisons, and detailed backtesting insights, TradeRewind serves as a comprehensive platform for financial exploration and learning.

#### Team Members
Scott Fry
Arlette Ngabonzima
Priyal Jain
Sophia Koehn

## Table of Contents
-----------------------
- [Key Features](#key-features)
- [Our Goal](#our-goal)
- [Data Sources](#data-sources)
- [Software Dependencies and License Information](#software-dependencies-and-license-information)
- [Directory Summary](#directory-summary)
- [Tutorial for Using the Tool](#tutorial-for-using-the-tool)
- [Video Demonstration](#video-demonstration)

## Key Features
------------------
#### Single Stock Page
This page allows users to analyze a single stock option. Users can view historical price trends, key metrics, and performance charts for a selected stock. It provides insights into the stock's behavior over time and helps users make informed decisions.

#### Comparison Page
The comparison page enables users to analyze multiple stocks side by side. Users can compare performance metrics, trends, and other key indicators to identify the best-performing stocks or strategies.

#### Stock Information
This section provides information of a companies name and its ticker.

#### Backtester Information
This page gives the users information on different stock metrics and strategies. The goal of this page is to help users decide which strategy would work best for their goals. 

## Our Goal
-------------
Questions of Interest:

1. Can traders test trading strategies without using real money?
2. Can traders validate strategies using historical trends?
3. Can traders identify bad trading strategies from bad timing?

Goal: TradeRewind is a Python toolkit that allows users to:

- **Define** their trading strategy (rules for when to buy/sell)
    
- **Backtest** the strategy on historical stock market data
    
- **Analyze** performance with professional-grade metrics
    
- **Visualize** results with charts and reports
    
- **Compare** different strategies to find the best approach

We aim to address these challenges and make financial decisions easier for all types of users.

## Data Sources
-------------------
https://pypi.org/project/yfinance/
The data source for this project is the yfinance Python library, which provides access to historical stock market data. This library allows users to retrieve data such as stock prices, trading volumes, and financial metrics for a wide range of companies. By leveraging yfinance, TradeRewind enables users to backtest trading strategies on real historical data, ensuring accurate and reliable analysis. The data is fetched directly from Yahoo Finance, a trusted source for financial information, making it suitable for both educational and professional use.

The dataset includes 500 parquet files. Each file is a single stock with columns: date, open, low, high, close, volumne, dividends,	stock splits, ticker, company_name,	sector,	return_1d,	return_5d,	return_20d,	log_return,	sma_20,	sma_50,	sma_200, ema_12, rsi_14, macd, macd_signal, atr_14, volatility_20d, volume_sma_20, volume_ratio, high_52w, low_52w, bb_middle, bb_upper, and ub_lower.


## Software Dependencies and License Information
-------------------
The project is built using Python 3.0+ and several open-source Python packages such as `pandas`, `NumPy`, `scikit-learn`, `Streamlit`, and `yfinance`. The complete list of dependencies can be found in the `environment.yml` file. This project is licensed under the MIT License, with full details available in the `LICENSE` file.

## Directory Summary
-------------------
The TradeRewind project is organized into the following directories:

```
.
├── charts/
│   ├── __init__.py
│   ├── buy_and_hold_chart.py
│   ├── common.py
│   ├── momentum_chart.py
│   ├── moving_average_chart.py
│   └── __pycache__/
├── data/
│   ├── A.parquet
│   ├── AAPL.parquet
│   ├── ABBV.parquet
│   ├── ...
├── docs/
├── pages/
├── strategies/
├── tests/
├── app.py
├── backtester.py
├── config.toml
├── csv_to_parquet.py
├── data_loading.py
├── environment.yml
├── graph_generation.py
├── home_page.py
├── LICENSE
├── logo.png
├── metrics.py
├── README.md
├── stock_history.py
├── streamlit_style.toml
├── ui_shared.py
└── __pycache__/
    ├── backtester.cpython-313.pyc
    ├── data_loading.cpython-313.pyc
    ├── ...
```

## Tutorial for Using the Tool
-------------------

### Step 1: Cloning the Repository
To get started with the project on your local machine, first ensure you have Git installed. If not, follow the instructions provided in the Git Guide. Once Git is set up, clone the repository to your computer by executing the following command in your terminal:

```bash
git clone git@github.com:your-username/TradeRewind.git
```

### Step 2: Navigate to the Project Directory
Change into the project directory:

```bash
cd TradeRewind
```

### Step 3: Create the Conda Environment
Before creating the Conda environment, ensure you have Conda installed. If you need to install Conda, follow the Conda Installation Guide. With Conda installed, create the project environment using:

```bash
conda env create -f environment.yml
```

This command reads the `environment.yml` file and sets up an environment named `traderewind` with all the required Python dependencies.

### Step 4: Activate the Conda Environment
Activate the newly created Conda environment:

```bash
conda activate traderewind
```

### Step 5: Run the Application
With the environment set up, you can now run the application using Streamlit:

```bash
streamlit run app.py
```

This will launch the TradeRewind application in your default web browser. Navigate to `http://localhost:8501` to interact with the tool.

### Step 6: Deactivate the Conda Environment
After using the application, you can deactivate the Conda environment by running:

```bash
conda deactivate
```

### To install the project package
The built packages are found in the dist folder as: 
    dist/trade_rewind-1.0.0-py3-none-any.whl
    dist/trade_rewind-1.0.0.tar.gz
    
To install the built package, run:

```bash
python3 -m pip install ./trade_rewind-1.0.0.tar.gz
```

## Video Demonstration
-------------------------
Access the demo here for a detailed understanding of the flow of our project. *ADD VIDEO



