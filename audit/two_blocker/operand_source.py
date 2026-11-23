import math
from hotloop import hotloop

@hotloop
def sin_float(x: float) -> float:
    return math.sin(x)

@hotloop
def cos_float(x: float) -> float:
    return math.cos(x)

@hotloop
def sqrt_float(x: float) -> float:
    return math.sqrt(x)

@hotloop
def log_float(x: float) -> float:
    return math.log(x)

@hotloop
def exp_float(x: float) -> float:
    return math.exp(x)

@hotloop
def atan2_float(x: float) -> float:
    return math.atan2(x, x)

@hotloop
def isnan_float(x: float) -> bool:
    return math.isnan(x)

@hotloop
def isinf_float(x: float) -> bool:
    return math.isinf(x)

@hotloop
def sin_int(x: int) -> float:
    return math.sin(x)

@hotloop
def cos_int(x: int) -> float:
    return math.cos(x)

@hotloop
def sqrt_int(x: int) -> float:
    return math.sqrt(x)

@hotloop
def log_int(x: int) -> float:
    return math.log(x)

@hotloop
def exp_int(x: int) -> float:
    return math.exp(x)

@hotloop
def atan2_int(x: int) -> float:
    return math.atan2(x, x)

@hotloop
def isnan_int(x: int) -> bool:
    return math.isnan(x)

@hotloop
def isinf_int(x: int) -> bool:
    return math.isinf(x)

@hotloop
def sin_bool(x: bool) -> float:
    return math.sin(x)

@hotloop
def cos_bool(x: bool) -> float:
    return math.cos(x)

@hotloop
def sqrt_bool(x: bool) -> float:
    return math.sqrt(x)

@hotloop
def log_bool(x: bool) -> float:
    return math.log(x)

@hotloop
def exp_bool(x: bool) -> float:
    return math.exp(x)

@hotloop
def atan2_bool(x: bool) -> float:
    return math.atan2(x, x)

@hotloop
def isnan_bool(x: bool) -> bool:
    return math.isnan(x)

@hotloop
def isinf_bool(x: bool) -> bool:
    return math.isinf(x)


def numeric_helper(x: float) -> float:
    return x + 1.0

@hotloop
def helper_expression(x: float) -> float:
    return math.log(numeric_helper(x))

@hotloop
def temporary_expression(x: float) -> float:
    y = x + 1.0
    return math.log(y)

@hotloop
def predicates(x: float) -> int:
    if math.isnan(x):
        return -999
    if math.isinf(x):
        if x > 0.0:
            return 999
        return -888
    return 0

def effect(x: float) -> float:
    print("EFFECT")
    return x

@hotloop
def effects(x: float) -> float:
    return math.log(effect(x))
