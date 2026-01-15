# MEV Parameter Configuration Materials

## Reference List

1. **BlockScholes (2024) - Ethereum Staking Deep Dive: Analysing Execution Layer Rewards & MEV**
   - URL: https://www.blockscholes.com/research/ethereum-staking-deep-dive---analysing-execution-layer-rewards-mev
   - Key Findings:
     - Execution layer rewards are **20%** of total rewards (Priority fees 17%, MEV 3%)
     - Average MEV: **0.038 ETH/block**
     - 99.99th percentile: **28.873 ETH/block** (760x average)
     - **52% of blocks have 0 MEV**
     - MEV shows clustering and strong correlation with price volatility
     - Highly skewed distribution (long tail)

2. **Flashbots - Quantifying MEV**
   - URL: https://writings.flashbots.net/quantifying-mev
   - Key Concepts:
     - MEV is additional revenue obtained by block producers manipulating transaction order
     - Primarily occurs in arbitrage, front-running, back-running, etc.
     - Network latency and transaction fee structure affect MEV opportunities

3. **The Marginal Effects of Ethereum Network MEV Transaction Re-Ordering.pdf**
   - Key Findings:
     - Marginal effects of transaction order manipulation on the network
     - MEV opportunities are closely related to the number of transactions per block
     - Transaction order manipulation possibility affects MEV opportunity frequency

## Bitcoin vs Ethereum Differences

### Ethereum's MEV Opportunities
- **Smart Contracts**: DeFi, DEX, lending protocols
- **Complex Transactions**: Multi-step arbitrage, liquidation
- **High Transaction Frequency**: More transactions = more MEV opportunities

### Bitcoin's MEV Opportunities
- **Simple Transfers**: Mostly simple UTXO transfers
- **Limited Smart Contracts**: Only very basic scripts
- **Low Transaction Frequency**: Relatively fewer transactions
- **Estimate: 10-17% of Ethereum level**

## Current Implementation Status

### Simulation Structure
- `mev_sampler.parquet`: MEV value sampling (100,001 samples)
- `simulate.py`: Uses `M = rng.choice(mev_vals)` for each block
- `honest_profit = pshares * (F + M) - costs`: Sum of fees (F) and MEV (M)

### Parameters in Use (Final Decision)

**Distribution Model**: Zero-Inflated Lognormal Distribution

**Parameter Values:**
- **zero_rate**: 0.80 (80% of blocks have 0 MEV)
  - Source: Based on BlockScholes (2024) "52% of blocks have 0 MEV", adjusted for Bitcoin
- **block_reward_ratio**: 0.004 (0.4%)
  - Source: Based on BlockScholes (2024) "MEV is 3% of total rewards", Bitcoin scaling (3% × 0.13 ≈ 0.4%)
- **mean_log**: 14.9
  - Source: Calculated value (median = 3,000,000 sat)
- **sigma_log**: 1.8
  - Source: Based on BlockScholes (2024) "99.99th percentile is 760x average"
- **max_mev_ratio**: 0.10 (10%)
  - Source: Based on BlockScholes (2024) "99.99th percentile: 28.873 ETH", conservative adjustment for Bitcoin

**Generated Sample Statistics:**
- Total samples: 100,001
- Zero rate: ~80%
- Average MEV: ~1,250,000 sat (0.4% of block reward)
- Non-zero median: ~3,000,000 sat
- 99th percentile: 31,250,000 sat (limited by max_mev_ratio)

### Implementation Method

**Using Parameter-Based Generation:**
- `build_mev_sampler()` function in `etl/build_samplers.py`
- Not using actual block data-based estimates (`data/raw/mev/mev_estimated_from_blocks_*.csv`)
- Using theoretical parameters scaled from Ethereum research for Bitcoin
- Generating samples with Zero-inflated Lognormal distribution

**Storage Location:**
- Parquet: `data/processed/sim_inputs/mev_sampler.parquet`
- CSV (reference): `mev/mev_samples_parameter_based.csv`

## Detailed Information

For detailed parameter decision rationale, calculation process, and verification methods, see `MEV_PARAMETER_GUIDE.md`.

## Future Improvements

- ⏳ Clustering model (reflecting time correlation)
- ⏳ Sensitivity analysis (parameter tuning)
- ⏳ Modeling correlation between price volatility and MEV
