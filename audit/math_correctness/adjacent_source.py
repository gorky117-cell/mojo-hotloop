import math
from hotloop import hotloop

def effect(x: float) -> float:
    print("EFFECT")
    return x

def power_helper(x: float, y: float) -> float:
    return math.pow(x, y)

@hotloop
def power(x: float, y: float) -> float:
    return math.pow(x, y)
@hotloop
def floor_value(x: float) -> float:
    return math.floor(x)
@hotloop
def ceil_value(x: float) -> float:
    return math.ceil(x)
@hotloop
def log_base(x: float, base: float) -> float:
    return math.log(x, base)
@hotloop
def keyword_log(x: float) -> float:
    return math.log(x=x)
@hotloop
def power_parent(x: float, y: float) -> float:
    return power_helper(x, y)
@hotloop
def effect_first(x: float, y: float) -> float:
    return math.log(effect(x)) + math.exp(y)
@hotloop
def overflow_before_effect(x: float, y: float) -> float:
    return math.exp(y) + math.log(effect(x))
@hotloop
def constant_exp() -> float:
    return math.exp(1.0)
@hotloop
def constant_sin() -> float:
    return math.sin(math.pi)
@hotloop
def integer_log(x: int) -> float:
    return math.log(x)
