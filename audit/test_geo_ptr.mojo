from std.memory import OpaquePointer
from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort
import std.math as math
from std.time import perf_counter_ns

@always_inline
def haversine_kernel(lats_ptr: OpaquePointer[MutUntrackedOrigin], lons_ptr: OpaquePointer[MutUntrackedOrigin], n: Int) -> Float64:
    if n <= 1:
        return 0.0
    var lats = lats_ptr.unsafe_bitcast[Float64]()
    var lons = lons_ptr.unsafe_bitcast[Float64]()
    var total_dist: Float64 = 0.0
    var r: Float64 = 6371.0
    var rad_factor: Float64 = 3.141592653589793 / 180.0
    for i in range(1, n):
        var lat1 = lats[i - 1] * rad_factor
        var lon1 = lons[i - 1] * rad_factor
        var lat2 = lats[i] * rad_factor
        var lon2 = lons[i] * rad_factor
        var dlat = lat2 - lat1
        var dlon = lon2 - lon1
        var half_dlat = dlat * 0.5
        var half_dlon = dlon * 0.5
        var sin_dlat = math.sin(half_dlat)
        var sin_dlon = math.sin(half_dlon)
        var a = sin_dlat * sin_dlat + math.cos(lat1) * math.cos(lat2) * sin_dlon * sin_dlon
        if a > 1.0:
            a = 1.0
        elif a < 0.0:
            a = 0.0
        var c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        total_dist += r * c
    return total_dist

def fast_haversine(arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var builtins = Python.import_module("builtins")
    var n = Int(py=arg0.__len__())
    if n <= 1:
        return PythonObject(0.0)

    # Check if numpy array (has ctypes attribute)
    var has_ctypes = Bool(py=builtins.hasattr(arg0, "ctypes"))
    if has_ctypes:
        var lats_addr = Int(py=arg0.ctypes.data)
        var lons_addr = Int(py=arg1.ctypes.data)
        var lats_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=lats_addr)
        var lons_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=lons_addr)
        var res = haversine_kernel(lats_op, lons_op, n)
        return PythonObject(res)
    else:
        # Fallback to copy list
        var lats = List[Float64]()
        for i in range(n):
            lats.append(Float64(py=arg0[i]))
        var lons = List[Float64]()
        for i in range(n):
            lons.append(Float64(py=arg1[i]))
        var lats_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=Int(lats.unsafe_ptr()))
        var lons_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=Int(lons.unsafe_ptr()))
        var res = haversine_kernel(lats_op, lons_op, n)
        return PythonObject(res)

@export
def PyInit_fast_geo() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast_geo")
        m.def_function[fast_haversine]("accumulate_haversine_distance")
        return m.finalize()
    except e:
        abort(String("error: ", e))
