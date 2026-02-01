#!/usr/bin/env python3
"""
Policy Effect Analysis and Visualization - V4 Cost Version
- Uses V4 simulation results (GUESS-based electricity cost)
- Policy configuration table + G_ratio effect graphs
"""

import os
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Results file path (V4 simulation results)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIM_RUNS_DIR = PROJECT_ROOT / "data/processed/sim_runs_v4"  # V4 results

# Find the most recent results.csv (auto-detect latest run_id)
def get_latest_results():
    """Find the most recent results.csv file"""
    run_dirs = sorted(SIM_RUNS_DIR.glob("run_id=*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for run_dir in run_dirs:
        results_file = run_dir / "results.csv"
        if results_file.exists():
            return results_file
    raise FileNotFoundError(f"No results.csv found in {SIM_RUNS_DIR}")

RESULTS_PATH = get_latest_results()
OUTPUT_DIR = PROJECT_ROOT / "docs/diagrams/monthly_analysis/v4_diagram"  # V4 output
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Style settings - increased font sizes
plt.rcParams.update({
    'font.size': 18,
    'axes.titlesize': 22,
    'axes.labelsize': 18,
    'xtick.labelsize': 16,
    'ytick.labelsize': 16,
    'legend.fontsize': 14,
    'figure.figsize': (10, 7),
    'axes.grid': True,
    'grid.alpha': 0.3,
})

def load_data():
    """Load data"""
    df = pd.read_csv(RESULTS_PATH)
    return df

def plot_policy_config_and_effect(df):
    """Policy configuration table + bar chart comparing policy effects"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), gridspec_kw={'width_ratios': [1.2, 2]})
    fig.suptitle('Analysis by Policies - V4 Cost', fontsize=22, fontweight='bold', y=1.02)
    
    # ===== Left: 6 policy table =====
    ax_table = axes[0]
    ax_table.axis('off')
    ax_table.set_title('Policy Configuration', fontsize=18, fontweight='bold', pad=10)
    
    policies_info = [
        ('A', True, True, True),
        ('B', True, False, True),
        ('C', True, True, False),
        ('D', True, False, False),
        ('E', False, True, True),
        ('F', False, False, False),
    ]
    
    cell_text = []
    cell_colors = []
    for policy, bf, ff, ad in policies_info:
        row = [policy, '✓' if bf else '✗', '✓' if ff else '✗', '✓' if ad else '✗']
        colors = [
            '#f0f0f0',
            '#90EE90' if bf else '#FFB6C1',
            '#90EE90' if ff else '#FFB6C1',
            '#90EE90' if ad else '#FFB6C1',
        ]
        cell_text.append(row)
        cell_colors.append(colors)
    
    table = ax_table.table(
        cellText=cell_text,
        colLabels=['Policy', 'Base Fee', 'Fee Floor', 'Adaptive'],
        cellColours=cell_colors,
        colColours=['#4472C4', '#4472C4', '#4472C4', '#4472C4'],
        cellLoc='center', loc='center',
        bbox=[0.0, 0.15, 1.0, 0.7]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.0, 2.0)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(fontweight='bold', color='white')
        cell.set_edgecolor('white')
        cell.set_linewidth(2)
    
    # ===== Right: Bar chart (policy comparison at G_ratio = 0.17%) =====
    ax = axes[1]
    ax.set_title('Deviation Rate β (%)', fontsize=18, fontweight='bold', pad=10)
    
    # Fixed parameters
    G_RATIO = 0.0017  # 0.17%
    FF_VALUE = 20000000  # 20M sat (applied to Fee Floor ON policies)
    
    # Policy settings: (policy_group, label, has_fee_floor)
    policies = [
        ('A_BF_FF_AD', 'A', True),   # FF ON → use FF=20M
        ('B_BF_AD', 'B', False),      # FF OFF → use FF=0
        ('C_BF_FF', 'C', True),       # FF ON → use FF=20M
        ('D_BF', 'D', False),         # FF OFF → use FF=0
        ('E_FF_AD', 'E', True),       # FF ON → use FF=20M
        ('F_NONE', 'F', False),       # FF OFF → use FF=0
    ]
    
    # BF ON: blue shades, BF OFF: red shades
    colors = ['#1f77b4', '#4a9fd4', '#1f77b4', '#4a9fd4', '#d62728', '#ff6b6b']
    
    values = []
    labels = []
    for policy, label, has_ff in policies:
        ff_sat = FF_VALUE if has_ff else 0
        p_data = df[(df['policy_group'] == policy) & (df['G_ratio'] == G_RATIO) & (df['fee_floor_sat'] == ff_sat)]
        val = p_data['beta_bar'].values[0] * 100 if len(p_data) > 0 else 0
        values.append(val)
        labels.append(label)
    
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=1.5)
    
    # Display values above bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, 
                f'{val:.1f}%', ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    # BFT threshold line
    ax.axhline(y=33.3, color='red', linestyle='--', linewidth=2.5)
    ax.fill_between([-0.5, 5.5], 33.3, 105, alpha=0.15, color='red')
    ax.text(-0.3, 35, 'BFT Threshold (33.3%)', fontsize=18, color='red', ha='left', fontweight='bold')
    
    ax.set_xlabel('Policy', fontweight='bold', fontsize=16)
    ax.set_ylabel('Deviation Rate β (%)', fontweight='bold', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=16, fontweight='bold')
    ax.set_ylim(0, 85)
    ax.set_xlim(-0.5, 5.5)
    ax.grid(True, alpha=0.3, axis='y')
    ax.tick_params(labelsize=14)
    
    # Legend: BF ON/OFF distinction (moved to lower right)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#1f77b4', edgecolor='black', label='Base Fee ON'),
        Patch(facecolor='#d62728', edgecolor='black', label='Base Fee OFF'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=13)
    
    # Fixed parameter annotation (bottom of graph)
    fig.text(0.5, -0.02, f'Fixed: G_ratio = {G_RATIO*100:.2f}%, Fee Floor = {FF_VALUE/1e6:.0f}M sat (when FF ON)', 
             ha='center', fontsize=12, style='italic', color='gray')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "policy_config_and_effect_v4.pdf", dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / "policy_config_and_effect_v4.png", dpi=150, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'policy_config_and_effect_v4.pdf'}")
    print(f"✓ Saved: {OUTPUT_DIR / 'policy_config_and_effect_v4.png'}")
    plt.close()

def plot_fee_floor_effect(df):
    """Fee Floor effect visualization (FF value comparison at G_ratio = 0.17%)"""
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.suptitle('Fee Floor Effect on Deviation Rate - V4 Cost (G_ratio = 0.17%)', fontsize=20, fontweight='bold', y=1.02)
    
    g_target = 0.0017
    ff_values = [0, 20000000, 40000000, 60000000]
    ff_labels = ['0', '20M', '40M', '60M']
    
    # Only policies with Fee Floor (A, C, E)
    policies = [
        ('A_BF_FF_AD', 'A (BF+FF+AD)', '#1f77b4', 'o'),
        ('C_BF_FF', 'C (BF+FF)', '#2ca02c', 's'),
        ('E_FF_AD', 'E (FF+AD)', '#d62728', '^'),
    ]
    
    x = np.arange(len(ff_labels))
    width = 0.25
    
    for i, (policy, label, color, marker) in enumerate(policies):
        values = []
        for ff in ff_values:
            p_data = df[(df['policy_group'] == policy) & (df['G_ratio'] == g_target) & (df['fee_floor_sat'] == ff)]
            val = p_data['beta_bar'].values[0] * 100 if len(p_data) > 0 else 0
            values.append(val)
        
        bars = ax.bar(x + (i - 1) * width, values, width, label=label, color=color, edgecolor='black', linewidth=1)
        
        # Display values above bars
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                        f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # BFT threshold line
    ax.axhline(y=33.3, color='red', linestyle='--', linewidth=2.5)
    ax.fill_between([-0.5, 3.5], 33.3, 75, alpha=0.15, color='red')
    ax.text(3.3, 35, 'BFT Threshold', fontsize=14, color='red', ha='right', fontweight='bold')
    
    ax.set_xlabel('Fee Floor (sat)', fontweight='bold', fontsize=16)
    ax.set_ylabel('Deviation Rate β (%)', fontweight='bold', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(ff_labels, fontsize=14)
    ax.set_ylim(0, 75)
    ax.set_xlim(-0.5, 3.5)
    ax.legend(loc='upper right', fontsize=12)
    ax.grid(True, alpha=0.3, axis='y')
    ax.tick_params(labelsize=12)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fee_floor_effect_v4.pdf", dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / "fee_floor_effect_v4.png", dpi=150, bbox_inches='tight')
    print(f"✓ Saved: {OUTPUT_DIR / 'fee_floor_effect_v4.pdf'}")
    print(f"✓ Saved: {OUTPUT_DIR / 'fee_floor_effect_v4.png'}")
    plt.close()

def generate_latex_table(df):
    """Generate LaTeX table"""
    
    print("\n" + "=" * 80)
    print("LaTeX Table: Policy Configuration and Effect (V4 Cost)")
    print("=" * 80)
    
    print(r"""
\begin{table}[htbp]
\centering
\caption{Policy Configuration and Deviation Rate at G\_ratio = 0.17\% (V4 Cost)}
\label{tab:policy_config_v4}
\begin{tabular}{c|ccc|c}
\hline
\textbf{Policy} & \textbf{Base Fee} & \textbf{Fee Floor} & \textbf{Adaptive} & \textbf{$\beta$ (\%)} \\
\hline""")
    
    g017 = df[df['G_ratio'] == 0.0017]
    
    policies_info = [
        ('A_BF_FF_AD', 'A', True, True, True),
        ('B_BF_AD', 'B', True, False, True),
        ('C_BF_FF', 'C', True, True, False),
        ('D_BF', 'D', True, False, False),
        ('E_FF_AD', 'E', False, True, True),
        ('F_NONE', 'F', False, False, False),
    ]
    
    for policy, label, bf, ff_on, ad in policies_info:
        p_data = g017[(g017['policy_group'] == policy) & (g017['fee_floor_sat'] == 0)]
        
        bf_str = r"\checkmark" if bf else "-"
        ff_str = r"\checkmark" if ff_on else "-"
        ad_str = r"\checkmark" if ad else "-"
        
        if len(p_data) > 0:
            beta = p_data['beta_bar'].values[0] * 100
            beta_str = f"{beta:.1f}" if beta >= 1 else r"\textbf{0.0}"
        else:
            beta_str = "-"
        
        row = f"{label} & {bf_str} & {ff_str} & {ad_str} & {beta_str} \\\\"
        print(row)
    
    print(r"""\hline
\end{tabular}
\end{table}
""")

def main():
    print("=" * 80)
    print("Policy Effect Analysis and Visualization - V4 Cost Version")
    print("=" * 80)
    
    # Load data
    df = load_data()
    print(f"✓ Data loaded: {len(df)} experiment results")
    print(f"  Source: {RESULTS_PATH}")
    
    # Generate graphs
    print("\nGenerating graphs...")
    plot_policy_config_and_effect(df)
    plot_fee_floor_effect(df)
    
    # LaTeX table
    generate_latex_table(df)
    
    print("\n" + "=" * 80)
    print("Complete!")
    print("=" * 80)
    print(f"\nGenerated files:")
    print(f"  - {OUTPUT_DIR / 'policy_config_and_effect_v4.pdf'}")
    print(f"  - {OUTPUT_DIR / 'fee_floor_effect_v4.pdf'}")

if __name__ == "__main__":
    main()
