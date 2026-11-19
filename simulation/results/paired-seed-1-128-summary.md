# Paired Cherenkov bootstrap

- Paired seeds: **128** (`1` through `128`).
- Baseline bridge success: **123/128**.
- Cherenkov bridge success: **126/128**.
- Mean step gain (baseline minus Cherenkov): **53.95 steps**; 95% paired-bootstrap CI **[41.06, 66.60]**.
- Cherenkov bridged earlier in **97/128** paired seeds.
- Mean occupied-cell gain: **107.91 cells**; 95% paired-bootstrap CI **[82.16, 132.88]**.
- Cherenkov used fewer occupied cells in **97/128** paired seeds.
- Bootstrap power estimate for the primary step endpoint: **n = 18** paired units for 80% power and **n = 22** for 90% power at two-sided alpha = 0.05.

The power estimate describes variance across simulated microstate seeds. A physical pilot replaces that variance estimate with dish-to-dish variance before fixing the material sample size.

## Decision rule

The Cherenkov condition supports the directional hypothesis when the paired-bootstrap confidence interval for baseline-minus-Cherenkov bridge steps lies entirely above zero. An interval containing zero retains the null. An interval entirely below zero reverses the hypothesized direction.
