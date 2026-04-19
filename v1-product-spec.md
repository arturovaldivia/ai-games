# Game Refactor Autopilot - v1 Product Spec

## 1. Product Summary
Game Refactor Autopilot v1 converts an existing web game project (HTML, JS, CSS, assets) into a modular architecture aligned with project guidelines, while preserving user-facing behavior and feel with minimal user supervision.

Primary outcome:
- Produce a working modularized project plus parity evidence against the original experience.

## 2. Goals and Non-Goals
### 2.1 Goals
- Ingest a game folder and auto-detect entrypoints, assets, and runtime dependencies.
- Decompose monolith code into modules, contracts, state ownership, and recipe artifacts.
- Generate a playable modular build.
- Preserve or intentionally replicate user-facing experience via measurable parity gates.
- Require user input only at bounded checkpoints.
- Emit complete audit artifacts for traceability and rollback.

### 2.2 Non-Goals (v1)
- Full multi-language support beyond HTML/CSS/JS browser games.
- Real-time collaborative editing workflows.
- Automatic redesign of game art direction.
- Multiplayer network architecture migration.

## 3. Target Users
- Technical product teams modernizing legacy web games.
- Engineering leads enforcing architecture standards.
- Small studios wanting automated refactor with guardrails.

## 4. User Problems Solved
- Manual refactor is slow and risky.
- Architecture rewrites often lose UX fidelity.
- Implicit dependencies in monoliths are hard to identify.
- Teams need confidence and rollback when automation makes mistakes.

## 5. Scope (v1)
### 5.1 In Scope
- Single-project local workspace processing.
- Guided autonomous refactor pipeline.
- Human checkpoints for ambiguity/high-risk decisions.
- Functional, interaction, and perceptual parity validation.
- Evidence report and migration artifacts.

### 5.2 Out of Scope
- Cloud orchestration for massive batch portfolio migration.
- Native mobile game engines.
- Auto-translation of language/runtime families.

## 6. Inputs and Outputs
### 6.1 Required Inputs
- Workspace path containing game source.
- Target guidelines profile (modular architecture contract).
- Baseline entry URL/file and run command (auto-detected with override).

### 6.2 Optional Inputs
- Priority weighting: functional vs interaction vs perceptual parity.
- Risk tolerance profile: conservative, balanced, aggressive.
- Allowed infra changes (serve root, path rewrites, bundling changes).

### 6.3 Outputs
- Modularized source tree.
- Decomposition artifacts:
  - module-registry
  - state-ownership
  - event-catalog
  - recipe
  - source-map
  - reconstruction-manifest
- Parity reports with evidence.
- Change log and rollback checkpoints.
- Final migration summary.

## 7. Product Workflow
### 7.1 Stage A: Discovery
System actions:
- Scan workspace for entrypoints and runtime graph.
- Detect screens, controls, assets, events, and stateful hotspots.

Outputs:
- discovery-report.json
- run profile and inferred serve strategy.

### 7.2 Stage B: Baseline Capture
System actions:
- Run original game in browser automation.
- Capture state transitions, screenshots, UI snapshots, and event traces.

Outputs:
- baseline bundle (screens, traces, interaction scripts).

### 7.3 Stage C: Decomposition Plan
System actions:
- Generate architecture artifacts aligned to guidelines.
- Mark module maturity targets and risks.

Checkpoint Q1 (user):
- Approve decomposition plan or request edits.

### 7.4 Stage D: Incremental Refactor
System actions:
- Apply transformations in bounded batches.
- Prefer deterministic transforms; use LLM synthesis where needed.
- Preserve compatibility adapters where required.

Outputs:
- batch commits/checkpoints.

### 7.5 Stage E: Validation and Auto-Repair
System actions:
- Execute parity gates after each batch.
- Attempt auto-repair on failures.
- Escalate to user if confidence/risk thresholds are breached.

Checkpoint Q2 (conditional):
- Resolve ambiguity or approve a high-risk path.

### 7.6 Stage F: Finalization
System actions:
- Produce final modular build and reports.
- Publish release candidate and residual risk list.

Checkpoint Q3 (user):
- Final sign-off.

## 8. Human-in-the-Loop Question System
### 8.1 Principles
- Ask only when uncertainty materially affects correctness/parity.
- Keep prompts short, with recommended defaults.
- Batch related questions into one step.

