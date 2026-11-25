from hotloop import hotloop
@hotloop
def list_mutation(values: list[int]) -> list[int]:
    old: int = values[0]
    values[0] = values[len(values)-1]
    values[len(values)-1] = old
    return values
