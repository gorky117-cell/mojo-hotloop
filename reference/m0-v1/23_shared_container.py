from hotloop import hotloop
@hotloop
def shared_container(values: list[float]) -> list[float]:
    result: list[float] = []
    result.append(values[0])
    result.append(values[0])
    return result
