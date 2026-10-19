"""Summarize saved investigation counts without rerunning or fitting simulations."""
import argparse,csv,hashlib,json
from pathlib import Path

def read(path):
    with path.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='results/contention_investigation')
    args=p.parse_args();out=Path(args.output)
    kinds=read(out/'contention_breakdown.csv');frames=read(out/'frame_breakdown.csv')
    n=max(int(r['stations']) for r in kinds)
    report=(out/'REPORT.md').read_text(encoding='utf-8')
    marker='\n## 5. Pooled contention and frame ratios'
    report=report.split(marker)[0]
    lines=[marker,'',f'These tables pool counts across seeds for DPS at N={n}, over the full observation window (including startup).',
        'Within-kind collision probability divides collided attempts of that kind by all attempts of that kind; it is not a share of frames.', '',
        '| Workload | Contending frame | Attempt share | Within-kind collision ratio |',
        '|---|---|---:|---:|']
    stats={}
    for workload in ('fixed','uniform'):
        group=[r for r in kinds if r['workload']==workload and int(r['stations'])==n and r['model']=='dps']
        total=sum(float(r['attempts']) for r in group)
        stats[workload]={}
        for role in ('EBSR','ICF','DATA'):
            selected=[r for r in group if r['kind']==role]
            a=sum(float(r['attempts']) for r in selected)
            c=sum(float(r['collided_attempts']) for r in selected)
            stats[workload][role]=dict(attempt_share=a/total,collision_ratio=c/a if a else None)
            lines.append(f'| {workload} | {role} | {100*a/total:.2f}% | '+(f'{100*c/a:.2f}%' if a else 'not applicable')+' |')
    lines+=['','| Workload | Transmitted frame | Frame share (includes failed initial frames) | Access role |',
            '|---|---|---:|---|']
    for workload in ('fixed','uniform'):
        group=[r for r in frames if r['workload']==workload and int(r['stations'])==n and r['model']=='dps']
        total=sum(float(r['transmitted_frames']) for r in group)
        for name in ('EBSR','ICF','ICR','DATA','ACK'):
            count=sum(float(r['transmitted_frames']) for r in group if r['frame']==name)
            role={'EBSR':'contends','ICF':'contends','ICR':'protected response',
                  'DATA':'protected HC only' if workload=='fixed' else 'direct LC contends; HC response protected',
                  'ACK':'protected response'}[name]
            lines.append(f'| {workload} | {name} | {100*count/total:.2f}% | {role} |')
    lines += ['', 'The observed EBSR and ICF within-kind collision probabilities differ. The k-only analytical closure assigns identical attempt probabilities to eligible AP/STA contenders locally, so it does not capture this role asymmetry. Retained counters, retry stages and repeated AP service are omitted information; these measurements expose a limitation, rather than justify fitting a correction without a richer model.',
        'All tested reduced-chain eigenvalues are positive and real (chain_spectrum.csv). Thus these parameter cases have no negative or complex eigenmodes that would generate alternating or rotational linear modes. Nonmonotonic transients and noisy sample windows can still occur.', '',
        'Regenerate these pooled tables from saved CSVs with `py -B summarize_contention.py`.']
    (out/'REPORT.md').write_text(report+'\n'.join(lines)+'\n',encoding='utf-8')
    (out/'pooled_ratios.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    config=json.loads((out/'config.json').read_text(encoding='utf-8'))
    config['postprocessing']=dict(script=str(Path(__file__)),sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        note='Pooled count tables added from existing CSVs, without rerunning or modifying simulation data.')
    (out/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print('Added pooled contention/frame ratios to',out/'REPORT.md')
if __name__=='__main__': main()
