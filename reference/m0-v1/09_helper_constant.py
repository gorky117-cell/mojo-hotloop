from hotloop import hotloop
def plain_constant() -> float:
    return 19.75

@hotloop
def helper_constant(x: float) -> float:
    return plain_constant()
