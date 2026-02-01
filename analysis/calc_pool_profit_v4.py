#!/usr/bin/env python3
"""
Calculate daily pool profit using V4 cost model (GUESS-based electricity cost).

This script:
1. Loads block-level revenue data from parquet
2. Loads V4 cost data (GUESS-based) from pool_daily_cost_v4.csv
3. Calculates Pi = Revenue - Cost
4. Saves to daily_pool_pi_usd_v4.csv
"""
from pathlib import Path
import pandas as pd

# ==============================
# Path Configuration
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent  # From analysis/ folder to project root
DATA_DIR = BASE_DIR / "data" / "processed"

BLOCK_PARQUET = DATA_DIR / "consolidated_block_data.parquet"
COST_CSV = DATA_DIR / "pool_daily_cost_v4.csv"  # V4 cost (GUESS-based)
OUTPUT = DATA_DIR / "daily_pool_pi_usd_v4.csv"

# ==============================
# 1. Read block-level parquet
# ==============================
print("Loading block data...")
blocks = pd.read_parquet(
    BLOCK_PARQUET,
    columns=["date", "pool_name", "total_reward_usd"]
)

# ==============================
# 2. Aggregate revenue by day × pool (core)
# ==============================
daily_revenue = (
    blocks
    .groupby(["date", "pool_name"], as_index=False)["total_reward_usd"]
    .sum()
    .rename(columns={"total_reward_usd": "revenue_usd"})
)

del blocks  # Memory cleanup
print(f"Revenue data: {len(daily_revenue)} rows")

# ==============================
# 3. Read V4 cost (day × pool)
# ==============================
print("Loading V4 cost data...")
costs = pd.read_csv(
    COST_CSV,
    usecols=["date", "pool_name", "cost_usd_per_day"]
)

# Convert to dict (memory-safe)
cost_map = {
    (r.date, r.pool_name): r.cost_usd_per_day
    for r in costs.itertuples(index=False)
}
print(f"Cost map: {len(cost_map)} entries")

# ==============================
# 4. Assign cost + Calculate Pi
# ==============================
daily_revenue["cost_usd"] = [
    cost_map.get((d, p), 0.0)
    for d, p in zip(daily_revenue["date"], daily_revenue["pool_name"])
]

daily_revenue["Pi_usd"] = (
    daily_revenue["revenue_usd"] - daily_revenue["cost_usd"]
)

# ==============================
# 5. Save
# ==============================
daily_revenue.sort_values(["date", "pool_name"], inplace=True)
daily_revenue.to_csv(OUTPUT, index=False)

print(f"✅ {OUTPUT.name} generation complete")
print(daily_revenue.head())
