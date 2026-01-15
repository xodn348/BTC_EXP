from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent  # From analysis/ folder to project root
DATA_DIR = BASE_DIR / "data" / "processed"

csv_path = DATA_DIR / "consolidated_block_data.csv"
parquet_path = DATA_DIR / "consolidated_block_data.parquet"

df = pd.read_csv(
    csv_path,
    usecols=["date", "pool_name", "total_reward_usd"],
)

df.to_parquet(
    parquet_path,
    engine="pyarrow",
    compression="snappy"
)

print("✅ consolidated_block_data.parquet generation complete")
