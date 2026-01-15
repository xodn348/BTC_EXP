#!/usr/bin/env python3
"""
Mempool.space API Audit Score Collector & Analyzer

Pipeline:
1. Iterate Block Heights (790,000 ~ 890,000)
2. Fetch Audit Score (Match Rate) & Pool Info from Mempool.space API
3. Map Block -> Pool
4. Analyze Deviation Proxy by Pool (Pre/Post Halving)
"""

import requests
import pandas as pd
import time
import pathlib
import logging
import sys
from datetime import datetime
from tqdm import tqdm
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
START_HEIGHT = 790000
END_HEIGHT = 890000
HALVING_HEIGHT = 840000
API_BASE_URL = "https://mempool.space/api"
API_V1_BASE_URL = "https://mempool.space/api/v1"
FORCE_RESTART = False  # Set to False to resume from existing file

# Paths
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data/raw/audit"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "audit_scores.csv"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / "fetch_audit.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Use session for connection pooling (faster) & Retries
session = requests.Session()
retry_strategy = Retry(
    total=5,
    backoff_factor=2,  # Wait 2s, 4s, 8s... on failures
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

def get_block_hash(height):
    """Fetch block hash by height"""
    try:
        resp = session.get(f"{API_BASE_URL}/block-height/{height}", timeout=10)
        if resp.status_code == 200:
            return resp.text
        else:
            logging.warning(f"Failed to get hash for {height}: {resp.status_code}")
    except Exception as e:
        logging.error(f"Error fetching hash for {height}: {e}")
    return None

def get_block_details(block_hash):
    """Fetch block details including pool and audit score (matchRate)"""
    try:
        resp = session.get(f"{API_V1_BASE_URL}/block/{block_hash}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            
            # Extract Pool Name
            pool_name = "Unknown"
            if 'extras' in data and 'pool' in data['extras']:
                pool_name = data['extras']['pool'].get('name', "Unknown")
            
            # Extract Audit Score (matchRate)
            # Note: matchRate is often available in 'extras' for mined blocks
            match_rate = None
            if 'extras' in data:
                match_rate = data['extras'].get('matchRate', None)
            
            return {
                'timestamp': data.get('timestamp'),
                'pool_name': pool_name,
                'match_rate': match_rate,
                'tx_count': data.get('tx_count'),
                'size': data.get('size'),
            }
    except Exception as e:
        logging.error(f"Error fetching details for {block_hash}: {e}")
    return None

def fetch_single_block(height):
    """Helper function for parallel execution"""
    block_hash = get_block_hash(height)
    if block_hash:
        details = get_block_details(block_hash)
        if details:
            return {'height': height, **details}
    return None

def collect_data():
    """Collect data from API"""
    # Handle Force Restart
    if FORCE_RESTART and OUTPUT_FILE.exists():
        logging.info("Force restart enabled. Removing existing data file to start fresh.")
        OUTPUT_FILE.unlink()

    # Load existing data to resume
    if OUTPUT_FILE.exists():
        df = pd.read_csv(OUTPUT_FILE)
        # Only resume from blocks that have valid match_rate
        if 'match_rate' in df.columns:
            collected_heights = set(df.dropna(subset=['match_rate'])['height'].unique())
        else:
            collected_heights = set()
        logging.info(f"Resuming... {len(collected_heights)} blocks already collected.")
    else:
        df = pd.DataFrame(columns=['height', 'timestamp', 'pool_name', 'match_rate', 'tx_count', 'size'])
        collected_heights = set()

    logging.info(f"Starting collection from {START_HEIGHT} to {END_HEIGHT}")
    
    # Verify API connection before starting loop
    if not get_block_hash(START_HEIGHT):
        logging.error(f"Failed to connect to API or fetch block {START_HEIGHT}. Check internet connection or API URL.")
        return
    
    new_rows = []
    save_interval = 100
    total_blocks = END_HEIGHT - START_HEIGHT + 1
    initial_count = len(collected_heights)
    
    # Determine blocks to fetch
    blocks_to_fetch = [h for h in range(START_HEIGHT, END_HEIGHT + 1) if h not in collected_heights]
    
    with tqdm(total=total_blocks, initial=initial_count, unit="block", desc="Fetching Audit Scores") as pbar:
        # Use ThreadPoolExecutor for parallel processing (Reduced to 2 to avoid 429 errors)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all tasks
            future_to_height = {executor.submit(fetch_single_block, h): h for h in blocks_to_fetch}
            
            for future in concurrent.futures.as_completed(future_to_height):
                result = future.result()
                if result:
                    new_rows.append(result)
                
                pbar.update(1)
                
                # Save periodically
                if len(new_rows) >= save_interval:
                    new_df = pd.DataFrame(new_rows)
                    if OUTPUT_FILE.exists():
                        new_df.to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
                    else:
                        new_df.to_csv(OUTPUT_FILE, index=False)
                    new_rows = []

    # Save remaining
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        if OUTPUT_FILE.exists():
            new_df.to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
        else:
            new_df.to_csv(OUTPUT_FILE, index=False)
        logging.info("Collection complete.")

def analyze_data():
    """Analyze collected data: Pool Mapping & Deviation Proxy"""
    if not OUTPUT_FILE.exists():
        logging.error("No data file found. Run collection first.")
        return

    logging.info("Starting analysis and cleanup...")
    df = pd.read_csv(OUTPUT_FILE)
    
    # 1. Clean up: Deduplicate and Sort
    original_count = len(df)
    
    # Ensure match_rate is numeric for proper sorting/analysis
    df['match_rate'] = pd.to_numeric(df['match_rate'], errors='coerce')
    
    # Sort by height and match_rate (putting NaNs first so 'last' keeps valid values)
    df = df.sort_values(by=['height', 'match_rate'], na_position='first')
    df = df.drop_duplicates(subset=['height'], keep='last')
    df = df.sort_values(by=['height'])
    
    # Save cleaned data back to file
    df.to_csv(OUTPUT_FILE, index=False)
    logging.info(f"Cleaned data saved. Removed {original_count - len(df)} duplicates. Total rows: {len(df)}")
    
    # 2. Integrity Check
    expected_heights = set(range(START_HEIGHT, END_HEIGHT + 1))
    collected_heights = set(df['height'].unique())
    missing_blocks = sorted(list(expected_heights - collected_heights))
    
    print("\n" + "="*60)
    print("DATA INTEGRITY REPORT")
    print("="*60)
    print(f"Range            : {START_HEIGHT} - {END_HEIGHT}")
    print(f"Expected Count   : {len(expected_heights)}")
    print(f"Collected Count  : {len(collected_heights)}")
    logging.info("\n" + "="*60)
    logging.info("DATA INTEGRITY REPORT")
    logging.info("="*60)
    logging.info(f"Range            : {START_HEIGHT} - {END_HEIGHT}")
    logging.info(f"Expected Count   : {len(expected_heights)}")
    logging.info(f"Collected Count  : {len(collected_heights)}")
    
    if missing_blocks:
        print("-" * 60)
        print(f"WARNING: {len(missing_blocks)} blocks are MISSING!")
        logging.info("-" * 60)
        logging.warning(f"WARNING: {len(missing_blocks)} blocks are MISSING!")
        if len(missing_blocks) <= 20:
            print(f"Missing Heights: {missing_blocks}")
            logging.info(f"Missing Heights: {missing_blocks}")
        else:
            print(f"Missing Heights: {missing_blocks[:10]} ... {missing_blocks[-10:]}")
            logging.info(f"Missing Heights: {missing_blocks[:10]} ... {missing_blocks[-10:]}")
        print("Run the script again to fetch these missing blocks.")
        logging.info("Run the script again to fetch these missing blocks.")
    else:
        print("-" * 60)
        print("STATUS           : SUCCESS (All blocks present)")
        logging.info("-" * 60)
        logging.info("STATUS           : SUCCESS (All blocks present)")
    print("="*60 + "\n")
    logging.info("="*60 + "\n")
    
    # Pre-processing
    df['is_post_halving'] = df['height'] >= HALVING_HEIGHT
    df['deviation_proxy'] = 100 - df['match_rate']  # Assuming match_rate is 0-100
    
    # Filter valid scores
    df_valid = df.dropna(subset=['match_rate'])
    
    # Group by Pool and Halving Status
    stats = df_valid.groupby(['pool_name', 'is_post_halving'])['match_rate'].agg(['count', 'mean', 'std']).reset_index()
    
    print("\n" + "="*80)
    print(f"Pool Audit Score Analysis (Deviation Proxy) - Halving Height: {HALVING_HEIGHT}")
    print("="*80)
    print(f"{'Pool Name':<20} {'Period':<10} {'Blocks':<8} {'Avg Match Rate':<15} {'Deviation Proxy':<15}")
    print("-" * 80)
    logging.info("\n" + "="*80)
    logging.info(f"Pool Audit Score Analysis (Deviation Proxy) - Halving Height: {HALVING_HEIGHT}")
    logging.info("="*80)
    logging.info(f"{'Pool Name':<20} {'Period':<10} {'Blocks':<8} {'Avg Match Rate':<15} {'Deviation Proxy':<15}")
    logging.info("-" * 80)
    
    for _, row in stats.iterrows():
        period = "Post" if row['is_post_halving'] else "Pre"
        deviation = 100 - row['mean']
        print(f"{row['pool_name']:<20} {period:<10} {int(row['count']):<8} {row['mean']:>14.2f}% {deviation:>14.2f}%")
        logging.info(f"{row['pool_name']:<20} {period:<10} {int(row['count']):<8} {row['mean']:>14.2f}% {deviation:>14.2f}%")
    print("="*80)
    logging.info("="*80)

if __name__ == "__main__":
    # Uncomment collect_data() to run collection (takes time)
    collect_data()
    
    # Run analysis on collected data
    if OUTPUT_FILE.exists():
        analyze_data()
    else:
        print(f"Data file not found at {OUTPUT_FILE}. Please uncomment collect_data() to fetch data.")