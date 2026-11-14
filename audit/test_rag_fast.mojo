from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.collections import List
from std.os import abort
from std.time import perf_counter_ns

@export
def PyInit_fast_rag() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast_rag")
        m.def_function[fast_chunk_document]("chunk_document")
        return m.finalize()
    except e:
        abort(String("error: ", e))

def fast_chunk_document(arg0: PythonObject, arg1: PythonObject, arg2: PythonObject) raises -> PythonObject:
    var text_str = String(py=arg0)
    var chunk_size = Int(py=arg1)
    var chunk_overlap = Int(py=arg2)
    var n = len(text_str.codepoints())
    var _builtins = Python.import_module("builtins")
    var _py_res = _builtins.list()
    if n == 0 or chunk_size <= 0:
        return _py_res

    # Check if text is ASCII (common case)
    var is_ascii = (text_str.byte_length() == n)
    var step = chunk_size - chunk_overlap
    if step <= 0:
        step = 1

    if is_ascii:
        var bytes = text_str.as_bytes()
        var start = 0
        while start < n:
            var ideal_end = start + chunk_size
            if ideal_end >= n:
                _py_res.append(arg0[start:n])
                break
            var lookback = ideal_end - chunk_overlap
            if lookback < start:
                lookback = start
            var boundary = -1
            var idx = ideal_end
            while idx > lookback:
                var b = bytes[idx]
                if b == 32 or b == 10 or b == 9:
                    boundary = idx
                    break
                idx -= 1
            var end = ideal_end
            if boundary > start:
                end = boundary
            _py_res.append(arg0[start:end])
            var next_start = end - chunk_overlap
            if next_start <= start:
                next_start = start + step
                if next_start <= start:
                    next_start = start + 1
            start = next_start
    else:
        var cps = List[Codepoint]()
        for cp in text_str.codepoints():
            cps.append(cp)
        var start = 0
        while start < n:
            var ideal_end = start + chunk_size
            if ideal_end >= n:
                _py_res.append(arg0[start:n])
                break
            var lookback = ideal_end - chunk_overlap
            if lookback < start:
                lookback = start
            var boundary = -1
            var idx = ideal_end
            while idx > lookback:
                var cp = cps[idx]
                var c = Int(cp)
                if c == 32 or c == 10 or c == 9:
                    boundary = idx
                    break
                idx -= 1
            var end = ideal_end
            if boundary > start:
                end = boundary
            _py_res.append(arg0[start:end])
            var next_start = end - chunk_overlap
            if next_start <= start:
                next_start = start + step
                if next_start <= start:
                    next_start = start + 1
            start = next_start

    return _py_res
