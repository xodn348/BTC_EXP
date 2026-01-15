# Miner Cost Calculation Formulas

## Method B: Power Consumption Based Calculation

### Input Data
- $E_{annual}$: Annual power consumption (TWh) - `annualised consumption GUESS, TWh` (using CBECI estimate)
- $p_{elec}$: Electricity price = 0.05 USD/kWh (CBECI default, fixed)
  - Average miner electricity price assumption based on CBECI model parameters
- $P_{BTC}$: BTC price (USD) - `btc_usd`
- $R_b$: Block reward (BTC)
  - $R_b = 6.25$ BTC (block height < 840,000)
  - $R_b = 3.125$ BTC (block height ≥ 840,000)

### Calculation Steps

**Step 1: Annual Power Consumption → Daily Power Consumption**
```
E_daily = E_annual / 365  (TWh/day)
```

**Step 2: Daily Power Consumption → Per-Block Power Consumption**
```
E_block = (E_daily × 10^9) / 144  (kWh/block)

where:
- 10^9: TWh → kWh conversion (1 TWh = 10^9 kWh)
- 144: Blocks per day (1 block per 10 minutes, 24 hours × 6 blocks/hour)

Note: Per-block power consumption is independent of halving (total network power consumption divided by number of blocks)
However, actual power consumption may change if mining difficulty changes after halving
```

**Step 3: Per-Block Power Consumption → Per-Block Cost (USD)**
```
C_block_USD = E_block × p_elec  (USD/block)

where:
- E_block: Per-block power consumption (kWh/block)
- p_elec: Electricity price = 0.05 USD/kWh (CBECI default, fixed)
```

**Step 4: Per-Block Cost (USD) - Final Result**
```
C_block_USD = E_block × p_elec  (USD/block)

Note: Unified in USD units (no sat conversion)
```

### Final Formula (Method B)

```
C_block_USD = (E_annual / 365 × 10^9 / 144) × p_elec

Simplified:
C_block_USD = (E_annual × 10^9 × p_elec) / (365 × 144)
C_block_USD = (E_annual × 10^9 × 0.05) / 52,560

where:
- E_annual: Annual power consumption (TWh) - using CBECI GUESS value
- p_elec: Electricity price = 0.05 USD/kWh (CBECI default, fixed)
- 52,560 = 365 × 144 (blocks per year)
```

---

## Method A: CBECI "Cost to Mine One BTC" Based Calculation

### Input Data
- $C_{BTC}$: Cost to mine 1 BTC (USD) - `Estimated cost of minting USD`
- $P_{BTC}$: BTC price (USD) - `btc_usd`
- $R_b$: Block reward (BTC)
  - $R_b = 6.25$ BTC (block height < 840,000, pre-halving)
  - $R_b = 3.125$ BTC (block height ≥ 840,000, post-halving, 2024-04-20)

### Halving Information
- **Halving Date**: 2024-04-20
- **Halving Block Height**: 840,000
- **Pre-Halving**: Block reward 6.25 BTC (blocks 790,000 ~ 839,999)
- **Post-Halving**: Block reward 3.125 BTC (blocks 840,000 ~ 890,000)

**Important**: CBECI's "Cost to Mine One BTC" is the cost to mine 1 BTC, so it should be independent of halving
(1 BTC is always 1 BTC). However, actual cost may change if mining difficulty changes after halving.

### Calculation Steps

**Step 1: CBECI "Cost to Mine One BTC" → Per-Block Cost (USD)**
```
C_block_USD = C_BTC × R_b  (USD/block)

where:
- C_BTC: CBECI "Cost to Mine One BTC" (USD) - cost to mine 1 BTC
- R_b: Block reward (BTC)
  - R_b = 6.25 BTC (block height < 840,000, pre-halving)
  - R_b = 3.125 BTC (block height ≥ 840,000, post-halving)
- Note: Since CBECI data is cost per 1 BTC, multiply by block reward to get per-block cost
```

### Final Formula (Method A)

```
C_block_USD = C_BTC × R_b

where:
- C_BTC: CBECI "Cost to Mine One BTC" (USD)
- R_b: Block reward (BTC)
  - R_b = 6.25 (pre-halving)
  - R_b = 3.125 (post-halving)
```

---

## Validation: Relative Error + 95% Confidence Interval

### Relative Error Calculation

```
RE_i = |C_B,i - C_A,i| / C_A,i

where:
- C_B,i: Cost of block i calculated by Method B
- C_A,i: Cost of block i calculated by Method A
- RE_i: Relative error of block i
```

### Relative Error Statistics

```
RE_mean = (1/n) × Σ RE_i
RE_std = √((1/(n-1)) × Σ(RE_i - RE_mean)²)
```

### 95% Confidence Interval

```
CI_95% = RE_mean ± t_{0.025, n-1} × (RE_std / √n)

where:
- t_{0.025, n-1}: 97.5th percentile of t-distribution (degrees of freedom n-1)
- n: Number of blocks
```

### Validation Criteria

```
✅ Pass: CI_upper ≤ ε (e.g., ε = 0.05 = 5%)
❌ Fail: CI_upper > ε
```

---

## Cost Distribution per Miner

### Input Data
- $\bar{C}_{block}$: Average per-block cost (USD)
- $h_i$: Hash rate ratio (share) of Miner i
- $N$: Number of miners

### Calculation

```
C_i = C_block × h_i  (USD/block)

where:
- C_i: Per-block cost of Miner i (USD)
- h_i: Share of Miner i (Σ h_i = 1)
```

### Final Output

```
miner_cost_curve.parquet:
  - miner_id: Miner ID
  - C_i: Per-block cost of Miner i (USD/block)
```

---

## Unit Conversion Summary

```
1 TWh = 10^9 kWh
1 BTC = 10^8 sat
1 day = 144 blocks (1 block per 10 minutes)
1 year = 365 days
```

---

## Validation Example

### Example Values
- $E_{annual}$ = 200 TWh (CBECI GUESS)
- $p_{elec}$ = 0.05 USD/kWh (CBECI default)
- $P_{BTC}$ = 50,000 USD
- $C_{BTC}$ = 25,000 USD (cost to mine 1 BTC)
- $R_b$ = 6.25 BTC

### Method B Calculation
```
E_daily = 200 / 365 = 0.5479 TWh/day
E_block = (0.5479 × 10^9) / 144 = 3,802,777.78 kWh/block
C_block_USD = 3,802,777.78 × 0.05 = 190,138.89 USD/block
```

### Method A Calculation
```
C_block_USD = 25,000 / 6.25 = 4,000 USD/block
C_block_sat = (4,000 / 50,000) × 10^8 = 8,000,000 sat/block
```

### Relative Error
```
RE = |380,277,778 - 8,000,000| / 8,000,000 = 46.53
```

⚠️ **Note**: The above example may have unit or calculation logic issues. Validation with actual data required.
