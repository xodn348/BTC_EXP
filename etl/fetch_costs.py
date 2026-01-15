"""
Script to collect/generate miner operating cost data

Data sources:
- Cambridge Bitcoin Electricity Index (CBECI)
- ASIC vendor specifications
- Electricity price data
- Or model-based estimation

Usage:
    python etl/fetch_costs.py --source sample
    python etl/fetch_costs.py --source cbeci --electricity-price 0.05
"""

import argparse
import pathlib
import pandas as pd
import numpy as np
import requests
from datetime import datetime

RAW_COSTS_DIR = pathlib.Path("data/raw/costs")
RAW_COSTS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_cbeci_data(output_file=None):
    """
    Fetch power consumption data from Cambridge Bitcoin Electricity Index.
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
        df = pd.DataFrame(data)
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RAW_COSTS_DIR / f"costs_cbeci_{timestamp}.csv"
        else:
            output_file = pathlib.Path(output_file)
        
        df.to_csv(output_file, index=False)
        print(f"Fetched {len(df)} cost records")
        print(f"Saved to {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"Error fetching from CBECI: {e}")
        print("Falling back to sample data...")
        return generate_sample_costs(output_file=output_file)


def calculate_miner_costs(
    hash_rates,
    electricity_price_kwh=0.05,
    efficiency_j_per_th=0.03,
    output_file=None
):
    """
    Calculate miner cost from hash rate and electricity price.
    
    Args:
        hash_rates: Hash rate for each miner (TH/s)
        electricity_price_kwh: Electricity price (USD/kWh)
        efficiency_j_per_th: ASIC efficiency (J/TH)
        output_file: Output file path
    """
    # Calculate power consumption
    # If efficiency is in J/TH, then 1 TH/s at efficiency J/TH = W (power)
    # Example: 0.03 J/TH = 0.03 W per TH/s
    power_consumption_w = hash_rates * efficiency_j_per_th
    
    # Cost per hour (USD/hour)
    cost_per_hour_usd = (power_consumption_w / 1000) * electricity_price_kwh  # W -> kW
    
    # Cost per block (USD/block, assuming ~10 min block time)
    block_time_hours = 10 / 60
    cost_per_block_usd = cost_per_hour_usd * block_time_hours
    
    # BTC price (USD/BTC, example value)
    btc_price_usd = 50000  # Needs to be updated with actual value
    
    # Convert to sat units (1 BTC = 100M sat)
    cost_per_block_sat = (cost_per_block_usd / btc_price_usd) * 100_000_000
    
    data = {
        "miner_id": range(len(hash_rates)),
        "hash_rate_th": hash_rates,
        "power_consumption_w": power_consumption_w,
        "cost_per_block_usd": cost_per_block_usd,
        "cost_per_block_sat": cost_per_block_sat.astype(int),
        "electricity_price_kwh": electricity_price_kwh,
        "efficiency_j_per_th": efficiency_j_per_th,
        "timestamp": datetime.now().isoformat()
    }
    
    df = pd.DataFrame(data)
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = RAW_COSTS_DIR / f"costs_calculated_{timestamp}.csv"
    else:
        output_file = pathlib.Path(output_file)
    
    df.to_csv(output_file, index=False)
    print(f"Calculated costs for {len(df)} miners")
    print(f"Cost range: {df['cost_per_block_sat'].min()} ~ {df['cost_per_block_sat'].max()} sat/block")
    print(f"Saved to {output_file}")
    
    return output_file


def generate_sample_costs(
    num_miners=10,
    electricity_price_kwh=0.05,
    output_file=None
):
    """
    Generate sample miner cost data.
    Generated to match miner_shares.
    """
    # Get hash rate ratios from miner_shares
    shares_file = pathlib.Path("data/processed/sim_inputs/miner_shares.parquet")
    
    if shares_file.exists():
        shares_df = pd.read_parquet(shares_file)
        shares = shares_df['h_i'].values
        num_miners = len(shares)
    else:
        # Use default distribution
        shares = np.array([0.25, 0.18, 0.12, 0.10, 0.08, 0.07, 0.07, 0.05, 0.04, 0.04])
        shares = shares[:num_miners]
        shares = shares / shares.sum()  # Normalize
    
    # Calculate cost for simulation
    # Instead of actual hash rate calculation, use cost ratio relative to block reward
    # Block reward: ~6.25 BTC = 625M sat (current, decreases after halving)
    # Assume miner cost is about 10-30% of reward
    
    # Base block reward (sat)
    base_block_reward_sat = 625_000_000  # 6.25 BTC
    
    # Miner cost is proportional to hash rate ratio, limited to certain % of reward
    # Example: largest miner's cost = 20% of reward
    cost_ratio = 0.2  # Max cost is 20% of reward
    max_cost_sat = base_block_reward_sat * cost_ratio
    
    # Set cost proportional to hash rate ratio
    # Largest miner gets max_cost_sat, others proportionally
    max_share = shares.max()
    costs_sat = (shares / max_share) * max_cost_sat if max_share > 0 else shares * max_cost_sat
    
    # Set minimum cost (1% of reward)
    min_cost_sat = base_block_reward_sat * 0.01
    costs_sat = np.maximum(costs_sat, min_cost_sat)
    
    # Generate cost data directly
    data = {
        "miner_id": range(len(shares)),
        "cost_per_block_sat": costs_sat.astype(int),
        "share": shares,
        "timestamp": datetime.now().isoformat()
    }
    
    df = pd.DataFrame(data)
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = RAW_COSTS_DIR / f"costs_sample_{timestamp}.csv"
    else:
        output_file = pathlib.Path(output_file)
    
    df.to_csv(output_file, index=False)
    print(f"Generated costs for {len(df)} miners")
    print(f"Cost range: {df['cost_per_block_sat'].min()} ~ {df['cost_per_block_sat'].max()} sat/block")
    print(f"Saved to {output_file}")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Miner operating cost data collection/generation"
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["cbeci", "sample", "calculate"],
        default="sample",
        help="Data source (default: sample)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path"
    )
    parser.add_argument(
        "--electricity-price",
        type=float,
        default=0.05,
        help="Electricity price (USD/kWh, default: 0.05)"
    )
    parser.add_argument(
        "--efficiency",
        type=float,
        default=0.03,
        help="ASIC efficiency (J/TH, default: 0.03)"
    )
    parser.add_argument(
        "--num-miners",
        type=int,
        default=10,
        help="Number of miners to generate (default: 10)"
    )
    
    args = parser.parse_args()
    
    if args.source == "cbeci":
        fetch_cbeci_data(output_file=args.output)
    elif args.source == "sample":
        generate_sample_costs(
            num_miners=args.num_miners,
            electricity_price_kwh=args.electricity_price,
            output_file=args.output
        )
    elif args.source == "calculate":
        # Can be extended to specify hash rates directly
        hash_rates = np.ones(args.num_miners) * 100  # Example: 100 TH/s each
        calculate_miner_costs(
            hash_rates=hash_rates,
            electricity_price_kwh=args.electricity_price,
            efficiency_j_per_th=args.efficiency,
            output_file=args.output
        )
    else:
        print(f"Unknown source: {args.source}")
        return


if __name__ == "__main__":
    main()
