"""Simple saturated Wi-Fi simulation. Classical saturated DCF and queue-based traffic extension."""
import random

# All times are microseconds; frame sizes are bits.
SLOT = 50.0
SIFS = 28.0
DIFS = 128.0
PROP_DELAY = 1.0
DATA_RATE = 1.0  # Mbit/s = bits per microsecond

PHY_HEADER = 128
MAC_HEADER = 272
PAYLOAD = 8184
ACK = 112 + PHY_HEADER
RTS = 160 + PHY_HEADER
CTS = 112 + PHY_HEADER
H = PHY_HEADER + MAC_HEADER


# Ts: duration of a successful exchange. Tc: duration of a collision.
TS_BASIC = (H + PAYLOAD + ACK) / DATA_RATE + SIFS + DIFS + 2 * PROP_DELAY
TC_BASIC = (H + PAYLOAD) / DATA_RATE + DIFS + PROP_DELAY
TS_RTS_CTS = ((RTS + CTS + H + PAYLOAD + ACK) / DATA_RATE
              + 3 * SIFS + DIFS + 4 * PROP_DELAY)
TC_RTS_CTS = RTS / DATA_RATE + DIFS + PROP_DELAY


def simulate(mode="basic", n=10, W=32, m=5, target_successes=100000, seed=0):
    """Each station always has a packet ready.

    mode: "basic" or "rts"
    n: number of stations
    W: initial number of backoff choices (0 through W-1)
    m: maximum backoff stage; packets retry indefinitely
    target_successes: stop after this many successful packets in the network
    """
    if n < 1 or W < 2 or m < 0 or target_successes < 1:
        raise ValueError("Use n >= 1, W >= 2, m >= 0 and target_successes >= 1")
    if mode == "basic":
        Ts, Tc = TS_BASIC, TC_BASIC
    elif mode == "rts":
        Ts, Tc = TS_RTS_CTS, TC_RTS_CTS
    else:
        raise ValueError('mode must be "basic" or "rts"')

    rng = random.Random(seed)
    stage = [0] * n
    backoff = [rng.randrange(W) for i in range(n)]
    packet_collision_time = [0.0] * n

    current_time = 0.0
    successes = 0
    attempts = 0
    collided_attempts = 0
    collision_events = 0
    total_completed_collision_time = 0.0

    while successes < target_successes:
        transmitting = [i for i in range(n) if backoff[i] == 0]

        # 1. Nobody transmits: count down one idle slot.
        if len(transmitting) == 0:
            for i in range(n):
                backoff[i] -= 1
            current_time += SLOT

        # 2. One station transmits: its packet succeeds.
        elif len(transmitting) == 1:
            i = transmitting[0]
            current_time += Ts
            successes += 1
            attempts += 1

            # Include this completed packet's collision time in the average.
            total_completed_collision_time += packet_collision_time[i]
            packet_collision_time[i] = 0.0

            # The next packet starts at stage zero with a new backoff.
            stage[i] = 0
            backoff[i] = rng.randrange(W)

        # 3. Multiple stations transmit: all their attempts collide.
        else:
            current_time += Tc
            collision_events += 1
            attempts += len(transmitting)
            collided_attempts += len(transmitting)

            for i in transmitting:
                packet_collision_time[i] += Tc
                stage[i] = min(stage[i] + 1, m)
                window = W * (2 ** stage[i])
                backoff[i] = rng.randrange(window)

        # Other stations' counters stay frozen during success/collision events.

    simulation_seconds = current_time / 1000000
    throughput_bps = successes * PAYLOAD / simulation_seconds

    return {
        "normalized_throughput": throughput_bps / (DATA_RATE * 1000000),
        "collision_probability": collided_attempts / attempts,
        "mean_collision_delay_ms": total_completed_collision_time / successes / 1000,
        "collision_events_per_second": collision_events / simulation_seconds,
        "successes": successes,
        "attempts": attempts,
        "collision_events": collision_events,
    }


def simulate_traffic(traffic='saturated', access='basic', **kwargs):
    """DCF packet simulation; Poisson is an extension of saturated Bianchi.

    Use simulate() above for the original success-count saturated experiment.
    """
    from .simulation import simulate_traffic as engine
    if access not in ('basic', 'rts'):
        raise ValueError('access must be basic or rts')
    return engine(mode=access, traffic=traffic, **kwargs)

def analytical_collision_probability(n, W=32, m=5):
    """Solve Bianchi's two equations for p by narrowing the interval [0, 1]."""
    low, high = 0.0, 1.0
    for step in range(60):
        p = (low + high) / 2
        # Bianchi's tau equation, written to also work when p = 0.5.
        backoff_sum = sum((2 * p) ** k for k in range(m))
        tau = 2 / (W + 1 + W * p * backoff_sum)
        predicted_p = 1 - (1 - tau) ** (n - 1)
        if p > predicted_p:
            high = p
        else:
            low = p
    return (low + high) / 2


def analytical_collision_rate(n, mode="basic", W=32, m=5):
    """Expected number of network collision events per second."""
    p = analytical_collision_probability(n, W, m)
    backoff_sum = sum((2 * p) ** k for k in range(m))
    tau = 2 / (W + 1 + W * p * backoff_sum)

    # Probabilities of the three possible outcomes of a slot.
    idle = (1 - tau) ** n
    success = n * tau * (1 - tau) ** (n - 1)
    collision = max(0.0, 1 - idle - success)

    if mode == "basic":
        Ts, Tc = TS_BASIC, TC_BASIC
    elif mode == "rts":
        Ts, Tc = TS_RTS_CTS, TC_RTS_CTS
    else:
        raise ValueError('mode must be "basic" or "rts"')
    average_slot_us = idle * SLOT + success * Ts + collision * Tc
    return collision / (average_slot_us / 1000000)

