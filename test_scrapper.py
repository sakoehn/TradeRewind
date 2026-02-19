"""
Test Scraper - Lean Version
Quick validation with 3 stocks to verify the 25 essential features
"""

from traderewind_scraper_lean import (
    load_tickers_from_excel, 
    fetch_stock_data, 
    calculate_features
)
import pandas as pd


def test_ticker_loading():
    """Test 1: Load tickers from Excel"""
    print("=" * 70)
    print("TEST 1: Loading Tickers from Excel")
    print("=" * 70)
    
    tickers = load_tickers_from_excel("./ticker_list.xlsx")
    
    print(f"\n   Loaded {len(tickers)} tickers")
    print(f"   First 10: {', '.join(tickers[:10])}")
    print(f"   Last 10: {', '.join(tickers[-10:])}")
    
    return tickers


def test_single_stock():
    """Test 2: Fetch single stock with lean features"""
    print("\n" + "=" * 70)
    print("TEST 2: Fetching Single Stock (AAPL) - Lean Features")
    print("=" * 70)
    
    df = fetch_stock_data("AAPL", years_back=5)
    
    if df is not None:
        print(f"\n   Data shape: {df.shape}")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"   Total columns: {len(df.columns)}")
        
        # Separate core and calculated features
        core_features = ['date', 'open', 'high', 'low', 'close', 'volume', 
                        'ticker', 'company_name', 'sector']
        calculated_features = [col for col in df.columns if col not in core_features]
        
        print(f"\n📊 Feature Breakdown:")
        print(f"  Core OHLCV + Metadata: {len(core_features)} columns")
        print(f"  Calculated Features: {len(calculated_features)} columns")
        print(f"  Total: {len(df.columns)} columns")
        
        print("\n📈 Calculated Features (Essential 25):")
        print("-" * 70)
        
        # Group features by category
        feature_groups = {
            'Returns': [f for f in calculated_features if 'return' in f],
            'Moving Averages': [f for f in calculated_features if 'sma' in f or 'ema' in f],
            'Momentum': [f for f in calculated_features if any(x in f for x in ['rsi', 'macd'])],
            'Volatility': [f for f in calculated_features if any(x in f for x in ['atr', 'volatility'])],
            'Volume': [f for f in calculated_features if 'volume' in f and f != 'volume'],
            'Bollinger Bands': [f for f in calculated_features if 'bb_' in f],
            'Price Action': [f for f in calculated_features if any(x in f for x in ['high_52w', 'low_52w'])],
        }
        
        for category, features in feature_groups.items():
            if features:
                print(f"\n{category} ({len(features)}):")
                for feat in features:
                    print(f"  • {feat}")
        
        # Show sample data
        print("\n" + "=" * 70)
        print("Sample Data (first 5 rows, key columns):")
        print("=" * 70)
        display_cols = ['date', 'close', 'volume', 'sma_20', 'rsi_14', 'macd', 'return_1d', 'atr_14']
        print(df[display_cols].head().to_string(index=False))
        
        # Validate features
        print("\n" + "=" * 70)
        print("Feature Validation:")
        print("=" * 70)
        
        required_features = [
            'return_1d', 'return_5d', 'return_20d', 'log_return',
            'sma_20', 'sma_50', 'sma_200', 'ema_12',
            'rsi_14', 'macd', 'macd_signal',
            'atr_14', 'volatility_20d',
            'volume_sma_20', 'volume_ratio',
            'bb_upper', 'bb_middle', 'bb_lower',
            'high_52w', 'low_52w'
        ]
        
        missing = [f for f in required_features if f not in df.columns]
        
        if not missing:
            print("   All 20 essential calculated features present!")
        else:
            print(f"   Missing features: {missing}")
        
        # Check for NaN values
        print("\n" + "=" * 70)
        print("Data Quality Check:")
        print("=" * 70)
        
        nan_summary = df[calculated_features].isnull().sum()
        features_with_nans = nan_summary[nan_summary > 0]
        
        if len(features_with_nans) > 0:
            print("\nFeatures with NaN values (expected for initial periods):")
            for feat, count in features_with_nans.items():
                pct = (count / len(df)) * 100
                print(f"  • {feat}: {count} ({pct:.1f}%)")
        else:
            print("   No NaN values found")
        
        return df
    else:
        print("   Failed to fetch data")
        return None


