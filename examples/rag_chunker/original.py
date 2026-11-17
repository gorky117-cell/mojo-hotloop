from hotloop import hotloop

@hotloop
def chunk_document(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    n: int = len(text)
    if n == 0 or chunk_size <= 0:
        return chunks

    step: int = chunk_size - chunk_overlap
    if step <= 0:
        step = 1

    start: int = 0
    while start < n:
        ideal_end: int = start + chunk_size
        if ideal_end >= n:
            chunks.append(text[start:n])
            break

        lookback_limit: int = ideal_end - chunk_overlap
        if lookback_limit < start:
            lookback_limit = start

        boundary: int = -1
        idx: int = ideal_end
        while idx > lookback_limit:
            ch: str = text[idx]
            if ch == " " or ch == "\n" or ch == "\t":
                boundary = idx
                break
            idx -= 1

        end: int = ideal_end
        if boundary > start:
            end = boundary

        chunks.append(text[start:end])

        next_start: int = end - chunk_overlap
        if next_start <= start:
            next_start = start + step
            if next_start <= start:
                next_start = start + 1
        start = next_start

    return chunks


@hotloop
def chunk_document_offsets(text: str, chunk_size: int, chunk_overlap: int) -> list[int]:
    """
    Computes [start_0, end_0, start_1, end_1, ...] offsets.
    Returning paired integer offsets eliminates the per-chunk string object allocation
    across the FFI boundary. Slices can be viewed or materialized in Python as text[s:e].
    """
    offsets: list[int] = []
    n: int = len(text)
    if n == 0 or chunk_size <= 0:
        return offsets

    step: int = chunk_size - chunk_overlap
    if step <= 0:
        step = 1

    start: int = 0
    while start < n:
        ideal_end: int = start + chunk_size
        if ideal_end >= n:
            offsets.append(start)
            offsets.append(n)
            break

        lookback_limit: int = ideal_end - chunk_overlap
        if lookback_limit < start:
            lookback_limit = start

        boundary: int = -1
        idx: int = ideal_end
        while idx > lookback_limit:
            ch: str = text[idx]
            if ch == " " or ch == "\n" or ch == "\t":
                boundary = idx
                break
            idx -= 1

        end: int = ideal_end
        if boundary > start:
            end = boundary

        offsets.append(start)
        offsets.append(end)

        next_start: int = end - chunk_overlap
        if next_start <= start:
            next_start = start + step
            if next_start <= start:
                next_start = start + 1
        start = next_start

    return offsets

