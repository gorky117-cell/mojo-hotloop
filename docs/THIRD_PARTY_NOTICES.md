# Third-party notices and external toolchain

The Hotloop Python distribution declares Apache-2.0 for its own code and has no mandatory third-party Python runtime dependency in the corrective candidate. NumPy is an optional external dependency (BSD-3-Clause); the candidate preserves its Python semantics through fallback. Historical descriptions of automatic ndarray zero-copy admission are not current support promises.

Setuptools is the external build backend (MIT). Optional benchmarking tools such as Numba, RapidFuzz and the manually written C++ references are comparison tools, not automatic Hotloop output or required inference services.

## External Mojo / MAX SDK & Compiled Artifacts

1. **Hotloop package (`wheel` / `sdist`):** Distributed under Apache-2.0 with **zero** Modular, Mojo, or MAX binaries bundled inside the package.
2. **Separate local SDK usage (`hotloop build`):** The Mojo SDK/compiler is independently installed by the user. Installed `mojo`, `mojo-compiler`, `mojo-compiler-mojo-libs`, `mojo-lldb-libs` (`1.2.0`), and `modular` (`26.7.0`) package metadata specifies `LicenseRef-MAX-Platform-Software-License` without shipping license text inside `.dist-info`. Current [upstream source licensing](https://github.com/modular/modular/blob/main/LICENSE) distinguishes Apache-2.0-with-LLVM-exception components from [MAX terms](https://www.modular.com/legal/max-license); those version-specific terms must not be conflated. No unverified Modular license or redistribution right is assumed or claimed.
3. **Do not redistribute compiled Mojo `.so` artifacts:** Locally compiled native extensions (for example `fast.so`) incorporate Mojo-emitted object code and dynamically link Modular SDK shared libraries (`libKGENCompilerRTShared.so`, `libMSupportGlobals.so`, `libAsyncRTRuntimeGlobals.so`). Precompiled `.so` binaries are **not** Apache-2.0 redistributables and must **not** be redistributed; build native modules strictly for local execution under your own installed SDK license.

## Modular Trademark Attribution

Mojo Hotloop is an independent open-source project and is not affiliated with, operated by, sponsored by, or endorsed by Modular, Inc. MAX® and Mojo® are trademarks or registered trademarks of Modular, Inc., referenced solely to identify the external compiler toolchain. No trademark license or endorsement is claimed (see [Modular trademark policy](https://www.modular.com/legal/trademark)).

## Application algorithm descriptions

These descriptions follow the actual Python sources, rather than certifying ownership or patent status:

- OCR Matcher: bounded/banded Levenshtein dynamic programming; not a claim that the source implements Myers' diff algorithm.
- AR Spatial: closest point to a ray among point coordinates; not a triangle-intersection implementation.
- Geographic Distance: sequential Haversine calculations.
- Quantitative Backtest: stateful price/stop simulation using a linear congruential generator.
- PII: Luhn and Verhoeff checksum validation with text token scanning.

Original contribution ownership and any future redistribution remain subject to maintainer review and existing Apache/DCO obligations. No SDK binary, precompiled `.so` artifact, logo, or vendor endorsement is distributed by this package.
