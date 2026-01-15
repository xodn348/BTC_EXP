# Bitcoin Fee Policy Simulation

Bitcoin miner behavior simulation for post-reward era fee policy analysis.

## Quickstart

> **⚠️ All commands must be run from the project root directory (`btc_exp/`).**

```bash
# 1. Clone and setup
git clone https://github.com/xodn348/BTC_EXP.git
cd BTC_EXP
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 2. Data collection (takes several hours for 100K blocks)
python etl/fetch_blocks.py --start 790000 --end 890000
python etl/fetch_price.py --source yfinance
python etl/fetch_mempool_audit.py   # Pool info & audit scores

# 3. Build datasets
python etl/create_consolidated_dataset.py
python analysis/01_calc_pool_cost.py

# 4. Run simulation
python sim/simulate.py --config sim/config_default.yaml

# 5. Visualize results
python sim/plot_policy.py
python sim/plot_threshold.py
```

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| γ (gamma) | 0.99 | Discount factor |
| λ | 0.00167 | Block rate (1/600 sec) |
| base_delay | 742 ms | Base network delay |
| κ | 26.40 ms/MB | Delay per MB |
| α | 0.125 | Base fee adjustment speed |
| U* | 0.80 | Target utilization |

## Calibration Window

Block heights **790,000 → 890,000** (±50,000 blocks around April 2024 halving)

## Data Sources

| Data | Source | Script |
|------|--------|--------|
| Block data | Blockchain.com API | `etl/fetch_blocks.py` |
| Price data | Yahoo Finance | `etl/fetch_price.py` |
| Pool info & Audit | Mempool.space API | `etl/fetch_mempool_audit.py` |
| Mining costs | CBECI | `data/raw/costs/` (included) |
| MEV estimates | Parameter-based | `mev/mev_samples_parameter_based.csv` (included) |

## References

### Data Sources
- [CBECI](https://ccaf.io/cbeci/index) - Cambridge Bitcoin Electricity Consumption Index
- [Blockchain.com](https://www.blockchain.com/) - Block, pool, hashrate data
- [KIT Network Delay](https://dsn.tm.kit.edu/bitcoin/) - Block propagation delay (`base_delay_ms`, `kappa_ms_per_MB`)
- [Mempool.space](https://mempool.space/docs/api/rest#get-block-audit-score) - Block audit scores

### Core Research
| Parameter/Concept | Reference |
|-------------------|-----------|
| Selfish Mining, Withholding delay (w) | Eyal & Sirer (2014) - "Majority is not enough" [FC 2014] |
| BFT Stability (β < 1/3) | Garay, Kiayias & Leonardos (2015) - "The Bitcoin Backbone Protocol" [EUROCRYPT 2015] |
| Miner Incentive Instability | Carlsten et al. (2016) - "On the Instability of Bitcoin Without the Block Reward" [CCS 2016] |
| Base Fee (EIP-1559 style) | [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) |
| MEV Estimation | Daian et al. (2020) - "Flash Boys 2.0" [IEEE S&P 2020] |
| Fee Market | Easley, O'Hara & Basu (2019) - "From Mining to Markets" [JFE] |
| Orphan Rate Model | Decker & Wattenhofer (2013) - "Information Propagation in the Bitcoin Network" [IEEE P2P] |
