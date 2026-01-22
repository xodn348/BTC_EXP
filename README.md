# Bitcoin Fee Policy Simulation

Bitcoin miner behavior simulation for post-reward era fee policy analysis.

## Reproducibility

> **All data is included.** Run simulation immediately without API calls.  
> To fetch fresh data from APIs, see "Full Pipeline" below.

### Quick Start (No API Required)

```bash
git clone https://github.com/xodn348/BTC_EXP.git
cd BTC_EXP
pip install -r requirements.txt
python sim/simulate.py --config sim/config_default.yaml
python sim/plot_policy.py
```

### Full Pipeline (Fetch Fresh Data)

```bash
# 1. Clone and setup
git clone https://github.com/xodn348/BTC_EXP.git
cd BTC_EXP
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Collect data from APIs (takes several hours)
python etl/fetch_blocks.py --start 790000 --end 890000
python etl/fetch_price.py --source yfinance
python etl/fetch_pool_audit.py
python etl/fetch_mev_from_blocks.py

# 3. Build simulation datasets
python etl/build_dataset.py
python etl/build_pool_cost.py

# 4. Run simulation
python sim/simulate.py --config sim/config_default.yaml

# 5. Visualize results
python sim/plot_policy.py
python sim/plot_threshold.py
```

> ⚠️ **Note**: All commands must be run from the project root directory (`BTC_EXP/`).

### Data Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: Data Collection (ETL)                                      │
├─────────────────────────────────────────────────────────────────────┤
│  fetch_blocks.py      → data/raw/blocks/*.csv      (Blockchain.com) │
│  fetch_price.py       → data/raw/prices/*.csv      (Yahoo Finance)  │
│  fetch_pool_audit.py  → data/raw/audit/*.csv       (Mempool.space)  │
│  fetch_mev_from_blocks.py → data/raw/mev/*.csv     (Estimated)      │
│  fetch_costs.py       → data/raw/costs/*.csv       (CBECI)          │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: Build Datasets                                             │
├─────────────────────────────────────────────────────────────────────┤
│  build_dataset.py     → data/processed/consolidated_block_data.csv  │
│  build_pool_cost.py   → data/processed/pool_daily_cost.csv          │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: Simulation                                                 │
├─────────────────────────────────────────────────────────────────────┤
│  simulate.py          → data/processed/sim_runs/run_id=*/           │
│                          ├── results.csv                            │
│                          └── config.yaml                            │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: Visualization                                              │
├─────────────────────────────────────────────────────────────────────┤
│  plot_policy.py       → docs/diagrams/                              │
│  plot_threshold.py    → docs/diagrams/                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Included Data (No API Required)

These files are included in the repository:

| File | Description |
|------|-------------|
| `data/raw/costs/Historical Cost to Mine One BTC (daily).csv` | Mining cost data from CBECI |
| `data/raw/network_delay/invstat.gpd` | KIT network delay data |
| `mev/mev_samples_parameter_based.csv` | MEV parameter samples |

### Data to Fetch (API Required)

| Data | API | Script | Time |
|------|-----|--------|------|
| Block data | Blockchain.com | `fetch_blocks.py` | ~6-12 hours |
| Price data | Yahoo Finance | `fetch_price.py` | ~1 min |
| Pool & Audit | Mempool.space | `fetch_pool_audit.py` | ~2-4 hours |
| MEV estimates | Local calculation | `fetch_mev_from_blocks.py` | ~1 min |

## Project Structure

```
BTC_EXP/
├── etl/                      # Data collection & processing
│   ├── fetch_blocks.py       # Block data (required)
│   ├── fetch_price.py        # Price data (required)
│   ├── fetch_pool_audit.py   # Pool info & audit (required)
│   ├── fetch_mev_from_blocks.py  # MEV estimation (required)
│   ├── fetch_costs.py        # Mining costs (optional, data included)
│   ├── build_dataset.py      # Build consolidated dataset
│   └── build_pool_cost.py    # Build pool cost dataset
├── sim/                      # Simulation
│   ├── simulate.py           # Main simulation
│   ├── config_default.yaml   # Configuration
│   ├── plot_policy.py        # Policy visualization
│   └── plot_threshold.py     # Threshold analysis
├── analysis/                 # Result analysis (optional)
├── data/
│   ├── raw/                  # Source data
│   └── processed/            # Simulation inputs & outputs
└── mev/                      # MEV parameters
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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
