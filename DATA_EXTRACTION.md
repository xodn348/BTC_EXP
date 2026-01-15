# Bitcoin Simulation Data Extraction Guide

This guide describes how to extract and prepare data for Bitcoin fee policy simulations.

## Overview

The data extraction process uses Python scripts to:
1. Fetch raw data from APIs (Blockchain.com, Yahoo Finance, CBECI)
2. Transform and consolidate into simulation-ready format
3. Generate simulation inputs

## Prerequisites

1. **Python Environment**
   ```bash
   python -m venv source
   source source/bin/activate
   pip install -r requirements.txt
   ```

2. **Required Packages**
   - pandas
   - numpy
   - requests
   - yfinance
   - pyarrow

## Data Sources

### 1. Block Data
- **Source**: Blockchain.com API
- **Script**: `etl/fetch_blocks.py`
- **Output**: `data/raw/blocks/blocks_blockchain_com_*.csv`
- **Required columns**:
  - `height` (INT): Block height
  - `block_timestamp` (TIMESTAMP): Block timestamp
  - `total_fees_sat` (INT): Total fees in satoshis
  - `total_vbytes` (INT): Total virtual bytes
  - `avg_sat_per_vb` (FLOAT): Average sat/vB
  - `tx_count` (INT): Transaction count
  - `weight` (INT): Block weight
  - `size_bytes` (INT): Block size in bytes
  - `pool_name` (STRING): Mining pool name

### 2. Price Data
- **Source**: Yahoo Finance
- **Script**: `etl/fetch_price.py`
- **Output**: `data/raw/prices/btc_price_*.csv`
- **Required columns**:
  - `date` (DATE): Date
  - `btc_usd` (FLOAT): BTC price in USD

### 3. Hashrate and Energy Data
- **Source**: Blockchain.com API
- **Script**: `etl/fetch_hashrate_energy.py`
- **Output**: `data/raw/hashrate_energy/hashrate_energy_*.csv`
- **Required columns**:
  - `date` (DATE): Date
  - `hashrate_eh` (FLOAT): Network hashrate in EH/s
  - `power GUESS, GW` (FLOAT): Estimated power consumption
  - `annualised consumption GUESS, TWh` (FLOAT): Annualized energy

### 4. Mining Cost Data (CBECI)
- **Source**: Cambridge Bitcoin Electricity Consumption Index
- **File**: `data/raw/costs/Historical Cost to Mine One BTC (daily).csv`
- **Required columns**:
  - `Date` (DATE): Date
  - `Estimated cost of minting USD` (FLOAT): Cost to mine 1 BTC

### 5. Pool Share Data
- **Source**: Blockchain.com API (included in blocks data)
- **File**: `data/raw/pools/pools_timeseries_daily_*.csv`
- **Required columns**:
  - `date` (DATE): Date
  - `pool_name` (STRING): Pool name
  - `share` (FLOAT): Hashrate share (0-1)

### 6. MEV Data
- **Source**: Parameter-based estimation
- **File**: `mev/mev_samples_parameter_based.csv`
- **Required columns**:
  - `height` (INT): Block height
  - `mev_sat` (INT): MEV in satoshis
  - `mev_usd` (FLOAT): MEV in USD

## Data Collection Scripts

### Fetch Block Data
```bash
python etl/fetch_blocks.py
```

Options:
- `--start_height`: Starting block height (default: 790000)
- `--end_height`: Ending block height (default: 890000)

### Fetch Price Data
```bash
python etl/fetch_price.py
```

### Fetch Hashrate/Energy Data
```bash
python etl/fetch_hashrate_energy.py
```

## Data Consolidation

### Create Consolidated Dataset
```bash
python etl/create_consolidated_dataset.py
```

This script:
1. Loads raw block data
2. Merges price data (by date)
3. Merges MEV estimates (by height)
4. Calculates block subsidy based on halving
5. Creates miner cost data

