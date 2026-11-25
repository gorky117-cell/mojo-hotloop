from hotloop import hotloop
@hotloop
def list_element(values: list[float], index: int) -> float:
    return values[index]
