# Engineering Ethics & Professional Practice — Mojo Hotloop v0.1.0

The Mojo Hotloop project voluntarily aligns its engineering standards, contributor conduct, benchmark reporting, and governance with established international computing ethics frameworks:

1. The **ACM Code of Ethics and Professional Conduct** ([acm.org/code-of-ethics](https://www.acm.org/code-of-ethics))
2. The **ACM/IEEE-CS Software Engineering Code of Ethics and Professional Practice** ([computer.org/education/code-of-ethics](https://www.computer.org/education/code-of-ethics))

> [!NOTE]
> **Voluntary Professional Alignment**: This document reflects a voluntary commitment to ethical, rigorous, and transparent software engineering. It does **not** claim formal certification, accreditation, sponsorship, or organizational endorsement by ACM or IEEE. These ethical guidelines guide contributor conduct and project governance without altering or restricting the rights granted under the [Apache License 2.0](file:///home/gaurav/mojo-hotloop/LICENSE).

---

## Part 1: ACM Code of Ethics — Four-Part Framework

### I. General Ethical Principles

1. **Contribute to Society and Human Well-Being (ACM 1.1)**:
   - Provide accessible, transparent, and energy-efficient computing tools. By optimizing hot computational loops natively and reducing unnecessary CPU cycles, the project contributes to lower operational and computational resource consumption.
2. **Avoid Harm (ACM 1.2)**:
   - Protect memory safety and execution integrity. The compiler must reject untyped or dangerous constructs cleanly, guard against buffer overflows, and gracefully fall back to safe CPython rather than crash or corrupt host memory.
3. **Be Honest and Trustworthy (ACM 1.3)**:
   - Report benchmark timings, memory characteristics, and compiler limitations with scientific rigor. Never fabricate performance numbers, suppress unfavorable benchmark outcomes, or present micro-benchmarks as universal speedups.
4. **Be Fair and Take Action Not to Discriminate (ACM 1.4)**:
   - Welcome contributors across all backgrounds, identities, skill levels, and affiliations under our [Contributor Covenant Code of Conduct](file:///home/gaurav/mojo-hotloop/CODE_OF_CONDUCT.md).
5. **Respect the Work Required to Produce New Ideas, Inventions, Creative Works, and Computing Artifacts (ACM 1.5)**:
   - Honor copyright, licenses, and patent limitations. Attribute algorithmic provenance meticulously (e.g. Myers, Luhn, Verhoeff, Haversine, Knuth LCG, Möller–Trumbore) and respect third-party intellectual property and Modular trademark policies.
6. **Respect Privacy (ACM 1.6)**:
   - The transpiler operates strictly offline (`dependencies = []`). It transfers zero user source code, runtime arguments, telemetry, or system information over the network.
7. **Honor Confidentiality (ACM 1.7)**:
   - Treat private vulnerability reports, security disclosures, and reporter identities with strict confidentiality in accordance with [SECURITY.md](file:///home/gaurav/mojo-hotloop/SECURITY.md).

---

### II. Professional Responsibilities

1. **Strive to Achieve High Quality in Both the Processes and Products of Professional Work (ACM 2.1)**:
   - Enforce rigorous testing across adversarial inputs, extreme numerical boundaries, and memory leak regression suites prior to any release candidate.
2. **Maintain High Standards of Professional Competence, Conduct, and Ethical Practice (ACM 2.2)**:
   - Follow verified compiler design patterns, deterministic AST transformations, and documented C-ABI interop standards.
3. **Know and Respect Existing Rules Pertaining to Professional Work (ACM 2.3)**:
   - Comply with open-source legal requirements (Apache-2.0, DCO sign-offs, SPDX identifiers, PEP 639 packaging metadata).
4. **Accept and Provide Appropriate Professional Review (ACM 2.4)**:
   - All code contributions undergo constructive, transparent peer review. Maintainers and contributors welcome critique and reproducible counter-evidence.
5. **Give Comprehensive and Thorough Evaluations of Computer Systems and Their Impacts, Including Analysis of Possible Risks (ACM 2.5)**:
   - Disclose compiler boundaries, unsupported syntax, FFI allocation bottlenecks, and edge cases in public documentation ([docs/SUPPORTED_SYNTAX.md](file:///home/gaurav/mojo-hotloop/docs/SUPPORTED_SYNTAX.md) and [docs/BENCHMARKS.md](file:///home/gaurav/mojo-hotloop/docs/BENCHMARKS.md)).
6. **Perform Work Only in Areas of Competence (ACM 2.6)**:
   - Maintain focus on Python-to-Mojo AST compilation for numerical and text hot loops. Do not claim universal general-purpose Python language compilation.
7. **Foster Public Awareness and Understanding of Computing, Its Technologies, and Their Consequences (ACM 2.7)**:
   - Provide educational documentation, clear execution tracing, and transparent compiler diagnostics explaining why native vs. fallback execution occurred.
8. **Access Computing and Communication Resources Only When Authorized or When Compelled by the Public Good (ACM 2.8)**:
   - Respect user machine boundaries; do not write outside the project cache directory (`__mojocache__`), execute unauthorized shell commands, or run arbitrary code.
9. **Design and Implement Systems That Are Robustly and Usably Secure (ACM 2.9)**:
   - Implement defense-in-depth: ELF magic header validation before dynamic library loading, atomic file writing with `os.replace`, SHA-256 source code verification in manifests, and strict subprocess list arguments (`shell=False`).

---

### III. Professional Leadership Principles

1. **Ensure That the Public Good Is the Central Concern During All Professional Computing Work (ACM 3.1)**:
   - Prioritize correctness and security over raw benchmark speedups. A faster result that produces incorrect calculations or memory faults is fundamentally unacceptable.
2. **Articulate, Encourage Acceptance of, and Evaluate Fulfillment of Social Responsibilities (ACM 3.2)**:
   - Encourage responsible development and application of acceleration techniques.
3. **Manage Personnel and Resources to Enhance the Quality of Working Life (ACM 3.3)**:
   - Foster a supportive, low-friction, welcoming community where contributor time and effort are valued.
4. **Articulate, Apply, and Support Policies and Processes That Reflect the Principles of the Code (ACM 3.4)**:
   - Maintain clear guidelines in `CONTRIBUTING.md`, enforce reproducible benchmark evidence, and uphold issue/PR templates.
5. **Create Opportunities for Members of the Organization or Group to Grow as Professionals (ACM 3.5)**:
   - Label beginner-friendly issues (`good first issue`), offer constructive feedback on PRs, and document compiler internals thoroughly.
6. **Use Care When Modifying or Retiring Systems (ACM 3.6)**:
   - Maintain observable backward compatibility and deprecation notices before altering syntax support or public interfaces.
7. **Recognize and Take Special Care of Systems That Become Integrated Into the Infrastructure of Society (ACM 3.7)**:
   - Ensure that if Mojo Hotloop is adopted in scientific or quantitative pipelines, its numerical results remain deterministic, reproducible, and verifiable.

---

### IV. Compliance with the Code

1. **Uphold, Promote, and Respect the Principles of the Code (ACM 4.1)**:
   - Project maintainers and contributors commit to these principles as an integral standard of quality engineering.
2. **Treat Violations of the Code as Inconsistent with Membership in the Community (ACM 4.2)**:
   - Plagiarism, data fabrication, deceptive benchmarking, harassment, or malicious code injection will result in immediate removal, PR rejection, or banning in accordance with our enforcement guidelines.
3. **Fair Reporting & Remediation**:
   - Provide confidential reporting channels via GitHub Security Advisories for security, privacy, or ethical misconduct.
   - Investigate all reports objectively, document findings, and apply proportionate corrective action without retaliation.

---

## Part 2: ACM/IEEE-CS Software Engineering Code of Ethics

Mojo Hotloop adopts the **Eight Principles** of the ACM/IEEE-CS Software Engineering Code:

| Principle | Name | Project Application |
|---|---|---|
| **1** | **PUBLIC** | Software engineers shall act consistently with the public interest. We prioritize numerical correctness, data integrity, and safety over speedup figures. |
| **2** | **CLIENT AND EMPLOYER** | Software engineers shall act in a manner that is in the best interests of their client, employer, and the public. We provide dependable, auditable, offline tools with predictable behavior. |
| **3** | **PRODUCT** | Software engineers shall ensure that their products and related modifications meet the highest professional standards possible. Rigorous adversarial testing, 7,220+ verified test cases, zero memory leaks, and transparent fallback. |
| **4** | **JUDGMENT** | Software engineers shall maintain integrity and independence in their professional judgment. We do not alter benchmark results, select biased baselines, or distort competitor comparisons. |
| **5** | **MANAGEMENT** | Software engineering managers and leaders shall subscribe to and promote an ethical approach to the management of software development and maintenance. Open, accountable governance with documented review procedures. |
| **6** | **PROFESSION** | Software engineers shall advance the integrity and reputation of the profession consistent with the public interest. Transparent open-source practices under Apache-2.0, DCO sign-offs, and complete technical provenance. |
| **7** | **COLLEAGUES** | Software engineers shall be fair to and supportive of their colleagues. Respectful code reviews, Contributor Covenant 2.1 enforcement, and proper attribution for all contributions. |
| **8** | **SELF** | Software engineers shall participate in lifelong learning regarding the practice of their profession and promote an ethical approach to the practice of the profession. Continuous learning from upstream Mojo/LLVM advances and open collaboration. |

---

## Part 3: Relationship to Apache-2.0 License

- These engineering ethics guidelines represent a **voluntary professional covenant** governing project governance, contributor review, and scientific integrity.
- They **do not modify, restrict, or condition** the legal permissions granted by the [Apache License 2.0](file:///home/gaurav/mojo-hotloop/LICENSE). Downstream users, commercial entities, academics, and community forks retain the full legal rights granted by the Apache-2.0 license.
