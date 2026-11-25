from hotloop import hotloop
@hotloop
def printed_owner(value: float) -> float:
    print('seen')
    return value
