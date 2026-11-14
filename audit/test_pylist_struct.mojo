from std.memory import OpaquePointer
from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort

struct _PyFloatList(Sized):
    var _op: OpaquePointer[MutUntrackedOrigin]
    var _len: Int
    var _owned: List[Float64]

    @always_inline
    def __init__(out self, py_obj: PythonObject) raises:
        var builtins = Python.import_module("builtins")
        self._len = Int(py=py_obj.__len__())
        if Bool(py=builtins.hasattr(py_obj, "ctypes")):
            var addr = Int(py=py_obj.ctypes.data)
            self._op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=addr)
            self._owned = List[Float64]()
        else:
            self._owned = List[Float64]()
            for i in range(self._len):
                self._owned.append(Float64(py=py_obj[i]))
            self._op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=Int(self._owned.unsafe_ptr()))

    @always_inline
    def __len__(self) -> Int:
        return self._len

    @always_inline
    def __getitem__(self, idx: Int) -> Float64:
        var i = idx
        if i < 0:
            i += self._len
        var ptr = self._op.unsafe_bitcast[Float64]()
        return ptr[i]

@always_inline
def _len(l: _PyFloatList) -> Int:
    return len(l)

@export
def PyInit_test_pylist() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("test_pylist")
        m.def_function[sum_float_list]("sum_float_list")
        return m.finalize()
    except e:
        abort(String("error: ", e))

def sum_float_list(arg0: PythonObject) raises -> PythonObject:
    var xs = _PyFloatList(arg0)
    var total: Float64 = 0.0
    for i in range(len(xs)):
        total += xs[i]
    return PythonObject(total)
