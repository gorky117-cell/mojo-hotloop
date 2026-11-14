from hotloop import hotloop

@hotloop
def count_greater(values: list[float], threshold: float) -> int:
    count: int = 0
    for v in values:
        if v > threshold:
            count += 1
    return count
