"""Independent saturated DPS semi-Markov approximation; no fitted inputs."""
import math
from .bianchi import SLOT, SIFS, DIFS, PROP_DELAY, H, PAYLOAD, ACK, analytical_collision_probability
from .simulation import ULTiming, LCPower, HCPower


def predict_dps(n=10, W=32, m=5, timing=None, power=None, hc_power=None):
    """k=reported STAs; local Bianchi decoupling ignores retained-counter history.

    Equal EBSR/ICF sizes required for the single collision-duration model.
    Returns independent predictions and embedded/wall-clock state occupancy.
    """
    if n < 1 or W < 2 or m < 0: raise ValueError('Invalid contention parameters')
    timing, power, hp = timing or ULTiming(), power or LCPower(), hc_power or HCPower()
    if timing.ebsr_bits != timing.icf_bits:
        raise ValueError('Analytical model currently requires equal EBSR/ICF lengths')
    rc = timing.control_rate_mbps
    rate = timing.hc_rate_mbps
    up, down = (timing.switch_up_us, timing.switch_down_us)
    te = timing.ebsr_bits/rc + DIFS + PROP_DELAY
    tu = (timing.icf_bits+timing.icr_bits+ACK)/rc + (H+PAYLOAD)/rate + 3*SIFS + DIFS + 4*PROP_DELAY + up + down
    tc_frame = timing.ebsr_bits/rc
    tc = tc_frame + DIFS + PROP_DELAY
    # Per-event all-STA rewards, including overhearing; AP energy excluded.
    def radio_frame(bits, rate, sta_sender=False, high=False):
        length = bits/rate
        if high:
            target = hp.tx_w if sta_sender else hp.rx_w
            return length*(target+(n-1)*power.rx_w)/1e6
        return length*((power.tx_w+(n-1)*power.rx_w) if sta_sender else n*power.rx_w)/1e6
    ee = radio_frame(timing.ebsr_bits,rc,True)+n*power.idle_w*(DIFS+PROP_DELAY)/1e6
    eu = radio_frame(timing.icf_bits,rc)+n*power.idle_w*(SIFS+PROP_DELAY)/1e6
    eu += radio_frame(timing.icr_bits,rc,True,True)+radio_frame(H+PAYLOAD,rate,True,True)+radio_frame(ACK,rc,False,True)
    eu += 2*(SIFS+PROP_DELAY)*((hp.idle_w+(n-1)*power.idle_w))/1e6
    eu += (up+down)*(hp.switch_w+(n-1)*power.idle_w)/1e6
    eu += n*power.idle_w*(DIFS+PROP_DELAY)/1e6
    states=[]
    for k in range(n+1):
        ns=n-k
        contenders=ns+int(k>0)
        p=analytical_collision_probability(contenders,W,m)
        tau=2/(W+1+W*p*sum((2*p)**j for j in range(m)))
        p0=(1-tau)**contenders
        isolated=tau*(1-tau)**(contenders-1)
        pe=ns*isolated
        pa=isolated if k else 0.
        pc=max(0.,1-p0-pe-pa)
        duration=p0*SLOT+pe*te+pa*tu+pc*tc
        # Unconditional expected number of STA transmissions in a collision.
        tx_collision=max(0.,ns*tau-pe)
        ec=tc_frame*(tx_collision*power.tx_w+(n*pc-tx_collision)*power.rx_w)/1e6
        ec+=pc*(DIFS+PROP_DELAY)*n*power.idle_w/1e6
        energy=p0*SLOT*n*power.idle_w/1e6+pe*ee+pa*eu+ec
        states.append(dict(k=k, tau=tau, p=p, p0=p0, pe=pe, pa=pa, pc=pc,
                           duration_us=duration, energy_j=energy,
                           attempts=contenders*tau, collided_attempts=contenders*tau-pe-pa))
    logs=[0.]
    for k in range(n): logs.append(logs[-1]+math.log(states[k]['pe'])-math.log(states[k+1]['pa']))
    weights=[math.exp(v-max(logs)) for v in logs]
    pi=[v/sum(weights) for v in weights]
    avg=lambda key: sum(prob*s[key] for prob,s in zip(pi,states))
    duration=avg('duration_us'); service=avg('pa'); collision=avg('pc')
    for prob,s in zip(pi,states):
        s['embedded_probability']=prob
        s['time_probability']=prob*s['duration_us']/duration
    return dict(throughput_mbps=PAYLOAD*service/duration,
                collision_ratio=max(0.,avg('collided_attempts'))/avg('attempts'),
                mean_channel_cost_ms=duration/service/1000,
                mean_sta_power_w=avg('energy_j')/(duration/1e6)/n,
                energy_per_delivered_packet_mj=avg('energy_j')/service*1000,
                idle_fraction=avg('p0')*SLOT/duration,
                success_fraction=(avg('pe')*te+service*tu)/duration,
                collision_fraction=collision*tc/duration,
                mean_reported_stas=sum(s['k']*s['time_probability'] for s in states),
                ebsr_service_balance=avg('pe')-service,
                states=states)


def predict_dps_transient(n=10, W=32, m=5, steps=10000, sample_every=20, timing=None):
    """Evolve the k-only closure from no pending reports in virtual-event index.

    This is not an exact wall-clock transient or a retained-backoff model.
    expected_elapsed_s sums expected holding times; it is not a deterministic
    map between event index and physical time for individual sample paths.
    """
    if steps < 0 or sample_every < 1:
        raise ValueError('Nonnegative steps and positive sample interval required')
    prediction = predict_dps(n=n, W=W, m=m, timing=timing)
    states = prediction['states']
    alpha = [1.] + [0.]*n
    cumulative_attempts = cumulative_collided = elapsed = 0.
    rows = []
    for step in range(steps+1):
        attempts = sum(a*s['attempts'] for a,s in zip(alpha,states))
        collided = sum(a*max(0.,s['collided_attempts']) for a,s in zip(alpha,states))
        if step % sample_every == 0 or step == steps:
            rows.append(dict(event_index=step, expected_elapsed_s=elapsed/1e6,
                expected_reported_stas=sum(k*a for k,a in enumerate(alpha)),
                instantaneous_collision_ratio=collided/attempts,
                cumulative_collision_ratio=cumulative_collided/cumulative_attempts if cumulative_attempts else math.nan,
                stationary_collision_ratio=prediction['collision_ratio']))
        if step == steps: break
        cumulative_attempts += attempts
        cumulative_collided += collided
        elapsed += sum(a*s['duration_us'] for a,s in zip(alpha,states))
        next_alpha = [0.]*(n+1)
        for k,(a,s) in enumerate(zip(alpha,states)):
            next_alpha[k] += a*(s['p0']+s['pc'])
            if k < n: next_alpha[k+1] += a*s['pe']
            if k > 0: next_alpha[k-1] += a*s['pa']
        alpha = next_alpha
    return rows
