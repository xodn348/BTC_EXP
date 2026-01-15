# Bitcoin Fee Policy Simulation

Bitcoin miner behavior simulation for post-reward era fee policy analysis.

## Quickstart

```bash
# 1. Clone and setup
git clone https://github.com/xodn348/BTC_EXP.git
cd BTC_EXP
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 2. Data collection (takes several hours for 100K blocks)
python etl/fetch_blocks.py --start 790000 --end 890000
python etl/fetch_price.py --source yfinance
python etl/fetch_pool_audit.py

# 3. Build datasets
python etl/build_dataset.py
python etl/build_pool_cost.py

# 4. Run simulation
python sim/simulate.py --config sim/config_default.yaml

# 5. Visualize results
python sim/plot_policy.py
python sim/plot_threshold.py
```

## Project Structure

```
BTC_EXP/
├── etl/                    # Data collection & processing
│   ├── fetch_blocks.py     # Block data from Blockchain.com
│   ├── fetch_price.py      # Price data from Yahoo Finance
│   ├── fetch_pool_audit.py # Pool info & audit from Mempool.space
│   ├── build_dataset.py    # Build consolidated_block_data.csv
│   └── build_pool_cost.py  # Build pool_daily_cost.csv
├── sim/                    # Simulation
│   ├── simulate.py         # Main simulation
│   ├── config_default.yaml # Configuration
│   ├── plot_policy.py      # Policy effect visualization
│   └── plot_threshold.py   # Threshold analysis
├── analysis/               # Result analysis
│   ├── analyze_blocks.py   # Block data analysis
│   ├── calc_pool_profit.py # Pool profit calculation
│   └── plot_*.py           # Various plots
└── data/
    ├── raw/                # Source data
    └── processed/          # Simulation inputs & outputs
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

## Data Sources

| Data | Source | Script |
|------|--------|--------|
| Block data | Blockchain.com API | `etl/fetch_blocks.py` |
| Price data | Yahoo Finance | `etl/fetch_price.py` |
| Pool & Audit | Mempool.space API | `etl/fetch_pool_audit.py` |
| Mining costs | CBECI | `data/raw/costs/` (included) |
| MEV estimates | Parameter-based | `mev/` (included) |

## References

### Data Sources
- [CBECI](https://ccaf.io/cbeci/index) - Cambridge Bitcoin Electricity Consumption Index
- [Blockchain.com](https://www.blockchain.com/) - Block, pool, hashrate data
- [KIT Network Delay](https://dsn.tm.kit.edu/bitcoin/) - Block propagation delay
- [Mempool.space](https://mempool.space/docs/api/rest) - Block audit scores

### Core Research
| Concept | Reference |
|---------|-----------|
| Selfish Mining | Eyal & Sirer (2014) - "Majority is not enough" [FC 2014] |
| Bitcoin Backbone | Garay et al. (2015) - "The Bitcoin Backbone Protocol" [EUROCRYPT 2015] |
| Fee Instability | Carlsten et al. (2016) - "On the Instability of Bitcoin Without the Block Reward" [CCS 2016] |
| Base Fee | [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559) |
| MEV | Daian et al. (2020) - "Flash Boys 2.0" [IEEE S&P 2020] |
| Orphan Rate | Decker & Wattenhofer (2013) - "Information Propagation in the Bitcoin Network" [IEEE P2P] |
