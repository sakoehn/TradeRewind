"""
TradeRewind Data Scraper
Only essential features for backtesting strategies

Feature Set: ~25 focused features 
- Core OHLCV data
- Key moving averages for trend
- Essential momentum indicators
- Volume and volatility metrics
- Returns for performance calculation
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import warnings
warnings.filterwarnings('ignore')


def load_tickers_from_excel(file_path: str) -> list:
    """Load ticker list from Excel file"""
    df = pd.read_excel(file_path)
    tickers = df['Symbol'].tolist()
    tickers = [ticker.replace('.', '-') for ticker in tickers]
    
    print(f"   Loaded {len(tickers)} tickers")
    return tickers


def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate ONLY essential features for TradeRewind backtesting
    
    Feature Categories (Total: ~25 features):
    1. Returns (4) - For performance calculation
    2. Moving Averages (4) - For trend-following strategies
    3. Momentum (3) - RSI, MACD for signals
    4. Volatility (2) - ATR, historical volatility
    5. Volume (2) - Volume analysis
    6. Price Action (2) - Support/resistance levels
    
    These features support:
    - Buy/sell signal generation
    - Risk management
    - Performance tracking
    - Trade validation
    """
    if df is None or df.empty:
        return df
    
    df = df.copy()
    df = df.sort_values('date').reset_index(drop=True)
    
    #   RETURNS (4 features)  
    # Needed for: Performance metrics, Sharpe ratio calculation
    df['return_1d'] = df['close'].pct_change(1)
    df['return_5d'] = df['close'].pct_change(5)
    df['return_20d'] = df['close'].pct_change(20)
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    
    #   MOVING AVERAGES (4 features)  
    # Needed for: Trend identification, golden cross/death cross strategies
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    
    #   MOMENTUM INDICATORS (3 features)  
    # Needed for: Buy/sell signals, overbought/oversold conditions
    
    # RSI (Relative Strength Index) - Most common momentum indicator
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # MACD - Trend following momentum
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    #   VOLATILITY (2 features)  
    # Needed for: Position sizing, risk management, stop-loss placement
    
    # ATR (Average True Range) - For stop-loss calculation
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr_14'] = true_range.rolling(14).mean()
    
    # Historical Volatility - For Sharpe ratio calculation
    df['volatility_20d'] = df['return_1d'].rolling(20).std()
    
    #   VOLUME (2 features)  
    # Needed for: Trade validation, liquidity check
    df['volume_sma_20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma_20']
    
    #   PRICE ACTION (2 features)  
    # Needed for: Support/resistance, breakout strategies
    df['high_52w'] = df['high'].rolling(252).max()
    df['low_52w'] = df['low'].rolling(252).min()
    
    #   BOLLINGER BANDS (3 features)  
    # Needed for: Mean reversion strategies, volatility breakouts
    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    
    return df


