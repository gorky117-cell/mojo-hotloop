from hotloop import hotloop
@hotloop
def full_slice_owner(text: str) -> str:
    return text[:]
