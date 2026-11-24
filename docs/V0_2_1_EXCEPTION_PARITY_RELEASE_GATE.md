# v0.2.1 exception-parity release gate

Local engineering candidate, 24 November 2026. Full verification is in progress;
this intermediate source commit is not a release approval.

Runtime baseline: 582afcdaa18802df48e81a3acd80a19cee899c7e.
Preserved performance diagnosis: 42472fef4d0631d34ec7e463d8b6555fb082d2c5.

The generated generic bounds helper previously emitted "index out of range".
Proven Python-list reads now use a list-specific checked helper; plain stores
use the assignment-specific message. Augmented assignment retains a read check.
The generic helper and Python exception bridge are unchanged. Plain stores also
materialize the RHS once before evaluating their target, preserving CPython order.

The focused public-interface gate passes 390 observations: 236 correct native,
125 correct Python fallbacks and 29 expected strict refusals. No wrong result.
This is behavioral coverage, not a performance claim. Unsupported explicit
raises and effectful helpers remain Python fallback or strict refusal.

The final record will replace this provisional document after installed-artifact,
security, application, historical compatibility and performance verification.
Final local report revision: $Format:%H$.
