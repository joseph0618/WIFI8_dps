"""Bianchi-based UL DPS and traffic simulator; see README.md."""
import random
import math
from collections import deque
from dataclasses import dataclass
from .bianchi import (SLOT, SIFS, DIFS, PROP_DELAY, DATA_RATE, PHY_HEADER,
                     H, PAYLOAD, ACK, RTS, CTS)


@dataclass(frozen=True)
class ULTiming:
    """Prototype frame lengths in bits (including PHY); replace with your spec.

    Single shared channel, no PHY errors; LC is represented by data_rate_mbps.
    DPS switches the granted STA after ICF, reverting after ACK.
    These parameters are research assumptions, not standard-specified timings.
    """
    ebsr_bits: int = PHY_HEADER + 160
    icf_bits: int = PHY_HEADER + 160
    icr_bits: int = PHY_HEADER + 112
    data_rate_mbps: float = DATA_RATE
    control_rate_mbps: float = DATA_RATE
    hc_rate_mbps: float = 10.0
    switch_up_us: float = 100.0
    switch_down_us: float = 100.0


@dataclass(frozen=True)
class LCPower:
    """Illustrative watts per STA, not measured or standard-specified values."""
    idle_w: float = 0.10
    rx_w: float = 0.20
    tx_w: float = 0.50


@dataclass(frozen=True)
class HCPower:
    idle_w: float = 0.30
    rx_w: float = 0.50
    tx_w: float = 1.00
    switch_w: float = 0.40


