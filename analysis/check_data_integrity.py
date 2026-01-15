from pathlib import Path
import pandas as pd

# ==============================
# Path Configuration
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent  # From analysis/ folder to project root
DATA_FILE = BASE_DIR / "data" / "processed" / "daily_pool_pi_usd.csv"

if not DATA_FILE.exists():
    print(f"❌ Data file not found: {DATA_FILE}")
    exit(1)

# ==============================
# Load and Analyze Data
# ==============================
df = pd.read_csv(DATA_FILE)

# 0. Data integrity check (cases where cost is 0)
zeros = df[df["cost_usd"] == 0]
if not zeros.empty:
    print(f"\n⚠️  [WARNING] Found {len(zeros)} records with cost_usd = 0!")
    print("   -> This may indicate a data mapping issue. Example dates:")
    print(zeros[["date", "pool_name", "revenue_usd", "cost_usd"]].head(3))

# Calculate per-pool totals
pool_stats = df.groupby("pool_name")[["revenue_usd", "cost_usd", "Pi_usd"]].sum()

# Sort by profit (Pi)
pool_stats = pool_stats.sort_values("Pi_usd", ascending=False)

# Calculate margin rate (profit / revenue)
pool_stats["margin_percent"] = (pool_stats["Pi_usd"] / pool_stats["revenue_usd"] * 100)
# Calculate cost ratio (cost / revenue) - for verification
pool_stats["cost_ratio"] = (pool_stats["cost_usd"] / pool_stats["revenue_usd"] * 100)

# Number formatting (thousands separator, no decimals)
pd.options.display.float_format = '{:,.0f}'.format

print("\n📊 [Top 7 Pools Analysis]")
print(pool_stats[["revenue_usd", "cost_usd", "Pi_usd", "margin_percent", "cost_ratio"]].head(7))

# Check daily data sample (Foundry USA)
print("\n🔍 [Daily Data Sample: Foundry USA]")
if "Foundry USA" in df["pool_name"].values:
    sample = df[df["pool_name"] == "Foundry USA"].sort_values("date").tail(5)
    print(sample[["date", "revenue_usd", "cost_usd", "Pi_usd"]])
else:
    print("Foundry USA data not found.")

print("\n💡 Interpretation Guide:")
print("1. If cost_ratio is less than 1%: Cost may have been calculated 'Per Block' instead of 'Daily'.")
print("   -> Need to modify 1_calc_cost.py to multiply by 144.")
print("2. If cost_usd is 0: Data was missing when generating pool_daily_cost.csv.")
print("3. Normal case: cost_ratio should be between 50%~90% (mining margins are typically thin).")
