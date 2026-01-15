* Proposal
1. Initial thought was that without block reward, miner's ROI would decrease, leading to fewer honest miners and reduced network security
2. Thought that increasing block size and introducing base fee would reduce incentive for miners to deviate
3. Conducted experiments with actual on-chain data as below
4. During this period, the key factor determining Vi_honest and Vi_deviation was not block size but G_t (the gain obtainable through deviation)
5. G_t threshold = ratio × X_t (where ratio = (ρ_dev - ρ_honest) / (1 - ρ_dev)), and as w increases, ρ_dev increases, raising ratio and G_t threshold
6. Present G_t threshold formula in the thesis, and show that increasing w is the key factor in raising G_t threshold to make deviation harder


* Experiment Information
Period: 2023.05.16(height 790,000) - 2025.03.29(height 890,000)
Miner: 13 pools (average hash rate share by pool during the period)
Miner's profit: hash rate proportion(F + M) - C
F (tx Fee): fee_rate (sat/vB) × block_capacity_vB from actual block data
M (MEV): Zero-inflated Lognormal distribution samples (based on Ethereum research, adjusted for Bitcoin)
Cost: CBECI "Cost to Mine One BTC" × block reward → distributed proportionally by miner share
Vi = Σ γ^t × Πi(St, ai) (discounted sum of miner's profit in every round)

Test whether Vi_honest > Vi_deviation and the network satisfies BFT threshold which is dev < 1/3.


Direction:
1. Block height 790,000 - 890,000 block data experiment
2. Set Vi_hon, Vi_dev and compare
3. Vi_hon - Vi_dev is similar with difference in i round
4. Incentive margin G_t is determined by ratio of (ρ_dev - ρ_honest) / (1 - ρ_dev)
5. Setting higher rho_dev is necessary to higher G_t
6. Withholding time w determines ρ_dev, which affects G_t threshold ratio; higher w → higher G_t threshold → harder deviation
