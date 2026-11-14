from hotloop import hotloop

@hotloop
def clean_pdf_text(text: str) -> str:
    n: int = len(text)
    if n == 0:
        return ""

    result: str = ""
    i: int = 0
    while i < n:
        ch: str = text[i]

        # 1. Hyphen repair at line break: e.g. "word-\nnext" -> "wordnext"
        if ch == "-" and i + 1 < n and (text[i + 1] == "\n" or text[i + 1] == "\r"):
            if i > 0 and ((text[i - 1] >= "a" and text[i - 1] <= "z") or (text[i - 1] >= "A" and text[i - 1] <= "Z")):
                i += 1
                while i < n and (text[i] == "\n" or text[i] == "\r" or text[i] == " " or text[i] == "\t"):
                    i += 1
                continue

        # 2. Form feed / page break character
        if ch == "\f":
            result += "\n\n"
            i += 1
            while i < n and (text[i] == " " or text[i] == "\t" or text[i] == "\n" or text[i] == "\r"):
                i += 1
            continue

        # 3. Page header removal: e.g. "\nPage 4\n"
        if ch == "\n" and i + 1 < n:
            if i + 6 <= n and text[i + 1:i + 6] == "Page ":
                j: int = i + 6
                while j < n and text[j] >= "0" and text[j] <= "9":
                    j += 1
                if j == n or text[j] == "\n" or text[j] == "\r":
                    i = j
                    continue

        # 4. Whitespace normalization: multiple spaces/tabs into single space
        if ch == " " or ch == "\t":
            result += " "
            i += 1
            while i < n and (text[i] == " " or text[i] == "\t"):
                i += 1
            continue

        # 5. Collapse 3+ newlines into 2 newlines (paragraph break)
        if ch == "\n":
            nl_count: int = 0
            while i < n and (text[i] == "\n" or text[i] == "\r"):
                if text[i] == "\n":
                    nl_count += 1
                i += 1
            if nl_count >= 2:
                result += "\n\n"
            else:
                result += "\n"
            continue

        result += ch
        i += 1

    return result
