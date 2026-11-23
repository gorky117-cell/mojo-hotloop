import math
from hotloop import hotloop

def plain_log(x: float) -> float:
    return math.log(x)

@hotloop
def sine(x: float) -> float:
    return math.sin(x)
@hotloop
def cosine(x: float) -> float:
    return math.cos(x)
@hotloop
def square_root(x: float) -> float:
    return math.sqrt(x)
@hotloop
def logarithm(x: float) -> float:
    return math.log(x)
@hotloop
def exponential(x: float) -> float:
    return math.exp(x)
@hotloop
def angle(y: float, x: float) -> float:
    return math.atan2(y, x)
@hotloop
def helper_flow(x: float) -> float:
    return plain_log(x)
@hotloop
def overflow_first(x: float, y: float) -> float:
    return math.exp(x) + math.log(y)
@hotloop
def domain_first(x: float, y: float) -> float:
    return math.log(y) + math.exp(x)
@hotloop
def nested(x: float) -> float:
    return math.log(math.exp(x))
