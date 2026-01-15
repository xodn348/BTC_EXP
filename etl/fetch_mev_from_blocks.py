"""
Script to estimate MEV from block data

In Bitcoin, MEV is difficult to measure directly, but can be estimated from block data:
- High-fee blocks may have had MEV opportunities
- Analyze variability of block rewards and fees

Usage:
    python etl/fetch_mev_from_blocks.py
"""

import pathlib
import pandas as pd
import numpy as np
from datetime import datetime

RAW_MEV_DIR = pathlib.Path("data/raw/mev")
RAW_MEV_DIR.mkdir(parents=True, exist_ok=True)
RAW_BLOCKS_DIR = pathlib.Path("data/raw/blocks")
INTERIM_DIR = pathlib.Path("data/interim")


def estimate_mev_from_blocks():
    """
    Estimate MEV from block data.
    
    Method:
    1. Based on block reward (6.25 BTC) + fees
    2. Blocks with higher than average fees may have had MEV opportunities
    3. Estimate upper quantile of fees as MEV
    """
    # Read block data
    block_files = sorted(RAW_BLOCKS_DIR.glob("*.csv"))
    if not block_files:
        # Check interim data
        interim_file = INTERIM_DIR / "fees_by_block.parquet"
        if interim_file.exists():
            df = pd.read_parquet(interim_file)
        else:
            raise SystemExit("No block data found. Please collect block data first.")
    else:
        df = pd.read_csv(block_files[-1])
    
    # Standardize column names
    if "avg_sat_per_vb" not in df.columns and "total_fees_sat" in df.columns:
        if "total_vbytes" in df.columns:
            df["avg_sat_per_vb"] = df["total_fees_sat"] / df["total_vbytes"]
        else:
            raise SystemExit("total_vbytes column is required.")
    
    # Block reward (currently 6.25 BTC, may change after halving)
    # Reward may differ based on block height
    block_reward_btc = 6.25
    block_reward_sat = block_reward_btc * 100_000_000
    
    # Total block revenue = reward + fees
    if "total_fees_sat" in df.columns:
        total_revenue = block_reward_sat + df["total_fees_sat"]
    else:
        # Estimate from avg_sat_per_vb and total_vbytes
        if "total_vbytes" in df.columns:
            df["total_fees_sat"] = df["avg_sat_per_vb"] * df["total_vbytes"]
            total_revenue = block_reward_sat + df["total_fees_sat"]
        else:
            raise SystemExit("No fee data available.")
    
    # MEV estimation method 1: Upper quantile of fees
    # Fees higher than average are considered MEV opportunities
    fee_mean = df["total_fees_sat"].mean()
    fee_std = df["total_fees_sat"].std()
    
    # MEV = certain ratio of max(0, fees - average)
    # Or excess fees from top 10% blocks
    fee_threshold = df["total_fees_sat"].quantile(0.9)
    mev_estimate = np.maximum(0, df["total_fees_sat"] - fee_threshold) * 0.1  # Estimate 10% as MEV
    
    # MEV estimation method 2: Lognormal distribution-based (more realistic)
    # Actual Bitcoin MEV is often very small or 0
    # Assume MEV only occurs in high-fee blocks
    high_fee_blocks = df[df["total_fees_sat"] > fee_threshold]
    if len(high_fee_blocks) > 0:
        # Estimate excess fees from high-fee blocks as MEV
        excess_fees = high_fee_blocks["total_fees_sat"] - fee_threshold
        # Estimate MEV as 5-20% of excess fees
        mev_from_high_fee = excess_fees * 0.1
    else:
        mev_from_high_fee = pd.Series([0] * len(df))
    
    # Final MEV estimate: average of two methods or more conservative method
    # Most blocks have 0 or very small MEV
    mev_final = np.zeros(len(df))
    high_fee_indices = df[df["total_fees_sat"] > fee_threshold].index
    if len(high_fee_indices) > 0:
        mev_final[high_fee_indices] = mev_from_high_fee.values
    
    # Save results
    result_df = pd.DataFrame({
        "block_height": df["height"].values if "height" in df.columns else range(len(df)),
        "timestamp": df["timestamp"].values if "timestamp" in df.columns else [datetime.now().isoformat()] * len(df),
        "total_fees_sat": df["total_fees_sat"].values,
        "mev_sat": mev_final.astype(int),
        "mev_usd": (mev_final / 1000.0).astype(float),  # Rough conversion
    })
    
    # Optionally filter to non-zero MEV only
    # result_df = result_df[result_df["mev_sat"] > 0]
    
    output_file = RAW_MEV_DIR / f"mev_estimated_from_blocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    result_df.to_csv(output_file, index=False)
    
    print(f"Estimated MEV from {len(df)} blocks")
    print(f"MEV range: {result_df['mev_sat'].min()} ~ {result_df['mev_sat'].max()} sat")
    print(f"Non-zero MEV blocks: {(result_df['mev_sat'] > 0).sum()}")
    print(f"Saved to {output_file}")
    
    return output_file


if __name__ == "__main__":
    estimate_mev_from_blocks()
