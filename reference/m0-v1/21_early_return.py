from hotloop import hotloop
@hotloop
def early_return(limit: int) -> int:
    for i in range(limit):
        if i*i > limit:
            return i
    return -1
