from std.time import perf_counter_ns
from std.collections import List

def lev_with_strings(s1_str: String, s2_str: String) raises -> Int:
    var cps1 = List[Codepoint]()
    for c in s1_str.codepoints():
        cps1.append(c)
    var cps2 = List[Codepoint]()
    for c in s2_str.codepoints():
        cps2.append(c)
    var m = len(cps1)
    var n = len(cps2)
    var prev = List[Int]()
    var curr = List[Int]()
    for j in range(n + 1):
        prev.append(j)
        curr.append(0)
    for i in range(1, m + 1):
        curr[0] = i
        var ch1 = String(cps1[i - 1])
        for j in range(1, n + 1):
            var cost = 1
            if ch1 == String(cps2[j - 1]):
                cost = 0
            var val = min(prev[j] + 1, min(curr[j - 1] + 1, prev[j - 1] + cost))
            curr[j] = val
        for j in range(n + 1):
            prev[j] = curr[j]
    return prev[n]

def lev_with_cps(cps1: List[Codepoint], cps2: List[Codepoint]) raises -> Int:
    var m = len(cps1)
    var n = len(cps2)
    var prev = List[Int]()
    var curr = List[Int]()
    for j in range(n + 1):
        prev.append(j)
        curr.append(0)
    for i in range(1, m + 1):
        curr[0] = i
        var cp1 = cps1[i - 1]
        for j in range(1, n + 1):
            var cost = 1
            if cp1 == cps2[j - 1]:
                cost = 0
            var val = min(prev[j] + 1, min(curr[j - 1] + 1, prev[j - 1] + cost))
            curr[j] = val
        for j in range(n + 1):
            prev[j] = curr[j]
    return prev[n]

def main() raises:
    var s1 = String("Receipt Total: $452.99")
    var s2 = String("Reciept Totel: $452.89")
    var cps1 = List[Codepoint]()
    for c in s1.codepoints():
        cps1.append(c)
    var cps2 = List[Codepoint]()
    for c in s2.codepoints():
        cps2.append(c)

    var iters = 1000
    var t0 = perf_counter_ns()
    for _ in range(iters):
        _ = lev_with_strings(s1, s2)
    var t1 = perf_counter_ns()
    print("With String allocs: ", Float64(t1 - t0) / Float64(iters * 1000), "us")

    var t2 = perf_counter_ns()
    for _ in range(iters):
        _ = lev_with_cps(cps1, cps2)
    var t3 = perf_counter_ns()
    print("With Codepoints:    ", Float64(t3 - t2) / Float64(iters * 1000), "us")
