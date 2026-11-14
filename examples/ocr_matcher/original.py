from hotloop import hotloop

def levenshtein_distance(s1: str, s2: str, max_dist: int) -> int:
    m: int = len(s1)
    n: int = len(s2)
    diff: int = m - n
    if diff < 0:
        diff = -diff
    if diff > max_dist:
        return max_dist + 1

    prev: list[int] = []
    curr: list[int] = []
    for j in range(n + 1):
        prev.append(j)
        curr.append(0)

    for i in range(1, m + 1):
        curr[0] = i
        min_row: int = i
        ch1: str = s1[i - 1]
        for j in range(1, n + 1):
            cost: int = 1
            if ch1 == s2[j - 1]:
                cost = 0
            del_cost: int = prev[j] + 1
            ins_cost: int = curr[j - 1] + 1
            sub_cost: int = prev[j - 1] + cost
            val: int = del_cost
            if ins_cost < val:
                val = ins_cost
            if sub_cost < val:
                val = sub_cost
            curr[j] = val
            if val < min_row:
                min_row = val
        if min_row > max_dist:
            return max_dist + 1
        for j in range(n + 1):
            prev[j] = curr[j]

    return prev[n]

@hotloop
def find_closest_match(query: str, candidates: list[str], max_distance: int) -> int:
    best_idx: int = -1
    best_dist: int = max_distance + 1
    num_candidates: int = len(candidates)

    for i in range(num_candidates):
        cand: str = candidates[i]
        dist: int = levenshtein_distance(query, cand, best_dist - 1)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
            if best_dist == 0:
                break

    return best_idx
