from hotloop import hotloop
@hotloop
def factorial(n: int) -> int:
    value: int = 1
    for i in range(2,n+1):
        value *= i
    return value
