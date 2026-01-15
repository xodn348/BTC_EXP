from pathlib import Path
import pandas as pd

# ==============================
# Path Configuration
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent  # From analysis/ folder to project root
DATA_DIR = BASE_DIR / "data" / "processed"

BLOCK_PARQUET = DATA_DIR / "consolidated_block_data.parquet"
COST_CSV = DATA_DIR / "pool_daily_cost.csv"
OUTPUT = DATA_DIR / "daily_pool_pi_usd.csv"

# ==============================
# 1. Read block-level parquet
# ==============================
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

# ==============================
# 3. Read cost (day × pool)
# ==============================
costs = pd.read_csv(
    COST_CSV,
    usecols=["date", "pool_name", "cost_usd_per_day"]
)

# Convert to dict (memory-safe)
cost_map = {
    (r.date, r.pool_name): r.cost_usd_per_day
    for r in costs.itertuples(index=False)
}

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

print("✅ daily_pool_pi_usd.csv generation complete")
print(daily_revenue.head())
