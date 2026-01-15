#!/usr/bin/env python3
"""
Consolidated Dataset Generator

Purpose:
  - Create block height-based consolidated dataset for simulation and analysis
  - Merge Block, Price, MEV data by block height
  - Merge Block, Price, MEV, Audit(Pool) data by block height
  - Provide base data for Miner Profit (Pi) calculation

Output:
  - data/processed/consolidated_block_data.csv
"""

import pandas as pd
import pathlib
import logging
import sys
import glob

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Path configuration
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def get_latest_file(directory, pattern):
    files = sorted(list(directory.glob(pattern)))
    if not files:
        return None
    return files[-1]

def main():
    logging.info("Starting consolidated dataset generation by block height...")

    # 1. Block Data (Base)
    block_file = get_latest_file(RAW_DIR / "blocks", "blocks_blockchain_com_*.csv")
    if not block_file:
        logging.error("Block data not found. (data/raw/blocks/)")
        return
    logging.info(f"Loading block data: {block_file.name}")
    blocks_df = pd.read_csv(block_file)
    
    # Date conversion (timestamp -> date)
    if 'timestamp' in blocks_df.columns:
        blocks_df['date'] = pd.to_datetime(blocks_df['timestamp'], unit='s').dt.date
    elif 'block_timestamp' in blocks_df.columns:
        blocks_df['date'] = pd.to_datetime(blocks_df['block_timestamp']).dt.date

    # 2. Price Data (BTC price)
    price_file = get_latest_file(RAW_DIR / "prices", "btc_price_*.csv")
    if not price_file:
        logging.warning("Price data not found. (data/raw/prices/) - Proceeding without price info")
        price_df = pd.DataFrame()
    else:
        logging.info(f"Loading price data: {price_file.name}")
        price_df = pd.read_csv(price_file)
        # Unify date column
        if 'Date' in price_df.columns:
            price_df['date'] = pd.to_datetime(price_df['Date']).dt.date
        elif 'date' in price_df.columns:
            price_df['date'] = pd.to_datetime(price_df['date']).dt.date
            
        # Unify price column
        if 'btc_usd' not in price_df.columns and 'Close' in price_df.columns:
             price_df['btc_usd'] = price_df['Close']
          
        # Remove duplicate dates (prevent data explosion during merge)
        price_df = price_df.drop_duplicates(subset=['date'])

    # 3. MEV Data (Estimated)
    mev_file = get_latest_file(RAW_DIR / "mev", "mev_estimated_from_blocks_*.csv")
    if not mev_file:
        logging.warning("MEV data not found. (data/raw/mev/) - Proceeding without MEV info")
        mev_df = pd.DataFrame()
    else:
        logging.info(f"Loading MEV data: {mev_file.name}")
        mev_df = pd.read_csv(mev_file)
        # Rename block_height to height if needed
        if 'block_height' in mev_df.columns:
            mev_df = mev_df.rename(columns={'block_height': 'height'})
    
    # 4. Audit Data (Pool & Match Rate)
    audit_df = pd.DataFrame()
    audit_files = []

    # Search for files in audit and pool folders
    f_audit = get_latest_file(RAW_DIR / "audit", "audit_*.csv")
    if f_audit: audit_files.append(f_audit)
    
    f_pool = get_latest_file(RAW_DIR / "pool", "pool_*.csv")
    if f_pool: audit_files.append(f_pool)

    if not audit_files:
        logging.warning("Audit/Pool data not found. (data/raw/audit/ or data/raw/pool/) - Proceeding without Pool/Audit info")
    else:
        for f in audit_files:
            logging.info(f"Loading Audit/Pool data: {f.name}")
            temp_df = pd.read_csv(f)
            audit_df = pd.concat([audit_df, temp_df], ignore_index=True)

        # Convert height column to integer and remove duplicates
        if 'height' in audit_df.columns:
             audit_df['height'] = pd.to_numeric(audit_df['height'], errors='coerce')
             audit_df = audit_df.dropna(subset=['height'])
             audit_df['height'] = audit_df['height'].astype(int)
             audit_df = audit_df.drop_duplicates(subset=['height'])

    # --- Data Merge ---
    logging.info("Merging data...")
    
    # Merge based on Block data
    merged = blocks_df.copy()
    
    # Merge Price (on date)
    if not price_df.empty:
        merged = pd.merge(merged, price_df[['date', 'btc_usd']], on='date', how='left')
        # Forward fill price for missing dates if any
        merged['btc_usd'] = merged['btc_usd'].ffill()

    # Merge MEV (on height)
    if not mev_df.empty:
        # Keep only relevant columns from MEV
        mev_cols = ['height', 'mev_sat', 'mev_usd']
        mev_subset = mev_df[[c for c in mev_cols if c in mev_df.columns]]
        merged = pd.merge(merged, mev_subset, on='height', how='left')
        merged['mev_sat'] = merged['mev_sat'].fillna(0)
        merged['mev_usd'] = merged['mev_usd'].fillna(0.0)
    else:
        merged['mev_sat'] = 0
        merged['mev_usd'] = 0.0

    # Merge Audit (on height)
    if not audit_df.empty:
        audit_cols = ['height', 'pool_name', 'match_rate']
        audit_subset = audit_df[[c for c in audit_cols if c in audit_df.columns]]
        merged = pd.merge(merged, audit_subset, on='height', how='left')
    else:
        merged['pool_name'] = None
        merged['match_rate'] = None
    
    # --- Calculate Derived Variables ---
    
    # 1. Block Subsidy (with halving applied)
    # Halving heights: 840,000 (2024-04-20)
    merged['block_subsidy_btc'] = merged['height'].apply(lambda h: 3.125 if h >= 840000 else 6.25)
    merged['block_subsidy_sat'] = merged['block_subsidy_btc'] * 100_000_000
    
    # 2. Total Reward (sat)
    # total_fees_sat is in blocks_df, ensure it's numeric and fill NaNs
    if 'total_fees_sat' in merged.columns:
        merged['total_fees_sat'] = pd.to_numeric(merged['total_fees_sat'], errors='coerce').fillna(0)
    else:
        logging.warning("'total_fees_sat' column missing in block data. Assuming 0 fees.")
        merged['total_fees_sat'] = 0

    merged['total_reward_sat'] = merged['block_subsidy_sat'] + merged['total_fees_sat'] + merged['mev_sat']
    merged['total_reward_btc'] = merged['total_reward_sat'] / 100_000_000
    
    # 3. Total Reward (USD)
    if 'btc_usd' in merged.columns:
        merged['total_reward_usd'] = merged['total_reward_btc'] * merged['btc_usd']

    # Save
    output_file = PROCESSED_DIR / "consolidated_block_data.csv"
    merged.to_csv(output_file, index=False)
    logging.info(f"Consolidated dataset saved: {output_file}")
    
    # Sample output
    print("\n[Generated Data Sample]")
    cols_to_show = ['height', 'date', 'total_fees_sat', 'mev_sat', 'total_reward_btc']
    if 'btc_usd' in merged.columns:
        cols_to_show.append('btc_usd')
    if 'pool_name' in merged.columns:
        cols_to_show.append('pool_name')
    if 'match_rate' in merged.columns:
        cols_to_show.append('match_rate')
    print(merged[cols_to_show].tail())

if __name__ == "__main__":
    main()
