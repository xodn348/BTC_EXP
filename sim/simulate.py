import argparse, yaml, pathlib, time
import numpy as np
import pandas as pd


class Miner:
    """Miner object: manages profit and deviation decision per block for each miner
    
    Paper approach (Algorithm 1):
    - Decision made by comparing Π_dev(t) ≥ Π_hon(t) at each round t
    - Vi = Σ γ^t Π_i(t) is computed post-simulation as a result metric
    """
    
    def __init__(self, miner_id, share, cost):
        self.miner_id = miner_id
        self.share = share  # h_i: hash rate share
        self.cost = cost    # C_i: cost per block
        
        # Per-block history
        self.history = []  # Each block: {'block_idx': t, 'profit_honest': val, 'profit_dev': val, 'dev_flag': flag}
        
        # For Vi calculation (computed post-simulation)
        self.Vi_honest = 0.0  # Σ γ^t Π_hon(t)
        self.Vi_dev = 0.0     # Σ γ^t Π_dev(t)
    
    def decide_and_record(self, block_idx, profit_honest, profit_dev):
        """
        Paper Algorithm 1: Decision by per-round profit comparison
        
        if Π_dev(t) ≥ Π_hon(t) then
            deviation
        else
            honest
        """
        # Per-round profit comparison (Paper Eq. 3.6)
        # If profit_dev == profit_honest, no reason to deviate (strictly better)
        dev_flag = 1.0 if profit_dev > profit_honest else 0.0
        
        self.history.append({
            'block_idx': block_idx,
            'profit_honest': float(profit_honest),
            'profit_dev': float(profit_dev),
            'dev_flag': dev_flag
        })
        
        return dev_flag
    
    def compute_vi_post(self, gamma):
        """
        Post-simulation Vi calculation (result metric)
        Vi = Σ_{t=0}^{T} γ^t Π_i(t)
        """
        self.Vi_honest = 0.0
        self.Vi_dev = 0.0
        
        for t, record in enumerate(self.history):
            discount = gamma ** t
            self.Vi_honest += discount * record['profit_honest']
            self.Vi_dev += discount * record['profit_dev']
        
        return self.Vi_honest, self.Vi_dev
    
    def get_history_dataframe(self):
        """Return per-block data as DataFrame"""
        if not self.history:
            return pd.DataFrame()
        df = pd.DataFrame(self.history)
        df['miner_id'] = self.miner_id
        return df


