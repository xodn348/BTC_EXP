"""
Script to collect Bitcoin price data

Data sources:
- CoinGecko API (free, public)
- CoinMarketCap API (API key required)
- Yahoo Finance
- Or public datasets

Usage:
    python etl/fetch_price.py --source coingecko --start-date 2024-01-01 --end-date 2024-12-31
    python etl/fetch_price.py --source sample --days 365
"""

import argparse
import pathlib
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

RAW_PRICE_DIR = pathlib.Path("data/raw/prices")
RAW_PRICE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_coingecko_price(start_date=None, end_date=None, days=365, output_file=None):
    """
    Fetch Bitcoin price data from CoinGecko API.
    Free API, be mindful of rate limits.
    """
    print("Fetching price data from CoinGecko...")
    
    # CoinGecko API endpoint
    base_url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    
    # Calculate dates
    if end_date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    if start_date is None:
        start_date = end_date - timedelta(days=days)
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    
    # CoinGecko uses days parameter
    days_diff = (end_date - start_date).days
    if days_diff > 365:
        print(f"Warning: CoinGecko free API supports max 365 days. Using {days_diff} days may require multiple requests.")
    
    params = {
        "vs_currency": "usd",
        "days": min(days_diff, 365),
        "interval": "daily"
    }
    
    try:
        print(f"Fetching data from {start_date.date()} to {end_date.date()} ({days_diff} days)...")
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Response format: {"prices": [[timestamp_ms, price], ...]}
        prices = data.get("prices", [])
        
        # Convert to DataFrame
        df = pd.DataFrame(prices, columns=["timestamp_ms", "btc_usd"])
        df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms").dt.date
        df = df[["date", "btc_usd"]]
        
        # Filter date range
        df = df[(df["date"] >= start_date.date()) & (df["date"] <= end_date.date())]
        df = df.sort_values("date").reset_index(drop=True)
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RAW_PRICE_DIR / f"btc_price_coingecko_{timestamp}.csv"
        else:
            output_file = pathlib.Path(output_file)
        
        df.to_csv(output_file, index=False)
        print(f"Fetched {len(df)} price records")
        print(f"Price range: ${df['btc_usd'].min():,.2f} - ${df['btc_usd'].max():,.2f}")
        print(f"Saved to {output_file}")
        
        # Prevent rate limit
        time.sleep(1)
        
        return output_file
        
    except Exception as e:
        print(f"Error fetching from CoinGecko: {e}")
        raise SystemExit("Failed to fetch price data from CoinGecko API. Please check your internet connection and try again.")


def fetch_yahoo_finance_price(start_date=None, end_date=None, output_file=None):
    """
    Fetch Bitcoin price data via Yahoo Finance.
    Requires yfinance package.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance package not installed. Install with: pip install yfinance")
        return generate_sample_price(start_date=start_date, end_date=end_date, output_file=output_file)
    
    print("Fetching price data from Yahoo Finance...")
    
    # Calculate dates
    if end_date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    if start_date is None:
        start_date = end_date - timedelta(days=365)
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    
    try:
        # Bitcoin ticker
        btc = yf.Ticker("BTC-USD")
        
        # Fetch data
        df = btc.history(start=start_date, end=end_date)
        
        # Clean DataFrame
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["Date"]).dt.date
        df = df[["date", "Close"]]
        df.columns = ["date", "btc_usd"]
        df = df.sort_values("date").reset_index(drop=True)
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RAW_PRICE_DIR / f"btc_price_yahoo_{timestamp}.csv"
        else:
            output_file = pathlib.Path(output_file)
        
        df.to_csv(output_file, index=False)
        print(f"Fetched {len(df)} price records")
        print(f"Price range: ${df['btc_usd'].min():,.2f} - ${df['btc_usd'].max():,.2f}")
        print(f"Saved to {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"Error fetching from Yahoo Finance: {e}")
        raise SystemExit("Failed to fetch price data from Yahoo Finance. Please check your internet connection and try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Bitcoin price data collection"
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["coingecko", "yahoo"],
        default="coingecko",
        help="Data source (default: coingecko)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD format, default: today)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Recent N days of data (used when start-date not specified, default: 365)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path"
    )
    
    args = parser.parse_args()
    
    if args.source == "coingecko":
        fetch_coingecko_price(
            start_date=args.start_date,
            end_date=args.end_date,
            days=args.days,
            output_file=args.output
        )
    elif args.source == "yahoo":
        fetch_yahoo_finance_price(
            start_date=args.start_date,
            end_date=args.end_date,
            output_file=args.output
        )
    else:
        raise SystemExit(f"Unknown source: {args.source}")


if __name__ == "__main__":
    main()
