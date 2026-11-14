from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort

# 1. Codepoint length
def native_codepoint_len(py_s: PythonObject) raises -> PythonObject:
    var s = String(py=py_s)
    return PythonObject(len(s.codepoints()))

# 2. Codepoint at index (supporting negative indexing)
def native_codepoint_at(py_s: PythonObject, py_idx: PythonObject) raises -> PythonObject:
    var s = String(py=py_s)
    var idx = Int(py=py_idx)
    var n = len(s.codepoints())
    var real_idx = idx if idx >= 0 else n + idx
    if real_idx < 0 or real_idx >= n:
        raise Error("HOTLOOP_INDEX_ERROR: string index out of range")
    return PythonObject(String(s[codepoint=real_idx]))

# 3. Codepoint slice
def native_codepoint_slice(py_s: PythonObject, py_start: PythonObject, py_end: PythonObject) raises -> PythonObject:
    var s = String(py=py_s)
    var start = Int(py=py_start)
    var end = Int(py=py_end)
    var n = len(s.codepoints())
    
    var real_start = start if start >= 0 else n + start
    if real_start < 0:
        real_start = 0
    if real_start > n:
        real_start = n
        
    var real_end = end if end >= 0 else n + end
    if real_end < 0:
        real_end = 0
    if real_end > n:
        real_end = n
        
    if real_start >= real_end:
        return PythonObject("")
        
    return PythonObject(String(s[codepoint=real_start:real_end]))

# 4. Codepoint to byte offset mapping
def native_codepoint_to_byte_offsets(py_s: PythonObject) raises -> PythonObject:
    var s = String(py=py_s)
    var builtins = Python.import_module("builtins")
    var py_list = builtins.list()
    
    var byte_offset = 0
    var ptr = s.unsafe_ptr()
    var byte_len = s.byte_length()
    
    for i in range(byte_len):
        var b = ptr[i]
        # In UTF-8, a byte is a codepoint start if (b & 0xC0) != 0x80
        if (b & 0xC0) != 0x80:
            py_list.append(i)
            
    return py_list

# 5. String iteration & reconstruction
def native_reverse_codepoints(py_s: PythonObject) raises -> PythonObject:
    var s = String(py=py_s)
    var n = len(s.codepoints())
    var out = String()
    for i in range(n - 1, -1, -1):
        out.write(s[codepoint=i])
    return PythonObject(out)

@export
def PyInit_unicode_primitives() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("unicode_primitives")
        m.def_function[native_codepoint_len]("native_codepoint_len")
        m.def_function[native_codepoint_at]("native_codepoint_at")
        m.def_function[native_codepoint_slice]("native_codepoint_slice")
        m.def_function[native_codepoint_to_byte_offsets]("native_codepoint_to_byte_offsets")
        m.def_function[native_reverse_codepoints]("native_reverse_codepoints")
        return m.finalize()
    except e:
        abort(String("error: ", e))
