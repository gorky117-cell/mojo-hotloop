# Pre-M0 credibility review

Status: PARTIAL, local documentation proposal. Base public main is 080125ec03b68a55423d426a48c112b7415f8b48. No runtime or workflow change is included. Pre-M0 is not DONE without maintainer review/approval.

## Already completed work

Public PR #6 merged prior documentation/benchmark/native-CI improvements. Existing canonical data already explained 82.4x versus 69.34x and 7.49x versus 4.96x. This review does not pretend that work was absent. Remaining defects were stale qualification/platform descriptions, historical native-array claims presented beside the corrective candidate, unverifiable universal superiority language and current-data drift.

## Claim reconciliation

| Claim | Evidence / disposition |
|---|---|
| Backtest 82.4x vs 69.34x | Different historical sessions; docs/BENCHMARKS.md already distinguishes them. Preserve both as history; current tables use the new versioned R1 dataset. |
| PII 7.49x vs 4.96x | Different payload/protocol and mean/median history. Do not combine these with current candidate measurements. |
| Historical 174x/SIMD maxima | Mismatched representation methodology is not accepted as a current comparative claim. Raw historical reports remain indexed, not promoted. |
| Beats Numba/Codon | Small historical deltas within noise do not establish superiority; current matched original-source/list comparisons explicitly retain losses. No new Codon/Cython/Pythran performance is invented. |
| Native ndarray/zero-copy | Historical route; withdrawn in the corrective candidate. Lists use validated copies and buffers/NumPy fall back. |
| Private entry equals public speed | Incorrect scope: validation/conversion and wrapper latency remain separate; public tables use public calls only. |
| PDF compiled regex | Its actual output contract fails the current fixture qualification, so it is excluded from strict ranking. |
| Universal/zero-overhead acceleration | Removed from current-facing summary. Tiny native calls may be slower than Python. |

Current README and docs/CURRENT_BENCHMARKS.md are generated from benchmarks/current_public_v0_2_1_20261122.json. The legacy generator's current CLI delegates to that dataset and checks historical report/table bytes independently. Its update mode no longer overwrites history.

## Licensing and trademark findings

LICENSE and NOTICE are unchanged. Package ownership/license declarations are existing maintainer declarations, not a new legal certification.

The [published trademark policy](https://www.modular.com/legal/trademark) is accessible and calls for the existing attribution for licensees. Independence and no endorsement remain prominent; no logo or exclusive grant is asserted. Applicability of a trademark/software license is not granted by this audit.

Current [upstream source LICENSE](https://github.com/modular/modular/blob/main/LICENSE) and [MAX terms](https://www.modular.com/legal/max-license) distinguish components. Installed mojo, mojo-compiler and mojo-lldb-libs 1.2.0 metadata instead names LicenseRef-MAX-Platform-Software-License. That exact binary-terms applicability needs owner/vendor clarification before claiming it is all Apache or redistributing generated SDK-containing artifacts. No SDK binary is bundled by the reviewed Hotloop wheel. No automatic license approval is made.

THIRD_PARTY_NOTICES now describes the actual banded Levenshtein OCR and closest-point/ray algorithms, correcting unrelated Myers/triangle-intersection descriptions. It avoids unsupported global ownership/public-domain certification.

## Repository structure and acceptance

Historical paths, raw data, immutable tags and packaging/legal files stay in place. A navigable history index supplies version/contract context; moving old files would introduce avoidable link/package risk.

This separate diff updates README, qualification banners, notices, history index, versioned public data and documentation generators. Required checks: generated-table consistency, historical byte comparison, local links, adversarial AST tests and a no-runtime/no-workflow diff assertion. External URLs and private research commits must not be claimed publicly accessible merely because a local report exists.

Remaining owner actions: review this diff, resolve external SDK-term wording, approve DCO attribution and authorize a focused docs PR. Earlier approved PR #6 does not approve this new proposal. No push, publication or repository-setting change occurred.
