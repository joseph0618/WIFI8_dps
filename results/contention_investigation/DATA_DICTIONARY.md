# Investigation output definitions

The experiments are saturated, 60 seconds per run, three seeds, N=5/20/50. `fixed` means 8184 payload bits and always-DPS; `uniform` means integer-uniform 64–1500 payload bytes with the strictly-greater-than 512-byte DPS rule. Baseline model names are `bianchi` (LC) and `bianchi_hc` (HC).

| File | Contents / denominator |
|---|---|
| `simulation_raw.csv` | Full-run totals and collision ratios after a 5-second warm-up cutoff |
| `time_series.csv` | Quarter-second windows; collision counts assigned by contention attempt start time, occupancy integrated across time boundaries |
| `equal_event_check.csv` | Comparison of the first 1000 contender sets in paired LC/HC runs, plus their attempt/collision counts |
| `contention_breakdown.csv` | EBSR/ICF/direct-DATA/RTS attempts; attempt share divides by all attempts; within-kind collision ratio divides by that kind's attempts |
| `frame_breakdown.csv` | Transmitted-frame shares, including collided initial frames; protected responses are counted as frames, not as separate contentions |
| `waiting_decomposition.csv` | Completed-pair count and mean/summed contributions by successful/collided contention kind; `after_warmup` requires EBSR start >=5 s |
| `waiting_examples.csv` | First and last five completed report/grant pairs per DPS run; endpoints excluded |
| `state_occupancy.csv` | Measured fraction of channel observation time with k reported STAs, including time occupied by the in-progress exchange |
| `analytical_transient.csv` | Evolution of the reduced fixed-payload k-only closure in virtual-event index; expected elapsed time is not an exact time-domain mapping |
| `chain_spectrum.csv` | Eigenvalues summarized for the reduced analytical transition matrices |
| `pooled_ratios.json` | Largest-N per-role ratios pooled by count across seeds |
| `config.json` | Run arguments, source hashes used for execution and separate report-postprocessing provenance |

Window and cumulative plot ratios pool attempt counts across seeds; they do not average per-seed/window ratios equally. The warm-up-excluded ratios are finite estimates, not a stationarity proof. No fitted oscillatory function or empirical collision correction is used.

The waiting-attempt count is network-wide. It counts individual collided senders and other stations' successful contentions, not just attempts by the tagged STA. FIFO implies successful intervening ICFs = reports ahead at EBSR. In fixed DPS each such ICF has one protected ICR, DATA and ACK. In mixed DPS direct LC transmissions add DATA/ACK pairs. End-of-window uncompleted pairs remain excluded from waiting averages, so censoring persists.

Frame shares include actual frame starts before the horizon and may include partial last frames. Collision participants with unequal durations are counted once each, despite having multiple airtime segments. Frame shares are neither payload throughput shares nor channel airtime shares. The raw simulator airtime ledger remains available in simulation_raw.csv.
