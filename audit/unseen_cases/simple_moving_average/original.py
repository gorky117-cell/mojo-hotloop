from hotloop import hotloop

@hotloop
def simple_moving_average(values: list[float], window: int) -> list[float]:
    if len(values) < window or window <= 0:
        return []
    result: list[float] = []
    window_sum: float = 0.0
    for i in range(window):
        window_sum += values[i]
    result.append(window_sum / window)
    for i in range(window, len(values)):
        window_sum += values[i] - values[i - window]
        result.append(window_sum / window)
    return result
