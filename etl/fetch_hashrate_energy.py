"""
Script to collect Bitcoin hashrate and energy data

Data sources:
- Cambridge Bitcoin Electricity Index (CBECI)
- Blockchain.com statistics
- Or calculation/estimation

Usage:
    python etl/fetch_hashrate_energy.py --source blockchain_com --start-date 2024-01-01
    python etl/fetch_hashrate_energy.py --source sample --days 365
"""

import argparse
import pathlib
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

RAW_HASHRATE_DIR = pathlib.Path("data/raw/hashrate_energy")
RAW_HASHRATE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_blockchain_com_hashrate(start_date=None, end_date=None, days=365, output_file=None):
    """
    Fetch hashrate data from Blockchain.com API.
    """
    print("Fetching hashrate data from Blockchain.com...")
    
    # Blockchain.com stats API
    # Note: Verify actual API endpoint
    base_url = "https://api.blockchain.info/charts/hash-rate"
    
    # Calculate dates
    if end_date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    if start_date is None:
        start_date = end_date - timedelta(days=days)
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    
    # Blockchain.com API uses days parameter
    days_diff = (end_date - start_date).days
    if days_diff <= 30:
        timespan = "30days"
    elif days_diff <= 90:
        timespan = "3months"
    elif days_diff <= 365:
        timespan = "1year"
    else:
        timespan = "all"
    
    params = {
        "timespan": timespan,
        "format": "json",
        "sampled": "true"  # Sample to reduce data volume
    }
    
    try:
        print(f"Fetching data from {start_date.date()} to {end_date.date()} (timespan: {timespan})...")
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Blockchain.com API response format: {"values": [{"x": timestamp_ms, "y": value}, ...]}
        if "values" not in data:
            raise SystemExit(f"Unexpected response format from Blockchain.com API: {list(data.keys())}")
        
        values = data.get("values", [])
        if len(values) == 0:
            raise SystemExit("No data returned from Blockchain.com API")
        
        # Convert to DataFrame
        df = pd.DataFrame(values)
        if "x" not in df.columns or "y" not in df.columns:
            raise SystemExit(f"Unexpected data format. Columns: {df.columns.tolist()}")
        
        # Convert timestamp (seconds, Unix timestamp)
        df["date"] = pd.to_datetime(df["x"], unit="s").dt.date
        
        # Blockchain.com API provides hashrate in TH/s (terahash/second)
        # Check unit field: "Hash Rate TH/s"
        unit = data.get("unit", "").upper()
        if "TH/S" in unit or "TH/S" in unit:
            # Convert TH/s to EH/s: 1 EH/s = 1e6 TH/s
            df["hashrate_eh"] = df["y"] / 1e6
        elif "EH" in unit or "EXAHASH" in unit:
            # Already in EH/s
            df["hashrate_eh"] = df["y"]
        elif "H/S" in unit or "HASH" in unit:
            # If in H/s, convert to EH/s: 1 EH/s = 1e18 H/s
            df["hashrate_eh"] = df["y"] / 1e18
        else:
            # If unit unknown, assume TH/s (most common)
            print(f"Warning: Unknown unit '{unit}', assuming TH/s")
            df["hashrate_eh"] = df["y"] / 1e6
        
        df = df[["date", "hashrate_eh"]]
        
        # Filter date range (API only provides past data, so limit end_date to today)
        today = datetime.now().date()
        filter_end_date = min(end_date.date(), today)
        df = df[(df["date"] >= start_date.date()) & (df["date"] <= filter_end_date)]
        df = df.sort_values("date").reset_index(drop=True)
        
        if len(df) == 0:
            raise SystemExit(f"No data in the specified date range: {start_date.date()} to {filter_end_date}. API may only provide historical data up to today.")
        
        # Add energy data (use defaults since actual data unavailable)
        # Electricity prices vary by region but use common range
        df["elec_low"] = 0.03  # USD/kWh (cheap regions)
        df["elec_med"] = 0.05  # USD/kWh (average)
        df["elec_high"] = 0.10  # USD/kWh (expensive regions)
        # ASIC efficiency improves over time but use average here
        df["asic_j_per_th"] = 0.03  # J/TH (current efficient ASIC, e.g., Antminer S21)
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RAW_HASHRATE_DIR / f"hashrate_energy_blockchain_{timestamp}.csv"
        else:
            output_file = pathlib.Path(output_file)
        
        df.to_csv(output_file, index=False)
        print(f"Fetched {len(df)} records")
        print(f"Hashrate range: {df['hashrate_eh'].min():.2f} - {df['hashrate_eh'].max():.2f} EH/s")
        print(f"Saved to {output_file}")
        
        # Prevent rate limit
        time.sleep(1)
        
        return output_file
        
    except Exception as e:
        print(f"Error fetching from Blockchain.com: {e}")
        raise SystemExit("Failed to fetch hashrate data from Blockchain.com API. Please check your internet connection and API documentation.")


def fetch_cbeci_data(start_date=None, end_date=None, days=365, output_file=None):
    """
    Fetch data from Cambridge Bitcoin Electricity Index (CBECI).
    """
    print("Fetching data from Cambridge Bitcoin Electricity Index...")
    
    # CBECI API endpoint (example)
    # Check Cambridge documentation for actual API
    api_url = "https://ccaf.io/api/v1/cbeci/index"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Convert API response to DataFrame
        # Modify according to actual response format
        df = pd.DataFrame(data)
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RAW_HASHRATE_DIR / f"hashrate_energy_cbeci_{timestamp}.csv"
        else:
            output_file = pathlib.Path(output_file)
        
        df.to_csv(output_file, index=False)
        print(f"Fetched {len(df)} records")
        print(f"Saved to {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"Error fetching from CBECI: {e}")
        raise SystemExit("Failed to fetch data from CBECI API. Please check your internet connection and API documentation.")


def main():
    parser = argparse.ArgumentParser(
        description="Bitcoin hashrate and energy data collection"
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["blockchain_com", "cbeci"],
        default="blockchain_com",
        help="Data source (default: blockchain_com)"
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
    
    if args.source == "blockchain_com":
        fetch_blockchain_com_hashrate(
            start_date=args.start_date,
            end_date=args.end_date,
            days=args.days,
            output_file=args.output
        )
    elif args.source == "cbeci":
        fetch_cbeci_data(
            start_date=args.start_date,
            end_date=args.end_date,
            days=args.days,
            output_file=args.output
        )
    else:
        raise SystemExit(f"Unknown source: {args.source}")


if __name__ == "__main__":
    main()
