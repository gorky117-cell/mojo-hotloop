import sys
import numpy as np

sys.path.insert(0, '/home/gaurav/mojo-hotloop/audit')
import test_pylist

arr_np = np.array([1.5, 2.5, 3.5, 4.5], dtype=np.float64)
arr_list = [1.5, 2.5, 3.5, 4.5]

res_np = test_pylist.sum_float_list(arr_np)
res_list = test_pylist.sum_float_list(arr_list)

print('NumPy sum:', res_np)
print('List sum: ', res_list)
assert res_np == 12.0
assert res_list == 12.0
print('BOTH WORKED PERFECTLY!')
