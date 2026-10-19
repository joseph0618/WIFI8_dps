# Saturated contention investigation

54 runs; 60 s/run; 3 seeds; late estimates exclude first 5 s.
Fixed workload: 8184 payload bits, all packets use DPS. Uniform workload: payloads uniform integer [64,1500] bytes, DPS threshold >512 bytes.

## 1. Why Bianchi HC and LC have similar collision ratios

Saturation keeps every baseline STA eligible. Both use the same W=32, m=5 and frozen-backoff rule. PHY rate changes event duration, not which zero counters transmit. Independent payload RNGs do not change this backoff coupling.
All equal-event tests found identical sender/collision sequences for LC and HC. Fixed-duration windows contain different numbers of events, so finite-window ratios need not match exactly. Faster HC may have MORE collisions per second despite a similar collided-attempt ratio.
DPS removes reported STAs from contention and adds only one AP contender. Its active population can be much smaller than N; HC rate alone does not imply that HC DCF must collide less than DPS.

| Workload | STAs | Model | Full collision ratio | Late collision ratio | Late collision events/s |
|---|---:|---|---:|---:|---:|
| fixed | 5 | bianchi | 0.17994 | 0.18054 | 10.56 |
| fixed | 5 | bianchi_hc | 0.17761 | 0.17757 | 65.68 |
| fixed | 5 | dps | 0.07455 | 0.07425 | 23.66 |
| fixed | 20 | bianchi | 0.39389 | 0.39105 | 25.27 |
| fixed | 20 | bianchi_hc | 0.39114 | 0.39078 | 173.48 |
| fixed | 20 | dps | 0.07573 | 0.07511 | 23.96 |
| fixed | 50 | bianchi | 0.53031 | 0.52284 | 36.16 |
| fixed | 50 | bianchi_hc | 0.52364 | 0.52265 | 257.85 |
| fixed | 50 | dps | 0.07737 | 0.07524 | 23.99 |
| uniform | 5 | bianchi | 0.18011 | 0.18072 | 13.04 |
| uniform | 5 | bianchi_hc | 0.17851 | 0.17848 | 75.10 |
| uniform | 5 | dps | 0.09897 | 0.09793 | 26.50 |
| uniform | 20 | bianchi | 0.39163 | 0.38923 | 30.05 |
| uniform | 20 | bianchi_hc | 0.39163 | 0.39130 | 195.30 |
| uniform | 20 | dps | 0.10369 | 0.10207 | 27.70 |
| uniform | 50 | bianchi | 0.53065 | 0.52447 | 42.04 |
| uniform | 50 | bianchi_hc | 0.52360 | 0.52275 | 285.61 |
| uniform | 50 | dps | 0.10610 | 0.10295 | 27.99 |

## 2. What the large EBSR-to-trigger count means

The metric counts NETWORK-WIDE contention attempts, not retries of the tagged STA. After EBSR, that STA cannot recontend. The AP serves every older report first; each such grant contributes a successful ICF. Newly served STAs can win another EBSR before the tagged grant. Collided senders add further attempts.
For every completed sampled pair, successful intervening ICF count equals the number of reports ahead at EBSR exactly. ICR/DATA/ACK in those grants are protected response frames, not separate contention attempts.
The following averages pool completed pairs whose EBSR starts after warm-up; endpoints are excluded. Horizon censoring remains: undelivered pairs are not included.

| Workload | STAs | Reports ahead = successful ICFs | Successful EBSRs | Successful direct DATA | Collided attempts | Total attempts | Events | Wait ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed | 5 | 3.179 | 3.179 | 0.000 | 0.487 | 6.845 | 6.600 | 11.716 |
| fixed | 20 | 18.173 | 18.173 | 0.000 | 2.926 | 39.271 | 37.796 | 62.111 |
| fixed | 50 | 48.172 | 48.172 | 0.000 | 7.813 | 104.157 | 100.217 | 162.957 |
| uniform | 5 | 2.727 | 2.727 | 1.242 | 0.687 | 7.383 | 7.037 | 14.552 |
| uniform | 20 | 17.674 | 17.674 | 7.992 | 4.853 | 48.193 | 45.735 | 88.729 |
| uniform | 50 | 47.671 | 47.670 | 21.476 | 13.342 | 130.159 | 123.397 | 237.154 |

