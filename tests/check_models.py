"""Protocol, contention metric, horizon and analytical consistency checks."""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dps_sim.simulation import simulate_traffic, ULTiming, LCPower, HCPower
from dps_sim.analytical import predict_dps
from dps_sim import dps

for mode in ('basic', 'rts', 'ul_dps', 'basic_hc'):
    for traffic in ('saturated', 'poisson'):
        r = simulate_traffic(mode=mode, traffic=traffic, n=5, duration_s=.5,
                             arrival_rate_pps=50)
        assert r['generated'] == r['delivered'] + r['dropped'] + r['pending']
        assert 0 <= r['collision_ratio'] <= 1
        assert r['collision_ratio'] == r['collided_attempts'] / r['attempts']
        assert abs(sum(v for k,v in r.items() if k.endswith('_sta_seconds')) - 2.5) < 1e-9
        assert abs(sum(r[k] for k in ('idle_channel_seconds', 'success_channel_seconds', 'collision_channel_seconds'))-.5) < 1e-9
        assert abs(r['sta_energy_j']-r['lc_energy_j']-r['hc_energy_j']) < 1e-9

# Independently reconstruct paired EBSR/UL counts from the frame trace.
for n in (1, 8):
    trace = []
    r = dps.simulate(n=n, duration_s=1, W=4, trace=trace)
    attempts = 0
    pending = {}
    expected = []
    for e in trace:
        if e['frame'] in ('EBSR', 'ICF', 'COLLISION'):
            if e['frame'] == 'EBSR':
                pending[e['senders'][0]] = attempts + 1
            elif e['frame'] == 'ICF':
                target = e['hc_sta']  # ICF is LC; target is recovered at ICR below.
                trigger_attempts = attempts
            attempts += len(e['senders'])
        elif e['frame'] == 'ICR':
            target = e['senders'][0]
        elif e['frame'] == 'ACK' and e['end_us'] <= 1e6:
            expected.append(trigger_attempts - pending.pop(target))
    assert len(expected) == r['delivered']
    assert sum(expected) == r['transmissions_between_ebsr_and_hc_ul']
    assert r['mean_transmissions_between_ebsr_and_hc_ul'] == sum(expected)/len(expected)
    if n == 1:
        frames = [e['frame'] for e in trace if e['frame'] != 'IDLE']
        assert frames[:7] == ['EBSR','ICF','SWITCH_UP','ICR','DATA','ACK','SWITCH_DOWN']
        assert all(e['capability']=='HC' for e in trace if e['frame'] in ('ICR','DATA','ACK'))
        assert expected == [0]*len(expected)
        ack = next(e['end_us'] for e in trace if e['frame']=='ACK')
        short = dps.simulate(n=1, W=4, duration_s=(ack+1)/1e6)
        assert short['delivered'] == 1

zero = dps.simulate(traffic='poisson', arrival_rate_pps=0, duration_s=.1)
assert zero['collision_ratio'] == 0
assert math.isnan(zero['mean_transmissions_between_ebsr_and_hc_ul'])
for n in (1, 5, 20, 50):
    p = predict_dps(n=n)
    assert 0 <= p['collision_ratio'] <= 1
    assert abs(sum(s['embedded_probability'] for s in p['states'])-1) < 1e-12
    assert abs(sum(s['time_probability'] for s in p['states'])-1) < 1e-12
    assert abs(p['ebsr_service_balance']) < 1e-12
    assert abs(p['idle_fraction']+p['success_fraction']+p['collision_fraction']-1) < 1e-12
    uniform = predict_dps(n=n, power=LCPower(.4,.4,.4), hc_power=HCPower(.4,.4,.4,.4))
    assert abs(uniform['mean_sta_power_w']-.4) < 1e-12
assert predict_dps(n=1)['collision_ratio'] < 1e-12
assert predict_dps(n=10)['throughput_mbps'] > predict_dps(n=10, timing=ULTiming(switch_up_us=1000, switch_down_us=1000))['throughput_mbps']
print('Protocol, paired transmission counts, collision ratio, energy and analytical checks passed')