def fetch_stock_data(ticker: str, years_back: int = 15) -> pd.DataFrame:
    """
    Fetch historical data and calculate essential features
    
    Args:
        ticker: Stock ticker symbol
        years_back: Number of years (default: 15)
        
    Returns:
        DataFrame with OHLCV + essential features (~25 columns total)
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365)
        
        # Download data
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, interval="1d", auto_adjust=True)
        
        if df.empty:
            print(f"   {ticker}: No data")
            return None
        
        # Clean column names
        df.columns = df.columns.str.lower()
        df = df.reset_index()
        df.columns = df.columns.str.lower()
        
        # Add metadata
        info = stock.info
        df['ticker'] = ticker
        df['company_name'] = info.get('longName', ticker)
        df['sector'] = info.get('sector', 'Unknown')
        
        # Calculate essential features
        df = calculate_features(df)
        
        print(f"   {ticker}: {len(df)} rows × {len(df.columns)} features | {df['company_name'].iloc[0]}")
        
        return df
        
    except Exception as e:
        print(f"   {ticker}: {str(e)}")
        return None


def scrape_all_stocks(tickers: list, years_back: int = 15, max_workers: int = 5, 
                     delay: float = 0.2, output_dir: str = "./data/traderewind"):
    """
    Scrape all stocks with essential features only
    
    Output: ~25 focused features per stock 
    """
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "individual_stocks"), exist_ok=True)
    
    data = {}
    successful = []
    failed = []
    total = len(tickers)
    
    print(f"\n{'='*70}")
    print(f"TradeRewind Data Scraper")
    print(f"{'='*70}")
    print(f"Stocks: {total}")
    print(f"Period: {years_back} years")
    print(f"Features: ~25 essential features (optimized for backtesting)")
    print(f"{'='*70}\n")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(fetch_stock_data, ticker, years_back): ticker 
            for ticker in tickers
        }
        
        for i, future in enumerate(as_completed(future_to_ticker), 1):
            ticker = future_to_ticker[future]
            
            try:
                df = future.result()
                
                if df is not None and not df.empty:
                    data[ticker] = df
                    successful.append(ticker)
                    
                    # Save individual file
                    filepath = os.path.join(output_dir, "individual_stocks", f"{ticker}.csv")
                    df.to_csv(filepath, index=False)
                else:
                    failed.append(ticker)
                    
            except Exception as e:
                print(f"   {ticker}: {str(e)}")
                failed.append(ticker)
            
            if i % 25 == 0 or i == total:
                print(f"\nProgress: {i}/{total} ({i/total*100:.1f}%)")
                print(f"   Success: {len(successful)} |    Failed: {len(failed)}\n")
            
            time.sleep(delay)
    
    # # Save combined dataset
    # if data:
    #     print(f"\n{'='*70}")
    #     print("Creating combined dataset...")
    #     print(f"{'='*70}\n")
        
    #     combined_df = pd.concat(data.values(), ignore_index=True)
    #     combined_path = os.path.join(output_dir, "traderewind_data.csv")
    #     combined_df.to_csv(combined_path, index=False)
        
    #     # Show feature list
    #     feature_cols = [col for col in combined_df.columns 
    #                    if col not in ['date', 'ticker', 'company_name', 'sector', 
    #                                  'open', 'high', 'low', 'close', 'volume']]
        
    #     print(f"   Combined dataset saved: {combined_path}")
    #     print(f"  Total rows: {len(combined_df):,}")
    #     print(f"  Total columns: {len(combined_df.columns)}")
    #     print(f"  Unique stocks: {combined_df['ticker'].nunique()}")
    #     print(f"  Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    #     print(f"  File size: {os.path.getsize(combined_path) / (1024**2):.1f} MB")
        
        print(f"\n{'='*70}")
        print("FEATURE LIST (Essential Features Only)")
        print(f"{'='*70}")
        print("\nCore OHLCV:")
        print("  • date, open, high, low, close, volume")
        
        print("\nCalculated Features:")
        for i, feat in enumerate(feature_cols, 1):
            print(f"  {i}. {feat}")
        
        print(f"\nTotal Features: {len(feature_cols)} calculated + 5 OHLCV = {len(feature_cols) + 5}")
        
        # Save metadata
        metadata = {
            'scrape_date': datetime.now().isoformat(),
            'total_tickers': total,
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / total * 100,
            'years_back': years_back,
            'total_features': len(combined_df.columns),
            'calculated_features': feature_cols,
        }
        
        with open(os.path.join(output_dir, "metadata.json"), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"Total attempted: {total}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print(f"Success rate: {metadata['success_rate']:.1f}%")
        print(f"Dataset optimized for TradeRewind backtesting")
        print(f"{'='*70}\n")
    
    return data


def main():
    
    # Load tickers
    ticker_file = "./ticker_list.xlsx"
    tickers = load_tickers_from_excel(ticker_file)
    
    # Test mode option
    test_mode = input(f"\nFound {len(tickers)} tickers. Run TEST MODE with 10 stocks? (y/n): ").lower()
    
    if test_mode == 'y':
        tickers = tickers[:10]
        print(f"\nTEST MODE: {len(tickers)} stocks")
    else:
        print(f"\nFULL MODE: {len(tickers)} stocks")
        print("Estimated time: 2-3 hours")
    
    # Scrape
    start_time = time.time()
    data = scrape_all_stocks(
        tickers=tickers,
        years_back=15,
        max_workers=5,
        delay=0.2,
        output_dir="./data/yfin_data"
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n   Complete in {elapsed/60:.1f} minutes")
    print(f"   Data: ./data/yfin_data/")

if __name__ == "__main__":
    main()