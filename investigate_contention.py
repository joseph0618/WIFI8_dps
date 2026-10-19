"""Saturated collision transients and FIFO waiting-interval decomposition."""
import argparse,csv,hashlib,json,math,statistics,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from dps_sim.simulation import simulate_traffic,ULTiming
from dps_sim.diagnostics import ContentionDiagnostics
from dps_sim.analytical import predict_dps,predict_dps_transient
from dps_sim.bianchi import analytical_collision_probability
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

COMPONENTS=['success_EBSR','success_ICF','success_DATA','success_RTS',
            'collision_EBSR','collision_ICF','collision_DATA','collision_RTS']

def write(path,rows):
    if not rows: return
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def percentile(values,q):
    return sorted(values)[max(0,math.ceil(q*len(values))-1)] if values else math.nan

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--duration',type=float,default=60)
    p.add_argument('--warmup',type=float,default=5)
    p.add_argument('--runs',type=int,default=3)
    p.add_argument('--stations',type=int,nargs='+',default=[5,20,50])
    p.add_argument('--bin-seconds',type=float,default=.25)
    p.add_argument('--output',default='results/contention_investigation')
    args=p.parse_args()
    if args.duration<=args.warmup or args.warmup<0 or args.runs<2 or args.bin_seconds<=0:
        p.error('Use duration > warmup >= 0, >=2 seeds and positive bin width')
    # Aligned warm-up prevents partial-bin selection from shifting the cutoff.
    if abs(args.warmup/args.bin_seconds-round(args.warmup/args.bin_seconds))>1e-9:
        p.error('Warm-up must be a multiple of bin width')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    files=[Path(__file__),*Path(__file__).parent.glob('src/dps_sim/*.py')]
    config=dict(arguments=vars(args),traffic='saturated',W=32,m=5,timing=vars(ULTiming()),
        workloads={'fixed':'8184 payload bits; every packet uses DPS',
                   'uniform':'integer uniform [64,1500] bytes; DPS threshold >512 bytes'},
        notes='Optional observer only; no random draws or policy changes. Ratios use attempt denominators. Late windows are warm-up-excluded estimates, not a proof of stationarity.',
        source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in files})
    (out/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    raw=[];time=[];types=[];frames=[];pair_summary=[];samples=[];occupancy=[];prefixes={}
    for workload in ('fixed','uniform'):
        for n in args.stations:
            for model in ('bianchi','bianchi_hc','dps'):
                mode={'bianchi':'basic','bianchi_hc':'basic_hc',
                      'dps':'ul_dps' if workload=='fixed' else 'ul_dps_threshold'}[model]
                for seed in range(args.runs):
                    context=dict(workload=workload,stations=n,model=model,seed=seed)
                    d=ContentionDiagnostics(bin_seconds=args.bin_seconds)
                    r=simulate_traffic(mode=mode,n=n,seed=seed,duration_s=args.duration,diagnostics=d,
                        payload_size_range_bytes=[64,1500] if workload=='uniform' else None)
                    assert sum(d.attempts.values())==r['attempts']
                    assert sum(d.collided.values())==r['collided_attempts']
                    assert sum(x['intervening_attempts'] for x in d.pairs)==r['transmissions_between_ebsr_and_hc_ul']
                    rr=d.time_rows(args.duration)
                    late=[x for x in rr if x['start_s']>=args.warmup]
                    late_a=sum(x['attempts'] for x in late);late_c=sum(x['collided_attempts'] for x in late)
                    raw.append(dict(**context,**r,late_attempts=late_a,late_collided_attempts=late_c,
                        late_collision_ratio=late_c/late_a if late_a else math.nan,
                        late_collision_events_per_second=sum(x['collision_events'] for x in late)/(args.duration-args.warmup)))
                    time.extend(dict(**context,**row) for row in rr)
                    for role in ('EBSR','ICF','DATA','RTS'):
                        a=d.attempts[role];c=d.collided[role]
                        types.append(dict(**context,kind=role,attempts=a,collided_attempts=c,
                            attempt_share=a/r['attempts'] if r['attempts'] else math.nan,
                            within_kind_collision_ratio=c/a if a else math.nan,
                            collided_attempt_share=c/r['collided_attempts'] if r['collided_attempts'] else math.nan))
                    frame_counts=dict(EBSR=d.attempts['EBSR'],ICF=d.attempts['ICF'],RTS=d.attempts['RTS'],
                        ICR=d.frames['ICR'],CTS=d.frames['CTS'],ACK=d.frames['ACK'],
                        DATA=d.attempts['DATA']+max(0,d.frames['DATA']-d.components['success_DATA']))
                    total_frames=sum(frame_counts.values())
                    for name,count in frame_counts.items():
                        frames.append(dict(**context,frame=name,transmitted_frames=count,
                            frame_share=count/total_frames if total_frames else math.nan,
                            contention_attempts=d.attempts[name] if name in ('EBSR','ICF','DATA','RTS') else 0,
                            protected_frames=(max(0,count-d.attempts['DATA']) if name=='DATA' else count if name in ('ICR','ACK','CTS') else 0)))
                    for k,t in sorted(d.occupancy_us.items()):
                        occupancy.append(dict(**context,reported_stas=k,time_probability=t/(args.duration*1e6)))
                    for phase,pp in [('full',d.pairs),('after_warmup',[x for x in d.pairs if x['start_us']>=args.warmup*1e6])]:
                        if not pp: continue
                        row=dict(**context,phase=phase,completed_pairs=len(pp),
                            mean_reports_ahead=statistics.mean(x['reports_ahead'] for x in pp),
                            mean_intervening_attempts=statistics.mean(x['intervening_attempts'] for x in pp),
                            mean_intervening_events=statistics.mean(x['intervening_events'] for x in pp),
                            mean_wait_ms=statistics.mean(x['wait_ms'] for x in pp),
                            p50_attempts=percentile([x['intervening_attempts'] for x in pp],.5),
                            p95_attempts=percentile([x['intervening_attempts'] for x in pp],.95))
                        total=sum(x['intervening_attempts'] for x in pp)
                        for comp in COMPONENTS:
                            count=sum(x['attempt_'+comp] for x in pp)
                            row['total_'+comp]=count
                            row['mean_'+comp]=count/len(pp)
                            row['share_'+comp]=count/total if total else 0.
                        pair_summary.append(row)
                    if model=='dps':
                        for x in d.pairs:
                            assert x['reports_ahead']==x['attempt_success_ICF']
                        for x in d.pairs[:5]+d.pairs[-5:]: samples.append(dict(**context,**x))
                    if model!='dps':
                        prefixes[(workload,n,seed,model)]=(d.prefix,d.first_prefix_attempts,d.first_prefix_collided)
                print('Measured',workload,n,model,flush=True)
    invariance=[]
    for workload in ('fixed','uniform'):
        for n in args.stations:
            for seed in range(args.runs):
                a=prefixes[(workload,n,seed,'bianchi')];b=prefixes[(workload,n,seed,'bianchi_hc')]
                common=min(len(a[0]),len(b[0]));same=a[0][:common]==b[0][:common]
                assert same
                invariance.append(dict(workload=workload,stations=n,seed=seed,
                    compared_events=common,identical_sender_sequences=same,
                    lc_attempts=a[1],hc_attempts=b[1],lc_collided=a[2],hc_collided=b[2]))
    transient=[];spectral=[]
    for n in args.stations:
        prediction=predict_dps(n=n)
        transient.extend(dict(stations=n,**x) for x in predict_dps_transient(n=n,steps=20000,sample_every=20))
        Q=np.zeros((n+1,n+1))
        for k,s in enumerate(prediction['states']):
            Q[k,k]=s['p0']+s['pc']
            if k<n:Q[k,k+1]=s['pe']
            if k>0:Q[k,k-1]=s['pa']
        eig=np.linalg.eigvals(Q)
        spectral.append(dict(stations=n,min_real_eigenvalue=float(eig.real.min()),
            max_imaginary_abs=float(abs(eig.imag).max()),
            subdominant_abs_eigenvalue=float(sorted(abs(eig))[-2])))
    for filename,rows in [('simulation_raw.csv',raw),('time_series.csv',time),
        ('contention_breakdown.csv',types),('frame_breakdown.csv',frames),
        ('waiting_decomposition.csv',pair_summary),('waiting_examples.csv',samples),
        ('state_occupancy.csv',occupancy),('equal_event_check.csv',invariance),
        ('analytical_transient.csv',transient),('chain_spectrum.csv',spectral)]: write(out/filename,rows)
    # Pool attempts across seeds instead of averaging ratios with different denominators.
    for workload in ('fixed','uniform'):
        fig,axes=plt.subplots(2,len(args.stations),figsize=(5*len(args.stations),8),squeeze=False)
        for col,n in enumerate(args.stations):
            for model in ('bianchi','bianchi_hc','dps'):
                selected=[x for x in time if x['workload']==workload and x['stations']==n and x['model']==model]
                points=[]
                for start in sorted(set(x['start_s'] for x in selected)):
                    group=[x for x in selected if x['start_s']==start]
                    aa=sum(x['attempts'] for x in group);cc=sum(x['collided_attempts'] for x in group)
                    points.append((start,aa,cc))
                cumulative_a=cumulative_c=0;xx=[];yy=[];cumulative=[]
                for start,aa,cc in points:
                    cumulative_a+=aa;cumulative_c+=cc
                    xx.append(start+args.bin_seconds/2)
                    yy.append(cc/aa if aa else math.nan)
                    cumulative.append(cumulative_c/cumulative_a if cumulative_a else math.nan)
                axes[0,col].plot(xx,yy,label=model,alpha=.8)
                axes[1,col].plot(xx,cumulative,label=model)
            p=analytical_collision_probability(n)
            axes[1,col].axhline(p,color='gray',linestyle=':',label='DCF fixed point')
            if workload=='fixed':
                axes[1,col].axhline(predict_dps(n=n)['collision_ratio'],color='black',linestyle=':',label='DPS stationary closure')
            for row in (0,1):
                axes[row,col].set(xlabel='Elapsed time (s)',ylabel='Collision ratio per attempt',title=f'N={n}')
                axes[row,col].set_ylim(bottom=0);axes[row,col].grid(alpha=.3)
            axes[0,col].set_xlim(0,min(10,args.duration))
        axes[0,0].legend(fontsize=8);axes[1,0].legend(fontsize=7)
        fig.suptitle(f'{workload}: window ratios (first 10 s) and cumulative ratios; {args.runs} seeds pooled')
        fig.tight_layout();fig.savefig(out/f'{workload}_collision_transients.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,workload in zip(axes,('fixed','uniform')):
        bottom=np.zeros(len(args.stations))
        for comp in COMPONENTS:
            values=[]
            for n in args.stations:
                group=[r for r in pair_summary if r['workload']==workload and r['stations']==n and r['phase']=='after_warmup']
                values.append(sum(r['total_'+comp] for r in group)/sum(r['completed_pairs'] for r in group))
            if any(values): ax.bar([str(n) for n in args.stations],values,bottom=bottom,label=comp)
            bottom+=values
        ax.set(xlabel='Number of STAs',ylabel='Mean intervening contention attempts',title=workload)
        ax.legend(fontsize=7);ax.grid(axis='y',alpha=.3)
    fig.tight_layout();fig.savefig(out/'waiting_decomposition.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for n in args.stations:
        rr=[r for r in transient if r['stations']==n]
        axes[0].plot([r['event_index'] for r in rr],[r['instantaneous_collision_ratio'] for r in rr],label=f'N={n}')
        axes[1].plot([r['event_index'] for r in rr],[r['expected_reported_stas'] for r in rr],label=f'N={n}')
    axes[0].set(ylabel='Instantaneous expected collision ratio',xlabel='Virtual-event index')
    axes[1].set(ylabel='Expected reported STAs',xlabel='Virtual-event index')
    for ax in axes:ax.grid(alpha=.3);ax.legend()
    fig.suptitle('Transient k-only closure from k=0; not an exact retained-backoff transient')
    fig.tight_layout();fig.savefig(out/'analytical_transient.png',dpi=180);plt.close(fig)
    report=['# Saturated contention investigation','',
        f'{len(raw)} runs; {args.duration:g} s/run; {args.runs} seeds; late estimates exclude first {args.warmup:g} s.',
        'Fixed workload: 8184 payload bits, all packets use DPS. Uniform workload: payloads uniform integer [64,1500] bytes, DPS threshold >512 bytes.', '',
        '## 1. Why Bianchi HC and LC have similar collision ratios','',
        'Saturation keeps every baseline STA eligible. Both use the same W=32, m=5 and frozen-backoff rule. PHY rate changes event duration, not which zero counters transmit. Independent payload RNGs do not change this backoff coupling.',
        'All equal-event tests found identical sender/collision sequences for LC and HC. Fixed-duration windows contain different numbers of events, so finite-window ratios need not match exactly. Faster HC may have MORE collisions per second despite a similar collided-attempt ratio.',
        'DPS removes reported STAs from contention and adds only one AP contender. Its active population can be much smaller than N; HC rate alone does not imply that HC DCF must collide less than DPS.', '',
        '| Workload | STAs | Model | Full collision ratio | Late collision ratio | Late collision events/s |',
        '|---|---:|---|---:|---:|---:|']
    for workload in ('fixed','uniform'):
        for n in args.stations:
            for model in ('bianchi','bianchi_hc','dps'):
                g=[r for r in raw if r['workload']==workload and r['stations']==n and r['model']==model]
                full=sum(r['collided_attempts'] for r in g)/sum(r['attempts'] for r in g)
                late=sum(r['late_collided_attempts'] for r in g)/sum(r['late_attempts'] for r in g)
                events=statistics.mean(r['late_collision_events_per_second'] for r in g)
                report.append(f'| {workload} | {n} | {model} | {full:.5f} | {late:.5f} | {events:.2f} |')
    report += ['', '## 2. What the large EBSR-to-trigger count means','',
        'The metric counts NETWORK-WIDE contention attempts, not retries of the tagged STA. After EBSR, that STA cannot recontend. The AP serves every older report first; each such grant contributes a successful ICF. Newly served STAs can win another EBSR before the tagged grant. Collided senders add further attempts.',
        'For every completed sampled pair, successful intervening ICF count equals the number of reports ahead at EBSR exactly. ICR/DATA/ACK in those grants are protected response frames, not separate contention attempts.',
        'The following averages pool completed pairs whose EBSR starts after warm-up; endpoints are excluded. Horizon censoring remains: undelivered pairs are not included.', '',
        '| Workload | STAs | Reports ahead = successful ICFs | Successful EBSRs | Successful direct DATA | Collided attempts | Total attempts | Events | Wait ms |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for workload in ('fixed','uniform'):
        for n in args.stations:
            g=[r for r in pair_summary if r['workload']==workload and r['stations']==n and r['phase']=='after_warmup']
            total=sum(r['completed_pairs'] for r in g)
            mean=lambda key:sum(r[key]*r['completed_pairs'] for r in g)/total
            collision=sum(sum(r['total_collision_'+role] for role in ('EBSR','ICF','DATA','RTS')) for r in g)/total
            report.append(f"| {workload} | {n} | {mean('mean_reports_ahead'):.3f} | {mean('mean_success_EBSR'):.3f} | {mean('mean_success_DATA'):.3f} | {collision:.3f} | {mean('mean_intervening_attempts'):.3f} | {mean('mean_intervening_events'):.3f} | {mean('mean_wait_ms'):.3f} |")
    report += ['', '## 3. Ratios by contention and frame kind','',
        '`contention_breakdown.csv` separates EBSR, ICF, direct DATA and RTS: attempt_share uses ALL contention attempts, while within_kind_collision_ratio uses attempts of that kind only.',
        '`frame_breakdown.csv` includes ICR and ACK as protected transmissions. frame_share uses all transmitted frames, including collided initial frames. It must not be compared directly to attempt_share. Frame counts include frames starting before the horizon, including partial final frames.',
        '`waiting_decomposition.csv` gives the fraction and mean count of successful/collided attempts of every kind inside the waiting interval. `waiting_examples.csv` contains the first and last five completed pairs per DPS run.', '',
        '## 4. Transients and the mathematical approximation','',
        'Simulation window ratios can fluctuate; cumulative ratios usually smooth as samples accumulate. Neither fluctuating windows nor a finite plateau proves oscillation, divergence, or convergence to a unique steady value.',
        'The new analytical calculation evolves alpha(j+1)=alpha(j)Q from alpha(0) concentrated at k=0. It predicts an EVENT-INDEX transient using local equilibrium tau(k), not the exact transient of retained counters/stages. Instantaneous expected collision ratio is sum alpha*C / sum alpha*A; cumulative ratio uses sums over preceding event indices.',
        'The finite irreducible aperiodic birth-death closure converges to its stationary distribution. Its spectrum is recorded in chain_spectrum.csv; do not impose an oscillatory fit on the data. The expected elapsed-time column is not an exact wall-clock time change.',
        'The stationary fixed-payload closure is not applied to the mixed uniform threshold workload. No simulator statistics were fitted into analytical probabilities.', '',
        '## Reproduce','', '```powershell','py -B tests/check_diagnostics.py','py -B investigate_contention.py','```']
    (out/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('Saved investigation:',out,flush=True)

if __name__=='__main__': main()