### 8.2 Question Categories
- Canonical user entry flow.
- Priority tradeoff (functional vs perceptual parity).
- Allowed structural changes (paths, serving, wrappers).
- Feature preservation exceptions.
- Acceptance thresholds.

### 8.3 Decision Policy
- Low risk: auto-apply.
- Medium risk: auto-apply + notify.
- High risk: require explicit confirmation.

## 9. Parity Model and Gates
### 9.1 Parity Axes
- Functional parity: rules, scoring, progression, outcomes.
- Interaction parity: controls, gestures, modals, transitions.
- Perceptual parity: layout hierarchy, motion, feedback, pacing.

### 9.2 Gate Thresholds (v1 defaults)
- Functional parity >= 0.95
- Interaction parity >= 0.90
- Perceptual parity >= 0.85
- No P0/P1 regressions open.

### 9.3 Blocking Conditions
- Entry flow mismatch.
- Broken asset/runtime path assumptions.
- Core loop regressions.
- Crash or startup failure.

## 10. Module Maturity Levels
- L1 Stub: contract wired, placeholder behavior.
- L2 Functional: logic works.
- L3 Behavioral Parity: behavior matches baseline.
- L4 Experience Parity: user-facing quality equivalent.

Release rule:
- All user-visible modules must reach L4.

## 11. System Architecture (v1)
### 11.1 Core Services
- Discovery Engine
- Baseline Capture Engine
- Decomposition Engine
- Refactor Orchestrator
- Validator Suite
- Auto-Repair Engine
- Decision Engine (question routing)
- Artifact Store and Report Generator

### 11.2 Execution Model
- Directed acyclic workflow with resumable checkpoints.
- Idempotent stage execution where possible.
- Full state persisted per run.

### 11.3 Safety Controls
- Snapshot before each batch.
- Automatic rollback on gate failure beyond retry budget.
- Hard limits on cascade depth and change size.

## 12. Data and Artifact Contract
### 12.1 Run Manifest
Fields:
- runId
- inputPath
- baselineProfile
- guidelineProfile
- riskPolicy
- stageStatus
- checkpointDecisions

### 12.2 Artifact Naming
- /CMS/decomposition/* for architecture artifacts
- /CMS/scaffold/* for modular runtime outputs
- /CMS/reports/* for parity and summary outputs

## 13. UX and CLI Surfaces
### 13.1 v1 CLI
Example commands:
- refactor init <workspace>
- refactor run --profile balanced
- refactor status <runId>
- refactor approve <checkpointId>
- refactor rollback <checkpointId>

### 13.2 v1 UI (optional webview)
- Run timeline
- Live parity scores
- Open questions panel
- Diff explorer
- One-click approve/rollback

## 14. Observability and Metrics
### 14.1 Product Metrics
- Time to first playable modular build.
- Percentage of runs passing parity gates on first pass.
- Number of user questions per run.
- Mean rollback count per run.
- Final acceptance rate.

### 14.2 Operational Metrics
- Stage duration and retry counts.
- Validation failure categories.
- Auto-repair success rate.

## 15. Security and Privacy
- Local-first processing by default.
- No source upload unless explicitly enabled.
- Redact sensitive tokens/keys in logs and reports.

## 16. Risks and Mitigations
- Hidden coupling risk -> mandatory coupling discovery and baseline traces.
- Over-confident automation -> confidence thresholds + human checkpoints.
- Perceptual mismatch -> explicit perceptual gate and evidence review.
- Runtime path issues -> serve/root invariants as blocking checks.

## 17. Rollout Plan
### 17.1 Milestones
- M1: Internal alpha on 3 sample games.
- M2: Beta with checkpoint UX and report stability.
- M3: v1 GA with policy profiles and CI hooks.

### 17.2 Entry Criteria for GA
- >= 80% runs produce playable modular build.
- >= 70% runs pass all parity gates with <= 2 manual checkpoints.
- No unresolved P0 class failures.

## 18. Definition of Done (v1)
A run is complete when:
- Modular build is playable.
- All parity gates pass threshold.
- Required modules are L4.
- Final report and artifacts are generated.
- User final checkpoint is approved.

## 19. Open Questions for v1.1
- Cross-game reusable pattern library and templates.
- Automated animation/audio fidelity scoring improvements.
- Multi-repo and cloud-scale orchestration.
- Enterprise policy packs and governance integration.
