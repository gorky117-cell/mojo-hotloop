from hotloop import hotloop

@hotloop
def get_int(xs: list[int], i: int) -> int:
    return xs[i]
@hotloop
def get_float(xs: list[float], i: int) -> float:
    return xs[i]
@hotloop
def get_bool(xs: list[bool], i: int) -> bool:
    return xs[i]
@hotloop
def get_str(xs: list[str], i: int) -> str:
    return xs[i]
@hotloop
def compute(xs: list[int], i: int) -> int:
    return xs[i] + 1
@hotloop
def local_read(i: int) -> int:
    xs = [1000, 2000]
    return xs[i] + 1
@hotloop
def literal_read(i: int) -> int:
    return [1000, 2000][i] + 1

def make_values() -> list[int]:
    return [1, 2]
@hotloop
def helper_list(i: int) -> int:
    return make_values()[i] + 1

def shift(i: int) -> int:
    return i + 1
def index_value(i: int) -> int:
    return shift(i) - 1
@hotloop
def nested_index(xs: list[int], i: int) -> int:
    return xs[index_value(i)]
@hotloop
def read_before_div(xs: list[int], i: int, divisor: int) -> int:
    return xs[i] + 4 // divisor
@hotloop
def div_before_read(xs: list[int], i: int, divisor: int) -> int:
    return 4 // divisor + xs[i]
@hotloop
def local_store(i: int, value: int) -> int:
    xs = [1, 2]
    xs[i] = value
    return xs[0] + xs[1]
@hotloop
def local_aug(i: int, value: int) -> int:
    xs = [1, 2]
    xs[i] += value
    return xs[0] + xs[1]
@hotloop
def store_rhs_first(i: int, divisor: int) -> int:
    xs = [1, 2]
    xs[i] = 4 // divisor
    return 0
@hotloop
def aug_read_first(i: int, divisor: int) -> int:
    xs = [1, 2]
    xs[i] += 4 // divisor
    return 0

def effect_index(i: int) -> int:
    print("INDEX")
    return i
def effect_value(value: int) -> int:
    print("RHS")
    return value
@hotloop
def effect_read(xs: list[int], i: int) -> int:
    return xs[effect_index(i)]
@hotloop
def effect_store(i: int) -> int:
    xs = [1, 2]
    xs[effect_index(i)] = effect_value(7)
    return 0
