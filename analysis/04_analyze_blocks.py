#!/usr/bin/env python3
"""
Monthly Block Data Analysis Script

Analysis contents:
1. Monthly Average Price per vB (sat/vB)
2. Monthly Block Fill Ratio
3. Pre/Post halving comparison
"""

import pandas as pd
import numpy as np
import pathlib
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
PROJECT_ROOT = pathlib.Path(__file__).parent.parent  # From analysis/ folder to project root
RAW_BLOCKS_DIR = PROJECT_ROOT / "data/raw/blocks"
OUTPUT_DIR = PROJECT_ROOT / "docs/diagrams/monthly_analysis"
OUTPUT_DIR = PROJECT_ROOT / "data/processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Halving information
HALVING_HEIGHT = 840000
HALVING_DATE = "2024-04-20"

# Block Fill Ratio calculation basis: Bitcoin weight-based
# Bitcoin block limit: max weight = 4,000,000
# vbytes × 4 = weight
# Therefore: Block Fill Ratio = (vbytes × 4) / 4,000,000 = weight / 4,000,000
MAX_BLOCK_WEIGHT = 4_000_000  # Bitcoin maximum block weight

def load_block_data():
    """Load block data"""
    block_files = sorted(RAW_BLOCKS_DIR.glob("blocks_blockchain_com_*.csv"))
    if not block_files:
        raise SystemExit("Block data file not found.")
    
    df = pd.read_csv(block_files[-1])
    
    # Timestamp conversion
    if 'block_timestamp' in df.columns:
        df['block_timestamp'] = pd.to_datetime(df['block_timestamp'])
    elif 'timestamp' in df.columns:
        df['block_timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Calculate avg_sat_per_vb (if not present)
    if 'avg_sat_per_vb' not in df.columns:
        if 'total_fees_sat' in df.columns and 'total_vbytes' in df.columns:
            df['avg_sat_per_vb'] = df['total_fees_sat'] / df['total_vbytes']
        else:
            raise SystemExit("Cannot calculate avg_sat_per_vb.")
    
    # Add column for monthly grouping
    df['year_month'] = df['block_timestamp'].dt.to_period('M')
    df['year_month_str'] = df['year_month'].astype(str)
    df['is_post_halving'] = df['height'] >= HALVING_HEIGHT
    
    return df

def calculate_monthly_metrics(df):
    """Calculate monthly metrics"""
    monthly_stats = []
    
    for year_month, group in df.groupby('year_month'):
        stats = {
            'year_month': str(year_month),
            'year': year_month.year,
            'month': year_month.month,
            'block_count': len(group),
            'is_post_halving': group['is_post_halving'].iloc[0],
        }
        
        # 1. Average Price per vB (Median only - ignore outliers)
        stats['avg_sat_per_vb_median'] = group['avg_sat_per_vb'].median()
        
        # 1.5 Total Fees (Median)
        if 'total_fees_sat' in group.columns:
            stats['total_fees_median'] = group['total_fees_sat'].median()
        else:
            stats['total_fees_median'] = np.nan

        # R_t: Block reward (block subsidy)
        #   - Pre-halving (height < 840,000): 6.25 BTC = 625,000,000 sat
        #   - Post-halving (height >= 840,000): 3.125 BTC = 312,500,000 sat
        # F_t: Actual block's total_fees_sat
        # M_t: Sampled from MEV sampler (no MEV info in actual block data)
        if 'total_fees_sat' in group.columns and 'height' in group.columns:
            F_t_values = group['total_fees_sat'].values
            # Determine R_t based on block height
            R_t_values = np.where(group['height'].values < HALVING_HEIGHT, 
                                  625_000_000,  # Pre-halving: 6.25 BTC
                                  312_500_000)   # Post-halving: 3.125 BTC
            
            # Load MEV sampler (use 0 if not available)
            mev_parquet = PROJECT_ROOT / "data/processed/sim_inputs/mev_sampler.parquet"
            if mev_parquet.exists():
                mev_df = pd.read_parquet(mev_parquet)
                mev_median = mev_df["mev_sat"].median()
            else:
                mev_median = 0  # Use 0 if no MEV data
            
            # X_t = R_t + F_t + M_t (use median for M_t)
            X_t_values = R_t_values + F_t_values + mev_median
            stats['X_t_median'] = np.median(X_t_values)
        else:
            stats['X_t_median'] = np.nan
        
        # 3. Block Fill Ratio (Median only - ignore outliers)
        # Calculation: (vbytes × 4) / MAX_BLOCK_WEIGHT = weight / 4,000,000
        # Bitcoin block limit: max weight = 4,000,000
        # vbytes × 4 = weight
        if 'total_vbytes' in group.columns:
            # vbytes × 4 = weight, weight / 4,000,000 = fill ratio
            fill_ratios = (group['total_vbytes'] * 4) / MAX_BLOCK_WEIGHT
        elif 'weight' in group.columns:
            # Use weight directly if available
            fill_ratios = group['weight'] / MAX_BLOCK_WEIGHT
        else:
            raise ValueError("total_vbytes or weight column is required.")
        
        stats['block_fill_ratio_median'] = fill_ratios.median()
        
        monthly_stats.append(stats)
    
    return pd.DataFrame(monthly_stats)

def print_analysis_table(monthly_stats):
    """Print analysis table (Median only - ignore outliers)"""
    print("\n" + "=" * 100)
    print("Monthly Block Data Analysis Results (Median - Ignoring Outliers)")
    print("=" * 100)
    
    # Prepare table data
    print(f"\n{'Year-Month':<12} {'Halving':<10} {'Blocks':<8} {'Price/vB (Median)':<20} {'Fees (M sat)':<15} {'Fill Ratio (Median %)':<25}")
    print("-" * 100)
    
    for _, row in monthly_stats.iterrows():
        halving = "Post" if row['is_post_halving'] else "Pre"
        print(f"{row['year_month']:<12} {halving:<10} {row['block_count']:<8} "
              f"{row['avg_sat_per_vb_median']:>18.2f}  {row['total_fees_median']/1e6:>13.2f}  "
              f"{row['block_fill_ratio_median']*100:>23.2f}")
    
    print("=" * 100)
    
    # Pre/Post halving comparison
    pre_halving = monthly_stats[~monthly_stats['is_post_halving']]
    post_halving = monthly_stats[monthly_stats['is_post_halving']]
    
    print("\nPre/Post Halving Comparison (Median):")
    print("-" * 100)
    print(f"{'Metric':<40} {'Pre-Halving (Median)':<25} {'Post-Halving (Median)':<25} {'Change':<25}")
    print("-" * 100)
    
    # Price per vB (Median)
    pre_price_median = pre_halving['avg_sat_per_vb_median'].median()
    post_price_median = post_halving['avg_sat_per_vb_median'].median()
    price_change = ((post_price_median - pre_price_median) / pre_price_median) * 100
    
    print(f"{'Price per vB (sat/vB)':<40} {pre_price_median:>23.2f}  {post_price_median:>23.2f}  {price_change:>23.1f}%")
    
    # Block Fill Ratio (Median)
    pre_fill_median = pre_halving['block_fill_ratio_median'].median() * 100
    post_fill_median = post_halving['block_fill_ratio_median'].median() * 100
    fill_change = post_fill_median - pre_fill_median
    
    print(f"{'Block Fill Ratio (%)':<40} {pre_fill_median:>23.2f}  {post_fill_median:>23.2f}  {fill_change:>23.2f}pp")
    
    # X_t (Median)
    pre_X_t_median = pre_halving['X_t_median'].median() / 1e6
    post_X_t_median = post_halving['X_t_median'].median() / 1e6
    X_t_change = ((post_X_t_median - pre_X_t_median) / pre_X_t_median) * 100
    
    print(f"{'X_t = F_t + M_t (M sat)':<40} {pre_X_t_median:>23.2f}  {post_X_t_median:>23.2f}  {X_t_change:>23.1f}%")
    
    # Correlation check (graph similarity verification)
    if 'total_fees_median' in monthly_stats.columns:
        corr = monthly_stats['avg_sat_per_vb_median'].corr(monthly_stats['total_fees_median'])
        print("-" * 100)
        print(f"[Verification] sat/vB and Total Fees correlation: {corr:.6f} (closer to 1.0 = more similar graphs)")

    print("=" * 100)
    
    # Statistics summary
    print("\nStatistics Summary:")
    print("-" * 100)
    print(f"Pre-halving period: {len(pre_halving)} months ({pre_halving['year_month'].iloc[0]} ~ {pre_halving['year_month'].iloc[-1]})")
    print(f"Post-halving period: {len(post_halving)} months ({post_halving['year_month'].iloc[0]} ~ {post_halving['year_month'].iloc[-1]})")
    print(f"Halving date: {HALVING_DATE} (block height {HALVING_HEIGHT:,})")
    print("=" * 100)

def create_graphs_pdf(monthly_stats):
    """Generate graphs as separate PDF files"""
    sns.set_style("whitegrid")
    
    # Date conversion
    monthly_stats['date'] = pd.to_datetime(monthly_stats['year_month'].astype(str) + '-01')
    halving_date = pd.to_datetime(HALVING_DATE)
    
    # Split pre/post halving
    pre_halving = monthly_stats[~monthly_stats['is_post_halving']]
    post_halving = monthly_stats[monthly_stats['is_post_halving']]
    
    # PDF 1: Price per vB
    pdf_path1 = OUTPUT_DIR / 'monthly_price_per_vb.pdf'
    with PdfPages(pdf_path1) as pdf:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Draw entire data as one continuous line
        ax.plot(monthly_stats['date'], monthly_stats['avg_sat_per_vb_median'],
                marker='o', linewidth=2.5, markersize=8, color='#2E86AB', 
                label='Price per vB (Median)', zorder=3)
        
        # Mark pre/post halving with different colored markers
        if len(pre_halving) > 0:
            ax.scatter(pre_halving['date'], pre_halving['avg_sat_per_vb_median'],
                      s=100, color='#2E86AB', marker='o', 
                      label='Pre-Halving', zorder=4, edgecolors='darkblue', linewidths=1.5)
        
        if len(post_halving) > 0:
            ax.scatter(post_halving['date'], post_halving['avg_sat_per_vb_median'],
                      s=100, color='#A23B72', marker='s', 
                      label='Post-Halving', zorder=4, edgecolors='darkred', linewidths=1.5)
        
        ax.axvline(halving_date, color='red', linestyle='--', linewidth=2.5,
                   label=f'Halving ({HALVING_DATE})', alpha=0.8, zorder=2)
        
        ax.set_xlabel('Date', fontsize=18, fontweight='bold')
        ax.set_ylabel('Price per vB (sat/vB)', fontsize=18, fontweight='bold')
        ax.set_title('Satoshi per vB', fontsize=20, fontweight='bold', pad=15)
        ax.legend(fontsize=12, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--', zorder=1)
        ax.set_ylim(bottom=0)
        
        # Add statistics info
        if len(pre_halving) > 0 and len(post_halving) > 0:
            pre_mean = pre_halving['avg_sat_per_vb_median'].median()
            post_mean = post_halving['avg_sat_per_vb_median'].median()
            textstr = f'Pre-Halving Median: {pre_mean:.2f} sat/vB\nPost-Halving Median: {post_mean:.2f} sat/vB'
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=11,
                    verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    print(f"Price per vB PDF saved: {pdf_path1}")
    
    # PDF 2: Block Fill Ratio
    pdf_path2 = OUTPUT_DIR / 'monthly_block_fill_ratio.pdf'
    with PdfPages(pdf_path2) as pdf:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Draw entire data as one continuous line
        ax.plot(monthly_stats['date'], monthly_stats['block_fill_ratio_median'] * 100,
                marker='o', linewidth=2.5, markersize=8, color='#2E86AB', 
                label='Block Fill Ratio (Median)', zorder=3)
        
        # Mark pre/post halving with different colored markers
        if len(pre_halving) > 0:
            ax.scatter(pre_halving['date'], pre_halving['block_fill_ratio_median'] * 100,
                      s=100, color='#2E86AB', marker='o', 
                      label='Pre-Halving', zorder=4, edgecolors='darkblue', linewidths=1.5)
        
        if len(post_halving) > 0:
            ax.scatter(post_halving['date'], post_halving['block_fill_ratio_median'] * 100,
                      s=100, color='#A23B72', marker='s', 
                      label='Post-Halving', zorder=4, edgecolors='darkred', linewidths=1.5)
        
        ax.axvline(halving_date, color='red', linestyle='--', linewidth=2.5,
                   label=f'Halving ({HALVING_DATE})', alpha=0.8, zorder=2)
        
        # Set y-axis range narrower to clearly show differences
        fill_ratio_values = monthly_stats['block_fill_ratio_median'] * 100
        y_min = max(0, fill_ratio_values.min() - 2)
        y_max = min(100, fill_ratio_values.max() + 2)
        ax.set_ylim(y_min, y_max)
        
        ax.set_xlabel('Date', fontsize=18, fontweight='bold')
        ax.set_ylabel('Block Utilization (%)', fontsize=18, fontweight='bold')
        ax.set_title('Block Utilization Ratio: Weight/4MB', fontsize=20, fontweight='bold', pad=15)
        ax.legend(fontsize=12, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--', zorder=1)
        
        # Add statistics info
        if len(pre_halving) > 0 and len(post_halving) > 0:
            pre_mean = pre_halving['block_fill_ratio_median'].median() * 100
            post_mean = post_halving['block_fill_ratio_median'].median() * 100
            textstr = f'Pre-Halving Median: {pre_mean:.2f}%\nPost-Halving Median: {post_mean:.2f}%'
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=11,
                    verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    print(f"Block Fill Ratio PDF saved: {pdf_path2}")
    
    # PDF 3: X_t (F_t + M_t)
    pdf_path3 = OUTPUT_DIR / 'monthly_X_t.pdf'
    with PdfPages(pdf_path3) as pdf:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Draw entire data as one continuous line
        ax.plot(monthly_stats['date'], monthly_stats['X_t_median'] / 1e6,
                marker='o', linewidth=2.5, markersize=8, color='#2E86AB', 
                label='X_t (Median)', zorder=3)
        
        # Mark pre/post halving with different colored markers
        if len(pre_halving) > 0:
            ax.scatter(pre_halving['date'], pre_halving['X_t_median'] / 1e6,
                      s=100, color='#2E86AB', marker='o', 
                      label='Pre-Halving', zorder=4, edgecolors='darkblue', linewidths=1.5)
        
        if len(post_halving) > 0:
            ax.scatter(post_halving['date'], post_halving['X_t_median'] / 1e6,
                      s=100, color='#A23B72', marker='s', 
                      label='Post-Halving', zorder=4, edgecolors='darkred', linewidths=1.5)
        
        ax.axvline(halving_date, color='red', linestyle='--', linewidth=2.5,
                   label=f'Halving ({HALVING_DATE})', alpha=0.8, zorder=2)
        
        ax.set_xlabel('Date', fontsize=18, fontweight='bold')
        ax.set_ylabel('$X_t$ (Million sat)', fontsize=20, fontweight='bold')
        ax.set_title('Total Reward $X_t = R_t + F_t + M_t$', fontsize=20, fontweight='bold', pad=15)
        ax.legend(fontsize=12, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--', zorder=1)
        ax.set_ylim(bottom=0)
        
        # Add statistics info
        if len(pre_halving) > 0 and len(post_halving) > 0:
            pre_mean = pre_halving['X_t_median'].median() / 1e6
            post_mean = post_halving['X_t_median'].median() / 1e6
            textstr = f'Pre-Halving Median: {pre_mean:.2f} M sat\nPost-Halving Median: {post_mean:.2f} M sat'
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=11,
                    verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    print(f"X_t PDF saved: {pdf_path3}")

def create_fees_pdf(monthly_stats):
    """Generate monthly fees median graph as PDF"""
    sns.set_style("whitegrid")
    
    # Create date column if not present (already exists if create_graphs_pdf was called first)
    if 'date' not in monthly_stats.columns:
        monthly_stats['date'] = pd.to_datetime(monthly_stats['year_month'].astype(str) + '-01')
        
    halving_date = pd.to_datetime(HALVING_DATE)
    
    # Split pre/post halving
    pre_halving = monthly_stats[~monthly_stats['is_post_halving']]
    post_halving = monthly_stats[monthly_stats['is_post_halving']]
    
    pdf_path = OUTPUT_DIR / 'monthly_fees_median.pdf'
    with PdfPages(pdf_path) as pdf:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Draw entire data as one continuous line
        ax.plot(monthly_stats['date'], monthly_stats['total_fees_median'] / 1e6,
                marker='o', linewidth=2.5, markersize=8, color='#2E86AB', 
                label='Fees Median', zorder=3)
        
        # Mark pre/post halving with different colored markers
        if len(pre_halving) > 0:
            ax.scatter(pre_halving['date'], pre_halving['total_fees_median'] / 1e6,
                      s=100, color='#2E86AB', marker='o', 
                      label='Pre-Halving', zorder=4, edgecolors='darkblue', linewidths=1.5)
        
        if len(post_halving) > 0:
            ax.scatter(post_halving['date'], post_halving['total_fees_median'] / 1e6,
                      s=100, color='#A23B72', marker='s', 
                      label='Post-Halving', zorder=4, edgecolors='darkred', linewidths=1.5)
        
        ax.axvline(halving_date, color='red', linestyle='--', linewidth=2.5,
                   label=f'Halving ({HALVING_DATE})', alpha=0.8, zorder=2)
        
        ax.set_xlabel('Date', fontsize=18, fontweight='bold')
        ax.set_ylabel('Fees Median (Million sat)', fontsize=18, fontweight='bold')
        ax.set_title('Transaction Fees $F_t$', fontsize=20, fontweight='bold', pad=15)
        ax.legend(fontsize=12, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--', zorder=1)
        ax.set_ylim(bottom=0)
        
        # Add statistics info
        if len(pre_halving) > 0 and len(post_halving) > 0:
            pre_mean = pre_halving['total_fees_median'].median() / 1e6
            post_mean = post_halving['total_fees_median'].median() / 1e6
            textstr = f'Pre-Halving Median: {pre_mean:.2f} M sat\nPost-Halving Median: {post_mean:.2f} M sat'
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=11,
                    verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
    
    print(f"Fees Median PDF saved: {pdf_path}")

def main():
    print("=" * 120)
    print("Monthly Block Data Analysis")
    print("=" * 120)
    print(f"\nBlock Fill Ratio calculation basis:")
    print(f"  - Maximum block weight: {MAX_BLOCK_WEIGHT:,} (Bitcoin standard)")
    print(f"  - Formula: Block Fill Ratio = (vbytes × 4) / {MAX_BLOCK_WEIGHT:,} = weight / {MAX_BLOCK_WEIGHT:,}")
    print(f"  - vbytes × 4 = weight (Bitcoin formula)")
    print(f"  - Halving: {HALVING_DATE} (block height {HALVING_HEIGHT:,})")
    
    # Load block data
    print("\n1. Loading block data...")
    df = load_block_data()
    print(f"   Total blocks: {len(df):,}")
    print(f"   Period: {df['block_timestamp'].min()} ~ {df['block_timestamp'].max()}")
    
    # Calculate monthly metrics
    print("\n2. Calculating monthly metrics...")
    monthly_stats = calculate_monthly_metrics(df)
    print(f"   Months analyzed: {len(monthly_stats)}")
    
    # Print table
    print_analysis_table(monthly_stats)
    
    # Generate graph PDFs
    print("\n4. Generating graph PDFs...")
    create_graphs_pdf(monthly_stats)
    
    # Additional: Generate monthly fees median PDF
    print("\n5. Generating monthly fees median PDF...")
    create_fees_pdf(monthly_stats)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
