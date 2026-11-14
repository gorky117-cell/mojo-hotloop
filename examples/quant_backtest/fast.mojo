from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort
import std.math as math

@export
def PyInit_fast() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast")
        m.def_function[stateful_trailing_backtest]("stateful_trailing_backtest")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def stateful_trailing_backtest(arg0: PythonObject, arg1: PythonObject, arg2: PythonObject, arg3: PythonObject) raises -> PythonObject:
    var ticks = Int(py=arg0)
    var start_price = Float64(py=arg1)
    var stop_pct = Float64(py=arg2)
    var fee_rate = Float64(py=arg3)
    var res = _native_stateful_trailing_backtest(ticks, start_price, stop_pct, fee_rate)
    return PythonObject(res)

def _native_stateful_trailing_backtest(ticks: Int, start_price: Float64, stop_pct: Float64, fee_rate: Float64) -> Float64:
    if (ticks <= 0):
        return start_price
    var price = start_price
    var peak_price = start_price
    var cash = 0.0
    var units = 1.0
    var in_position = True
    var cooldown = 0
    var lcg_state = 42
    for _ in range(ticks):
        lcg_state = (((1664525 * lcg_state) + 1013904223) & 4294967295)
        var rand_val = (Float64(lcg_state) / Float64(4294967296.0))
        price = (price * (1.0 + ((rand_val - 0.5) * 0.02)))
        if in_position:
            if (price > peak_price):
                peak_price = price
            elif ((stop_pct > 0.0) and (price <= (peak_price * (1.0 - stop_pct)))):
                cash = ((units * price) * (1.0 - fee_rate))
                units = 0.0
                in_position = False
                cooldown = 5
        else:
            if (cooldown > 0):
                cooldown -= 1
            if (cooldown == 0):
                units = (Float64((cash * (1.0 - fee_rate))) / Float64(price))
                cash = 0.0
                in_position = True
                peak_price = price
    if in_position:
        return (units * price)
    else:
        return cash
