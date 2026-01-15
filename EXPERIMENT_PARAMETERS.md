# Experiment Parameters Definition

This file tracks where each parameter and calculation element is defined in the codebase.

**Last Updated**: 2026-01-15

## Vi Calculation: Vi = E[Σ γ^t Πi(St, ai)]

### Discount Factor (γ)
- **Value**: 0.99
- **Definition**: [`sim/config_default.yaml`](sim/config_default.yaml) → `gamma: 0.99`
- **Usage**: [`sim/simulate.py`](sim/simulate.py) → `discount = gamma ** t`
- **Status**: ✅ Defined
- **Rationale**: Industry standard for reinforcement learning and game theory

### State Variables: St = {Ft, Mt, hi, δt}

#### Ft (Fee at time t)
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `F_raw = F_rate * vB_t`
- **Source**: `data/processed/consolidated_block_data.csv` → `avg_sat_per_vb`, `total_vbytes`
- **Status**: ✅ Defined
- **Note**: Actual fees from historical block data

#### Mt (MEV at time t)
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `M = float(block_row['mev_sat'])`
- **Source**: `data/processed/consolidated_block_data.csv` → `mev_sat`
- **Status**: ✅ Defined
- **Note**: Parameter-based MEV estimates from `mev/mev_samples_parameter_based.csv`

#### hi (Miner share)
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `shares = top13['normalized_share'].values`
- **Source**: `data/processed/pool_daily_cost.csv` → `daily_share`
- **Status**: ✅ Defined
- **Note**: Top 13 miners (pools with ≥1% share, covering 99.52% of hashrate)

#### δt (Network delay at time t)
- **Formula**: 
  - **Honest**: δ_hon(B) = base_delay_ms + kappa_ms_per_MB × B_MB
  - **Deviating**: δ_dev(B) = δ_hon(B) + w
- **Parameters**:
  - `base_delay_ms`: 742 ms (from KIT invstat.gpd, 50th percentile)
  - `kappa_ms_per_MB`: 26.40 ms/MB (linear regression)
  - `w_seconds`: 1.0 s (withholding delay)
- **Definition**: [`sim/config_default.yaml`](sim/config_default.yaml)
- **Usage**: [`sim/simulate.py`](sim/simulate.py) → `delta_ms = base_delay + kappa * Bt_MB`
- **Status**: ✅ Defined

### Payoff Function: Πi(St, ai)

**Honest strategy**:
- **Formula**: Π_i^hon = p_i^hon · X_t - C_i
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `profit_honest = p_hon * X_t - block_costs[i]`

**Deviation strategy**:
- **Formula**: Π_i^dev = p_i^dev · (X_t + G_t) - C_i
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `profit_dev = p_dev * (X_t + G_t) - block_costs[i]`

#### pi (Success probability)
- **Formula**: 
  - p_i^hon = h_i × (1 - ρ_honest)
  - p_i^dev = h_i × (1 - ρ_dev)
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → lines 246-247
- **Status**: ✅ Defined

#### ρ (Orphan rate)
- **Formula**: 
  - ρ_honest = 1 - exp(-λ × δ_hon)
  - ρ_dev = 1 - exp(-λ × δ_dev)
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → lines 211-213
  ```python
  rho_honest = 1 - np.exp(-lambda_rate * delta_sec)
  rho_dev = 1 - np.exp(-lambda_rate * delta_dev_sec)
  ```
- **Usage**: 
  - Success probability: `p_i = share × (1 - rho)`
  - Deviation threshold: `ratio_i = (rho_dev - rho_honest) / (1 - rho_dev)`
- **Status**: ✅ Defined

#### X_t (Total Block Reward)
- **Formula**: X_t = R_t + F_t + M_t
- **Components**:
  - R_t: Block subsidy (0 for post-reward simulation, actual value for analysis)
  - F_t: Transaction fees (from `avg_sat_per_vb × total_vbytes`)
  - M_t: MEV (from `mev_sat`)
- **Config**: `include_block_reward: false` (post-reward scenario)
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `X_t = R_t + F_eff + M`
- **Status**: ✅ Defined

#### G_t (Deviation Additional Gain)
- **Formula**: G_t = G_norm × (U_t / U_star)
- **Description**: Proportional to congestion ratio
- **Parameters**:
  - G_norm = G_ratio × X_t_avg
  - G_ratio: [0.0, 0.0017, 0.005, 0.01, 0.015]
  - U_star: 0.80 (target utilization)
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `G_t = G_norm * congestion_ratio`
- **Status**: ✅ Defined

#### G_norm (Base Deviation Gain)
- **Formula**: G_norm = G_ratio × X_t_avg
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → line 488
- **Usage**: `G_t = G_norm * congestion_ratio`
- **Status**: ✅ Defined

#### Ci (Cost for miner i)
- **Source**: `data/processed/pool_daily_cost.csv` → `cost_usd_per_day`
- **Conversion**: `cost_sat_per_block = (cost_usd_per_day / 144 / btc_usd) × 100,000,000`
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `cost_map[(date, miner_id)]`
- **Status**: ✅ Defined

