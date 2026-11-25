from hotloop import hotloop
@hotloop
def unsupported_ternary(x: float, y: float, choose: bool) -> float:
    return x if choose else y
