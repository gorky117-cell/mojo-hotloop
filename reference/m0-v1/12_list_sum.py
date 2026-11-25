from hotloop import hotloop
@hotloop
def list_sum(values: list[float]) -> float:
    total: float = 0.0
    for i in range(len(values)):
        total += values[i]
    return total
