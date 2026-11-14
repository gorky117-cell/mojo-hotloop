import os
import sys

# Ensure hotloop package is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from hotloop import hotloop

@hotloop
def stateful_trailing_backtest(ticks: int, start_price: float, stop_pct: float, fee_rate: float) -> float:
    if ticks <= 0:
        return start_price

    price = start_price
    peak_price = start_price
    cash = 0.0
    units = 1.0
    in_position = True
    cooldown = 0
    lcg_state = 42

    for _ in range(ticks):
        lcg_state = (1664525 * lcg_state + 1013904223) & 0xFFFFFFFF
        rand_val = lcg_state / 4294967296.0
        price = price * (1.0 + (rand_val - 0.5) * 0.02)

        if in_position:
            if price > peak_price:
                peak_price = price
            elif stop_pct > 0.0 and price <= peak_price * (1.0 - stop_pct):
                cash = units * price * (1.0 - fee_rate)
                units = 0.0
                in_position = False
                cooldown = 5
        else:
            if cooldown > 0:
                cooldown -= 1
            if cooldown == 0:
                units = (cash * (1.0 - fee_rate)) / price
                cash = 0.0
                in_position = True
                peak_price = price

    if in_position:
        return units * price
    else:
        return cash
