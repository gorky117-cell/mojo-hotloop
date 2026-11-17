# Copyright 2026 Gaurav Kumar Singh
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
End-to-end NumPy ndarray acceleration example with Mojo Hotloop.
Demonstrates zero-copy C-pointer dispatch for 1-D C-contiguous arrays.
"""

from hotloop import hotloop


@hotloop
def exponential_decay_filter(signal: list[float], decay: float) -> float:
    """
    Computes an autoregressive recursive exponential decay filter over a 1D float array.
    Recursive loops cannot be vectorized in standard NumPy without writing custom C extensions.
    Mojo Hotloop compiles this to native SIMD-capable machine code with zero copy overhead.
    """
    n: int = len(signal)
    if n == 0:
        return 0.0

    state: float = signal[0]
    weight: float = 1.0 - decay
    for i in range(1, n):
        state = state * decay + signal[i] * weight
    return state
