# Size-triggered DPS data dictionary

All payload sizes and the DPS threshold are **payload bytes**, excluding the separate DATA header. A packet exactly equal to the threshold uses direct LC. All models share the configured size distribution; names are `bianchi` (LC), `dps` (size-triggered), and `bianchi_hc` (HC).

| Output | Meaning |
|---|---|
| `results.csv` | One row per traffic/model/station-count/seed simulation |
| `summary.csv` | Per-configuration arithmetic means, standard errors and finite-value run counts |
| `comparisons.csv` | Paired-seed differences between DPS and each baseline; candidate minus baseline |
| `config.json` | Arguments, payload probabilities, policy, rates, powers and source hashes |
| `traffic_metrics.png` | Delay, actual payload throughput, packet PRR and collision ratio |
| `saturated_metrics.png`, `poisson_metrics.png` | Separate traffic views; delay uses a symmetric logarithmic scale above 1 ms |
| `energy_metrics.png` | STA power, energy/packet, p95 delay, packet-delivery fairness |
| `size_metrics.png` | Delivered payload size, byte PRR, DPS delivery fraction and energy/Mbit |
| `ebsr_to_hc_ul_transmissions.png` | Intervening attempts for completed DPS grants only |
| `threshold_sensitivity/` | Five-threshold comparison, with raw/summary data, plots and configuration |

| Metric | Definition |
|---|---|
| `generated_payload_bits` | Sum of all generated payload bits, including drops and pending packets |
| `delivered_payload_bits` | Payload bits whose ACK completes in the window |
| `dropped_payload_bits` | Payload bits dropped at queue overflow |
| `pending_payload_bits` | Payload bits still queued or waiting for service at the end |
| `throughput_mbps` | Delivered payload bits / observation microseconds |
| `prr` | Delivered / generated packets |
| `byte_prr` | Delivered / generated payload bits |
| `direct_delivered` | Successful direct DCF deliveries; LC for size-triggered DPS, baseline capability otherwise |
| `dps_delivered`, `ap_exchanges` | Completed report/grant-based deliveries |
| `dps_delivery_fraction` | Completed DPS grants / all delivered packets; zero for both Bianchi baselines |
| `mean_delivered_payload_bytes` | Delivered bits / (8 times delivered packets) |
| `energy_per_delivered_mbit_j` | Total all-STA joules / delivered payload Mbit |
| `mean_sta_power_w` | Total all-STA joules / duration / number of STAs; AP excluded |
| `generated_payload_X_bytes_count` | Count of generated payloads of size X bytes, including drops; only exported for explicit size-list workloads |
| `delivered_payload_X_bytes_count` | Count of delivered payloads of size X bytes; only exported for explicit size-list workloads |
| `collision_ratio` | Collided contention attempts / total contention attempts; all colliding senders count |
| `mean_transmissions_between_ebsr_and_hc_ul` | Intervening contention attempts after successful EBSR and before corresponding successful ICF, both endpoints excluded; divided by completed DPS grants, not all deliveries |
| `jain_fairness` | Jain index of per-STA delivered packet counts, not byte throughput |

Packet and bit totals each satisfy generated = delivered + dropped + pending. Delay, payload means and energy per delivery use only delivered packets in their denominator; these can hide undelivered/backlogged traffic. NaN means the metric has no applicable completed sample. Means in summary.csv weight runs equally, not packets. Error bars show one standard error, not a confidence interval.

The default workload is integer-uniform on [64,1500] payload bytes, inclusive, with probability 1/1437 for each size and mean 782 bytes. It is a synthetic sensitivity workload. ns-3 has application-dependent packet-size behavior; it supplies no universal packet-size distribution that this experiment claims to reproduce. No transport segmentation, TCP dynamics, aggregation, or PHY loss is modeled. The fixed-payload analytical model does not predict this mixed policy.
