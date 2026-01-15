#!/usr/bin/env python3
"""
Script for running simulation and organizing results into tables
"""
import subprocess
import pandas as pd
import pathlib
import time
from datetime import datetime

def run_simulation(config_path=None):
    """Run simulation"""
    print("=" * 80)
    print("Running simulation...")
    print("=" * 80)
    
    # Set path relative to project root (running from sim/ folder)
    project_root = pathlib.Path(__file__).resolve().parent.parent
    if config_path is None:
        config_path = project_root / "sim" / "config_default.yaml"
    simulate_script = project_root / "sim" / "simulate.py"
    
    result = subprocess.run(
        ["python3", str(simulate_script), "--config", str(config_path)],
        capture_output=True,
        text=True,
        cwd=str(project_root)  # Run from project root
    )
    
    if result.returncode != 0:
        print("❌ Simulation failed:")
        print(result.stderr)
        return None
    
    # Find result directory from output
    output_lines = result.stdout.split('\n')
    for line in output_lines:
        if 'wrote' in line and 'results.csv' in line:
            # Format: "wrote data/processed/sim_runs/run_id=20260108_174626/results.csv"
            result_path = line.split('wrote ')[-1].strip()
            return pathlib.Path(result_path)
    
    # If not found in output, use most recent result directory
    sim_runs_dir = project_root / "data/processed/sim_runs"
    if sim_runs_dir.exists():
        run_dirs = sorted(sim_runs_dir.glob("run_id=*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if run_dirs:
            return run_dirs[0] / "results.csv"
    
    return None

def create_summary_table(results_path):
    """Organize results into summary tables"""
    print("\n" + "=" * 80)
    print("Analyzing results and generating tables...")
    print("=" * 80)
    
    results = pd.read_csv(results_path)
    
    # 1. Overall summary table
    summary_data = {
        'Metric': [
            'beta_bar (mean)',
            'beta_bar (range)',
            'ROI_mean (mean)',
            'ROI_mean (range)',
            'stable_bft',
            'rho_honest (mean)',
            'rho_dev (mean)',
            'pr_D_ge_1',
            'Number of policy combinations'
        ],
        'Value': [
            f"{results['beta_bar'].mean():.4f}",
            f"{results['beta_bar'].min():.4f} ~ {results['beta_bar'].max():.4f}",
            f"{results['ROI_mean'].mean():.4f}",
            f"{results['ROI_mean'].min():.4f} ~ {results['ROI_mean'].max():.4f}",
            f"{results['stable_bft'].value_counts().to_dict()}",
            f"{results['rho_honest'].mean():.6f}",
            f"{results['rho_dev'].mean():.6f} ({results['rho_dev'].mean()*100:.4f}%)",
            f"{results['pr_D_ge_1'].unique()[0] if len(results['pr_D_ge_1'].unique()) > 0 else 'N/A'}",
            f"{len(results)}"
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # 2. Policy comparison table
    policy_comparison = []
    for policy in ['A_ON', 'B_OFF']:
        policy_data = results[results['policy_group'] == policy]
        if len(policy_data) > 0:
            policy_comparison.append({
                'Policy Group': policy,
                'Policy Description': 'Base Fee + Fee Floor + Adaptive' if policy == 'A_ON' else 'Adaptive only',
                'beta_bar (mean)': f"{policy_data['beta_bar'].mean():.4f}",
                'ROI (mean)': f"{policy_data['ROI_mean'].mean():.4f}",
                'ROI (std)': f"{policy_data['ROI_std'].mean():.4f}",
                'stable_bft': f"{policy_data['stable_bft'].sum()} / {len(policy_data)}",
                'rho_honest (mean)': f"{policy_data['rho_honest'].mean():.6f}",
                'rho_dev (mean)': f"{policy_data['rho_dev'].mean():.6f}",
            })
    policy_df = pd.DataFrame(policy_comparison)
    
    # 3. Detailed parameter table
    detail_cols = [
        'policy_group', 'G_ratio', 'fee_floor_sat',
        'beta_bar', 'ROI_mean', 'ROI_std',
        'stable_bft', 'rho_honest', 'rho_dev', 'pr_D_ge_1'
    ]
    # Remove missing columns
    detail_cols = [col for col in detail_cols if col in results.columns]
    detail_df = results[detail_cols].copy()
    detail_df = detail_df.sort_values(['policy_group', 'G_ratio', 'fee_floor_sat'])
    
    # Number formatting
    for col in ['beta_bar', 'ROI_mean', 'ROI_std', 'rho_honest', 'rho_dev', 'pr_D_ge_1']:
        if col not in detail_df.columns:
            continue
        if col == 'beta_bar':
            detail_df[col] = detail_df[col].apply(lambda x: f"{x:.4f}")
        elif col in ['ROI_mean', 'ROI_std']:
            detail_df[col] = detail_df[col].apply(lambda x: f"{x:.4f}")
        elif col in ['rho_honest', 'rho_dev']:
            detail_df[col] = detail_df[col].apply(lambda x: f"{x:.6f}")
        elif col == 'pr_D_ge_1':
            detail_df[col] = detail_df[col].apply(lambda x: f"{x:.1f}")
    
    # Save to results directory
    results_dir = results_path.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1) Summary table
    summary_path = results_dir / f"summary_table_{timestamp}.csv"
    summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ Summary table saved: {summary_path}")
    
    # 2) Policy comparison table
    policy_path = results_dir / f"policy_comparison_{timestamp}.csv"
    policy_df.to_csv(policy_path, index=False, encoding='utf-8-sig')
    print(f"✓ Policy comparison table saved: {policy_path}")
    
    # 3) Detailed table
    detail_path = results_dir / f"detailed_results_{timestamp}.csv"
    detail_df.to_csv(detail_path, index=False, encoding='utf-8-sig')
    print(f"✓ Detailed results table saved: {detail_path}")
    
    # 4) Also save in Markdown format (improved readability)
    md_path = results_dir / f"results_summary_{timestamp}.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Simulation Results Summary\n\n")
        f.write(f"**Execution time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 1. Overall Summary\n\n")
        f.write(summary_df.to_markdown(index=False) + "\n\n")
        
        f.write("## 2. Policy Comparison\n\n")
        f.write(policy_df.to_markdown(index=False) + "\n\n")
        
        f.write("## 3. Key Findings\n\n")
        f.write("### ⚠️ Warnings:\n")
        if results['beta_bar'].mean() > 0.33:
            f.write(f"- **beta_bar = {results['beta_bar'].mean():.4f}**: Does not satisfy BFT stability condition (beta_bar > 1/3)\n")
        if results['ROI_mean'].mean() < 0:
            f.write(f"- **ROI = {results['ROI_mean'].mean():.4f}**: Costs exceed revenue (negative ROI)\n")
        
        f.write("\n## 4. Detailed Results\n\n")
        f.write(detail_df.to_markdown(index=False) + "\n")
    
    print(f"✓ Markdown summary saved: {md_path}")
    
    # Print summary to console
    print("\n" + "=" * 80)
    print("Results Summary")
    print("=" * 80)
    print("\n[Overall Summary]")
    print(summary_df.to_string(index=False))
    print("\n[Policy Comparison]")
    print(policy_df.to_string(index=False))
    
    return {
        'summary': summary_df,
        'policy_comparison': policy_df,
        'detailed': detail_df,
        'paths': {
            'summary': summary_path,
            'policy': policy_path,
            'detailed': detail_path,
            'markdown': md_path
        }
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run simulation and generate result tables")
    parser.add_argument("--config", default="sim/config_default.yaml", help="Config file path")
    parser.add_argument("--results", help="Path to existing results file (skip simulation)")
    args = parser.parse_args()
    
    if args.results:
        results_path = pathlib.Path(args.results)
    else:
        results_path = run_simulation(args.config)
    
    if results_path is None or not results_path.exists():
        print("❌ Results file not found.")
        return 1
    
    print(f"\n✓ Results file loaded: {results_path}")
    create_summary_table(results_path)
    
    return 0

if __name__ == "__main__":
    exit(main())
