#!/usr/bin/env python3
"""
Deviation Threshold Analysis Plot (Pre vs Post Halving ratio)
- G_t threshold analysis in R_t = 0 scenario
- ratio_i computed separately for pre- and post-halving using period mean block size
"""

import os
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============================================================================
# Configuration (adjust here)
# ============================================================================
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data path
BLOCK_DATA_PATH = PROJECT_ROOT / 'data/processed/consolidated_block_data.csv'

# Output path
OUTPUT_DIR = PROJECT_ROOT / 'docs/diagrams/monthly_analysis/solution'
OUTPUT_NAME = 'threshold_analysis'

# Graph settings
FIGSIZE = (10, 7)
DPI = 300
X_MAX = 80   # X-axis max (M sat)
Y_MAX = 150  # Y-axis max (K sat)

# Colors
COLOR_THRESHOLD_LINE = '#2E86AB'
COLOR_PRE_HALVING = '#E94F37'
COLOR_POST_HALVING = '#4CAF50'

# Font sizes
FONT_TITLE = 18
FONT_LABEL = 16
FONT_TICK = 14
FONT_ANNOTATION = 13
FONT_ZONE_TEXT = 15

# BTC price (for USD conversion)
BTC_USD = 60000

# ============================================================================
# Calculations
# ============================================================================

# Load block data
block_data = pd.read_csv(BLOCK_DATA_PATH)

HALVING_HEIGHT = 840000
pre = block_data[block_data['height'] < HALVING_HEIGHT]
post = block_data[block_data['height'] >= HALVING_HEIGHT]

# Block size in MB: weight (WU) -> vB = weight/4 -> MB = vB/1e6
pre_mean_B_mb = (pre['weight'] / 4e6).mean()
post_mean_B_mb = (post['weight'] / 4e6).mean()

# Network delay parameters (from KIT invstat.gpd regression, full sample)
base_delay = 742  # ms
kappa = 26.40     # ms/MB
lambda_rate = 0.00167  # blocks/sec
w_sec = 1.0       # deviation additional delay

# ratio_i per period: use period-specific mean block size
def ratio_i_from_B_mb(B_mb):
    delta_sec = (base_delay + kappa * B_mb) / 1000.0
    rho_honest = 1 - np.exp(-lambda_rate * delta_sec)
    rho_dev = 1 - np.exp(-lambda_rate * (delta_sec + w_sec))
    return (rho_dev - rho_honest) / (1 - rho_dev)

ratio_i_pre = ratio_i_from_B_mb(pre_mean_B_mb)
ratio_i_post = ratio_i_from_B_mb(post_mean_B_mb)

print(f"Pre-halving  mean B_MB = {pre_mean_B_mb:.4f} -> ratio_i = {ratio_i_pre:.8f} = {ratio_i_pre*100:.6f}%")
print(f"Post-halving mean B_MB = {post_mean_B_mb:.4f} -> ratio_i = {ratio_i_post:.8f} = {ratio_i_post*100:.6f}%")

pre_X = (pre['total_fees_sat'] + pre['mev_sat']) / 1e6  # M sat
post_X = (post['total_fees_sat'] + post['mev_sat']) / 1e6

pre_mean = pre_X.mean()
post_mean = post_X.mean()
pre_thresh = ratio_i_pre * pre_mean * 1e6 / 1000   # K sat
post_thresh = ratio_i_post * post_mean * 1e6 / 1000  # K sat

# ============================================================================
# Generate graph
# ============================================================================

fig, ax = plt.subplots(figsize=FIGSIZE)

# X-axis range: two threshold lines (pre and post ratio)
x_range = np.linspace(0, X_MAX, 100)
threshold_pre = ratio_i_pre * x_range * 1e6 / 1000   # K sat
threshold_post = ratio_i_post * x_range * 1e6 / 1000  # K sat

# Threshold lines (pre vs post)
ax.plot(x_range, threshold_pre, '--', color=COLOR_PRE_HALVING, linewidth=2.5,
        label=f'Threshold (pre) = {ratio_i_pre*100:.4f}% × $X_t$')
