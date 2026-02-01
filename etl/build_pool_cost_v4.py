#!/usr/bin/env python3
"""
Processes raw electricity consumption data to compute mining electricity costs per day for each mining pool.

Based on Alexander Neumueller's formula:
  cost_per_block(t) = ((GUESS(t) / 365.25) * 1e9 * p_e) / BlockCount(t)

This script performs the following steps:
1. Loads the annualised electricity consumption estimate (GUESS(t)) from a raw CSV file.
2. Computes BlockCount(t) from historical block data (group-by date).
3. Computes cost per block:
      cost_per_block(t) = ((GUESS(t)/365.25) * 1e9 * p_e) / BlockCount(t)
   where p_e is electricity price (USD/kWh) and 1e9 converts TWh→kWh.
4. Allocates cost to each pool by actual blocks mined:
      cost_i(t) = cost_per_block(t) * blocks_mined_i(t)
5. Saves to data/processed/pool_daily_cost_v4.csv.

Note: This replaces earlier "cost to mine 1 BTC" based proxy, which may contain known inconsistencies.
"""
import pandas as pd
import pathlib

def generate_shares_from_raw(project_root):
    """
    Generates daily shares from raw pool data if the processed file doesn't exist.
    """
    raw_pool_dir = project_root / "data/raw/pools"
    if not raw_pool_dir.exists():
        raw_pool_dir = project_root / "data/raw/pool" # Fallback
    
    pool_files = sorted(list(raw_pool_dir.glob("*.csv")))
    if not pool_files:
        print(f"Warning: No raw pool data found in {raw_pool_dir}")
        return None

    print(f"Generating daily shares from {len(pool_files)} raw files...")
    pool_df = pd.concat([pd.read_csv(f) for f in pool_files], ignore_index=True)
    pool_df['date'] = pd.to_datetime(pool_df['date']).dt.date
    
    # Calculate daily totals
    daily_totals = pool_df.groupby('date')['blocks_mined'].sum().reset_index().rename(columns={'blocks_mined': 'total_blocks'})
    pool_daily = pd.merge(pool_df, daily_totals, on='date')
    pool_daily['daily_share'] = pool_daily['blocks_mined'] / pool_daily['total_blocks']
    
    # Map Miner IDs
    pool_map = {
        "Foundry USA": 0, "Foundry USA Pool": 0,
        "AntPool": 1, "Unknown": 2, "ViaBTC": 3, "F2Pool": 4,
        "Binance Pool": 5, "Mara Pool": 6, "MARA Pool": 6,
        "SBI Crypto": 7, "Braiins Pool": 8, "BTC.com": 9,
        "Poolin": 10, "BTC M4": 11, "Kucoin": 12, "KuCoin Pool": 12
    }
    pool_daily['miner_id'] = pool_daily['pool_name'].map(pool_map)
    pool_daily = pool_daily.dropna(subset=['miner_id'])
    pool_daily['miner_id'] = pool_daily['miner_id'].astype(int)
    
    # Return minimal required columns
    return pool_daily[['date', 'miner_id', 'pool_name', 'daily_share']]

