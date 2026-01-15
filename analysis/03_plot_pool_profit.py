from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ==============================
# Path Configuration
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent  # From analysis/ folder to project root
DATA_FILE = BASE_DIR / "data" / "processed" / "daily_pool_pi_usd.csv"
# Requested save path (with .pdf extension)
OUTPUT_FILE = BASE_DIR / "docs" / "diagrams" / "monthly_analysis" / "Pi_miner.pdf"

# Create directory if it doesn't exist
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ==============================
# 1. Load data
# ==============================
if not DATA_FILE.exists():
    print(f"❌ Data file not found: {DATA_FILE}")
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
# 2.5 Select top 7 pools
# ==============================
pool_ranks = monthly_pi.groupby("pool_name")["Pi_usd"].sum().sort_values(ascending=False)
selected_pools = pool_ranks.head(7).index.tolist()

print(f"ℹ️  Selected Pools (Top 7): {selected_pools}")
monthly_pi = monthly_pi[monthly_pi["pool_name"].isin(selected_pools)]

# ==============================
# 3. Visualization and save
# ==============================
plt.figure(figsize=(14, 8))
sns.set_theme(style="whitegrid")

sns.lineplot(
    data=monthly_pi, x="month_dt", y="Pi_usd", hue="pool_name", marker="o", palette="tab20"
)

# Emphasize y=0 line
plt.axhline(0, color='black', linewidth=1.5, alpha=0.5)

# Mark halving (April 2024)
halving_date = pd.Timestamp("2024-04-20")
plt.axvline(x=halving_date, color='red', linestyle='--', alpha=0.8)
plt.text(halving_date, plt.ylim()[1]*0.85, " Halving", color='red', fontsize=20, fontweight='bold')

plt.title(r"Profit $\Pi$ by Miner (Top 7)", fontsize=20, pad=20)
plt.xlabel("Date", fontsize=18)
plt.ylabel(r"Profit $\Pi$", fontsize=18)
plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", title="Pool Name")
plt.tight_layout()

plt.savefig(OUTPUT_FILE)
print(f"✅ Graph saved: {OUTPUT_FILE}")