ax.plot(x_range, threshold_post, '-', color=COLOR_POST_HALVING, linewidth=2.5,
        label=f'Threshold (post) = {ratio_i_post*100:.4f}% × $X_t$')

# Pre/post halving mean points
ax.scatter([pre_mean], [pre_thresh], color=COLOR_PRE_HALVING, s=200, zorder=5,
           edgecolor='black', linewidth=2, label=f'Pre-Halving ({pre_thresh:.0f}K sat)')
ax.scatter([post_mean], [post_thresh], color=COLOR_POST_HALVING, s=200, zorder=5,
           edgecolor='black', linewidth=2, label=f'Post-Halving ({post_thresh:.0f}K sat)')

# Region shading
ax.fill_between(x_range, np.maximum(threshold_pre, threshold_post), Y_MAX, alpha=0.35, color='#E74C3C')
ax.fill_between(x_range, 0, np.minimum(threshold_pre, threshold_post), alpha=0.35, color='#3498DB')

# Region text
ax.text(X_MAX * 0.7, Y_MAX * 0.8, 'Deviation', fontsize=FONT_ZONE_TEXT, 
        color='#C0392B', ha='center', fontweight='bold')
ax.text(X_MAX * 0.7, Y_MAX * 0.2, 'Honest', fontsize=FONT_ZONE_TEXT, 
        color='#2471A3', ha='center', fontweight='bold')

# Axis labels
ax.set_xlabel('$X_t$ (M satoshi)', fontsize=FONT_LABEL)
ax.set_ylabel('$G_t$ Threshold (K satoshi)', fontsize=FONT_LABEL)
ax.set_title('Deviation Threshold ($R_t = 0$)', fontsize=FONT_TITLE, fontweight='bold')

ax.set_xlim(0, X_MAX)
ax.set_ylim(0, Y_MAX)
ax.tick_params(axis='both', labelsize=FONT_TICK)
ax.legend(loc='upper left', fontsize=FONT_ANNOTATION)
ax.grid(True, alpha=0.3)

plt.tight_layout()

# Save
pdf_path = f'{OUTPUT_DIR}/{OUTPUT_NAME}.pdf'
png_path = f'{OUTPUT_DIR}/{OUTPUT_NAME}.png'
plt.savefig(pdf_path, dpi=DPI, bbox_inches='tight')
plt.savefig(png_path, dpi=DPI, bbox_inches='tight')
print(f'Saved: {pdf_path}')
print(f'Saved: {png_path}')

# ============================================================================
# Table output
# ============================================================================

sat_usd = BTC_USD / 1e8

print("\n" + "=" * 70)
print("Deviation Threshold Summary (Pre vs Post Halving)")
print("=" * 70)
print(f"Pre  deviation condition: G_t >= {ratio_i_pre*100:.4f}% × X_t")
print(f"Post deviation condition: G_t >= {ratio_i_post*100:.4f}% × X_t")
print()
print(f"{'Metric':<25} | {'Pre-Halving':>18} | {'Post-Halving':>18}")
print("-" * 68)
print(f"{'Blocks':<25} | {len(pre):>18,} | {len(post):>18,}")
print(f"{'Mean B_MB (MB)':<25} | {pre_mean_B_mb:>18.4f} | {post_mean_B_mb:>18.4f}")
print(f"{'ratio_i (%)':<25} | {ratio_i_pre*100:>18.6f} | {ratio_i_post*100:>18.6f}")
print(f"{'X_t Mean (sat)':<25} | {pre_X.mean()*1e6:>18,.0f} | {post_X.mean()*1e6:>18,.0f}")
print(f"{'Threshold Mean (sat)':<25} | {pre_thresh*1000:>18,.0f} | {post_thresh*1000:>18,.0f}")
print(f"{'Threshold Mean (USD)':<25} | ${pre_thresh*1000*sat_usd:>17,.2f} | ${post_thresh*1000*sat_usd:>17,.2f}")
print("-" * 68)