def process_pool_costs():
    """
    Main function to load, process, and save the pool cost data.
    """
    # Define project root and file paths relative to the script location
    try:
        PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent  # From etl/ folder to project root
    except NameError:
        # Handle case where __file__ is not defined (e.g., in an interactive session)
        PROJECT_ROOT = pathlib.Path('.').resolve()

    ELECTRICITY_GUESS_PATH = PROJECT_ROOT / "data/raw/costs/Historical annualised electricity consumption.csv"
    BLOCK_DATA_PATH = PROJECT_ROOT / "data/processed/consolidated_block_data.csv"
    # The target file also serves as the source for daily share information.
    POOL_DATA_PATH = PROJECT_ROOT / "data/processed/pool_daily_cost_v4.csv"
    OUTPUT_PATH = POOL_DATA_PATH # v4: GUESS-based electricity cost

    # --- Configuration ---
    ELECTRICITY_PRICE_USD_PER_KWH = 0.05  # per paper / dataset assumption

    # 1) Load annualised electricity consumption GUESS(t) [TWh/year]
    try:
        elec_df = pd.read_csv(ELECTRICITY_GUESS_PATH, skiprows=1)
        # Expect columns like:
        # 'Date and Time', 'annualised consumption GUESS, TWh'
        if "Date and Time" not in elec_df.columns or "annualised consumption GUESS, TWh" not in elec_df.columns:
            raise KeyError(
                "Required columns missing. Need 'Date and Time' and 'annualised consumption GUESS, TWh'. "
                f"Got: {elec_df.columns.tolist()}"
            )
        elec_df["date"] = pd.to_datetime(elec_df["Date and Time"]).dt.normalize()
        elec_df = elec_df[["date", "annualised consumption GUESS, TWh"]].rename(
            columns={"annualised consumption GUESS, TWh": "guess_twh_annual"}
        )
    except FileNotFoundError:
        print(f"Error: Electricity consumption file not found at {ELECTRICITY_GUESS_PATH}")
        return
    except Exception as e:
        print(f"Error processing electricity consumption file '{ELECTRICITY_GUESS_PATH}': {e}")
        return

    # 2) Compute BlockCount(t) and blocks_mined per pool from consolidated block data
    try:
        block_df = pd.read_csv(BLOCK_DATA_PATH, usecols=["date", "miner_id", "pool_name"])
        block_df["date"] = pd.to_datetime(block_df["date"]).dt.normalize()
        block_df = block_df.dropna(subset=["miner_id"])
        block_df["miner_id"] = block_df["miner_id"].astype(int)

        # BlockCount(t): total blocks mined on each day
        block_count_df = block_df.groupby("date").size().reset_index(name="block_count")

        # blocks_mined_i(t): blocks mined by each pool on each day
        mined_df = (
            block_df.groupby(["date", "miner_id", "pool_name"])
            .size()
            .reset_index(name="blocks_mined")
        )
    except FileNotFoundError:
        print(f"Error: Block data file not found at {BLOCK_DATA_PATH}")
        return
    except Exception as e:
        print(f"Error processing block data file '{BLOCK_DATA_PATH}': {e}")
        return

    # 3) Daily network electricity cost (USD/day)
    # CostDay_net(t) = (GUESS(t)/365.25) * 1e9 * p_e
    elec_df["cost_usd_net_per_day"] = (
        (elec_df["guess_twh_annual"] / 365.25) * 1e9 * ELECTRICITY_PRICE_USD_PER_KWH
    )

    # 4) Merge to compute cost_per_block(t)
    # cost_per_block(t) = CostDay_net(t) / BlockCount(t)
    merged_df = pd.merge(mined_df, block_count_df, on="date", how="left")
    merged_df = pd.merge(merged_df, elec_df[["date", "cost_usd_net_per_day"]], on="date", how="left")

    # Forward-fill GUESS-based daily cost if there are occasional missing days
    merged_df = merged_df.sort_values(["date", "miner_id"])
    merged_df["cost_usd_net_per_day"] = merged_df["cost_usd_net_per_day"].ffill()

    # Drop rows where we still can't compute costs or block counts
    missing = merged_df["cost_usd_net_per_day"].isna() | merged_df["block_count"].isna()
    if missing.any():
        n_missing = int(missing.sum())
        print(f"Warning: Dropping {n_missing} rows due to missing GUESS(t) cost or block_count.")
        merged_df = merged_df.loc[~missing].copy()

    # 5) Compute cost_per_block and allocate to pools by actual blocks mined
    # cost_per_block(t) = CostDay_net(t) / BlockCount(t)
    merged_df["cost_per_block"] = merged_df["cost_usd_net_per_day"] / merged_df["block_count"]
    
    # cost_i(t) = cost_per_block(t) * blocks_mined_i(t)
    merged_df["cost_usd_per_day"] = merged_df["cost_per_block"] * merged_df["blocks_mined"]
    
    # Also keep daily_share for reference
    merged_df["daily_share"] = merged_df["blocks_mined"] / merged_df["block_count"]

    # 6) Prepare the final dataframe and save
    output_df = merged_df[["date", "miner_id", "pool_name", "blocks_mined", "block_count", "cost_per_block", "daily_share", "cost_usd_per_day"]].copy()
    output_df['date'] = output_df['date'].dt.strftime('%Y-%m-%d')
    output_df.to_csv(OUTPUT_PATH, index=False, float_format='%.10f')

    print(f"Successfully processed and updated cost data in '{OUTPUT_PATH}'")
    print(f"Sample cost_per_block: ${output_df['cost_per_block'].iloc[0]:,.2f}")
    print(f"Electricity price (USD/kWh): {ELECTRICITY_PRICE_USD_PER_KWH}")

if __name__ == "__main__":
    process_pool_costs()
