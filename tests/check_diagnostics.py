"""Audit optional observers against existing totals and FIFO identities."""
import sys, math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dps_sim.simulation import simulate_traffic
from dps_sim.diagnostics import ContentionDiagnostics
from dps_sim.analytical import predict_dps_transient
for mode in ('basic','basic_hc','ul_dps','ul_dps_threshold'):
    for variable in (False,True):
        kwargs=dict(mode=mode,n=8,W=4,duration_s=.5)
        if variable: kwargs['payload_size_range_bytes']=[64,1500]
        d=ContentionDiagnostics(bin_seconds=.07,prefix_events=10)
        a=simulate_traffic(**kwargs)
        b=simulate_traffic(**kwargs,diagnostics=d)
        for key in a:
            assert a[key]==b[key] or (math.isnan(a[key]) and math.isnan(b[key])),(mode,key)
        assert sum(d.attempts.values())==a['attempts']
        assert sum(d.collided.values())==a['collided_attempts']
        assert d.collision_events==a['collision_events']
        assert abs(sum(d.occupancy_us.values())-5e5)<1e-6
        assert sum(x['attempts'] for x in d.time_rows(.5))==a['attempts']
        assert len(d.pairs)==a['ap_exchanges']
        assert sum(p['intervening_attempts'] for p in d.pairs)==a['transmissions_between_ebsr_and_hc_ul']
        for pair in d.pairs:
            assert pair['reports_ahead']==pair['attempt_success_ICF']
            assert pair['frame_ICF']==pair['frame_ICR']==pair['attempt_success_ICF']
            assert pair['frame_ACK']==pair['attempt_success_ICF']+pair['attempt_success_DATA']+pair['attempt_success_RTS']
            assert pair['intervening_attempts']==sum(v for k,v in pair.items() if k.startswith('attempt_'))
            assert pair['intervening_attempts']>=pair['intervening_events']
# Equal backoff trajectories at equal event index, independent of PHY airtime.
a=ContentionDiagnostics(prefix_events=100)
b=ContentionDiagnostics(prefix_events=100)
simulate_traffic(mode='basic',n=5,duration_s=5,diagnostics=a)
simulate_traffic(mode='basic_hc',n=5,duration_s=5,diagnostics=b)
assert a.prefix==b.prefix
assert a.first_prefix_attempts==b.first_prefix_attempts
assert a.first_prefix_collided==b.first_prefix_collided
r=predict_dps_transient(n=8,steps=10000,sample_every=100)
assert r[0]['expected_reported_stas']==0
assert abs(r[-1]['instantaneous_collision_ratio']-r[-1]['stationary_collision_ratio'])<1e-8
print('Observer invariance, contention/frame identities, FIFO waiting decomposition, equal-event LC/HC trajectories, and transient-chain convergence passed')
