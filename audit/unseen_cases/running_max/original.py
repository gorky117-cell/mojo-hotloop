from hotloop import hotloop

@hotloop
def running_max(values: list[float]) -> list[float]:
    if len(values) == 0:
        return []
    current_max: float = values[0]
    result: list[float] = []
    for v in values:
        if v > current_max:
            current_max = v
        result.append(current_max)
    return result
