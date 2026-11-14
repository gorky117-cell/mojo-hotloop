from std.memory import OpaquePointer
from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort
import std.math as math
from std.time import perf_counter_ns

@always_inline
def ar_kernel(
    xs_ptr: OpaquePointer[MutUntrackedOrigin],
    ys_ptr: OpaquePointer[MutUntrackedOrigin],
    zs_ptr: OpaquePointer[MutUntrackedOrigin],
    n: Int,
    ray_ox: Float64,
    ray_oy: Float64,
    ray_oz: Float64,
    ray_dx: Float64,
    ray_dy: Float64,
    ray_dz: Float64,
) raises -> Int:
    if n == 0:
        return -1

    var dir_len_sq = ray_dx * ray_dx + ray_dy * ray_dy + ray_dz * ray_dz
    if dir_len_sq <= 0.0:
        return -1

    var inv_len = 1.0 / math.sqrt(dir_len_sq)
    var dx = ray_dx * inv_len
    var dy = ray_dy * inv_len
    var dz = ray_dz * inv_len

    var best_idx = -1
    var min_dist_sq: Float64 = 1e30

    var xs = xs_ptr.unsafe_bitcast[Float64]()
    var ys = ys_ptr.unsafe_bitcast[Float64]()
    var zs = zs_ptr.unsafe_bitcast[Float64]()

    for i in range(n):
        var vx = xs[i] - ray_ox
        var vy = ys[i] - ray_oy
        var vz = zs[i] - ray_oz

        var t = vx * dx + vy * dy + vz * dz
        if t < 0.0:
            t = 0.0

        var wx = vx - t * dx
        var wy = vy - t * dy
        var wz = vz - t * dz

        var dist_sq = wx * wx + wy * wy + wz * wz
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            best_idx = i

    return best_idx

def fast_find_closest_point_to_ray(
    arg0: PythonObject,
    arg1: PythonObject,
    arg2: PythonObject,
    arg3: PythonObject,
    arg4: PythonObject,
    arg5: PythonObject,
    arg6: PythonObject,
    arg7: PythonObject,
    arg8: PythonObject,
) raises -> PythonObject:
    var builtins = Python.import_module("builtins")
    var n = Int(py=arg0.__len__())
    var ox = Float64(py=arg3)
    var oy = Float64(py=arg4)
    var oz = Float64(py=arg5)
    var dx = Float64(py=arg6)
    var dy = Float64(py=arg7)
    var dz = Float64(py=arg8)

    var has_ctypes = Bool(py=builtins.hasattr(arg0, "ctypes"))
    if has_ctypes:
        var x_addr = Int(py=arg0.ctypes.data)
        var y_addr = Int(py=arg1.ctypes.data)
        var z_addr = Int(py=arg2.ctypes.data)
        var x_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=x_addr)
        var y_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=y_addr)
        var z_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=z_addr)
        var res = ar_kernel(x_op, y_op, z_op, n, ox, oy, oz, dx, dy, dz)
        return PythonObject(res)
    else:
        var xs = List[Float64]()
        for i in range(n):
            xs.append(Float64(py=arg0[i]))
        var ys = List[Float64]()
        for i in range(n):
            ys.append(Float64(py=arg1[i]))
        var zs = List[Float64]()
        for i in range(n):
            zs.append(Float64(py=arg2[i]))
        var x_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=Int(xs.unsafe_ptr()))
        var y_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=Int(ys.unsafe_ptr()))
        var z_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=Int(zs.unsafe_ptr()))
        var res = ar_kernel(x_op, y_op, z_op, n, ox, oy, oz, dx, dy, dz)
        return PythonObject(res)

@export
def PyInit_fast_ar() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast_ar")
        m.def_function[fast_find_closest_point_to_ray]("find_closest_point_to_ray")
        return m.finalize()
    except e:
        abort(String("error: ", e))