**Outputs**:
- `data/processed/consolidated_block_data.csv`
- `data/processed/pool_daily_cost.csv`

## Data Timeline

### Primary Calibration Window: 2024 Halving ±50,000 Blocks

Based on the research design, the primary calibration dataset uses a symmetric window around the April 20, 2024 Bitcoin halving:

**Key Parameters**:
- **Center**: Block height 840,000 (April 20, 2024)
- **Window**: ±50,000 blocks (symmetric)
- **Total blocks**: ~100,000 blocks
- **Block height range**: 790,000 → 890,000
- **Duration**: ~694 days total
- **Approximate date range**: 2023-05-09 → 2025-04-02

**Rationale**:
1. **Halving as Economic Turning Point**: The halving reduces block subsidy by 50%, creating an immediate shift in miner revenue structure
2. **Balanced and Clean Data Window**: 50,000 blocks ≈ 347 days provides sufficient length for stable fee and MEV distributions
3. **Direct Relevance to Fee-Only Bitcoin Modeling**: Post-halving period is the closest real-world environment to a fee-dominant system
4. **Simple, Objective, and Defensible Choice**: Transparent and non-arbitrary

## Simulation Input Format

### consolidated_block_data.csv

| Column | Type | Description |
|--------|------|-------------|
| height | INT | Block height |
| date | DATE | Block date (YYYY-MM-DD) |
| block_timestamp | TIMESTAMP | Block timestamp |
| total_vbytes | INT | Total virtual bytes |
| avg_sat_per_vb | FLOAT | Average satoshi per vbyte |
| mev_sat | INT | MEV in satoshis |
| block_subsidy_sat | INT | Block subsidy in satoshis |
| btc_usd | FLOAT | BTC price in USD |
| miner_id | INT | Miner ID |
| pool_name | STRING | Pool name |

### pool_daily_cost.csv

| Column | Type | Description |
|--------|------|-------------|
| date | DATE | Date |
| miner_id | INT | Miner ID |
| pool_name | STRING | Pool name |
| daily_share | FLOAT | Daily hashrate share |
| cost_usd_per_day | FLOAT | Daily mining cost in USD |

## Policy Evaluation

The simulation compares these policy combinations:

| Policy | Base Fee | Fee Floor | Adaptive |
|--------|:--------:|:---------:|:--------:|
| A | ✓ | ✓ | ✓ |
| B | ✓ | ✗ | ✓ |
| C | ✓ | ✓ | ✗ |
| D | ✓ | ✗ | ✗ |
| E | ✗ | ✓ | ✓ |
| F | ✗ | ✗ | ✗ |

## Evaluation Metrics

### Deviation Ratio (β)
BFT stability metric:
```
β = (1/N) × Σ 1[Π_dev(t) > Π_hon(t)]
```
BFT-stable if β < 1/3.

### ROI (Return on Investment)
```
ROI = (Revenue - Cost) / Cost
```

## Network Delay Parameters

Calculated from KIT invstat.gpd data:
- **base_delay_ms**: 742 ms (50th percentile median)
- **kappa_ms_per_MB**: 26.40 ms/MB (linear regression)

Formula: `δt = base_delay_ms + kappa_ms_per_MB × B_MB`

## Troubleshooting

### Common Issues

1. **API rate limits**
   - Use `fetch_blocks_auto_resume.py` for automatic retry
   - Add delays between requests

2. **Missing data**
   - Check date ranges match across all data sources
   - Verify API endpoints are accessible

3. **Data format issues**
   - Ensure date formats are consistent (YYYY-MM-DD)
   - Check for missing or null values

## References

- [Blockchain.com API](https://www.blockchain.com/api)
- [Cambridge Bitcoin Electricity Index](https://ccaf.io/cbeci/index)
- [Yahoo Finance](https://finance.yahoo.com/)
- Research Design Document: Halving Window Specification
