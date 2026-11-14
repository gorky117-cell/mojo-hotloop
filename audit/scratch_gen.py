import ast
from hotloop.ast_transpiler import transpile_python_to_mojo

funcs = '''
import math
from hotloop import hotloop

@hotloop
def trapezoidal_integration(a: float, b: float, n_steps: int) -> float:
    if n_steps <= 0:
        return 0.0
    h = (b - a) / float(n_steps)
    inv_sqrt_2pi = 0.3989422804014327
    total = 0.5 * (math.exp(-a * a * 0.5) + math.exp(-b * b * 0.5))
    x = a
    for _ in range(1, n_steps):
        x += h
        total += math.exp(-x * x * 0.5)
    return total * h * inv_sqrt_2pi

@hotloop
def chebyshev_path_distance(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n <= 1:
        return 0.0
    total = 0.0
    for i in range(1, n):
        dx = abs(xs[i] - xs[i - 1])
        dy = abs(ys[i] - ys[i - 1])
        if dx > dy:
            total += dx
        else:
            total += dy
    return total

@hotloop
def exponential_moving_average(values: list[float], alpha: float) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    ema = values[0]
    one_minus_alpha = 1.0 - alpha
    for i in range(1, n):
        ema = alpha * values[i] + one_minus_alpha * ema
    return ema

@hotloop
def mask_digits(text: str) -> str:
    n = len(text)
    res = ""
    for i in range(n):
        if text[i] >= "0" and text[i] <= "9":
            res += "*"
        else:
            res += text[i]
    return res

@hotloop
def hamming_distance(s1: str, s2: str) -> int:
    n1 = len(s1)
    n2 = len(s2)
    min_len = min(n1, n2)
    dist = abs(n1 - n2)
    for i in range(min_len):
        if s1[i] != s2[i]:
            dist += 1
    return dist
'''

mojo_code = transpile_python_to_mojo(funcs, 'scratch_gen')
with open('/home/gaurav/mojo-hotloop/audit/scratch_gen.mojo', 'w') as f:
    f.write(mojo_code)
print('SUCCESS! Transpiled scratch_gen.mojo')
