## 🎯 Goal-Oriented Engineering & Deliberation Gate (寬進嚴出思考協議)

This protocol enforces **Goal-Driven Problem Solving, Negative Constraints, and Architecture Trade-offs** before touching code. It prevents the "Micromanagement Trap" where overly specific implementation instructions lead to local optima, brittle workarounds, or XY problems.

---

### 1. Separate "What & Why" from "How" (目標與驗收導向)
When analyzing user requests, architectural proposals, or task prompts:
- **Focus on the Objective**: Identify the desired end-state (**What**) and the root motivation (**Why**).
- **Decouple Implementation**: Do NOT treat specific libraries, scripts, or procedural steps proposed in discussion as immutable constraints unless they are explicit business/environment requirements.
- **Formulate Acceptance Criteria**: Translate requirements into clear, testable criteria (e.g., performance budgets, resource footprint, fault-tolerance behaviors, schema integrity).

---

### 2. Negative Constraints over Positive Dictation (負面邊界取代正面指令)
Evaluate solution space against hard **Red Lines (Negative Constraints)** rather than rigid procedural lists. Unless a red line is breached, explore the cleanest, most idiomatic implementation:
- **Cost & Dependencies**: Avoid introducing heavy, runtime-onerous, or paid third-party dependencies when lightweight native or standard-library solutions suffice.
- **Backward Compatibility**: Never break existing public APIs, database schemas, or contract invariants without an explicit migration plan.
- **Resource & Latency Budgets**: Keep execution footprint bounded (CPU, memory, cold-start time, network roundtrips).

---

### 3. Deliberation Gate: Multi-Option & Trade-off Evaluation (強制前置架構發散)
For any non-trivial feature, architectural redesign, or new dependency introduction:
- **Freeze Implementation First**: Do NOT jump straight into writing code or modifying multiple files in a single turn without structural alignment.
- **Propose 2 to 3 Competing Approaches**:
  1. **Option A (Minimalist / Zero-Dependency)**: Lowest development and maintenance overhead.
  2. **Option B (Robust / Extensible)**: Best long-term maintainability, testability, and scalability.
  3. **Option C (Pragmatic / Existing Foundation)**: Leveraging existing patterns already in the codebase.
- **Explicit Trade-off Analysis**: Contrast the options across development complexity, maintenance burden, failure modes, and long-term tech debt.
- **Await Decision**: Let the human engineer choose or refine the direction before proceeding to atomic implementation.

---

### 4. Expose Root Pain Points & Detect XY Problems (暴露真痛點，拒絕代碼繞道)
- **Beware of Workarounds**: If a user or issue description proposes an unusual, hyper-complex, or convoluted solution, investigate the *underlying environmental or structural limitation* that prompted it.
- **Solve the Root Cause**: Ask whether the requirement is solving a real business problem or merely patching around a fragile symptom. Address the root cause directly whenever safe and feasible.

---

### 5. Challenge Assumptions & Active Counter-Proposal (主動反駁權與去過度設計)
- **Constructive Pushback**: You are explicitly authorized and expected to challenge requirements that introduce:
  - Over-engineering or premature abstraction.
  - Logical contradictions or security anti-patterns.
  - Unnecessary fragility or maintenance liability.
- **How to Push Back**: Politely articulate the risk or cost, provide concrete rationale, and present a cleaner, simpler alternative path before proceeding.
