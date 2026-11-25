# Root cause frozen before compiler edits

Baseline 582afcdaa18802df48e81a3acd80a19cee899c7e.
The new 390-observation baseline gate found 108 incorrect observations and 18
correct helper-list fallbacks/refusals initially given an over-optimistic route
expectation. The latter policy is corrected to the existing conservative contract;
no compiler support or existing test is changed.

1. _checked_index checks UInt(idx)<UInt(n), then negative normalization, then
raises HOTLOOP_INDEX_ERROR: index out of range. It serves both _PyStr and list
lowering. The decorator forwards the tag payload unchanged as Python IndexError.
List reads need list index out of range; changing the shared helper/bridge globally
would alter non-list and intentional exceptions.

2. Plain subscript assignment uses the read-index lowering, so local native list
stores also use the wrong message. CPython stores require list assignment index
out of range; augmented stores first read and need the read message.

3. Mojo evaluates the emitted indexed assignment target before its RHS. In
xs[bad_index] = 4 // 0, the baseline raises IndexError instead of CPython's
ZeroDivisionError. Materialize the RHS once before target/index evaluation.
Do not move augmented-assignment RHS before its existing index/read check.

Native input-list mutations remain restricted. Explicit raise is unsupported
by this AST and correctly executes in Python or refuses strict mode. Print and
custom-index side effects similarly remain fallback/refusal, with no replay.
The existing helper-produced list return is unqualified; do not expand it.
