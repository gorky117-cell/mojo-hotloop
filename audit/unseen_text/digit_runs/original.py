from hotloop import hotloop

@hotloop
def count_ascii_digit_runs(text: str) -> int:
    runs: int = 0
    in_run: bool = False
    for ch in text:
        if ch >= "0" and ch <= "9":
            if not in_run:
                runs += 1
                in_run = True
        else:
            in_run = False
    return runs
