from hotloop import hotloop

@hotloop
def mask_ascii_digits(text: str) -> str:
    result: str = ""
    for ch in text:
        if ch >= "0" and ch <= "9":
            result += "*"
        else:
            result += ch
    return result