### Action (ai)
- **Options**: {honest, deviation}
- **Decision Rule**: `dev_flag = 1 if profit_dev > profit_honest else 0`
- **Definition**: [`sim/simulate.py`](sim/simulate.py) → `miner.decide_and_record()`
- **Status**: ✅ Defined

## Policy Parameters

### Base Fee (EIP-1559 style)
- **Formula**: `basefee(t+1) = basefee(t) × (1 + α × (U_t - U*) / U*)`
- **Parameters**:
  - `basefee0`: 20 sat/vB (initial)
  - `alpha`: 0.125 (adjustment speed)
  - `U_star`: 0.80 (target utilization)
- **Effect**: `F = max(basefee, F_raw)` when enabled
- **Definition**: [`sim/config_default.yaml`](sim/config_default.yaml)
- **Status**: ✅ Defined

### Fee Floor
- **Formula**: `F_eff = max(F, fee_floor_sat)`
- **Grid**: [0, 20M, 40M, 60M] sat
- **Definition**: [`sim/config_default.yaml`](sim/config_default.yaml) → `fee_floor_grid`
- **Usage**: [`sim/simulate.py`](sim/simulate.py) → line 206
- **Status**: ✅ Defined

### Adaptive Block Size
- **Formula**:
  - If U_t > U*: B(t+1) = min(B_max, (1 + δ) × B_t)
  - If U_t < U*: B(t+1) = max(B_min, (1 - δ) × B_t)
- **Parameters**:
  - `B_min_vB`: 1,000,000 vB (1 MB)
  - `B_max_vB`: 2,000,000 vB (2 MB)
  - `delta_step`: 0.10 (10% adjustment)
- **Definition**: [`sim/config_default.yaml`](sim/config_default.yaml)
- **Status**: ✅ Defined

## Simulation Parameters

| Parameter | Value | Location |
|-----------|-------|----------|
| T (simulation length) | 100,001 blocks | `config_default.yaml` |
| γ (discount factor) | 0.99 | `config_default.yaml` |
| λ (block rate) | 0.00167 /sec | `config_default.yaml` |
| base_delay_ms | 742 ms | `config_default.yaml` |
| kappa_ms_per_MB | 26.40 ms/MB | `config_default.yaml` |
| w_seconds | 1.0 s | `config_default.yaml` |
| alpha | 0.125 | `config_default.yaml` |
| U_star | 0.80 | `config_default.yaml` |
| delta_step | 0.10 | `config_default.yaml` |

## Policy Groups

| Policy | Base Fee | Fee Floor | Adaptive | Description |
|--------|:--------:|:---------:|:--------:|-------------|
| A | ✓ | ✓ | ✓ | All mechanisms |
| B | ✓ | ✗ | ✓ | Base Fee + Adaptive |
| C | ✓ | ✓ | ✗ | Base Fee + Fee Floor |
| D | ✓ | ✗ | ✗ | Base Fee only |
| E | ✗ | ✓ | ✓ | Fee Floor + Adaptive |
| F | ✗ | ✗ | ✗ | No policy (baseline) |

## Parameter Grids

| Parameter | Grid Values |
|-----------|-------------|
| G_ratio | [0.0, 0.0017, 0.005, 0.01, 0.015] |
| fee_floor_sat | [0, 20M, 40M, 60M] |
| U_star | [0.80] |
| delta_step | [0.10] |

## Data Files

| File | Description | Key Columns |
|------|-------------|-------------|
| `consolidated_block_data.csv` | Block-level data | height, total_vbytes, avg_sat_per_vb, mev_sat, block_subsidy_sat, btc_usd, miner_id |
| `pool_daily_cost.csv` | Daily miner costs | date, miner_id, daily_share, cost_usd_per_day |
| `config_default.yaml` | Simulation config | All parameters above |

## Summary

| Parameter | Status | Location |
|-----------|--------|----------|
| γ (gamma) | ✅ | config_default.yaml |
| Ft | ✅ | consolidated_block_data.csv |
| Mt | ✅ | consolidated_block_data.csv |
| hi | ✅ | pool_daily_cost.csv |
| δt | ✅ | config_default.yaml |
| ρ (rho) | ✅ | simulate.py (calculated from δ) |
| pi | ✅ | simulate.py (calculated from ρ) |
| X_t | ✅ | simulate.py (R + F + M) |
| G_t | ✅ | simulate.py (G_norm × U_t/U*) |
| G_norm | ✅ | simulate.py (G_ratio × X_t_avg) |
| fee_floor_sat | ✅ | simulate.py (from fee_floor_grid) |
| Ci | ✅ | pool_daily_cost.csv |
| Base Fee | ✅ | config_default.yaml |
| Fee Floor | ✅ | config_default.yaml |
| Adaptive | ✅ | config_default.yaml |
