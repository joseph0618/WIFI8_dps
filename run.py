import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
"""Run: py traffic_charts.py --duration 10 --arrival-rate 5"""
import argparse
import csv
import math
import statistics
import json
import hashlib
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dps_sim import bianchi, dps, ULTiming, LCPower, HCPower
from dps_sim.simulation import simulate_traffic


def main():
    parser = argparse.ArgumentParser(description="Bianchi-based UL access and LC/HC research model")
    parser.add_argument("--model", choices=["bianchi", "dps", "bianchi_hc", "both", "all"], default="all")
    parser.add_argument("--traffic", choices=["saturated", "poisson", "both"], default="both")
    parser.add_argument("--access", choices=["basic", "rts"], default="basic", help="Bianchi access method")
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--arrival-rate", type=float, default=5, help="Poisson packets/s per STA")
    parser.add_argument("--stations", type=int, nargs="+", default=[5, 10, 15, 20, 30, 50])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--runs", type=int, default=5, help="Independent seeds per configuration")
    parser.add_argument("--lc-rate", type=float, default=1, help="LC DATA rate, Mbps")
    parser.add_argument("--control-rate", type=float, default=1, help="Control rate, Mbps")
    parser.add_argument('--hc-rate', type=float, default=10)
    parser.add_argument('--switch-up-us', type=float, default=100)
    parser.add_argument('--switch-down-us', type=float, default=100)
    parser.add_argument('--queue-limit', type=int, default=1000)
    parser.add_argument('--window', type=int, default=32)
    parser.add_argument('--max-stage', type=int, default=5)
    for name, default in [('lc-idle-w', .1), ('lc-rx-w', .2), ('lc-tx-w', .5),
                          ('hc-idle-w', .3), ('hc-rx-w', .5), ('hc-tx-w', 1.), ('switch-w', .4)]:
        parser.add_argument('--'+name, type=float, default=default)
    parser.add_argument('--experiment', choices=['fixed', 'size-threshold'], default='fixed',
                        help='Keep original fixed-payload DPS or run variable-size threshold DPS')
    parser.add_argument('--payload-sizes-bytes', type=int, nargs='+', default=None,
                        help='Uniform discrete payload sizes for size-threshold experiment')
    parser.add_argument('--payload-size-range-bytes', type=int, nargs=2, metavar=('MIN', 'MAX'), default=None,
                        help='Inclusive uniform integer payload range; default 64 1500 in size-threshold experiment')
    parser.add_argument('--dps-threshold-bytes', type=int, default=512,
                        help='DPS triggers only when head payload size is strictly above this value')
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be at least 1')
    size_experiment = args.experiment == 'size-threshold'
    if args.dps_threshold_bytes < 0:
        parser.error('--dps-threshold-bytes must be nonnegative')
    if size_experiment:
        if args.payload_sizes_bytes is not None and args.payload_size_range_bytes is not None:
            parser.error('Choose a discrete size list or uniform range, not both')
        if args.payload_sizes_bytes is not None:
            if min(args.payload_sizes_bytes) <= 0:
                parser.error('--payload-sizes-bytes must be positive')
            payload_description = f'Uniform discrete payload sizes: {args.payload_sizes_bytes} bytes.'
        else:
            args.payload_size_range_bytes = args.payload_size_range_bytes or [64, 1500]
            low, high = args.payload_size_range_bytes
            if low <= 0 or low > high:
                parser.error('Payload range must satisfy 0 < MIN <= MAX')
            payload_description = f'Uniform integer payload sizes from {low} through {high} bytes, inclusive; each byte size has probability 1/{high-low+1}.' 
        if args.access != 'basic':
            parser.error('size-threshold comparison uses basic access for both Bianchi baselines')
    elif args.payload_sizes_bytes is not None or args.payload_size_range_bytes is not None:
        parser.error('--payload-sizes-bytes requires --experiment size-threshold')
    args.output = args.output or ('results/size_threshold_comparison' if size_experiment else 'results')
    output = Path(args.output)
    if size_experiment and output.resolve() in {
            Path('results/lc_hc_comparison').resolve(), Path('results/dps_validation').resolve()}:
        parser.error('Choose a separate output directory for size-threshold experiments')
    output.mkdir(parents=True, exist_ok=True)
    timing = ULTiming(data_rate_mbps=args.lc_rate, control_rate_mbps=args.control_rate,
                      hc_rate_mbps=args.hc_rate, switch_up_us=args.switch_up_us,
                      switch_down_us=args.switch_down_us)
    power = LCPower(args.lc_idle_w, args.lc_rx_w, args.lc_tx_w)
    hc_power = HCPower(args.hc_idle_w, args.hc_rx_w, args.hc_tx_w, args.switch_w)
    models = ['bianchi', 'dps', 'bianchi_hc'] if args.model == 'all' else (['bianchi', 'dps'] if args.model == 'both' else [args.model])
    if 'bianchi_hc' in models and args.access != 'basic':
        parser.error('bianchi_hc currently supports basic access only')
    metadata = dict(created_utc=datetime.now(timezone.utc).isoformat(), arguments=vars(args),
                    timing=asdict(timing), lc_power=asdict(power), hc_power=asdict(hc_power),
                    payload_probabilities=([1/len(args.payload_sizes_bytes)]*len(args.payload_sizes_bytes) if args.payload_sizes_bytes else None),
                    packet_size_policy=(payload_description if size_experiment
                                        else 'fixed 8184 payload bits'),
                    dps_policy=('payload bytes > threshold: EBSR and AP grant; otherwise direct LC DATA/ACK' if size_experiment
                                else 'every packet uses EBSR and AP grant'),
                    workload_pairing='independent contention/arrival/size RNGs; per-STA size streams shared across models',
                    realism='illustrative synthetic workload, not a measured or standard-mandated policy',
                    error_bars='one standard error across seeds; no confidence interval',
                    source_sha256={str(p.relative_to(Path(__file__).parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in [Path(__file__), *Path(__file__).parent.glob('src/dps_sim/*.py')]})
    (output/'config.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    rows = []
    summary = []
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    metrics = [("mean_delay_ms", "Mean delivered-packet delay (ms)"),
               ("throughput_mbps", "Aggregate throughput (Mbps)"),
               ("prr", "PRR (delivered / generated)"),
               ("collision_ratio", "Collision ratio (collided / attempted transmissions)")]
    for traffic in (("saturated", "poisson") if args.traffic == "both" else (args.traffic,)):
        for mode in models:
            results = []
            for n in args.stations:
                runs = []
                for seed in range(args.seed, args.seed + args.runs):
                    engine_mode = dict(bianchi=args.access, dps='ul_dps_threshold' if size_experiment else 'ul_dps', bianchi_hc='basic_hc')[mode]
                    result = simulate_traffic(mode=engine_mode, traffic=traffic, n=n,
                        duration_s=args.duration, arrival_rate_pps=args.arrival_rate,
                        queue_limit=args.queue_limit, W=args.window, m=args.max_stage,
                        seed=seed, timing=timing, power=power, hc_power=hc_power,
                        payload_sizes_bytes=args.payload_sizes_bytes,
                        payload_size_range_bytes=args.payload_size_range_bytes,
                        dps_threshold_bytes=args.dps_threshold_bytes)
                    runs.append(result)
                    rows.append(dict(traffic=traffic, model=mode, access=engine_mode, stations=n,
                        arrival_rate_pps=args.arrival_rate, lc_rate_mbps=args.lc_rate,
                        control_rate_mbps=args.control_rate, hc_rate_mbps=args.hc_rate, seed=seed, **result))
                aggregate = dict(traffic=traffic, model=mode, access=engine_mode, stations=n, runs=args.runs)
                for key in runs[0]:
                    values = [r[key] for r in runs if math.isfinite(r[key])]
                    aggregate[key] = statistics.mean(values) if values else math.nan
                    aggregate[key + '_se'] = (statistics.stdev(values)/math.sqrt(len(values))
                                              if len(values) > 1 else math.nan)
                    aggregate[key + '_valid_runs'] = len(values)
                results.append(aggregate)
                summary.append(aggregate)
            for ax, (metric, ylabel) in zip(axes.flat, metrics):
                ax.errorbar(args.stations, [r[metric] for r in results],
                        yerr=[r[metric + '_se'] for r in results] if args.runs > 1 else None,
                        marker="o", linestyle="-" if traffic == "saturated" else "--",
                        label=f"{mode}: {traffic}")
                ax.set_xlabel("Number of STAs")
                ax.set_ylabel(ylabel)
                ax.grid(alpha=0.3)
            print(f"Finished {mode}: {traffic}", flush=True)
    axes[1, 0].set_ylim(0, 1.05)
    axes[0, 0].legend(fontsize=8)
    experiment_title = (f"Size-triggered DPS (> {args.dps_threshold_bytes} B)" if size_experiment else "UL access and LC/HC research model")
    fig.suptitle(f"{experiment_title} — {args.duration:g} s; Poisson {args.arrival_rate:g} packets/s/STA")
    fig.tight_layout()
    fig.savefig(output / "traffic_metrics.png", dpi=180)
    plt.close(fig)
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (output / 'summary.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    # Separate traffic views keep high-load queueing from hiding HC delays.
    for traffic in sorted(set(r['traffic'] for r in summary)):
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        for model in models:
            group = [r for r in summary if r['traffic'] == traffic and r['model'] == model]
            for ax, (metric, label) in zip(axes.flat, metrics):
                ax.errorbar([r['stations'] for r in group], [r[metric] for r in group],
                            yerr=[r[metric+'_se'] for r in group] if args.runs>1 else None,
                            marker='o', label=model)
                if metric == 'mean_delay_ms': ax.set_yscale('symlog', linthresh=1)
                ax.set(xlabel='Number of STAs', ylabel=label)
                ax.grid(alpha=.3)
        axes[0,0].legend(fontsize=8)
        axes[1,0].set_ylim(0,1.05)
        fig.suptitle(f'{traffic} — delay uses a symmetric log scale above 1 ms')
        fig.tight_layout()
        fig.savefig(output/f'{traffic}_metrics.png',dpi=180)
        plt.close(fig)
    energy_metrics = [('mean_sta_power_w', 'Mean STA power (W)'),
                      ('energy_per_delivered_packet_mj', 'STA energy / delivered packet (mJ)'),
                      ('p95_delay_ms', 'Delivered delay p95 (ms)'),
                      ('jain_fairness', 'Jain packet-delivery fairness')]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for traffic in sorted(set(r['traffic'] for r in summary)):
        for model in models:
            group = [r for r in summary if r['traffic'] == traffic and r['model'] == model]
            for ax, (metric, label) in zip(axes.flat, energy_metrics):
                ax.plot([r['stations'] for r in group], [r[metric] for r in group], marker='o',
                        linestyle='-' if traffic == 'saturated' else '--', label=f'{model}: {traffic}')
                ax.set(xlabel='Number of STAs', ylabel=label)
                ax.grid(alpha=.3)
    axes[0,0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(output/'energy_metrics.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 5))
    for traffic in sorted(set(r['traffic'] for r in summary)):
        group = [r for r in summary if r['traffic'] == traffic and r['model'] == 'dps']
        if not group: continue
        metric = 'mean_transmissions_between_ebsr_and_hc_ul'
        ax.errorbar([r['stations'] for r in group], [r[metric] for r in group],
                    yerr=[r[metric+'_se'] for r in group] if args.runs > 1 else None,
                    marker='o', label=traffic)
    ax.set(xlabel='Number of STAs', ylabel='Mean intervening contention transmission attempts',
           title='Successful EBSR to corresponding HC UL trigger')
    ax.grid(alpha=.3)
    if any(r['model'] == 'dps' for r in summary): ax.legend()
    fig.tight_layout()
    fig.savefig(output/'ebsr_to_hc_ul_transmissions.png', dpi=180)
    plt.close(fig)
    comparisons = []
    for traffic in sorted(set(r['traffic'] for r in rows)):
        for n in args.stations:
            for baseline, candidate in [('bianchi','dps'), ('bianchi_hc','dps')]:
                left = {r['seed']:r for r in rows if r['traffic']==traffic and r['stations']==n and r['model']==baseline}
                right = {r['seed']:r for r in rows if r['traffic']==traffic and r['stations']==n and r['model']==candidate}
                for metric in ('throughput_mbps','mean_delay_ms','mean_sta_power_w','energy_per_delivered_packet_mj','prr','byte_prr','energy_per_delivered_mbit_j'):
                    pairs = [(left[k][metric],right[k][metric]) for k in left.keys() & right.keys()
                             if math.isfinite(left[k][metric]) and math.isfinite(right[k][metric])]
                    if not pairs: continue
                    differences = [b-a for a,b in pairs]
                    base = statistics.mean(a for a,b in pairs)
                    delta = statistics.mean(differences)
                    comparisons.append(dict(traffic=traffic, stations=n, baseline=baseline, candidate=candidate,
                        metric=metric, paired_runs=len(pairs), baseline_mean=base,
                        candidate_mean=statistics.mean(b for a,b in pairs), delta=delta,
                        delta_se=statistics.stdev(differences)/math.sqrt(len(pairs)) if len(pairs)>1 else math.nan,
                        relative_change_percent=100*delta/base if base else math.nan))
    if comparisons:
        with (output/'comparisons.csv').open('w',newline='',encoding='utf-8') as file:
            writer=csv.DictWriter(file,fieldnames=list(comparisons[0]));writer.writeheader();writer.writerows(comparisons)
    report = ['# Experiment results', '', 'All power, rates and transition delays are research assumptions; see config.json.',
              'Error bars are one standard error. Delivered delay excludes undelivered packets.', '',
              '| Traffic | Model | STAs | Mbps | Delay ms | PRR | W/STA | mJ/packet |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        report.append(f"| {r['traffic']} | {r['model']} | {r['stations']} | {r['throughput_mbps']:.4f} | {r['mean_delay_ms']:.3f} | {r['prr']:.4f} | {r['mean_sta_power_w']:.4f} | {r['energy_per_delivered_packet_mj']:.3f} |")
    if size_experiment:
        report[2:2] = [
            payload_description + ' Independent draw per generated packet.',
            f'DPS rule: head payload > {args.dps_threshold_bytes} bytes uses EBSR then AP ICF/ICR/DATA/ACK on HC; smaller/equal payloads use direct LC DATA/ACK.',
            'Models remain named bianchi (LC), dps (size-triggered), and bianchi_hc (HC).',
            'This is a synthetic size-based policy, not a validated claim of real deployment behavior.',
            'ns-3 has application-dependent traffic: [OnOff uses a configurable fixed packet size](https://www.nsnam.org/doxygen/db/d5c/classns3_1_1_on_off_application.html); [application-specific generators differ](https://www.nsnam.org/docs/models/html/applications.html). This uniform workload is not an ns-3 default.',
            'Jain fairness uses delivered packet counts per STA; it is not byte-throughput fairness when payload sizes vary.',
            'Size/arrival random streams are shared across models by seed. Saturated models deliver different prefixes; Poisson queue overflow may retain different packets.',
            'Throughput uses actual delivered payload bits. EBSR-to-HC-UL mean uses only completed DPS grants, excluding direct LC deliveries.',
            'Packet PRR and mean delay may hide packet-size selection effects; byte PRR and energy/Mbit are provided below.', '']
        report += ['', '## Size and route statistics', '',
                   '| Traffic | Model | STAs | Mean delivered bytes | Byte PRR | DPS delivery fraction | J/Mbit |',
                   '|---|---|---:|---:|---:|---:|---:|']
        for r in summary:
            report.append(f"| {r['traffic']} | {r['model']} | {r['stations']} | {r['mean_delivered_payload_bytes']:.2f} | {r['byte_prr']:.4f} | {r['dps_delivery_fraction']:.4f} | {r['energy_per_delivered_mbit_j']:.4f} |")
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        size_metrics = [('mean_delivered_payload_bytes', 'Mean delivered payload (bytes)'),
                        ('byte_prr', 'Byte PRR (delivered / generated bits)'),
                        ('dps_delivery_fraction', 'Fraction of deliveries using DPS grant'),
                        ('energy_per_delivered_mbit_j', 'All-STA energy / delivered Mbit (J)')]
        for traffic in sorted(set(r['traffic'] for r in summary)):
            for model in models:
                group = [r for r in summary if r['traffic'] == traffic and r['model'] == model]
                for ax, (metric, label) in zip(axes.flat, size_metrics):
                    ax.errorbar([r['stations'] for r in group], [r[metric] for r in group],
                                yerr=[r[metric+'_se'] for r in group] if args.runs > 1 else None,
                                marker='o', linestyle='-' if traffic == 'saturated' else '--',
                                label=f'{model}: {traffic}')
                    ax.set(xlabel='Number of STAs', ylabel=label)
                    ax.grid(alpha=.3)
        axes[0,0].legend(fontsize=7)
        axes[0,1].set_ylim(0,1.05)
        axes[1,0].set_ylim(0,1.05)
        fig.suptitle(experiment_title)
        fig.tight_layout()
        fig.savefig(output/'size_metrics.png', dpi=180)
        plt.close(fig)
    (output/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(f"Saved plots, raw data, summaries, paired comparisons and configuration in {output}")


if __name__ == "__main__":
    main()
