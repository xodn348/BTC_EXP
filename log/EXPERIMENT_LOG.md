# Bitcoin Simulation Experiment Log

This file records the experiment progress, results, findings, and issues on a daily basis.

---

## 2025-11-11 (Mon)

**Completed**: Real data collection completed (10,000 blocks, 5 pools, MEV estimation, price/hashrate API), simulation input data generation (fee/mev/miner samplers), sample data results deleted and cleaned up
**Findings**: MEV estimated from block data (10% have MEV>0), pool data share sum ≠ 1.0, miner cost still using calculated values
**Next**: Run simulation with actual data and analyze results

---

## 2025-11-10 (Sun)

**Completed**: Data collection scripts written, simulation input generated with sample data and basic simulation run (8 runs, all stable_bft=False)
**Findings**: Fork rate increases with block size B (B=1,2: 0.0, B=4: ~0.06, B=8: ~0.22), BFT stability not achieved at theta_bar=1.0, dev_profit calculation is placeholder
**Issues**: dev_profit calculation logic is placeholder (`honest_profit + 0.05`), actual deviation mechanism implementation needed

---

## 2025-12-17 (Wed)

**Completed**: Mining value query (CBECI), extracted 100,001 samples based on MEV parameters
**Findings**: MEV report, MEV distribution
**Issues**: 

---

## 2025-12-18 (Thu)

**Completed**: Experiment detail understanding
**Findings**: 
1. Assume each miner i is in mining pool H_i and H_i sustains same strategy and mining preference (i=[0-n])
2. Number of miners N is assumption and B_t is determined by (dev or hon)/N
3. Every round t's fraction miner rate B_t has to be < 1/3
**Issues**: 
1. Assumption that each miner i and pool H_i sustain their mining preference from the first mining
-> Cannot consider strategy change

---
## 2025-12-19 (Fri)

**Completed**: 
1. Determined N as average mining pool share with over 1% of mining share, covering 99% of mining pools
 miner_id    pool_name      h_i
        0  Foundry USA 0.257422
        1      AntPool 0.206900
        2      Unknown 0.156465
        3       ViaBTC 0.107850
        4       F2Pool 0.102941
        5 Binance Pool 0.054452
        6    Mara Pool 0.036270
        7   SBI Crypto 0.016172
        8 Braiins Pool 0.015933
        9      BTC.com 0.013451
       10       Poolin 0.011105
       11       BTC M4 0.010603
       12       Kucoin 0.010435
2. Discount factor r = 0.99 (standard in agent learning)
3. Continue finding network delay delta 
**Findings**: 
**Issues**: 

## 2025-12-20 (Sat)

**Completed**: 
1. Delay delta setting (2 reference paper values, KIT v)
**Findings**: 
1. Information propagation in the Bitcoin network
Under 20KB, round trip delay is cause of delay (96%)
Over 20KB, delay from block itself is cause of delay
Block size >> Delay

2. On Scaling Decentralized Blockchains
Under 80KB, latency delay is cause of delay
Over 80KB, delay from block itself is cause of delay
Block size >> Delay
**Issues**: 

----
## 2025-12-21 (Sun)

**Completed**: 
>> Network delay confirmed (transmission delay in network theory)
1. Network delay calculation using KIT invstat.gpd data
   - Matched 99,575 (block, delay) data in exp time period
   - Calculated base_delay and kappa using linear regression
   - base_delay = 742 ms (intercept: delay when block size is 0 MB)
   - kappa = 26.40 ms/MB (slope: delay increase per 1 MB)
   - Formula: δt = 742 + 26.40 * B_MB

**Findings**: 

**Issues**: 

---

## 2025-12-22 (Sun)

**Completed**: 
1. Vi calculation implementation with forward accumulation
2. Proposal-based profit calculation implementation
   - Π_i^hon = p_i^hon · X_t - C_i
   - Π_i^dev = p_i^dev · (X_t + G_t) - C_i
   - p_i^hon = h_i * (1 - ρ(B))
   - p_i^dev = h_i * (1 - ρ^dev(B))
3. Orphan rate calculation using Poisson process
   - ρ(B) = 1 - exp(-λ * δ(B))
   - Based on: block generation is Poisson process (rate = λ)
   - δ(B) = block propagation delay (not block creation time)
