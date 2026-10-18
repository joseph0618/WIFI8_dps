"""Independent DPS predictions versus fresh saturated simulations."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'src'))
import argparse,csv,json,math,statistics,hashlib
from dataclasses import asdict
from dps_sim.analytical import predict_dps
from dps_sim.simulation import simulate_traffic,ULTiming,LCPower,HCPower
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

METRICS=['throughput_mbps','collision_ratio','mean_sta_power_w',
         'energy_per_delivered_packet_mj','idle_fraction','collision_fraction']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=float,default=10)
    parser.add_argument('--runs',type=int,default=3)
    parser.add_argument('--stations',type=int,nargs='+',default=[5,20,50])
    parser.add_argument('--output',default='results/dps_validation')
    args=parser.parse_args()
    if args.runs<2 or args.duration<=0: parser.error('Use at least two runs and positive duration')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    scenarios=[('baseline',32,ULTiming()),('cw16',16,ULTiming()),('cw64',64,ULTiming()),
               ('hc_rate5',32,ULTiming(hc_rate_mbps=5)),
               ('long_switch',32,ULTiming(switch_up_us=1000,switch_down_us=1000))]
    lc,hp=LCPower(),HCPower()
    config=dict(arguments=vars(args),traffic='saturated',max_stage=5,lc_power=asdict(lc),hc_power=asdict(hp),
                scenarios=[dict(name=name,W=w,timing=asdict(t)) for name,w,t in scenarios],
                source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [Path(__file__),*Path('src/dps_sim').glob('*.py')]},
                note='Analytical predictions use only parameters, never simulated collision or occupancy statistics.')
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    raw=[];comparison=[];states=[]
    for name,w,t in scenarios:
        for model in ('dps',):

            for n in args.stations:
                prediction=predict_dps(n=n,W=w,m=5,timing=t,power=lc,hc_power=hp)
                for state in prediction['states']: states.append(dict(scenario=name,model=model,stations=n,**state))
                runs=[]
                for seed in range(args.runs):
                    r=simulate_traffic(mode='ul_dps',n=n,W=w,m=5,
                                       duration_s=args.duration,seed=seed,timing=t,power=lc,hc_power=hp)
                    r['idle_fraction']=r['idle_channel_seconds']/args.duration
                    r['collision_fraction']=r['collision_channel_seconds']/args.duration
                    runs.append(r);raw.append(dict(scenario=name,model=model,stations=n,seed=seed,**r))
                for metric in METRICS:
                    values=[r[metric] for r in runs];avg=statistics.mean(values)
                    se=statistics.stdev(values)/math.sqrt(len(values))
                    error=prediction[metric]-avg
                    comparison.append(dict(scenario=name,model=model,stations=n,metric=metric,
                        analytical=prediction[metric],simulation_mean=avg,simulation_se=se,
                        signed_error=error,relative_error_percent=100*error/avg if avg else math.nan))
            print('Validated',name,model,flush=True)
    for filename,data in [('simulation_raw.csv',raw),('comparison.csv',comparison),('analytical_states.csv',states)]:
        with (output/filename).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    fig,axes=plt.subplots(2,3,figsize=(16,9))
    for ax,metric in zip(axes.flat,METRICS):
        for model,color in [('dps','tab:blue')]:
            group=[r for r in comparison if r['scenario']=='baseline' and r['model']==model and r['metric']==metric]
            ax.plot([r['stations'] for r in group],[r['analytical'] for r in group],color=color,label=model+' analytical')
            ax.errorbar([r['stations'] for r in group],[r['simulation_mean'] for r in group],
                        yerr=[r['simulation_se'] for r in group],fmt='o',color=color,label=model+' simulation ±SE')
        ax.set(xlabel='Number of STAs',ylabel=metric);ax.grid(alpha=.3)
        # Use a zero baseline so small absolute differences are not magnified.
        ax.set_ylim(0, ax.get_ylim()[1] * 1.1)
    axes[0,0].legend(fontsize=8);fig.suptitle('Independent saturated DPS validation — baseline parameters')
    fig.tight_layout();fig.savefig(output/'validation.png',dpi=180);plt.close(fig)
    report=['# DPS analytical validation','',f'{len(raw)} fresh runs; {args.duration:g} s/run, {args.runs} seeds per configuration.',
            'Predictions were calculated before simulation and contain no fitted statistics.',
            'Scope: saturated, one packet/grant, equal EBSR/ICF size. ±SE is not a confidence interval.', '',
            '| Metric | Maximum absolute relative error across scenarios |', '|---|---:|']
    for metric in METRICS:
        errors=[abs(r['relative_error_percent']) for r in comparison if r['metric']==metric and math.isfinite(r['relative_error_percent'])]
        report.append(f'| {metric} | {max(errors):.2f}% |')
    report+=['','## Throughput prediction by scenario','','| Scenario | Model | STAs | Predicted Mbps | Simulated Mbps | Error |','|---|---|---:|---:|---:|---:|']
    for r in comparison:
        if r['metric']=='throughput_mbps':
            report.append(f"| {r['scenario']} | {r['model']} | {r['stations']} | {r['analytical']:.4f} | {r['simulation_mean']:.4f} | {r['relative_error_percent']:+.2f}% |")
    report+=['','## Interpretation',
             'The k-only chain uses local Bianchi equilibrium and ignores retained backoff history. Throughput agreement alone does not establish accurate collision dynamics.',
             'State probabilities in analytical_states.csv are predictions, not validated occupancy measurements. Delay, PRR, Poisson, and PHY capability correctness are not validated by this experiment.',
             'See ../../MATHEMATICAL_ANALYSIS.md for derivation, limitations and reproducible commands.']
    # Finite-window sensitivity of the largest baseline collision discrepancy.
    convergence=[];convergence_raw=[]
    for duration in (10,30,100):
        pred=predict_dps(n=50)
        rr=[simulate_traffic(n=50,duration_s=duration,seed=seed) for seed in range(args.runs)]
        for seed,r in enumerate(rr): convergence_raw.append(dict(seed=seed,stations=50,**r))
        for metric in ('throughput_mbps','collision_ratio'):
            values=[r[metric] for r in rr];avg=statistics.mean(values)
            convergence.append(dict(model='dps',stations=50,duration_s=duration,runs=args.runs,
                metric=metric,analytical=pred[metric],simulation_mean=avg,
                simulation_se=statistics.stdev(values)/math.sqrt(len(values)),
                relative_error_percent=100*(pred[metric]-avg)/avg))
    for filename,data in [('convergence.csv',convergence),('convergence_raw.csv',convergence_raw)]:
        with (output/filename).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    report+=['','## Finite observation-window check',
             f'Additional {3*args.runs} runs: baseline DPS, N=50, durations 10/30/100 s, starting from k=0.',
             'These are full-window estimates, not warm-up-discarded steady-state samples.', '',
             '| Duration s | Metric | Prediction | Simulation | Error |','|---:|---|---:|---:|---:|']
    for r in convergence:
        report.append(f"| {r['duration_s']} | {r['metric']} | {r['analytical']:.4f} | {r['simulation_mean']:.4f} | {r['relative_error_percent']:+.2f}% |")
    config['convergence']=dict(n=50,durations_s=[10,30,100],runs=args.runs,timing=asdict(ULTiming()),W=32,m=5)
    (output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (output/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(output/'REPORT.md')

if __name__=='__main__': main()
