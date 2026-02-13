# Deviation Threshold Ratio: Pre vs Post Halving

## 개요

`sim/plot_threshold.py`는 halving 전(height < 840,000)과 후(height ≥ 840,000) 구간별로 **ratio_i**를 각각 계산한다.  
ratio_i는 "G_t ≥ ratio_i × X_t 일 때 deviation 유인" 조건의 비율(약 0.17%)이다.

## 왜 Pre/Post ratio_i가 동일하게 나오는가

### 1. 계산 구조

- **지연**: δ = base_delay + κ × B_MB (ms)  
  - base_delay = 742 ms, κ = 26.40 ms/MB (KIT invstat.gpd 선형 회귀)
- **Orphan 확률**: ρ = 1 − exp(−λ × δ_sec), λ = 1/600 blocks/sec
- **Ratio**: ratio_i = (ρ_dev − ρ_honest) / (1 − ρ_dev)  
  - ρ_dev는 δ + w_sec(w=1s) 기준

ratio_i는 **구간별 평균 블록 크기 B_MB**에만 의존한다 (base_delay, κ, λ, w는 공통).

### 2. 데이터에서의 B_MB

| 구간   | 평균 B_MB (weight/4e6) |
|--------|-------------------------|
| Pre    | 0.9958 MB               |
| Post   | 0.9933 MB               |
| 차이   | 약 0.0025 MB (0.25%)    |

두 구간 모두 블록이 거의 풀(약 1 MB)에 가깝게 채워져 있어, **평균 블록 크기가 실질적으로 동일**하다.

### 3. 수치적 영향

- δ_pre ≈ (742 + 26.40×0.9958)/1000 ≈ 0.7683 s  
  δ_post ≈ (742 + 26.40×0.9933)/1000 ≈ 0.7682 s  
  → δ 차이 약 0.00007 s.
- λ×δ ≈ 0.00128 수준이라 ρ 차이는 10⁻⁵ 이하.
- 따라서 ratio_i 차이는 유효숫자 끝자리(약 10⁻¹⁷) 수준으로 **동일하다고 봐도 무방**하다.

### 4. 해석

- **방법상**: halving 전·후로 ratio를 나눠 구하는 것은 타당하다.
- **이번 데이터**: 전·후 구간 모두 블록 활용도가 비슷해 평균 B_MB가 거의 같고, 그 결과 **ratio_i가 같게 나오는 것이 자연스럽다**.
- **다른 데이터**: 블록 크기 분포가 전·후로 크게 다르면(예: 한쪽은 빈 블록 많음) ratio_i도 달라질 수 있다.

## 참고

- 네트워크 지연 파라미터: `data/raw/network_delay/kappa_calculation.log`, `deviation_delay_assumption.log`
- 스크립트: `sim/plot_threshold.py`