4. Deviation propagation delay model
   - δ_dev(B) = δ_hon(B) + w
   - w = {0.5s, 1.0s, 2.0s} (withholding delay)
   - Rationale: Eyal & Sirer (Selfish Mining) - "seconds-scale is the core scale"
   - Log: [`data/raw/network_delay/deviation_delay_assumption.log`](data/raw/network_delay/deviation_delay_assumption.log)

**Findings**: 
1. Orphan rate is not a measured value, but defined as probability that competing block occurs during propagation delay
2. Block propagation is in seconds, while average block interval is 10 minutes
3. Strategic timing (=withholding) affects the "second-unit propagation interval"

**References**:
- **Eyal, I., & Sirer, E. G. (2014). Majority is not enough: Bitcoin mining is vulnerable. Communications of the ACM, 61(7), 95-102.**
  - Key statement: "seconds-scale is the core scale"
  - Block propagation is in seconds, average block interval is 10 minutes
  - Strategic timing (=withholding) has impact in "second-unit propagation interval"
  - URL: ittayeyal.github.io
  - This statement serves as a strong primary basis for setting withholding delay (w) in seconds

**Issues**: 

----
## 2025-12-23 (Tue)

**Completed**: 
**Findings**: 
1. G_t value determines the magnitude of pi_hon, pi_dev

**Issues**: 
1. F needs to be proportionally adjusted larger as block size increases (M is the same regardless of pi_hon or pi_dev)

---

## 2025-12-24 (Wed)
**Completed**: 
1. Ran simulation experiment with G_t=0 setting
2. Code review completed

**Findings**: 

**Issues**: 
1. Need to test with varying G_t values tomorrow

---
## 2025-12-25 (Thu)
**Completed**: 
**Findings**: 
1. G_t threshold that creates deviation
Therefore: G_t > ratio · X_t
Where: ratio = (ρ_dev - ρ_honest) / (1 - ρ_dev)

2. To make deviation easier, create a situation where G_t can be lowered. Minimize the right-hand side
3. Reduce dev, hon orphan rate (minimize w), maximize (1 - ρ_dev)
4. As a result, deviation occurs even with small G_t
5. Consistent with research results of "Majority is not enough", "On instability of Bitcoin without the Block reward" and formalized

** Summary
1. capacity ↑  ⇒  payload ↓  ⇒  δ ↓  ⇒  ρ_hon ↓ , ρ_dev ↓
ρ_dev − ρ_hon → 0  ⇒  incentive margin → 0  ⇒  deviation occurs even at G_t ≈ 0
cf) Incentive margin = G_t
**Issues**: 

---
## 2025-12-26 (Fri)
**Completed**: 
1. G_t threshold calculation and Vi comparison simulation
2. Threshold analysis based on actual block data
3. Analysis of relationship between rho_dev and threshold

**Findings**: 

### G_t Threshold and Deviation Condition Analysis Results
1. **Difference between Vi_dev and Vi_hon is similar to difference in each round i**: Vi threshold (25,046 sat) ≈ single round threshold (22,769 sat) × 1.10

2. **Per-round difference is significantly affected by additional gain G_t**: As G_t increases, Π_i^dev increases rapidly, making Vi_dev > Vi_honest

3. **Additional gain G_t = ratio × X_t**: Deviation favorable condition is G_t > ratio · X_t, where ratio = (ρ_dev - ρ_honest) / (1 - ρ_dev)

4. **ratio depends on rho_dev - rho_honest. In current experiment, G_t threshold is very small, creating an environment where deviation is easy**
   - **Actual values** (X_t average ≈ 27,256,474 sat):
     - Minimum threshold: B=4MB, w=0.5s → ratio = 0.000835 (0.0835%), G_t threshold = 22,769 sat
     - Maximum threshold: B=8MB, w=2.0s → ratio = 0.003346 (0.3346%), G_t threshold = 91,189 sat
     - If alpha=0.1, G_t = 2,725,647 sat (30~120x threshold) → **deviation almost always favorable**
   - Problem: ratio is very small at 0.08%~0.33% for all parameters, network is stable so rho_dev-rho_honest difference is small

5. **To raise G_t threshold, rho_dev must be increased, which requires larger w**
   - w increase → ρ_dev increase → ratio increase → G_t threshold increase
   - Example (B=1MB): w=0.5s (0.0835%, 22,554 sat) → w=50.0s (8.709%, 2,351,301 sat, about 104x)

6. **Need methods to increase w**: Currently using fixed values w = {0.5s, 1.0s, 2.0s}. Future research needed on dynamic determination mechanism based on network state

