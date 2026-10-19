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
                     seed=0, timing=None, power=None, trace=None, hc_power=None,
                     payload_sizes_bytes=None, dps_threshold_bytes=512,
                     payload_size_range_bytes=None, diagnostics=None):
    """Packet-level extension of the original frozen-backoff simulator.

    UL prototype: STA contention -> EBSR -> AP contention -> ICF/ICR/DATA/ACK.
    AP serves reported STAs FIFO, one packet per grant. STA cannot recontend
    until that packet completes. All contenders share a serialized channel.
    Delay is arrival-to-ACK for delivered packets. PRR is delivered/generated
    during a fixed observation window, including queued packets at its end.
    Saturated traffic generates a replacement packet immediately after delivery.
    No retry limit or PHY loss; drops occur only on Poisson queue overflow.
    Optional payload sizes or an inclusive integer range are sampled uniformly per generated packet (bytes).
    In ul_dps_threshold, only head packets strictly larger than the byte threshold
    report via EBSR; smaller/equal packets contend for direct LC DATA/ACK.
    """
    timing = timing or ULTiming()
    power = power or LCPower()
    hc_power = hc_power or HCPower()
    ul_mode = mode in ("ul_dps", "ul_dps_threshold")
    threshold_mode = mode == "ul_dps_threshold"
    if payload_size_range_bytes is not None:
        if payload_sizes_bytes is not None:
            raise ValueError('Choose payload sizes or a uniform range, not both')
        payload_size_range_bytes = tuple(payload_size_range_bytes)
        if (len(payload_size_range_bytes) != 2 or
                any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in payload_size_range_bytes) or
                payload_size_range_bytes[0] > payload_size_range_bytes[1]):
            raise ValueError('Uniform payload range requires positive integer min <= max')
    if payload_sizes_bytes is not None:
        payload_sizes_bytes = tuple(payload_sizes_bytes)
        if not payload_sizes_bytes or any(not isinstance(x, int) or isinstance(x, bool) or x <= 0
                                         for x in payload_sizes_bytes):
            raise ValueError("Payload sizes must be positive integer bytes")
    if not isinstance(dps_threshold_bytes, int) or isinstance(dps_threshold_bytes, bool) or dps_threshold_bytes < 0:
        raise ValueError("DPS threshold must be nonnegative integer bytes")
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
    if mode not in ("basic", "rts", "ul_dps", "ul_dps_threshold", "basic_hc") or traffic not in ("saturated", "poisson"):
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
    # Per-STA streams preserve each STA's packet-size sequence across access models.
    # Draw for every generated packet, including drops; contention uses a separate RNG.
    size_rngs = [random.Random(seed + 2000003 + i * 1000033) for i in range(n)]
    arrival_rngs = ([random.Random(seed + 1000003 + i * 1000033) for i in range(n)]
                    if payload_sizes_bytes or payload_size_range_bytes else [arrivals_rng] * n)
    end = duration_s * 1e6
    queues = [deque() for _ in range(n)]
    stage = [0] * (n + 1)
    backoff = [None] * (n + 1)
    reported = set()
    grants = deque()
    next_arrival = [math.inf] * n
    generated = delivered = dropped = attempts = collided = collision_events = 0
    reports = ap_exchanges = 0
    generated_bits = delivered_bits = dropped_bits = 0
    direct_delivered = dps_delivered = 0
    size_generated = {size: 0 for size in (payload_sizes_bytes or ())}
    size_delivered = {size: 0 for size in (payload_sizes_bytes or ())}
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
            if diagnostics is not None and observed:
                diagnostics.observe_time(cursor, observed, len(reported))
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

    def make_packet(i, arrival):
        nonlocal generated_bits
        if payload_size_range_bytes:
            bits = 8 * size_rngs[i].randint(*payload_size_range_bytes)
        else:
            bits = 8 * size_rngs[i].choice(payload_sizes_bytes) if payload_sizes_bytes else PAYLOAD
        generated_bits += bits
        if payload_sizes_bytes:
            size_generated[bits // 8] += 1
        return (arrival, bits)

    def needs_report(i):
        return ul_mode and (not threshold_mode or queues[i][0][1] > 8 * dps_threshold_bytes)

    def collect_arrivals(until):
        nonlocal generated, dropped, dropped_bits
        if traffic != "poisson" or interval_rate == 0:
            return
        for i in range(n):
            while next_arrival[i] <= until:
                generated += 1
                packet = make_packet(i, next_arrival[i])
                if len(queues[i]) < queue_limit:
                    queues[i].append(packet)
                    if i not in reported:
                        activate(i)
                else:
                    dropped += 1
                    dropped_bits += packet[1]
                next_arrival[i] += arrival_rngs[i].expovariate(interval_rate)

    if traffic == "saturated":
        for i in range(n):
            queues[i].append(make_packet(i, 0.0))
            generated += 1
            activate(i)
    elif interval_rate:
        next_arrival = [arrival_rngs[i].expovariate(interval_rate) for i in range(n)]

    control = timing.control_rate_mbps

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
                if i == n:
                    bits, rate = timing.icf_bits, control
                elif needs_report(i):
                    bits, rate = timing.ebsr_bits, control
                elif mode == "rts":
                    bits, rate = RTS, control
                else:
                    bits = H + queues[i][0][1]
                    rate = timing.hc_rate_mbps if mode == "basic_hc" else timing.data_rate_mbps
                return bits / rate + DIFS + PROP_DELAY
            elapsed = max(collision_duration(i) for i in transmitting)
            airtimes = [(i, collision_duration(i) - DIFS - PROP_DELAY) for i in transmitting]
            boundaries = sorted(set([0.0] + [a for _, a in airtimes]))
            phases = [('COLLISION', right - left, [i for i, a in airtimes if a > left])
                      for left, right in zip(boundaries, boundaries[1:])]
            phases.append(gap(DIFS + PROP_DELAY))
        else:
            i = transmitting[0]
            if i < n and needs_report(i):
                phases = [frame('EBSR', timing.ebsr_bits, i), gap(PROP_DELAY + DIFS)]
            else:
                sta = grants[0] if i == n else i
                phases = []
                if i == n:
                    phases += [frame('ICF', timing.icf_bits, n), gap(SIFS + PROP_DELAY),
                               frame('ICR', timing.icr_bits, sta), gap(SIFS + PROP_DELAY)]
                elif mode == 'rts':
                    phases += [frame('RTS', RTS, sta), gap(SIFS + PROP_DELAY),
                               frame('CTS', CTS, n), gap(SIFS + PROP_DELAY)]
                data = timing.hc_rate_mbps if i == n or mode == 'basic_hc' else timing.data_rate_mbps
                phases += [frame('DATA', H + queues[sta][0][1], sta, data), gap(SIFS + PROP_DELAY),
                           frame('ACK', ACK, n), gap(PROP_DELAY + DIFS)]
        target = grants[0] if ul_mode and len(transmitting) == 1 and transmitting[0] == n else None
        if ul_mode and target is not None:
            icr_index = next(j for j, phase in enumerate(phases) if phase[0] == 'ICR')
            for j in range(icr_index, len(phases)-1):
                phases[j] = (*phases[j][:3], 'HC')
            phases.insert(icr_index, ('SWITCH_UP', timing.switch_up_us, [], 'SWITCH'))
            phases.insert(len(phases)-1, ('SWITCH_DOWN', timing.switch_down_us, [], 'SWITCH'))
        elapsed = sum(phase[1] for phase in phases)
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
        if diagnostics is not None:
            roles = [('ICF' if sender == n else 'EBSR' if needs_report(sender)
                      else 'RTS' if mode == 'rts' else 'DATA') for sender in transmitting]
            frame_records = []
            cursor = now
            for phase in phases:
                if phase[2]:
                    frame_records.append(dict(name=phase[0], start_us=cursor,
                                              end_us=cursor+phase[1], senders=phase[2]))
                cursor += phase[1]
            success_completed = (len(transmitting) == 1 and
                ((roles[0] == 'EBSR' and now+elapsed <= end) or
                 (roles[0] != 'EBSR' and ack_time <= end)))
            diagnostics.observe_event(dict(start_us=now, senders=transmitting, roles=roles,
                reported=len(reported), target=target, frames=frame_records,
                horizon_us=end, success_completed=success_completed))
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
            if i < n and needs_report(i):
                reports += 1
                report_attempts[i] = attempts
                reported.add(i)
                grants.append(i)
                activate(n)
            else:
                if i == n:
                    ap_exchanges += 1
                    dps_delivered += 1
                    i = grants.popleft()
                    transmissions_between += attempts - 1 - report_attempts.pop(i)
                    reported.remove(i)
                    if grants:
                        activate(n)
                else:
                    direct_delivered += 1
                # Delivery is at ACK reception, before the trailing DIFS.
                arrival, bits = queues[i].popleft()
                delivered_bits += bits
                if payload_sizes_bytes:
                    size_delivered[bits // 8] += 1
                delay = ack_time - arrival
                total_delay += delay
                delays.append(delay / 1000)
                delivered += 1
                per_sta_delivered[i] += 1
                if traffic == "saturated":
                    queues[i].append(make_packet(i, ack_time))
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
    for size in size_generated:
        extra[f'generated_payload_{size}_bytes_count'] = size_generated[size]
        extra[f'delivered_payload_{size}_bytes_count'] = size_delivered[size]
    return dict(**extra,
                generated_payload_bits=generated_bits, delivered_payload_bits=delivered_bits,
                dropped_payload_bits=dropped_bits,
                pending_payload_bits=sum(packet[1] for queue in queues for packet in queue),
                direct_delivered=direct_delivered, dps_delivered=dps_delivered,
                dps_delivery_fraction=dps_delivered / delivered if delivered else math.nan,
                byte_prr=delivered_bits / generated_bits if generated_bits else math.nan,
                mean_delivered_payload_bytes=delivered_bits / 8 / delivered if delivered else math.nan,
                energy_per_delivered_mbit_j=energy * 1e6 / delivered_bits if delivered_bits else math.nan,
                lc_energy_j=lc_energy, hc_energy_j=hc_energy,
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
                throughput_mbps=delivered_bits / end,
                prr=delivered / generated if generated else math.nan,
                collision_probability=collided / attempts if attempts else 0.0,
                collision_ratio=collided / attempts if attempts else 0.0,
                collided_attempts=collided,
                mean_transmissions_between_ebsr_and_hc_ul=transmissions_between / ap_exchanges if ul_mode and ap_exchanges else math.nan,
                transmissions_between_ebsr_and_hc_ul=transmissions_between,
                generated=generated, delivered=delivered, dropped=dropped,
                pending=pending, attempts=attempts, collision_events=collision_events,
                ebsr_successes=reports, ap_exchanges=ap_exchanges,
                duration_s=duration_s)

