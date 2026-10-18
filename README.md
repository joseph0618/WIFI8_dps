# UL trigger-based DPS simulator

DPS uses two separate contentions:

1. A STA wins a TXOP and transmits EBSR on LC. It then stops contending while waiting for AP service.
2. The AP wins a later TXOP and serves the oldest report: ICF (LC), switch up, ICR–DATA–ACK (HC), switch down to LC.

One packet is served per grant. Other STAs can win contention between the two TXOPs. The channel is serialized; there are no PHY errors or retry limits. Frame sizes, rates, switching times and power values are research assumptions.

## Run

```powershell
py -m pip install -r requirements.txt
py -B run.py --model all --traffic both --duration 30 --runs 5 --output results/lc_hc_comparison
py -B run.py --model dps --traffic poisson --hc-rate 10 --switch-up-us 100 --switch-down-us 100
py -B validate_dps.py
py -B tests/check_models.py
```

Models: `bianchi` is LC DCF, `dps` is LC contention with HC UL service, and `bianchi_hc` is HC DCF. `both` selects bianchi/dps; `all` selects all three. The former LC-only DPS implementation and `dps_hc` model selector have been removed.

## Metrics

- `collision_ratio`: collided contention transmission attempts / all contention transmission attempts. A collision involving three contenders adds three to both counts. Successful EBSR and AP ICF each count as one attempt; protected ICR/DATA/ACK do not contend separately. Idle slots are excluded. No attempts yields zero.
- `mean_transmissions_between_ebsr_and_hc_ul`: mean intervening contention transmission attempts after a successful EBSR and before its corresponding successful AP ICF. Both endpoints are excluded; collided attempts and other STAs' EBSRs/AP exchanges count. One protected exchange counts once, at its ICF. The value is zero if the corresponding AP wins immediately next. Only pairs whose DATA/ACK complete within the observation window enter the average; no completed pairs yields NaN. This is a network-wide attempt count, not a time or a frame count.
- `collision_probability` is retained as an alias of `collision_ratio`. Raw collision events and attempt counts are also exported.
- Delay and energy per delivered packet exclude undelivered packets from their denominator. PRR includes queued packets in generated traffic.

`run.py` exports raw CSV, per-seed means and standard errors, paired model comparisons, configuration/source hashes, and traffic/energy graphs. The new graph is `ebsr_to_hc_ul_transmissions.png`. Error bars show one standard error, not a 95% confidence interval. The new paired-count metric is measured in simulation; the k-only analytical approximation does not predict it.

## Folder

- `src/dps_sim/`: DCF baseline, DPS simulation and saturated analytical approximation.
- `run.py`: saturated/Poisson experiments and plots.
- `validate_dps.py`: independent saturated predictions versus fresh simulations.
- `tests/check_models.py`: protocol, paired-count, collision ratio, energy and analytical consistency checks.
- `MATHEMATICAL_ANALYSIS.md`: current analytical derivation and scope.
- `docs/background_analysis.md`: historical background, not current implementation documentation.
- `results/lc_hc_comparison/` and `results/dps_validation/`: regenerated current experiments; exact settings are in each config.json.

Existing outputs are overwritten in the chosen output directory. Use a separate directory to retain another experiment.