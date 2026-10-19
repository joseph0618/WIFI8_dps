"""Checks for variable payloads and the strictly-greater-than DPS size rule."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from dps_sim.simulation import simulate_traffic, ULTiming, LCPower, HCPower
from dps_sim.bianchi import H, ACK

# The optional extension preserves the fixed-size model at 1023 bytes = 8184 bits.
for mode in ('basic','basic_hc','rts','ul_dps'):
    a=simulate_traffic(mode=mode,n=4,duration_s=.4)
    b=simulate_traffic(mode=mode,n=4,duration_s=.4,payload_sizes_bytes=[1023])
    for key in ('delivered','attempts','collision_events','throughput_mbps','sta_energy_j','mean_delay_ms'):
        assert abs(a[key]-b[key])<1e-9,(mode,key)

# An equal-to-threshold packet stays LC; all-small reduces exactly to LC DCF.
for traffic in ('saturated','poisson'):
    kwargs=dict(n=5,duration_s=.5,traffic=traffic,arrival_rate_pps=300,
                payload_sizes_bytes=[64,256,512],seed=7)
    a=simulate_traffic(mode='basic',**kwargs)
    b=simulate_traffic(mode='ul_dps_threshold',dps_threshold_bytes=512,**kwargs)
    for key in ('delivered','attempts','throughput_mbps','sta_energy_j','mean_delay_ms'):
        assert abs(a[key]-b[key])<1e-9,(traffic,key)
    assert b['ebsr_successes']==b['dps_delivered']==b['hc_tx_sta_seconds']==0
    # Threshold zero sends every positive payload through the original DPS route.
    kwargs['payload_sizes_bytes']=[64,512,1500]
    a=simulate_traffic(mode='ul_dps',**kwargs)
    b=simulate_traffic(mode='ul_dps_threshold',dps_threshold_bytes=0,**kwargs)
    for key in ('delivered','attempts','throughput_mbps','sta_energy_j','mean_delay_ms'):
        assert abs(a[key]-b[key])<1e-9,(traffic,key)
    assert b['direct_delivered']==0 and b['dps_delivered']==b['delivered']

# Trace-based route and payload-throughput verification, including threshold equality.
trace=[]
r=simulate_traffic(mode='ul_dps_threshold',n=1,W=4,duration_s=1,seed=2,
                   payload_sizes_bytes=[64,512,1500],dps_threshold_bytes=512,trace=trace)
assert r['direct_delivered']>0 and r['dps_delivered']>0
bits=direct=granted=0
for e in trace:
    if e['frame']=='DATA':
        rate=10 if e['capability']=='HC' else 1
        payload=round((e['end_us']-e['start_us'])*rate-H)
        is_hc=e['capability']=='HC'
    if e['frame']=='ACK' and abs(e['end_us']-e['start_us']-ACK)<1e-8:
        assert is_hc==(payload>512*8),(payload,is_hc)
        bits+=payload
        granted+=is_hc
        direct+=not is_hc
assert bits==r['delivered_payload_bits']
assert bits/1e6==r['throughput_mbps']
assert direct==r['direct_delivered'] and granted==r['dps_delivered']
assert r['mean_transmissions_between_ebsr_and_hc_ul']==0

# Variable-length collisions, overflow, partial horizons, and energy conservation.
for mode in ('basic','basic_hc','ul_dps_threshold'):
    for traffic in ('saturated','poisson'):
        r=simulate_traffic(mode=mode,n=6,W=2,duration_s=.4,traffic=traffic,
                           arrival_rate_pps=500,queue_limit=2,
                           payload_sizes_bytes=[64,256,512,1024,1500],
                           power=LCPower(.4,.4,.4),hc_power=HCPower(.4,.4,.4,.4))
        assert r['generated']==r['delivered']+r['pending']+r['dropped']
        assert r['generated_payload_bits']==r['delivered_payload_bits']+r['pending_payload_bits']+r['dropped_payload_bits']
        assert r['direct_delivered']+r['dps_delivered']==r['delivered']
        assert r['dps_delivered']==r['ap_exchanges']
        assert abs(r['sta_energy_j']-6*.4*.4)<1e-9
        assert abs(sum(v for k,v in r.items() if k.endswith('_sta_seconds'))-6*.4)<1e-9
        assert sum(r[f'generated_payload_{b}_bytes_count'] for b in [64,256,512,1024,1500])==r['generated']
        assert sum(r[f'delivered_payload_{b}_bytes_count']*b*8 for b in [64,256,512,1024,1500])==r['delivered_payload_bits']
        assert r['collision_events']>0

# Exogenous Poisson workload is identical across access models, even with drops.
workloads=[]
for mode in ('basic','basic_hc','ul_dps_threshold'):
    r=simulate_traffic(mode=mode,traffic='poisson',n=5,duration_s=.4,arrival_rate_pps=1000,
                       queue_limit=1,payload_sizes_bytes=[64,512,1500],seed=3)
    workloads.append((r['generated'],r['generated_payload_bits'],
                      tuple(r[f'generated_payload_{b}_bytes_count'] for b in [64,512,1500])))
assert len(set(workloads))==1
for sizes in ([],[0],[1.5],[True]):
    try: simulate_traffic(payload_sizes_bytes=sizes)
    except ValueError: pass
    else: raise AssertionError(sizes)
print('Variable-size route boundaries, trace throughput, collision/energy ledgers, workload pairing and equivalence checks passed')

# Inclusive integer-uniform sampler: reproduce exact draws from its independent RNG.
import random
for mode in ('basic','basic_hc','ul_dps_threshold'):
    r=simulate_traffic(mode=mode,n=1,traffic='poisson',arrival_rate_pps=20000,
                       duration_s=1,queue_limit=1,seed=4,payload_size_range_bytes=[64,1500])
    rng=random.Random(4+2000003)
    sizes=[rng.randint(64,1500) for _ in range(r['generated'])]
    assert r['generated_payload_bits']==8*sum(sizes)
    assert abs(sum(sizes)/len(sizes)-782)<15
    assert r['generated_payload_bits']==r['delivered_payload_bits']+r['dropped_payload_bits']+r['pending_payload_bits']
for size in (64,512,1500):
    a=simulate_traffic(mode='ul_dps_threshold',n=3,duration_s=.3,payload_sizes_bytes=[size])
    b=simulate_traffic(mode='ul_dps_threshold',n=3,duration_s=.3,payload_size_range_bytes=[size,size])
    for key in ('delivered','attempts','throughput_mbps','sta_energy_j','dps_delivered'):
        assert abs(a[key]-b[key])<1e-9
for interval in ([1500,64],[0,1500],[64,1.5],[64]):
    try: simulate_traffic(payload_size_range_bytes=interval)
    except ValueError: pass
    else: raise AssertionError(interval)
print('Inclusive uniform-range sampler, mean, bit accounting and endpoint checks passed')
