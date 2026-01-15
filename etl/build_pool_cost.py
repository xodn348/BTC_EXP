#!/usr/bin/env python3
"""
Processes raw daily cost data to calculate and update the cost per block for each mining pool.

This script performs the following steps:
1.  Loads the historical daily cost to mine one Bitcoin from a raw CSV file.
2.  Loads daily pool share data. This script assumes the share data is present in the target output file itself.
3.  Merges the cost and share data based on the date.
4.  Calculates the cost per block for each pool using the formula:
    cost_per_block = (cost_to_mine_one_btc * btc_block_subsidy) * pool_daily_share
5.  Overwrites the target file with the updated cost calculations.
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

    COST_DATA_PATH = PROJECT_ROOT / "data/raw/costs/Historical Cost to Mine One BTC (daily).csv"
    # The target file also serves as the source for daily share information.
    POOL_DATA_PATH = PROJECT_ROOT / "data/processed/pool_daily_cost.csv"
    OUTPUT_PATH = POOL_DATA_PATH # Overwrite the existing file

    # --- Configuration ---
    HALVING_DATE = pd.to_datetime("2024-04-20")
    PRE_HALVING_SUBSIDY = 6.25  # BTC
    POST_HALVING_SUBSIDY = 3.125 # BTC

    # 1. Load and clean the historical cost data (cost to mine 1 BTC)
    try:
        cost_df = pd.read_csv(
            COST_DATA_PATH,
            skiprows=1,
            usecols=["Date", "Estimated cost of minting USD"],
        )
        cost_df.rename(columns={
            "Date": "date",
            "Estimated cost of minting USD": "cost_per_btc"
        }, inplace=True)
        cost_df['date'] = pd.to_datetime(cost_df['date'])
    except FileNotFoundError:
        print(f"Error: Cost data file not found at {COST_DATA_PATH}")
        return
    except (ValueError, KeyError) as e:
        try:
            df_debug = pd.read_csv(COST_DATA_PATH, nrows=1)
            print(f"Debug: Available columns in file: {df_debug.columns.tolist()}")
        except Exception:
            pass
        print(f"Error processing cost data file '{COST_DATA_PATH}': {e}")
        return

    # 2. Load the pool share data
    try:
        if POOL_DATA_PATH.exists():
            # Use existing file
            shares_df = pd.read_csv(
                POOL_DATA_PATH,
                usecols=["date", "miner_id", "pool_name", "daily_share"],
            )
            shares_df['date'] = pd.to_datetime(shares_df['date'])
        else:
            # Generate from raw data
            print(f"File not found: {POOL_DATA_PATH}. Attempting to generate from raw data...")
            shares_df = generate_shares_from_raw(PROJECT_ROOT)
            if shares_df is None:
                return
            shares_df['date'] = pd.to_datetime(shares_df['date'])
            
    except (ValueError, KeyError) as e:
        print(f"Error processing pool share data file '{POOL_DATA_PATH}': {e}")
        return

    # 3. Merge cost data with share data
    merged_df = pd.merge(shares_df, cost_df, on="date", how="left")
    merged_df['cost_per_btc'] = merged_df['cost_per_btc'].ffill()
    if merged_df['cost_per_btc'].isna().any():
        print("Warning: Some dates could not be matched with cost data. Corresponding costs will be NaN.")
        merged_df.dropna(subset=['cost_per_btc'], inplace=True)

    # 4. Calculate the new cost per block for each miner
    merged_df['block_subsidy'] = PRE_HALVING_SUBSIDY
    merged_df.loc[merged_df['date'] >= HALVING_DATE, 'block_subsidy'] = POST_HALVING_SUBSIDY
    
    # FIX: Calculate Daily Cost (approx 144 blocks/day), not Per Block Cost
    BLOCKS_PER_DAY = 144
    total_daily_cost_network = merged_df['cost_per_btc'] * merged_df['block_subsidy'] * BLOCKS_PER_DAY
    merged_df['cost_usd_per_day'] = total_daily_cost_network * merged_df['daily_share']

    # 5. Prepare the final dataframe and save
    output_df = merged_df[["date", "miner_id", "pool_name", "daily_share", "cost_usd_per_day"]].copy()
    output_df['date'] = output_df['date'].dt.strftime('%Y-%m-%d')
    output_df.to_csv(OUTPUT_PATH, index=False, float_format='%.10f')

    print(f"Successfully processed and updated cost data in '{OUTPUT_PATH}'")

if __name__ == "__main__":
    process_pool_costs()