## 3. Ratios by contention and frame kind

`contention_breakdown.csv` separates EBSR, ICF, direct DATA and RTS: attempt_share uses ALL contention attempts, while within_kind_collision_ratio uses attempts of that kind only.
`frame_breakdown.csv` includes ICR and ACK as protected transmissions. frame_share uses all transmitted frames, including collided initial frames. It must not be compared directly to attempt_share. Frame counts include frames starting before the horizon, including partial final frames.
`waiting_decomposition.csv` gives the fraction and mean count of successful/collided attempts of every kind inside the waiting interval. `waiting_examples.csv` contains the first and last five completed pairs per DPS run.

## 4. Transients and the mathematical approximation

Simulation window ratios can fluctuate; cumulative ratios usually smooth as samples accumulate. Neither fluctuating windows nor a finite plateau proves oscillation, divergence, or convergence to a unique steady value.
The new analytical calculation evolves alpha(j+1)=alpha(j)Q from alpha(0) concentrated at k=0. It predicts an EVENT-INDEX transient using local equilibrium tau(k), not the exact transient of retained counters/stages. Instantaneous expected collision ratio is sum alpha*C / sum alpha*A; cumulative ratio uses sums over preceding event indices.
The finite irreducible aperiodic birth-death closure converges to its stationary distribution. Its spectrum is recorded in chain_spectrum.csv; do not impose an oscillatory fit on the data. The expected elapsed-time column is not an exact wall-clock time change.
The stationary fixed-payload closure is not applied to the mixed uniform threshold workload. No simulator statistics were fitted into analytical probabilities.

## Reproduce

```powershell
py -B tests/check_diagnostics.py
py -B investigate_contention.py
```

## 5. Pooled contention and frame ratios

These tables pool counts across seeds for DPS at N=50, over the full observation window (including startup).
Within-kind collision probability divides collided attempts of that kind by all attempts of that kind; it is not a share of frames.

| Workload | Contending frame | Attempt share | Within-kind collision ratio |
|---|---|---:|---:|
| fixed | EBSR | 51.31% | 9.96% |
| fixed | ICF | 48.69% | 5.39% |
| fixed | DATA | 0.00% | not applicable |
| uniform | EBSR | 41.67% | 12.32% |
| uniform | ICF | 39.52% | 7.91% |
| uniform | DATA | 18.81% | 12.49% |

| Workload | Transmitted frame | Frame share (includes failed initial frames) | Access role |
|---|---|---:|---|
| fixed | EBSR | 21.54% | contends |
| fixed | ICF | 20.44% | contends |
| fixed | ICR | 19.34% | protected response |
| fixed | DATA | 19.34% | protected HC only |
| fixed | ACK | 19.34% | protected response |
| uniform | EBSR | 18.47% | contends |
| uniform | ICF | 17.51% | contends |
| uniform | ICR | 16.13% | protected response |
| uniform | DATA | 24.46% | direct LC contends; HC response protected |
| uniform | ACK | 23.42% | protected response |

The observed EBSR and ICF within-kind collision probabilities differ. The k-only analytical closure assigns identical attempt probabilities to eligible AP/STA contenders locally, so it does not capture this role asymmetry. Retained counters, retry stages and repeated AP service are omitted information; these measurements expose a limitation, rather than justify fitting a correction without a richer model.
All tested reduced-chain eigenvalues are positive and real (chain_spectrum.csv). Thus these parameter cases have no negative or complex eigenmodes that would generate alternating or rotational linear modes. Nonmonotonic transients and noisy sample windows can still occur.

Regenerate these pooled tables from saved CSVs with `py -B summarize_contention.py`.
