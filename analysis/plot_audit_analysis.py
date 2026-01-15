#!/usr/bin/env python3
"""
Pool Audit Score Visualization Script

Reads collected audit scores and block data, merges them,
and generates a monthly distribution PDF.
"""

import pandas as pd
import pathlib
import logging
import sys
import matplotlib.pyplot as plt
import seaborn as sns

# Paths (from analysis/ folder to project root)
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data/raw/audit"
OUTPUT_FILE = DATA_DIR / "audit_scores.csv"
ANALYSIS_DIR = PROJECT_ROOT / "docs/diagrams/monthly_analysis/audit_ratio"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def merge_and_visualize():
    """Merge audit scores with block data and generate monthly distribution PDF"""
    logging.info("Starting merge and visualization...")
    
    # Ensure analysis directory exists
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Audit Data
    if not OUTPUT_FILE.exists():
        logging.error(f"Audit data file not found at {OUTPUT_FILE}")
        return
    
    audit_df = pd.read_csv(OUTPUT_FILE)
    audit_df['match_rate'] = pd.to_numeric(audit_df['match_rate'], errors='coerce')
    
    # 2. Load Block Data
    blocks_dir = PROJECT_ROOT / "data/raw/blocks"
    block_files = list(blocks_dir.glob("*.csv"))
    
    if not block_files:
        logging.warning(f"No block data found in {blocks_dir}. Using audit data timestamps.")
        merged_df = audit_df.copy()
        merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'], unit='s')
    else:
        logging.info(f"Found {len(block_files)} block data files. Merging...")
        block_dfs = []
        for f in block_files:
            try:
                df = pd.read_csv(f)
                block_dfs.append(df)
            except Exception as e:
                logging.error(f"Error reading {f}: {e}")
        
        if block_dfs:
            blocks_df = pd.concat(block_dfs, ignore_index=True)
            # Ensure height is integer
            if 'height' in blocks_df.columns:
                blocks_df['height'] = pd.to_numeric(blocks_df['height'], errors='coerce')
            
            # Merge audit info into blocks
            audit_subset = audit_df[['height', 'pool_name', 'match_rate']].drop_duplicates(subset=['height'])
            merged_df = pd.merge(blocks_df, audit_subset, on='height', how='left')
            
            # Handle timestamp
            if 'block_timestamp' in merged_df.columns:
                merged_df['timestamp'] = pd.to_datetime(merged_df['block_timestamp'], errors='coerce')
            elif 'timestamp' in merged_df.columns:
                merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'])
        else:
            return

    # 3. Plot Monthly Distribution
    plot_df = merged_df.dropna(subset=['timestamp', 'match_rate']).copy()
    plot_df['month'] = plot_df['timestamp'].dt.to_period('M').astype(str)
    plot_df = plot_df.sort_values('month')

    # 4. Plot Low-Audit Ratio Time Series (Line Chart)
    logging.info("Generating Low-Audit Ratio Time Series...")
    
    # Use datetime for proper time series plotting
    plot_df['year_month'] = plot_df['timestamp'].dt.to_period('M')
    
    # Calculate cumulative proportions per month
    monthly_stats = []
    for name, group in plot_df.groupby('year_month'):
        total = len(group)
        if total > 0:
            monthly_stats.append({
                'date': name.to_timestamp(),
                'lt_90': (group['match_rate'] < 90).sum() / total,
                'lt_95': (group['match_rate'] < 95).sum() / total,
                'lt_98': (group['match_rate'] < 98).sum() / total
            })
    
    ts_df = pd.DataFrame(monthly_stats).sort_values('date')
    
    plt.figure(figsize=(14, 8))
    sns.set_theme(style="whitegrid")
    
    # Plot Lines
    plt.plot(ts_df['date'], ts_df['lt_90'], marker='o', linewidth=2, label='τ = 90% (Score < 90%)')
    plt.plot(ts_df['date'], ts_df['lt_95'], marker='s', linewidth=2, label='τ = 95% (Score < 95%)')
    plt.plot(ts_df['date'], ts_df['lt_98'], marker='^', linewidth=2, label='τ = 98% (Score < 98%)')
    
    # Halving Line (Red Dashed)
    halving_date = pd.Timestamp("2024-04-20")
    plt.axvline(halving_date, color='red', linestyle='--', linewidth=2, label='Halving (2024-04-20)')
    # Annotation for Halving
    plt.text(halving_date, 0.23, "Halving Event", color='red', ha='center', va='bottom', fontsize=20, fontweight='bold')
    
    # Gray Masking for Dec 2023-Jan 2024, Dec 2024-Jan 2025 (Event-based outliers)
    # Also adding Apr 2024-May 2024 for Halving period
    mask_ranges = [
        (pd.Timestamp("2023-12-01"), pd.Timestamp("2024-01-01"), "Event-driven", 'gray'),
        (pd.Timestamp("2024-12-01"), pd.Timestamp("2025-01-01"), "Event-driven", 'gray'),
        (pd.Timestamp("2024-03-01"), pd.Timestamp("2024-04-30"), None, 'red')
    ]
    for start_date, end_date, label, color in mask_ranges:
        span_end = end_date + pd.offsets.MonthEnd(0)
        alpha = 0.1 if color == 'red' else 0.3
        plt.axvspan(start_date, span_end, color=color, alpha=alpha, linewidth=0)
        # Annotation for Event-driven
        if label:
            mid_date = start_date + (span_end - start_date) / 2
            plt.text(mid_date, 0.20, label, color='dimgray', ha='center', va='bottom', fontsize=17, fontweight='bold')

    plt.title('Low Audit Blocks over Time', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Proportion of Blocks (Pr(Score < τ))', fontsize=12)
    plt.legend(title="Threshold (τ)", loc='upper left')
    plt.ylim(0, 0.30)
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    
    output_ts_pdf = ANALYSIS_DIR / "low_audit_ratio_timeseries.pdf"
    plt.savefig(output_ts_pdf)
    logging.info(f"Saved low-audit ratio time series to {output_ts_pdf}")

    # 5. Plot Audit Score vs Block Weight (WU)
    logging.info("Generating Audit Score vs Block Weight/Size plot...")
    
    x_col = None
    x_label = None
    
    if 'weight' in merged_df.columns:
        x_col = 'weight'
        x_label = 'Block Weight (WU)'
    elif 'size' in merged_df.columns:
        x_col = 'size'
        x_label = 'Block Size (Bytes)'
        logging.warning("Block weight not found, using block size as proxy.")
    
    # Save merged CSV
    output_csv = ANALYSIS_DIR / "blocks_with_audit_info.csv"
    merged_df.to_csv(output_csv, index=False)
    logging.info(f"Saved merged dataset to {output_csv}")

if __name__ == "__main__":
    merge_and_visualize()
