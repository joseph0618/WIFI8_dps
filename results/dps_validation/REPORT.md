# DPS analytical validation

45 fresh runs; 10 s/run, 3 seeds per configuration.
Predictions were calculated before simulation and contain no fitted statistics.
Scope: saturated, one packet/grant, equal EBSR/ICF size. ±SE is not a confidence interval.

| Metric | Maximum absolute relative error across scenarios |
|---|---:|
| throughput_mbps | 2.18% |
| collision_ratio | 19.53% |
| mean_sta_power_w | 0.91% |
| energy_per_delivered_packet_mj | 1.50% |
| idle_fraction | 7.98% |
| collision_fraction | 20.88% |

## Throughput prediction by scenario

| Scenario | Model | STAs | Predicted Mbps | Simulated Mbps | Error |
|---|---|---:|---:|---:|---:|
| baseline | dps | 5 | 2.4616 | 2.4309 | +1.26% |
| baseline | dps | 20 | 2.4629 | 2.4293 | +1.39% |
| baseline | dps | 50 | 2.4629 | 2.4230 | +1.65% |
| cw16 | dps | 5 | 2.7699 | 2.7204 | +1.82% |
| cw16 | dps | 20 | 2.7702 | 2.7157 | +2.01% |
| cw16 | dps | 50 | 2.7702 | 2.7111 | +2.18% |
| cw64 | dps | 5 | 1.9917 | 1.9852 | +0.33% |
| cw64 | dps | 20 | 1.9939 | 1.9849 | +0.45% |
| cw64 | dps | 50 | 1.9939 | 1.9811 | +0.65% |
| hc_rate5 | dps | 5 | 1.9565 | 1.9366 | +1.03% |
| hc_rate5 | dps | 20 | 1.9573 | 1.9358 | +1.11% |
| hc_rate5 | dps | 50 | 1.9573 | 1.9295 | +1.44% |
| long_switch | dps | 5 | 1.5970 | 1.5825 | +0.92% |
| long_switch | dps | 20 | 1.5975 | 1.5814 | +1.02% |
| long_switch | dps | 50 | 1.5975 | 1.5765 | +1.33% |

## Interpretation
The k-only chain uses local Bianchi equilibrium and ignores retained backoff history. Throughput agreement alone does not establish accurate collision dynamics.
State probabilities in analytical_states.csv are predictions, not validated occupancy measurements. Delay, PRR, Poisson, and PHY capability correctness are not validated by this experiment.
See ../../MATHEMATICAL_ANALYSIS.md for derivation, limitations and reproducible commands.

## Finite observation-window check
Additional 9 runs: baseline DPS, N=50, durations 10/30/100 s, starting from k=0.
These are full-window estimates, not warm-up-discarded steady-state samples.

| Duration s | Metric | Prediction | Simulation | Error |
|---:|---|---:|---:|---:|
| 10 | throughput_mbps | 2.4629 | 2.4230 | +1.65% |
| 10 | collision_ratio | 0.0796 | 0.0878 | -9.26% |
| 30 | throughput_mbps | 2.4629 | 2.4310 | +1.31% |
| 30 | collision_ratio | 0.0796 | 0.0793 | +0.46% |
| 100 | throughput_mbps | 2.4629 | 2.4336 | +1.21% |
| 100 | collision_ratio | 0.0796 | 0.0767 | +3.83% |
