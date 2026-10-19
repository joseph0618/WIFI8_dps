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
## Variable-size, size-triggered DPS experiment

This separate experiment retains model labels `bianchi` (LC DCF), `dps` (size-triggered DPS), and `bianchi_hc` (HC DCF). A head-of-line payload **strictly greater than** the threshold sends EBSR, then waits for the AP's separate contention win and HC exchange. Smaller/equal packets contend for direct LC DATA/ACK. The threshold applies to individual payload bytes, not queue length, aggregate buffered bytes, or application-object size.

```powershell
py -B run.py --experiment size-threshold --model all --traffic both --duration 10 --runs 3
# Custom mixture and threshold:
py -B run.py --experiment size-threshold --payload-size-range-bytes 64 1500 --dps-threshold-bytes 512 --output results/my_size_experiment
# Threshold sensitivity, including always-DPS (0) and all-LC (1500) endpoints:
py -B run_size_sweep.py
py -B tests/check_size_threshold.py
```

Default results go to `results/size_threshold_comparison/`; the original comparison and analytical-validation outputs are retained. The output set matches `lc_hc_comparison` and adds `size_metrics.png`. `threshold_sensitivity/` contains a five-threshold sweep at N=5/20/50 with CSVs, plots, configuration and report.

The default payload size is **integer-uniform from 64 through 1500 bytes, inclusive**: each of the 1437 sizes has probability 1/1437. The mean is 782 bytes, and the default DPS threshold is 512 bytes. This is a controlled synthetic workload, not a measured Internet packet distribution or an ns-3 default. ns-3's [OnOff application](https://www.nsnam.org/doxygen/db/d5c/classns3_1_1_on_off_application.html) uses a configurable fixed packet size; its [application-specific models](https://www.nsnam.org/docs/models/html/applications.html) use different generators. Video-frame/object sizes must not be confused with individual packet payload sizes after segmentation. No standard DPS threshold or universally optimal threshold is claimed here.

Every model uses the same per-STA packet-size sequence for a given seed. Variable-size Poisson arrivals also use shared per-STA arrival streams; dropped packets still consume their size draw. Saturated policies may deliver different prefixes, and Poisson policies can drop different packets. Throughput sums actual delivered payload bits. Alongside packet PRR, outputs include byte PRR, payload-bit conservation totals, per-size generated/delivered counts for explicit size-list workloads, mean delivered size, and energy per delivered Mbit. Fixed-payload analytical predictions do not validate the mixed threshold policy.

For mixed DPS, the EBSR-to-HC-UL mean is divided by completed **DPS grants**, excluding direct LC deliveries. Raw counters separate direct and DPS deliveries. Collision duration follows the longest colliding frame, with each sender's actual airtime accounted for in energy. The abstraction still excludes aggregation, PHY errors, TCP/IP headers/behavior, and realistic application burst correlations.

## Saturated contention investigation

```powershell
py -B tests/check_diagnostics.py
py -B investigate_contention.py
py -B summarize_contention.py
```

The optional observer does not change random streams or access rules. Results go to `results/contention_investigation/`: fixed and uniform-payload comparisons, quarter-second collision windows, cumulative and warm-up-excluded collision ratios, report-state occupancy, equal-event LC/HC checks, contention/frame shares, and exact FIFO waiting-interval decomposition. The default is 54 saturated runs of 60 seconds, with three seeds at N=5/20/50 and a 5-second warm-up cutoff. Existing comparison outputs are retained.

`predict_dps_transient()` adds an event-index transient of the fixed-payload k-only closure, starting at k=0. It does not model retained backoff memory exactly or predict the uniform threshold-policy transient. See the expanded Markdown/LaTeX derivations and the investigation report for denominators and limits.