def run_once(
    shares, costs, miner_ids, T,
    base_delay, kappa, gamma, lambda_rate, w_sec,
    basefee0,
    enable_basefee=True, enable_feefloor=False, fee_floor_sat=0.0,
    enable_adaptive=False, B_min_vB=1_000_000, B_max_vB=2_000_000, U_star=0.75, delta_step=0.05,
    G_norm=1.0, alpha=0.125,
    block_data=None,  # Actual block data (DataFrame): includes total_vbytes, avg_sat_per_vb, mev_sat, date
    daily_costs=None,  # Daily miner costs (DataFrame): date, miner_id, cost_usd_per_day
    include_block_reward=True,  # True: use actual block reward, False: R_t = 0 (future scenario)
):
    """
    Paper approach (Algorithm 1):
    - Decision made by comparing Π_dev(t) ≥ Π_hon(t) at each round t
    - Vi = Σ γ^t Π_i(t) is computed post-simulation as a result metric
    """
    # Create miner objects
    miners = [Miner(miner_id, share, cost) for miner_id, share, cost in zip(miner_ids, shares, costs)]
    num_miners = len(miners)

    # Validate block data
    if block_data is None or len(block_data) == 0:
        raise ValueError("Block data is required. Please provide block_data.")
    required_cols = ['total_vbytes', 'avg_sat_per_vb', 'mev_sat', 'date', 'block_subsidy_sat']
    missing_cols = [col for col in required_cols if col not in block_data.columns]
    if missing_cols:
        raise ValueError(f"Block data missing required columns: {missing_cols}")
    
    # Validate daily cost data and create mapping
    if daily_costs is None or len(daily_costs) == 0:
        raise ValueError("Daily cost data is required. Please provide daily_costs.")
    
    # Create date-to-BTC price mapping from block data (use each date's BTC price)
    if 'btc_usd' not in block_data.columns:
        raise ValueError("Block data requires btc_usd column.")
    block_btc_prices = block_data.groupby('date')['btc_usd'].first().to_dict()  # BTC price per date
    
    # Convert daily cost to per-block cost
    # pool_daily_cost.csv's cost_usd_per_day is "total cost for 144 blocks per day"
    # Therefore, per-block cost = cost / 144
    BLOCKS_PER_DAY = 144
    daily_costs = daily_costs.copy()
    daily_costs['cost_usd_per_block'] = daily_costs['cost_usd_per_day'] / BLOCKS_PER_DAY
    
    # Create (date, miner_id) to cost mapping (using each date's BTC price)
    cost_map = {}  # {(date, miner_id): cost_sat_per_block}
    fallback_btc_price = block_data['btc_usd'].mean() if len(block_data) > 0 else 57774.09  # Fallback: average price
    for _, row in daily_costs.iterrows():
        date_str = str(row['date'])
        # Use BTC price for that date (fallback if not available)
        btc_price = block_btc_prices.get(date_str, fallback_btc_price)
        cost_sat_per_block = (row['cost_usd_per_block'] / btc_price) * 100_000_000
        key = (date_str, row['miner_id'])
        cost_map[key] = cost_sat_per_block

    def basefee_update(basefee, U_t):
        if not enable_basefee:
            return basefee
        delta = alpha * (U_t - U_star) / U_star  # Paper Eq. 5.5: α · (U_t - U*) / U*
        new_basefee = max(0.0, basefee * (1 + delta))
        # Overflow prevention: set basefee upper limit (1e15 sat ≈ 10M BTC, realistic cap)
        return min(new_basefee, 1e15)

    def adaptive_B(Bt_vB, U_t):
        if not enable_adaptive:
            return Bt_vB
        # Paper 5.3.1: B_min = 1 MB, B_max = 2 MB
        # B_max_vB is set in config (default 2,000,000 vB = 2 MB)
        if U_t > U_star:
            return min(B_max_vB, (1 + delta_step) * Bt_vB)
        if U_t < U_star:
            return max(B_min_vB, (1 - delta_step) * Bt_vB)
        return Bt_vB

    # ========== Main simulation loop (Paper Algorithm 1) ==========
    print("  Running simulation...")
    
    deviates = 0
    actual_blocks_count = 0
    roi_numer = np.zeros(num_miners)
    total_costs_accum = np.zeros(num_miners)
    
    total_honest_blocks = orphan_honest_blocks = 0
    total_dev_blocks = orphan_dev_blocks = 0
    dt_list = []
    
    basefee = basefee0
    Bt_vB = B_min_vB
    Bt_MB = B_min_vB / 1_000_000
    
    for t in range(T):
        # 1) Load block data
        idx = t % len(block_data)
        block_row = block_data.iloc[idx]
        
        F_rate = float(block_row['avg_sat_per_vb'])
        M = float(block_row['mev_sat'])
        R_t_original = float(block_row['block_subsidy_sat'])  # Original block reward
        R_t = R_t_original if include_block_reward else 0.0
        vB_t = float(block_row['total_vbytes'])
        block_date = str(block_row['date'])
        actual_miner_id = int(block_row['miner_id']) if pd.notna(block_row['miner_id']) else -1
        
        # 2) Calculate U_t, Fee, Block size
        # U_t = actual usage / max capacity (adjusted by Adaptive)
        # Adaptive adjusts Bt_vB → U_t changes → Base Fee stabilizes
        U_t = min(1.0, vB_t / Bt_vB)
        
        # Apply Adaptive Block Size (Paper Eq. 5.12)
        # U_t > U* → increase block size → U_t decreases
        # U_t < U* → decrease block size → U_t increases
        Bt_vB = adaptive_B(Bt_vB, U_t)
        Bt_MB = Bt_vB / 1_000_000
        
        # Update base fee (Paper Eq. 5.5)
        # basefee is absolute amount (sat), changes are proportional
        basefee = basefee_update(basefee, U_t)
        
        # Fee calculation (Paper 5.3.1 - EIP-1559 style)
        # - basefee: minimum unit price varying with congestion (sat/vB)
        # - F_raw: actual fee read from data (sat)
        # 
        # Paper Eq. (5.5): b_{t+1} = b_t * (1 + α * (U_t - U*) / U*)
        # Base Fee is "unit price", so total Base Fee = basefee * vB_t
        # Total fee = max(F_raw, F_base) where F_base = basefee * vB_t
        F_raw = F_rate * vB_t  # Original fee (from data, sat)
        if enable_basefee:
            # basefee = sat/vB (unit price), F_base = unit price × block size
            F_base = basefee * vB_t
            F = max(F_raw, F_base)
        else:
            F = F_raw
        
        # Apply Fee Floor (Paper Eq. 5.6)
        F_eff = max(F, fee_floor_sat) if enable_feefloor else F
        
        # 3) Calculate network delay and orphan rate
        delta_ms = base_delay + kappa * Bt_MB
        delta_sec = delta_ms / 1000.0
        rho_honest = 1 - np.exp(-lambda_rate * delta_sec)
        delta_dev_sec = delta_sec + w_sec
        rho_dev = 1 - np.exp(-lambda_rate * delta_dev_sec)
        
        # 4) Calculate X_t, G_t (Paper Eq. 3.3, 5.3)
        # X_t = R_t + F_t + M_t
        X_t = R_t + F_eff + M
        
        # G_t: proportional to congestion (U_t) (Paper Eq. 5.9)
        # "U_t ↑ → congestion ↑ → δ_t ↑ → G_t ↑ → deviation incentive ↑"
        # G_t = G_norm × (U_t / U_star): higher congestion → higher G_t
        # Adaptive adjusts U_t → adjusts G_t → suppresses deviation
        congestion_ratio = U_t / U_star  # Congestion ratio (1.0 = target)
        G_t = G_norm * congestion_ratio
        
        # 5) Per-miner costs
        block_costs = np.array([cost_map.get((block_date, mid), costs[i]) for i, mid in enumerate(miner_ids)])
        
        # Find actual miner who mined this block
        actual_miner_idx = None
        if actual_miner_id in miner_ids:
            actual_miner_idx = np.where(miner_ids == actual_miner_id)[0][0]
        
        # 6) Calculate per-miner profit (Paper Eq. 3.4, 3.5)
        # Π_hon(t) = p_i^hon · X_t - C_i
        # Π_dev(t) = p_i^dev · (X_t + G_t) - C_i
        # 
        # Paper Eq. 3.10: deviation condition
        # G_t ≥ ratio_i · X_t → deviation
        # ratio_i = (p_hon - p_dev) / p_dev
        #
        # p_hon = share * (1 - rho_honest)  # Success probability for honest strategy
        # p_dev = share * (1 - rho_dev)     # Success probability for deviation strategy (lower)
        
        for i, miner in enumerate(miners):
            p_hon = shares[i] * (1 - rho_honest)  # Success probability for honest strategy
            p_dev = shares[i] * (1 - rho_dev)     # Success probability for deviation strategy
            
            # Paper Eq. 3.4, 3.5: expected profit
            profit_honest = p_hon * X_t - block_costs[i]
            profit_dev = p_dev * (X_t + G_t) - block_costs[i]
            
            # 7) Paper Algorithm 1: per-round profit comparison decision
            # if Π_dev(t) ≥ Π_hon(t) then deviation else honest
            dev_flag = miner.decide_and_record(t, profit_honest, profit_dev)
        
        # 8) Calculate beta_bar: deviation status of actual miner
        if actual_miner_idx is not None:
            actual_blocks_count += 1
            # Get dev_flag from actual miner's last record
            deviates += miners[actual_miner_idx].history[-1]['dev_flag']
            
            # Track orphan rate (count only honest/dev blocks)
            is_honest = miners[actual_miner_idx].history[-1]['dev_flag'] == 0
            if is_honest:
                total_honest_blocks += 1
            else:
                total_dev_blocks += 1
        
        # Store last rho values (theoretical values)
        last_rho_honest = rho_honest
        last_rho_dev = rho_dev
        
        # 9) Accumulate for ROI calculation
        for i, miner in enumerate(miners):
            roi_numer[i] += miner.history[-1]['profit_honest']
            total_costs_accum[i] += block_costs[i]
        
        # 10) Deviation margin D_t (Paper Eq. 3.12)
        # G_t ≥ ratio_i · X_t → deviation
        # ratio_i = (p_hon - p_dev) / p_dev (Paper Eq. 3.11)
        # p_hon = share * (1 - rho_honest), p_dev = share * (1 - rho_dev)
        # share cancels out: ratio_i = ((1-rho_honest) - (1-rho_dev)) / (1-rho_dev)
        #                            = (rho_dev - rho_honest) / (1 - rho_dev)
        ratio_i = (rho_dev - rho_honest) / max(1 - rho_dev, 1e-12)
        D_t = G_t / max(ratio_i * X_t, 1e-12)  # Use G_t (dynamic value)
        dt_list.append(D_t)

    # ========== Post-simulation Vi calculation ==========
    print("  Computing Vi post-simulation...")
    for miner in miners:
        miner.compute_vi_post(gamma)

    # ========== Aggregate results ==========
    beta_bar = deviates / actual_blocks_count if actual_blocks_count > 0 else 0.0
    # Use theoretical rho values (based on last block)
    rho_honest_final = last_rho_honest if 'last_rho_honest' in dir() else 0.0
    rho_dev_final = last_rho_dev if 'last_rho_dev' in dir() else 0.0
    
    ROI_per_miner = np.zeros(num_miners)
    for i in range(num_miners):
        if total_costs_accum[i] > 0:
            ROI_per_miner[i] = roi_numer[i] / total_costs_accum[i]
    ROI_mean = float(ROI_per_miner.mean())
    ROI_std = float(ROI_per_miner.std())
    
    stable_bft = beta_bar < (1/3)

    dt_arr = np.array(dt_list)
    pr_D_ge_1 = float((dt_arr >= 1.0).mean())

    # Combine per-miner history into DataFrame
    history_dfs = [miner.get_history_dataframe() for miner in miners]
    history_df = pd.concat(history_dfs, ignore_index=True) if history_dfs else pd.DataFrame()
    history_records = history_df.to_dict('records') if not history_df.empty else []

    return dict(
        beta_bar=beta_bar,
        ROI_mean=ROI_mean, ROI_std=ROI_std,
        stable_bft=stable_bft,
        rho_honest=rho_honest_final, rho_dev=rho_dev_final,
        pr_D_ge_1=pr_D_ge_1,
        U_star=U_star, delta_step=delta_step,
        enable_basefee=enable_basefee, enable_feefloor=enable_feefloor, enable_adaptive=enable_adaptive,
        fee_floor_sat=fee_floor_sat, B_min_vB=B_min_vB, B_max_vB=B_max_vB,
        w_sec=w_sec, alpha=alpha,
        history_records=history_records,
        miners=miners,
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="sim/config_default.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    # random_seed no longer used (random sampling removed)

    # Load top 13 miners from pool_daily_cost.csv
    print("=== Loading Miner Information ===\n")
    pool_cost = pd.read_csv("data/processed/pool_daily_cost.csv")
    
    # 1. Calculate average share per miner
    avg_shares = pool_cost.groupby(['miner_id', 'pool_name'])['daily_share'].mean().reset_index()
    avg_shares = avg_shares.sort_values('daily_share', ascending=False)
    
    # 2. Select top 13 miners
    top13 = avg_shares.head(13).copy()
    print(f"Selected top 13 miners:")
    print(top13[['miner_id', 'pool_name', 'daily_share']])
    print()
    
    # 3. Normalize shares (so sum of 13 miners' shares = 1)
    top13['normalized_share'] = top13['daily_share'] / top13['daily_share'].sum()
    print(f"Total share before normalization: {top13['daily_share'].sum():.4f}")
    print(f"Total share after normalization: {top13['normalized_share'].sum():.4f}")
    print()

    shares = top13['normalized_share'].values
    miner_ids = top13['miner_id'].values  # miner_id array for simulation

    # Initial costs use average values (fallback, actual costs vary per block)
    avg_costs = pool_cost[pool_cost['miner_id'].isin(miner_ids)].groupby('miner_id')['cost_usd_per_day'].mean()
    block_data_temp = pd.read_csv("data/processed/consolidated_block_data.csv")
    avg_btc_price = block_data_temp['btc_usd'].mean()
    BLOCKS_PER_DAY = 144
    costs = np.array([(avg_costs.get(mid, 0) / BLOCKS_PER_DAY / avg_btc_price * 100_000_000) for mid in miner_ids])
    
    print(f"Total {len(miner_ids)} miners: miner_ids={miner_ids.tolist()}")
    print(f"Share sum: {shares.sum():.4f}")
    print()
    
    # Prepare daily cost data (filter for top 13 miners only)
    daily_costs = pool_cost[pool_cost['miner_id'].isin(miner_ids)].copy()
    print(f"Daily cost data: {len(daily_costs):,} rows (top 13 miners)")
    print()

    out_dir = pathlib.Path("data/processed/sim_runs") / f"run_id={time.strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    open(out_dir/"config.yaml","w").write(open(args.config).read())

    # Load block data (consolidated data: includes total_vbytes, avg_sat_per_vb, mev_sat, date, block_subsidy_sat)
    try:
        block_data = pd.read_csv("data/processed/consolidated_block_data.csv")
        required_cols = ['total_vbytes', 'avg_sat_per_vb', 'mev_sat', 'date', 'block_subsidy_sat']
        missing_cols = [col for col in required_cols if col not in block_data.columns]
        if missing_cols:
            raise ValueError(f"Block data missing required columns: {missing_cols}")
        
        # Additional columns needed (height, btc_usd, miner_id)
        additional_cols = []
        if 'height' in block_data.columns:
            additional_cols.append('height')
        if 'btc_usd' in block_data.columns:
            additional_cols.append('btc_usd')
        if 'miner_id' in block_data.columns:
            additional_cols.append('miner_id')
        
        # Handle missing values
        all_cols = required_cols + additional_cols
        block_data = block_data[all_cols].dropna(subset=required_cols)
        print(f"Block data loaded: {len(block_data)} blocks (total_vbytes, avg_sat_per_vb, mev_sat, date, block_subsidy_sat)")
        
        # Check halving
        if 'height' in block_data.columns:
            HALVING_HEIGHT = 840000
            before_halving = block_data[block_data['height'] < HALVING_HEIGHT]
            after_halving = block_data[block_data['height'] >= HALVING_HEIGHT]
            if len(before_halving) > 0:
                print(f"   Pre-halving (height < {HALVING_HEIGHT}): {len(before_halving):,} blocks, reward: {before_halving['block_subsidy_sat'].iloc[0]:,.0f} sat (6.25 BTC)")
            if len(after_halving) > 0:
                print(f"   Post-halving (height >= {HALVING_HEIGHT}): {len(after_halving):,} blocks, reward: {after_halving['block_subsidy_sat'].iloc[0]:,.0f} sat (3.125 BTC)")
        else:
            # If height not available, check halving via block_subsidy_sat
            unique_subsidies = block_data['block_subsidy_sat'].unique()
            print(f"   Block reward range: {unique_subsidies.min():,.0f} ~ {unique_subsidies.max():,.0f} sat")
        
        if len(block_data) < cfg["T"]:
            print(f"Warning: Block data ({len(block_data)}) is less than T ({cfg['T']}). Using cyclic iteration.")
    except Exception as e:
        print(f"Error: Cannot load block data ({e}).")
        raise

    rows = []
    # w is a single value (not a grid)
    w_sec = cfg.get("w_seconds", 1.0)
    if isinstance(w_sec, list):
        w_sec = w_sec[0]  # Use first value if list
    
    # alpha is a single value (Base fee adjustment speed)
    alpha = cfg.get("alpha", 0.125)
    if isinstance(alpha, list):
        alpha = alpha[0]  # Use first value if list

    # Parameter grids (read from config)
    U_star_grid = cfg.get("U_star_grid", [0.80])
    delta_grid = cfg.get("delta_grid", [0.10])
    G_ratio_grid = cfg["G_ratio_grid"]  # Required in config
    fee_floor_grid = cfg["fee_floor_grid"]  # Required in config
    
    # Block reward inclusion setting
    include_block_reward = cfg.get("include_block_reward", True)
    
    # Calculate average X_t (G_t = G_ratio * X_t_avg)
    # For R_t=0 scenario, X_t = F + M
    X_t_avg = float(block_data['avg_sat_per_vb'].mean() * block_data['total_vbytes'].mean() + block_data['mev_sat'].mean())
    print(f"\nAverage X_t (R_t=0): {X_t_avg:,.0f} sat ({X_t_avg/1e8:.4f} BTC)")
    print(f"Block reward setting: {'Included (current scenario)' if include_block_reward else 'Excluded (future scenario, R_t = 0)'}")
    
    # Define 6 policy groups
    # A: Base Fee + Fee Floor + Adaptive
    # B: Base Fee + Adaptive (no Fee Floor)
    # C: Base Fee + Fee Floor (no Adaptive)
    # D: Base Fee only
    # E: Fee Floor + Adaptive (no Base Fee)
    # F: No policy (baseline)
    policy_groups = [
        {"name": "A_BF_FF_AD", "basefee": True,  "feefloor": True,  "adaptive": True,  "desc": "Base Fee + Fee Floor + Adaptive"},
        {"name": "B_BF_AD",    "basefee": True,  "feefloor": False, "adaptive": True,  "desc": "Base Fee + Adaptive"},
        {"name": "C_BF_FF",    "basefee": True,  "feefloor": True,  "adaptive": False, "desc": "Base Fee + Fee Floor"},
        {"name": "D_BF",       "basefee": True,  "feefloor": False, "adaptive": False, "desc": "Base Fee only"},
        {"name": "E_FF_AD",    "basefee": False, "feefloor": True,  "adaptive": True,  "desc": "Fee Floor + Adaptive"},
        {"name": "F_NONE",     "basefee": False, "feefloor": False, "adaptive": False, "desc": "No policy"},
    ]
    
    # Calculate total number of experiments
    # G_ratio(5) × [A(3) + B(1) + C(3) + D(1) + E(3) + F(1)] = 5 × 12 = 60
    # Fee Floor ON groups: A, C, E (each with fee_floor_grid values)
    # Fee Floor OFF groups: B, D, F (each with 1 value)
    total_runs = 0
    for pg in policy_groups:
        if pg["feefloor"]:
            total_runs += len(G_ratio_grid) * len(fee_floor_grid)
        else:
            total_runs += len(G_ratio_grid)
    
    print(f"\nTotal experiments: {total_runs}")
    print(f"G_ratio grid: {G_ratio_grid}")
    print(f"Fee Floor grid: {fee_floor_grid}")
    print(f"Policy groups: {[pg['name'] for pg in policy_groups]}")
    print()
    
    run_count = 0
    U_star = U_star_grid[0]  # Use single value
    delta_step = delta_grid[0]  # Use single value

    for G_ratio in G_ratio_grid:
        # G_t = G_ratio × X_t_avg
        G_norm = G_ratio * X_t_avg
        
        for pg in policy_groups:
            # If Fee Floor ON, iterate fee_floor_grid; if OFF, fix to 0
            ff_values = fee_floor_grid if pg["feefloor"] else [0]
            
            for fee_floor_sat in ff_values:
                run_count += 1
                print(f"  [{run_count}/{total_runs}] G_ratio={G_ratio*100:.2f}%, G_norm={G_norm:,.0f}, {pg['name']}, FF={fee_floor_sat:,}")
                
                result = run_once(
                    shares, costs, miner_ids,
                    cfg["T"], cfg["base_delay_ms"], cfg["kappa_ms_per_MB"], cfg["gamma"],
                    cfg.get("lambda_block_rate", 0.00167), w_sec,
                    cfg.get("basefee0", 1.0),
                    enable_basefee=pg["basefee"], 
                    enable_feefloor=pg["feefloor"], 
                    fee_floor_sat=fee_floor_sat,
                    enable_adaptive=pg["adaptive"], 
                    B_min_vB=cfg.get("B_min_vB", 1_000_000), 
                    B_max_vB=cfg.get("B_max_vB", 2_000_000),
                    U_star=U_star, delta_step=delta_step,
                    G_norm=G_norm,
                    alpha=alpha,
                    block_data=block_data,
                    daily_costs=daily_costs,
                    include_block_reward=include_block_reward,
                )
                result_clean = {k: v for k, v in result.items() if k not in ['history_records', 'miners']}
                result_clean.update(dict(
                    policy_group=pg["name"], 
                    G_ratio=G_ratio,
                    G_norm=G_norm, 
                    fee_floor_sat=fee_floor_sat,
                    include_block_reward=include_block_reward
                ))
                rows.append(result_clean)

    df = pd.DataFrame(rows)
    results_csv = out_dir/"results.csv"
    df.to_csv(results_csv, index=False)
    print(f"wrote {results_csv}")
    
    # Auto-generate tables
    print("\n" + "=" * 80)
    print("Generating result tables...")
    print("=" * 80)
    try:
        # Import create_summary_table from sim/run_and_summarize.py
        from run_and_summarize import create_summary_table
        create_summary_table(results_csv)
    except ImportError as e:
        print(f"Warning: Cannot import table generation module ({e}).")
        print("Run manually: python sim/run_and_summarize.py --results", results_csv)
    except Exception as e:
        print(f"Warning: Error during table generation ({e}).")
        print("Run manually: python sim/run_and_summarize.py --results", results_csv)

if __name__ == "__main__":
    main()
