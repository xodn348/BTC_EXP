#!/usr/bin/env python3
"""
Plot monthly miner profit using V4 cost model (GUESS-based electricity cost).

This script:
1. Loads daily_pool_pi_usd_v4.csv
2. Aggregates to monthly profit
3. Plots top 7 pools with halving marker
4. Saves to docs/diagrams/monthly_analysis/v4_diagram/
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ==============================
# Path Configuration
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent  # From analysis/ folder to project root
DATA_FILE = BASE_DIR / "data" / "processed" / "daily_pool_pi_usd_v4.csv"
OUTPUT_DIR = BASE_DIR / "docs" / "diagrams" / "monthly_analysis" / "v4_diagram"

# Create directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==============================
# 1. Load data
# ==============================
if not DATA_FILE.exists():
    print(f"❌ Data file not found: {DATA_FILE}")
    print("   Run calc_pool_profit_v4.py first.")
    exit(1)

df = pd.read_csv(DATA_FILE)
df["date"] = pd.to_datetime(df["date"])

# ==============================
# 2. Monthly aggregation
# ==============================
df["month"] = df["date"].dt.to_period("M")

monthly_pi = (
    df.groupby(["month", "pool_name"])["Pi_usd"]
    .sum()
    .reset_index()
)

# Convert to timestamp for plotting
monthly_pi["month_dt"] = monthly_pi["month"].dt.to_timestamp()

# ==============================
# 3. Select top 7 pools
# ==============================
pool_ranks = monthly_pi.groupby("pool_name")["Pi_usd"].sum().sort_values(ascending=False)
selected_pools = pool_ranks.head(7).index.tolist()

print(f"ℹ️  Selected Pools (Top 7): {selected_pools}")
monthly_pi = monthly_pi[monthly_pi["pool_name"].isin(selected_pools)]

# ==============================
# 4. Visualization and save
# ==============================
fig, ax = plt.subplots(figsize=(14, 8))

for pool in selected_pools:
    pool_data = monthly_pi[monthly_pi["pool_name"] == pool]
    ax.plot(pool_data["month_dt"], pool_data["Pi_usd"], marker='o', label=pool)

# Emphasize y=0 line
ax.axhline(0, color='black', linewidth=1.5, alpha=0.5)

# Mark halving (April 2024)
halving_date = pd.Timestamp("2024-04-20")
ax.axvline(x=halving_date, color='red', linestyle='--', alpha=0.8)
ax.text(halving_date, ax.get_ylim()[1]*0.85, " Halving", color='red', fontsize=20, fontweight='bold')

ax.set_title(r"Profit $\Pi$ by Miner (Top 7)", fontsize=20, pad=20)
ax.set_xlabel("Date", fontsize=18)
ax.set_ylabel(r"Profit $\Pi$", fontsize=18)
ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Pool Name")
ax.grid(True, alpha=0.3)

plt.tight_layout()

# Save PDF
output_pdf = OUTPUT_DIR / "Pi_miner_v4.pdf"
plt.savefig(output_pdf)
print(f"✅ Graph saved: {output_pdf}")

# Save PNG for preview
output_png = OUTPUT_DIR / "Pi_miner_v4.png"
plt.savefig(output_png, dpi=150)
print(f"✅ PNG preview saved: {output_png}")
