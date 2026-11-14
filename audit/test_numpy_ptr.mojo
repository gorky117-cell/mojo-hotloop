from std.memory import OpaquePointer
from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort

def sum_numpy_1d(py_arr: PythonObject) raises -> PythonObject:
    var ptr_int = Int(py=py_arr.ctypes.data)
    var size = Int(py=py_arr.size)
    var op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=ptr_int)
    var ptr = op.bitcast[Float64]()
    var total: Float64 = 0.0
    for i in range(size):
        total += ptr[i]
    return PythonObject(total)

@export
def PyInit_test_numpy_ptr() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("test_numpy_ptr")
        m.def_function[sum_numpy_1d]("sum_numpy_1d")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))
