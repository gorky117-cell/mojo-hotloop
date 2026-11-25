from hotloop import hotloop
@hotloop
def conditional_owner(x: float, y: float, choose: bool) -> float:
    if choose:
        return y
    return x