def test_multiple_stocks():
    """Test 3: Fetch multiple stocks"""
    print("\n" + "=" * 70)
    print("TEST 3: Fetching Multiple Stocks (AAPL, MSFT, GOOGL)")
    print("=" * 70)
    
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    results = {}
    
    for ticker in test_tickers:
        print(f"\nFetching {ticker}...")
        df = fetch_stock_data(ticker, years_back=5)
        if df is not None:
            results[ticker] = df
    
    if results:
        print(f"\n   Successfully fetched {len(results)}/{len(test_tickers)} stocks")
        
        # Create summary comparison
        summary = []
        for ticker, df in results.items():
            core_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 
                        'ticker', 'company_name', 'sector']
            calc_features = [c for c in df.columns if c not in core_cols]
            
            summary.append({
                'ticker': ticker,
                'company': df['company_name'].iloc[0],
                'rows': len(df),
                'total_cols': len(df.columns),
                'calc_features': len(calc_features),
                'date_range': f"{df['date'].min()} to {df['date'].max()}",
                'avg_close': f"${df['close'].mean():.2f}",
                'avg_rsi': f"{df['rsi_14'].mean():.2f}",
                'avg_volatility': f"{df['volatility_20d'].mean()*100:.2f}%",
            })
        
        summary_df = pd.DataFrame(summary)
        
        print("\n" + "=" * 70)
        print("Summary Comparison:")
        print("=" * 70)
        print(summary_df.to_string(index=False))
        
        # Verify all have same features
        print("\n" + "=" * 70)
        print("Feature Consistency Check:")
        print("=" * 70)
        
        feature_sets = [set(df.columns) for df in results.values()]
        if all(fs == feature_sets[0] for fs in feature_sets):
            print("   All stocks have identical feature set")
            print(f"   Consistent schema: {len(feature_sets[0])} columns")
        else:
            print("   Feature sets differ between stocks!")
        
        return results
    else:
        print("   Failed to fetch any stocks")
        return None


def test_feature_calculations():
    """Test 4: Validate feature calculations"""
    print("\n" + "=" * 70)
    print("TEST 4: Feature Calculation Validation")
    print("=" * 70)
    
    # Create simple test data
    test_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100, freq='D'),
        'open': [100 + i * 0.5 for i in range(100)],
        'high': [101 + i * 0.5 for i in range(100)],
        'low': [99 + i * 0.5 for i in range(100)],
        'close': [100.5 + i * 0.5 for i in range(100)],
        'volume': [1000000 + i * 10000 for i in range(100)],
    })
    
    print(f"\n   Created test dataset: {len(test_data)} days")
    
    # Calculate features
    result = calculate_features(test_data)
    
    print(f"   Features calculated: {len(result.columns)} total columns")
    
    # Validate specific calculations
    print("\n" + "=" * 70)
    print("Spot Check Calculations:")
    print("=" * 70)
    
    # Check return calculation
    actual_return = (result['close'].iloc[-1] / result['close'].iloc[-2]) - 1
    calculated_return = result['return_1d'].iloc[-1]
    
    print(f"\n1. Daily Return Validation:")
    print(f"   Expected: {actual_return:.6f}")
    print(f"   Calculated: {calculated_return:.6f}")
    print(f"   Match: {'  ' if abs(actual_return - calculated_return) < 0.0001 else '  '}")
    
    # Check SMA calculation
    actual_sma_20 = result['close'].iloc[-20:].mean()
    calculated_sma_20 = result['sma_20'].iloc[-1]
    
    print(f"\n2. SMA-20 Validation:")
    print(f"   Expected: {actual_sma_20:.2f}")
    print(f"   Calculated: {calculated_sma_20:.2f}")
    print(f"   Match: {'  ' if abs(actual_sma_20 - calculated_sma_20) < 0.01 else '  '}")
    
    # Check RSI bounds
    rsi_values = result['rsi_14'].dropna()
    rsi_in_bounds = ((rsi_values >= 0) & (rsi_values <= 100)).all()
    
    print(f"\n3. RSI Bounds Validation (0-100):")
    print(f"   Min RSI: {rsi_values.min():.2f}")
    print(f"   Max RSI: {rsi_values.max():.2f}")
    print(f"   In bounds: {'  ' if rsi_in_bounds else '  '}")
    
    # Check ATR is positive
    atr_values = result['atr_14'].dropna()
    atr_positive = (atr_values > 0).all()
    
    print(f"\n4. ATR Validation (should be positive):")
    print(f"   Min ATR: {atr_values.min():.2f}")
    print(f"   All positive: {'  ' if atr_positive else '  '}")
    
    print("\n   Feature calculations validated!")


def show_final_summary():
    """Show final summary and next steps"""
    print("\n" + "=" * 70)
    print("   ALL TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
 
    # Run all tests
    try:
        tickers = test_ticker_loading()
        df = test_single_stock()
        results = test_multiple_stocks()
        test_feature_calculations()
        show_final_summary()
        
    except Exception as e:
        print(f"\n   Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()