"""UL trigger-based DPS with LC contention and HC uplink."""
from .simulation import ULTiming, LCPower, simulate_traffic


def simulate(**kwargs):
    """STA wins: EBSR; AP wins: ICF-ICR-DATA-ACK with HC switching."""
    return simulate_traffic(mode='ul_dps', **kwargs)