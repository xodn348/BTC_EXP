# Diagram Proposals

Types and proposals for diagrams to explain experimental results. (Organized in order of Direction from expDraft.md)

## 1. Block Data Experiment Overview

**Purpose**: Show experimental data sources and range (Block height 790,000 - 890,000)

**Proposed Method**: Information box or timeline diagram

**Content**:
- Experiment period: Block height 790,000 - 890,000 (2023-05-16 ~ 2025-03-29)
- Data source: Actual Bitcoin block data
- Number of blocks: Approximately 100,000 blocks
- Key metrics: Fee, MEV, block size, etc.

**Visualization**: Simple information table or timeline

## 2. Vi_hon vs Vi_dev Comparison

**Purpose**: Show the process of setting and comparing Vi_honest and Vi_dev

**Proposed Method**: Python matplotlib (line plot, comparison chart)

**Data**:
- X-axis: Round t (0~1000)
- Y-axis: Vi_honest, Vi_dev (cumulative values)
- Different lines for each miner or average values

**Key Message**: 
- Calculate Vi_honest[i] and Vi_dev[i] for each miner i
- If Vi_dev > Vi_honest, choose deviation

## 3. Vi_hon - Vi_dev Difference (Similar to difference in each round i)

**Purpose**: Show that Vi_hon - Vi_dev is similar to the difference in each round i

**Proposed Method**: Python matplotlib (line plot, difference comparison)

**Data**:
- X-axis: Round t (0~20, detailed)
- Y-axis: 
  - Vi_honest[i] - Vi_dev[i] (cumulative difference)
  - Π_i^hon[t] - Π_i^dev[t] (per-round difference)
- Show that the two values are similar

**Key Message**: 
- Vi threshold (25,046 sat) ≈ single round threshold (22,769 sat) × 1.10
- Single round condition is a good approximation of Vi comparison

## 4. Incentive Margin G_t Formula Relationship

**Purpose**: Derive G_t = ratio × X_t, ratio = (ρ_dev - ρ_honest) / (1 - ρ_dev) formula

**Proposed Method**: Mermaid flowchart or Python matplotlib (formula box flow)

**Formula Derivation Process**:
```
Π_i^dev > Π_i^hon
  ↓
p_i^dev · (X_t + G_t) - C_i > p_i^hon · X_t - C_i
  ↓
p_i^dev · G_t > (p_i^hon - p_i^dev) · X_t
  ↓
G_t > (p_i^hon - p_i^dev) / p_i^dev · X_t
  ↓
G_t > (ρ_dev - ρ_honest) / (1 - ρ_dev) · X_t
  ↓
G_t > ratio · X_t
```

**Key Message**: 
- ratio = (ρ_dev - ρ_honest) / (1 - ρ_dev)
- G_t threshold = ratio × X_t

## 5. Higher rho_dev is necessary for higher G_t threshold

**Purpose**: Setting higher rho_dev is necessary to higher G_t

**Proposed Method**: Python matplotlib (Flow diagram or relationship diagram)

**Flow Relationship**:
```
rho_dev increase
  ↓
(ρ_dev - ρ_honest) increase  (numerator increase)
  ↓
(1 - ρ_dev) decrease  (denominator decrease)
  ↓
ratio = (ρ_dev - ρ_honest) / (1 - ρ_dev) increase
  ↓
G_t threshold = ratio × X_t increase
```

**Visualization**: 
- Flow diagram: rho_dev → ratio → threshold
- Include actual numerical examples

## 6. Higher w is necessary for higher G_t threshold

**Purpose**: Show that withholding time w determines G_t, and w needs to be larger

**Proposed Method**: Python matplotlib (line plot, w vs threshold)

**Data**:
- X-axis: w (0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0 s)
- Y-axis: 
  - ρ_dev values
  - ratio values  
  - G_t threshold (sat)
- Different lines for various B values

**Key Message**: 
- w increase → δ_dev = δ_hon + w increase → ρ_dev increase → ratio increase → G_t threshold increase
- Current w = {0.5s, 1.0s, 2.0s} is very small, so threshold is low

**Additional Diagrams (Supplementary)**

## A. Threshold vs Alpha Value Comparison

**Purpose**: Show how small the current threshold is (alpha=0.1 is 30~120x the threshold)

**Proposed Method**: Python matplotlib (bar chart, log scale)

**Data**:
- X-axis: Parameter combinations (B, w)
- Y-axis: G_t values (log scale)
- Compare threshold values vs alpha=0.1, 0.25, 0.5 values

## B. Parameter Space: Threshold Distribution by B, w

**Purpose**: Visualize threshold distribution across all parameter combinations

**Proposed Method**: Python matplotlib (heatmap)

**Data**:
- X-axis: B (1, 2, 4, 8 MB)
- Y-axis: w (0.5, 1.0, 2.0 s)
- Values: ratio or G_t threshold (heatmap color)

## Recommended Priority (Direction order)

1. **Diagram 1**: Block Data Experiment Overview (simple information table)
2. **Diagram 2**: Vi_hon vs Vi_dev comparison
3. **Diagram 3**: Vi_hon - Vi_dev difference (similar to per-round difference)
4. **Diagram 4**: Incentive Margin G_t formula relationship
5. **Diagram 5**: Higher rho_dev needed for higher G_t threshold (Flow diagram)
6. **Diagram 6**: Higher w needed for higher G_t threshold (w vs threshold plot)

**Supplementary Diagrams**:
- A. Threshold vs Alpha comparison (emphasize current problem)
- B. Parameter Space Heatmap (overall pattern)

## Implementation Method

All diagrams implemented with **Python matplotlib** and saved as PDF (for thesis insertion)

### Implementation Script
- File: `visualize_findings.py`
- Execution: `python visualize_findings.py <diagram_number>` (1-6)
- Output: `docs/diagrams/diagram*.pdf`

### Implementation Status for Each Diagram
1. ✅ Diagram 1: Block Data Experiment (simple information table)
2. ✅ Diagram 2: Vi_hon vs Vi_dev comparison
3. ✅ Diagram 3: Vi_hon - Vi_dev difference
4. ✅ Diagram 4: G_t formula relationship
5. ✅ Diagram 5: rho_dev → threshold Flow
6. ✅ Diagram 6: w vs threshold relationship
