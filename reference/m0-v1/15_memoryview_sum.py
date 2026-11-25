from hotloop import hotloop
@hotloop
def memoryview_sum(values: list[float]) -> float:
    total: float = 0.0
    for i in range(len(values)):
        total += values[i]
    return total
