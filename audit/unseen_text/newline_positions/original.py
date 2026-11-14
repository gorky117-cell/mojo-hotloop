from hotloop import hotloop

@hotloop
def unicode_newline_positions(text: str) -> list[int]:
    positions: list[int] = []
    idx: int = 0
    for ch in text:
        if ch == "\n" or ch == "\r":
            positions.append(idx)
        idx += 1
    return positions
