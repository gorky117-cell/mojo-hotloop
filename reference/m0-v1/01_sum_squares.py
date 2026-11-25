from hotloop import hotloop
@hotloop
def sum_squares(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i * i
    return total
