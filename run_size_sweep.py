"""Threshold sensitivity for a controlled variable-size payload workload."""
import argparse, csv, hashlib, json, math, statistics, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from dps_sim.simulation import simulate_traffic, ULTiming
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

METRICS=[('throughput_mbps','Aggregate throughput (Mbps)'),
         ('mean_delay_ms','Mean delivered delay (ms)'),
         ('mean_sta_power_w','Mean STA power (W)'),
         ('energy_per_delivered_mbit_j','All-STA energy / delivered Mbit (J)')]

def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--duration',type=float,default=10)
    p.add_argument('--runs',type=int,default=3)
    p.add_argument('--stations',type=int,nargs='+',default=[5,20,50])
    p.add_argument('--thresholds',type=int,nargs='+',default=[0,256,512,1024,1500])
    p.add_argument('--payload-size-range-bytes',type=int,nargs=2,default=[64,1500])
    p.add_argument('--arrival-rate',type=float,default=5)
    p.add_argument('--output',default='results/size_threshold_comparison/threshold_sensitivity')
    args=p.parse_args()
    if args.runs<2 or args.duration<=0 or min(args.thresholds)<0 or min(args.payload_size_range_bytes)<=0 or args.payload_size_range_bytes[0]>args.payload_size_range_bytes[1]:
        p.error('Use >=2 runs, positive duration and payloads, nonnegative thresholds')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    source=[Path(__file__),*Path(__file__).parent.glob('src/dps_sim/*.py')]
    config=dict(arguments=vars(args),timing=vars(ULTiming()),
                payload_probability_per_byte_size=1/(args.payload_size_range_bytes[1]-args.payload_size_range_bytes[0]+1),
                note='Uniform integer payload range, not a universal ns-3 distribution. Strict payload > threshold rule; identical per-STA arrival/size streams across policies.',
                source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in source})
    (out/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    raw=[];summary=[]
    for traffic in ('saturated','poisson'):
        for n in args.stations:
            policies=[('bianchi','basic',None),('bianchi_hc','basic_hc',None)]
            policies += [('dps','ul_dps_threshold',t) for t in args.thresholds]
            for model,mode,threshold in policies:
                runs=[]
                for seed in range(args.runs):
                    r=simulate_traffic(mode=mode,traffic=traffic,n=n,duration_s=args.duration,
                        arrival_rate_pps=args.arrival_rate,seed=seed,
                        payload_size_range_bytes=args.payload_size_range_bytes,
                        dps_threshold_bytes=threshold or 0)
                    runs.append(r)
                    raw.append(dict(traffic=traffic,stations=n,model=model,
                                    threshold_bytes='' if threshold is None else threshold,seed=seed,**r))
                row=dict(traffic=traffic,stations=n,model=model,
                         threshold_bytes='' if threshold is None else threshold,runs=args.runs)
                for key in runs[0]:
                    vals=[r[key] for r in runs if math.isfinite(r[key])]
                    row[key]=statistics.mean(vals) if vals else math.nan
                    row[key+'_se']=statistics.stdev(vals)/math.sqrt(len(vals)) if len(vals)>1 else math.nan
                summary.append(row)
            print('Swept',traffic,'N=',n,flush=True)
    write_csv(out/'results.csv',raw);write_csv(out/'summary.csv',summary)
    for traffic in ('saturated','poisson'):
        fig,axes=plt.subplots(2,2,figsize=(13,9))
        for n in args.stations:
            group=[r for r in summary if r['traffic']==traffic and r['stations']==n and r['model']=='dps']
            for ax,(metric,label) in zip(axes.flat,METRICS):
                line=ax.errorbar([r['threshold_bytes'] for r in group],[r[metric] for r in group],
                    yerr=[r[metric+'_se'] for r in group],marker='o',label=f'dps: N={n}')
                color=line.lines[0].get_color()
                for model,style in [('bianchi','--'),('bianchi_hc',':')]:
                    r=next(r for r in summary if r['traffic']==traffic and r['stations']==n and r['model']==model)
                    ax.axhline(r[metric],color=color,linestyle=style,alpha=.7,label=f'{model}: N={n}')
                ax.set(xlabel='DPS payload threshold (bytes; strict >)',ylabel=label)
                ax.grid(alpha=.3)
        axes[0,0].legend(fontsize=7,ncol=2)
        fig.suptitle(f'Threshold sensitivity: {traffic}; uniform integer payload sizes')
        fig.tight_layout();fig.savefig(out/f'{traffic}_threshold_metrics.png',dpi=180);plt.close(fig)
    report=['# DPS threshold sensitivity','',config['note'],'',
            f'Payload range: {args.payload_size_range_bytes} bytes, inclusive integer uniform. {args.duration:g} s/run, {args.runs} seeds.',
            'Zero threshold routes all packets through DPS; threshold >= largest payload reduces to direct LC DCF.',
            'Only delivered packets enter delay and per-delivery metrics. Saturated runs are capacity tests, not equal offered-byte-rate tests.',
            'A threshold that looks best here is workload-dependent; no universal optimal threshold is claimed.','',
            '| Traffic | STAs | Model | Threshold bytes | Mbps | Delay ms | W/STA | J/Mbit | DPS fraction |',
            '|---|---:|---|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        report.append(f"| {r['traffic']} | {r['stations']} | {r['model']} | {r['threshold_bytes']} | {r['throughput_mbps']:.4f} | {r['mean_delay_ms']:.3f} | {r['mean_sta_power_w']:.4f} | {r['energy_per_delivered_mbit_j']:.4f} | {r['dps_delivery_fraction']:.4f} |")
    (out/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('Saved',out)
if __name__=='__main__': main()