**Issues**: 


----
## 2025-12-28 (Sun)

**Completed**: 
**Findings**: 
- Final direction
1. Vi represents miner's profit and compares Vi_hon, Vi_dev at round i
2. G_t threshold determines which Vi is larger
3. Present G_t threshold formula and need to lower left side or raise right side (to prevent deviation)
4. Data confirms that after halving, network congestion decreases, space price drops, and G_t threshold decreases
5. It is certain that G_t threshold will decrease as block reward disappears with each halving, confirming that deviation is becoming easier
6. Even if G_t threshold decreases, lowering G_t (additional gain) itself is advantageous for reducing miner's incentive
7. Increase block size to reduce network congestion. Data confirms that network congestion space price has decreased
8. Lowering G_t itself risks losing potential honest miners as miner's profit decreases
9. Introduce delayed base fee to give time for blockchain to be confirmed and allow miners to mine with long-term perspective
10. Verify through empirical data?

**Issues**: 
1. F needs to be proportionally adjusted larger as block size increases (M is the same regardless of pi_hon or pi_dev)

---------------------------------------
St = {Ft, Mt, hi, δt}
Fee Ft = F_rate * B_MB * vB_per_MB
MEV Mt = Zero-inflated lognormal distribution (used Ethereum's data and made sample with MEV probability)
Hash share hi = average hash share throughout blockheight 790,000 to 890,000
Network delay δt = 


----
## 2025-12-29 (Mon)

**Completed**: 
1. Problem formulation done > empirical data and solution (created PDF)
2. Need to organize appendix table of contents and structure
(Vi calculation, Payoff function, State variable, etc.)
**Findings**: 
**Issues**: 

----
## 2025-12-30 (Tue)

**Completed**: 
1. Created all attachments for empirical data and solution, finished planning what to use
2. Organized and wrote appendix table of contents
(Vi calculation, Payoff function, State variable, etc.)
**Findings**: 
**Issues**: 
- Empirical data
F: 
Block utilization decreased after halving (decrease in demand)
> sat/vB decreased after halving (decrease in space price) > G_t threshold decreased

R:
X_t decreased due to block reward decrease after halving (miner profit decreased)
G_t threshold decreased

M:
MEV assumption is the same for honest or deviate

Conclusion: Did deviation become more likely as block audit score decreased?
Block audit score currently reacts strongly to one-time events (inscription, ordinal, or BTC price change), but we could see scores slightly increasing around the halving (2024-04).

-------
\section{Empirical Data Analysis of Bitcoin Network}
We have used blockchain.com's on-chain data of the Bitcoin network throughout block height 790,000 to 890,000 which is 2023.05.16 - 2025.03.29. Also, we figure out what would make $G_t$ threshold easier to be satisfied which incurs the deviation where $G_t\geq \mathrm{ratio}_i \cdot X_t$.
We found out $X_t$ has been significantly diminished after  

After halving, monthly fee (Median) decreases with time passes which means low F_t and low X_t in turn, representing easier deviation threshold G_t. (Fee decreases > threshold decreases)
/Monthly Fees graph

In general, it seems that each space in the chain got cheaper after halving in Sat/vB graph and the demand for using BTC got lowered through block utilization graph, following lowered fee. (Expanded that fee decreased, confirmed overall demand decreased through sat/vB, Block util)
/Sat/vB graph
/Block utilization

To check if deviation rate actually decreased as G_t decreased, we tracked the possibility of deviation through block audit ratio. Since there is no public data on deviation, we used mempool.space's block audit ratio. It is Actual profit to miner / expected mempool profit to miner, which indicates how close the behavior was to honest mining. Lower block audit ratio indicates higher possibility of processing txs not recorded in mempool and receiving private profit, which may indicate deviation.
Currently 3.125 BTC is given as block reward, and structural deviation due to low audit blocks from halving does not appear to be occurring. However, there were large fluctuations in January 2024 and January 2025 due to inscription, ordinal, and BTC price changes. These indicators can be seen as one-time events unrelated to deviation. The notable part is that scores slightly increased overall around the April 2024 halving.
/low audit blocks over time

As a result, we could not confirm a noticeable increase in deviation as G_t threshold decreased. However, since 3.125 BTC is currently given as block reward, the threshold has not been sufficiently lowered by low fees, and it is interpreted that receiving block reward is more advantageous than obtaining additional gain G_t.