def simulate_traffic(mode="ul_dps", traffic="saturated", n=10, W=32, m=5,
                     duration_s=10.0, arrival_rate_pps=5.0, queue_limit=1000,
                     seed=0, timing=None, power=None, trace=None, hc_power=None):
    """Packet-level extension of the original frozen-backoff simulator.

    UL prototype: STA contention -> EBSR -> AP contention -> ICF/ICR/DATA/ACK.
    AP serves reported STAs FIFO, one packet per grant. STA cannot recontend
    until that packet completes. All contenders share a serialized channel.
    Delay is arrival-to-ACK for delivered packets. PRR is delivered/generated
    during a fixed observation window, including queued packets at its end.
    Saturated traffic generates a replacement packet immediately after delivery.
    No retry limit or PHY loss; drops occur only on Poisson queue overflow.
    """
    timing = timing or ULTiming()
    power = power or LCPower()
    hc_power = hc_power or HCPower()
    hc_mode = mode in ("ul_dps", "basic_hc")
    ul_mode = mode == "ul_dps"
    if any(not math.isfinite(v) or v < 0 for v in
           (hc_power.idle_w, hc_power.rx_w, hc_power.tx_w, hc_power.switch_w,
            timing.switch_up_us, timing.switch_down_us)) or not math.isfinite(timing.hc_rate_mbps) or timing.hc_rate_mbps <= 0:
        raise ValueError("Invalid HC power, rate or transition timing")
    if any(not math.isfinite(v) or v < 0 for v in
           (power.idle_w, power.rx_w, power.tx_w)):
        raise ValueError("Power must be finite and nonnegative")
    for value in (n, W, m, queue_limit):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("Station, window, stage and queue limits must be integers")
    if mode not in ("basic", "rts", "ul_dps", "basic_hc") or traffic not in ("saturated", "poisson"):
        raise ValueError("Invalid mode or traffic")
    if (n < 1 or W < 2 or m < 0 or queue_limit < 1 or duration_s <= 0
            or arrival_rate_pps < 0 or timing.data_rate_mbps <= 0
            or timing.control_rate_mbps <= 0
            or not all(math.isfinite(x) for x in (duration_s, arrival_rate_pps,
                       timing.data_rate_mbps, timing.control_rate_mbps))
            or min(timing.ebsr_bits, timing.icf_bits, timing.icr_bits) <= 0):
        raise ValueError("Invalid station, backoff, queue, traffic, or timing parameter")
    rng = random.Random(seed)
    arrivals_rng = random.Random(seed + 1000003)
    end = duration_s * 1e6
    queues = [deque() for _ in range(n)]
    stage = [0] * (n + 1)
    backoff = [None] * (n + 1)
    reported = set()
    grants = deque()
    next_arrival = [math.inf] * n
    generated = delivered = dropped = attempts = collided = collision_events = 0
    reports = ap_exchanges = 0
    report_attempts = {}
    transmissions_between = 0
    total_delay = now = 0.0
    interval_rate = arrival_rate_pps / 1e6
    radio_us = dict(idle=0.0, rx=0.0, tx=0.0)
    hc_radio_us = dict(idle=0.0, rx=0.0, tx=0.0, switch=0.0)
    ledger = dict(idle=0.0, success=0.0, collision=0.0)
    frame_airtime = {}
    switch_ups = switch_downs = 0
    per_sta_delivered = [0] * n
    delays = []

    def account(start, phases, category='idle', target=None):
        nonlocal switch_ups, switch_downs
        cursor = start
        for phase in phases:
            name, length, senders = phase[:3]
            capability = 'HC' if mode == 'basic_hc' else (phase[3] if len(phase) > 3 else 'LC')
            observed = max(0.0, min(length, end - cursor))
            ledger[category] += observed
            frame_airtime[name] = frame_airtime.get(name, 0.0) + observed
            high = {target} if capability in ('HC', 'SWITCH') and target is not None else set()
            if mode == 'basic_hc':
                high = set(range(n))
            tx = {i for i in senders if i < n}
            for activity, members in [('tx', tx), ('rx', set(range(n))-tx if senders else set()),
                                      ('idle', set(range(n))-tx if not senders else set())]:
                radio_us[activity] += len(members-high) * observed
                if capability != 'SWITCH':
                    hc_radio_us[activity] += len(members & high) * observed
            if capability == 'SWITCH':
                hc_radio_us['switch'] += len(high) * observed
                if observed and name == 'SWITCH_UP': switch_ups += 1
                if observed and name == 'SWITCH_DOWN': switch_downs += 1
            if trace is not None and observed:
                trace.append(dict(start_us=cursor, end_us=cursor+observed, frame=name,
                                  senders=list(senders), capability=capability,
                                  hc_sta=sorted(high), waiting_for_ap=sorted(reported)))
            cursor += length

    def frame(name, bits, sender, rate=None, capability='LC'):
        return (name, bits / (rate or control), [sender], capability)

    def gap(length, capability='LC'):
        return ('IDLE', length, [], capability)

    def activate(i):
        if backoff[i] is None:
            stage[i] = 0
            backoff[i] = rng.randrange(W)

    def collect_arrivals(until):
        nonlocal generated, dropped
        if traffic != "poisson" or interval_rate == 0:
            return
        for i in range(n):
            while next_arrival[i] <= until:
                generated += 1
                if len(queues[i]) < queue_limit:
                    queues[i].append(next_arrival[i])
                    if i not in reported:
                        activate(i)
                else:
                    dropped += 1
                next_arrival[i] += arrivals_rng.expovariate(interval_rate)

    if traffic == "saturated":
        for i in range(n):
            queues[i].append(0.0)
            generated += 1
            activate(i)
    elif interval_rate:
        next_arrival = [arrivals_rng.expovariate(interval_rate) for _ in range(n)]

    control = timing.control_rate_mbps
    data = timing.hc_rate_mbps if hc_mode else timing.data_rate_mbps
    basic_success = (H + PAYLOAD) / data + ACK / control + SIFS + DIFS + 2 * PROP_DELAY
    rts_success = basic_success + (RTS + CTS) / control + 2 * SIFS + 2 * PROP_DELAY
    ebsr_success = timing.ebsr_bits / control + DIFS + PROP_DELAY
    ul_success = ((timing.icf_bits + timing.icr_bits + ACK) / control
                  + (H + PAYLOAD) / data + 3 * SIFS + DIFS + 4 * PROP_DELAY)

    while now < end:
        active = [i for i, b in enumerate(backoff) if b is not None]
        if not active:
            next_time = min(end, min(next_arrival))
            account(now, [gap(next_time - now)])
            now = next_time
            collect_arrivals(now)
            continue
        transmitting = [i for i in active if backoff[i] == 0]
        if not transmitting:
            if now + SLOT > end:
                account(now, [gap(end - now)])
                collect_arrivals(end)
                break
            for i in active:
                backoff[i] -= 1
            account(now, [gap(SLOT)])
            now += SLOT
            collect_arrivals(now)
            continue
        if len(transmitting) > 1:
            def collision_duration(i):
                bits = (timing.icf_bits if i == n else timing.ebsr_bits) if ul_mode else (RTS if mode == "rts" else H + PAYLOAD)
                rate = data if mode in ("basic", "basic_hc") else control
                return bits / rate + DIFS + PROP_DELAY
            elapsed = max(collision_duration(i) for i in transmitting)
            airtimes = [(i, collision_duration(i) - DIFS - PROP_DELAY) for i in transmitting]
            boundaries = sorted(set([0.0] + [a for _, a in airtimes]))
            phases = [('COLLISION', right - left, [i for i, a in airtimes if a > left])
                      for left, right in zip(boundaries, boundaries[1:])]
            phases.append(gap(DIFS + PROP_DELAY))
        else:
            i = transmitting[0]
            elapsed = (ul_success if i == n else ebsr_success) if ul_mode else (basic_success if mode in ("basic", "basic_hc") else rts_success)
            if ul_mode and i < n:
                phases = [frame('EBSR', timing.ebsr_bits, i), gap(PROP_DELAY + DIFS)]
            else:
                sta = grants[0] if i == n else i
                phases = []
                if ul_mode:
                    phases += [frame('ICF', timing.icf_bits, n), gap(SIFS + PROP_DELAY),
                               frame('ICR', timing.icr_bits, sta), gap(SIFS + PROP_DELAY)]
                elif mode == 'rts':
                    phases += [frame('RTS', RTS, sta), gap(SIFS + PROP_DELAY),
                               frame('CTS', CTS, n), gap(SIFS + PROP_DELAY)]
                phases += [frame('DATA', H + PAYLOAD, sta, data), gap(SIFS + PROP_DELAY),
                           frame('ACK', ACK, n), gap(PROP_DELAY + DIFS)]
        target = grants[0] if ul_mode and len(transmitting) == 1 and transmitting[0] == n else None
        if mode == 'ul_dps' and target is not None:
            icr_index = next(j for j, phase in enumerate(phases) if phase[0] == 'ICR')
            for j in range(icr_index, len(phases)-1):
                phases[j] = (*phases[j][:3], 'HC')
            phases.insert(icr_index, ('SWITCH_UP', timing.switch_up_us, [], 'SWITCH'))
            phases.insert(len(phases)-1, ('SWITCH_DOWN', timing.switch_down_us, [], 'SWITCH'))
            elapsed += timing.switch_up_us + timing.switch_down_us
        category = 'collision' if len(transmitting) > 1 else 'success'
        account(now, phases, category, target)
        ack_time = now
        for phase in phases:
            ack_time += phase[1]
            if phase[0] == 'ACK': break
        attempts += len(transmitting)
        if len(transmitting) > 1:
            collided += len(transmitting)
            collision_events += 1
        incomplete = now + elapsed > end
        if incomplete and (len(transmitting) > 1 or not any(p[0] == "ACK" for p in phases) or ack_time > end):
            collect_arrivals(end)
            break
        now += elapsed
        if len(transmitting) > 1:
            for i in transmitting:
                stage[i] = min(stage[i] + 1, m)
                backoff[i] = rng.randrange(W * 2 ** stage[i])
        else:
            i = transmitting[0]
            backoff[i] = None
            stage[i] = 0
            if ul_mode and i != n:
                reports += 1
                report_attempts[i] = attempts
                reported.add(i)
                grants.append(i)
                activate(n)
            else:
                if i == n:
                    ap_exchanges += 1
                    i = grants.popleft()
                    transmissions_between += attempts - 1 - report_attempts.pop(i)
                    reported.remove(i)
                    if grants:
                        activate(n)
                # Delivery is at ACK reception, before the trailing DIFS.
                delay = ack_time - queues[i].popleft()
                total_delay += delay
                delays.append(delay / 1000)
                delivered += 1
                per_sta_delivered[i] += 1
                if traffic == "saturated":
                    queues[i].append(ack_time)
                    generated += 1
                if queues[i]:
                    activate(i)
        collect_arrivals(min(now, end))
        if incomplete:
            break

    pending = sum(map(len, queues))
    delays.sort()
    lc_energy = sum(radio_us[k] * getattr(power, k + '_w') / 1e6 for k in radio_us)
    hc_energy = sum(hc_radio_us[k] * getattr(hc_power, k + '_w') / 1e6 for k in hc_radio_us)
    energy = lc_energy + hc_energy
    fairness = (delivered ** 2 / (n * sum(x*x for x in per_sta_delivered))
                if delivered else math.nan)
    extra = {f'hc_{k}_sta_seconds': v/1e6 for k, v in hc_radio_us.items()}
    extra.update({f'{k}_channel_seconds': v/1e6 for k, v in ledger.items()})
    for name in ('EBSR', 'ICF', 'ICR', 'DATA', 'ACK', 'RTS', 'CTS', 'COLLISION', 'SWITCH_UP', 'SWITCH_DOWN'):
        extra[name.lower()+'_airtime_seconds'] = frame_airtime.get(name, 0.0)/1e6
    return dict(**extra, lc_energy_j=lc_energy, hc_energy_j=hc_energy,
                switch_up_count=switch_ups, switch_down_count=switch_downs,
                mean_channel_cost_ms=end/delivered/1000 if delivered else math.nan,
                collisions_per_delivered=collision_events/delivered if delivered else math.nan,
                drop_ratio=dropped/generated if generated else math.nan,
                pending_ratio=pending/generated if generated else math.nan,
                mean_delay_ms=total_delay / delivered / 1000 if delivered else math.nan,
                p95_delay_ms=delays[math.ceil(.95 * len(delays))-1] if delays else math.nan,
                sta_energy_j=energy, mean_sta_power_w=energy / duration_s / n,
                energy_per_delivered_packet_mj=energy * 1000 / delivered if delivered else math.nan,
                lc_idle_sta_seconds=radio_us['idle'] / 1e6,
                lc_rx_sta_seconds=radio_us['rx'] / 1e6,
                lc_tx_sta_seconds=radio_us['tx'] / 1e6,
                jain_fairness=fairness,
                throughput_mbps=delivered * PAYLOAD / end,
                prr=delivered / generated if generated else math.nan,
                collision_probability=collided / attempts if attempts else 0.0,
                collision_ratio=collided / attempts if attempts else 0.0,
                collided_attempts=collided,
                mean_transmissions_between_ebsr_and_hc_ul=transmissions_between / delivered if ul_mode and delivered else math.nan,
                transmissions_between_ebsr_and_hc_ul=transmissions_between,
                generated=generated, delivered=delivered, dropped=dropped,
                pending=pending, attempts=attempts, collision_events=collision_events,
                ebsr_successes=reports, ap_exchanges=ap_exchanges,
                duration_s=duration_s)

