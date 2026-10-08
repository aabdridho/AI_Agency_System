# Changelog

## V0.14 - Project Orchestrator

- Added agency.py as the primary project orchestration entry point.
- Added persistent resumable orchestration state under runtime_data/orchestration/<project>/state.json.
- Integrated discovery, documentation, GOAT routing, execution, deterministic QA, delivery, economics, and deployment approval.
- Added explicit approval before real model execution.
- Preserved explicit approval before production deployment.
- Added orchestration-aware Control Room stages including economics.
- Added safe internal deployment-target auto-resolution.
- Added requirement-gate enforcement before routing and execution.
- Added negation-aware discovery and display-only contact normalization.
- Prevented display-only email contact from implying backend email delivery.
- Added interrupt cleanup and Windows execution hardening.
- Unified release version to 0.14.0.

## V0.13 - Observability, Cost and Billing

- Added token usage capture and model attribution.
- Added GOAT runtime model and effort configuration.
- Added equivalent provider/model list-cost calculation.
- Added estimated counterfactual GOAT savings.
- Added commercial billing summaries.
- Preserved the distinction between equivalent/list-price cost and actual provider cash cost.
- Added economics data to the Control Room.

## V0.9 - Controlled Deployment & Handoff Layer

- Added deployment guard requiring a `READY` V0.8 delivery report.
- Added deterministic deployment planning.
- Added first supported deployment path: validated Next.js -> Vercel.
- Added dry-run mode and explicit `DEPLOY` confirmation for remote production execution.
- Added deployment plan/result reports under `runtime_data/deployment/<project>/`.
- Added handoff JSON/Markdown under `runtime_data/handoff/<project>/`.
- Handoff reports expose environment variable names only, never values.
- V0.9 never merges or pushes `main`/`master` automatically.



## V0.8 - Delivery / Production Readiness Layer


### V0.8 client-input packet hardening

- Added deterministic `client_input_request.md` generation for `CLIENT_INPUT_REQUIRED`.
- Placeholder files are translated into section-specific client questions.
- Client facts are never inferred or auto-filled.
- Request packets live under runtime delivery data, never inside client repositories.
- Stale request packets are automatically removed after client blockers are resolved.


- Added `prepare_delivery.py`.
- Added deterministic delivery checks for Git cleanliness, integration branch, approved requirements, unresolved decisions, placeholder client content, tracked secret files, environment contract, deployment docs, and production validation.
- Delivery is fail-closed: blockers prevent a `READY` result.
- Reports are stored outside the project repository as JSON and Markdown.
- V0.8 intentionally does not deploy, push, or tag automatically.


## V0.7 - Task-aware deterministic QA

### V0.7 audit precision hardening
- Requirements audit no longer treats QA-like tasks such as `Validate submission flow end-to-end` as unfinished implementation merely because they appear before the `## QA` heading.
- Scope audit no longer scans portfolio copy/content for generic words like `database` or `authentication`.
- Scope audit now uses structural evidence: dependencies, implementation paths, and implementation-only source markers.
- This prevents QA repair from rewriting legitimate Data Engineering portfolio content simply to silence a keyword scanner.


### V0.7 Windows/Next.js preflight polish
- The CLI banner now correctly reports V0.7.
- Preflight can automatically restore tracked `next-env.d.ts` drift when it is the only dirty path, preventing `next build` generated changes from blocking a clean resume.
- Any real source/config change still blocks execution, and the error now lists changed paths.


- QA tasks now select a profile from their task meaning instead of repeating an identical command set.
- `submission_e2e`: runs targeted test/e2e scripts where available and audits contact submission coverage.
- `requirements_audit`: checks the approved gate, implementation task completion, required sections, and confirmed contact fields.
- `validation`: runs lint, explicit typecheck, tests, and build.
- `responsive_audit`: requires deterministic responsive implementation evidence plus typecheck/build where available.
- `scope_audit`: detects common implementation indicators for features explicitly documented as out of scope.
- Execution reports include the selected `qa_profile`.
- Existing bounded QA auto-repair works on failures from specialized profiles.


### Automatic deterministic QA repair loop
- Failed deterministic QA can trigger one bounded repair task on an isolated `ai/repair/...` branch.
- The QA routing fallback owner is used as the preferred repair owner; one model fallback is allowed if the repair owner itself fails.
- A repair must produce real repository changes, commit cleanly, merge into integration, and then deterministic QA is rerun.
- Repair loops are bounded by a global execution budget (`max_qa_repair_cycles`, default 2) to prevent runaway model loops.
- Execution reports now record whether QA initially failed, whether repair was attempted, the repair owner/branch, and whether the repair succeeded.
- Node QA now runs an explicit `typecheck` script when present, in addition to lint/test/build.
- Deterministic QA and Git subprocess output are decoded as UTF-8 with replacement on Windows.


## V0.6 €” Execution Layer

### Safe resume after interrupted execution
- Real execution automatically skips implementation tasks whose verified `TASK-*` commit is already contained in the integration branch.
- Old placeholder task branches that only point to the baseline are not treated as completed.
- This allows interrupted runs to continue from the next unfinished task without rerunning completed work.

### Windows CLI stream encoding hardening
- Claude/Codex subprocess output is decoded explicitly as UTF-8.
- Invalid/unsupported terminal bytes are replaced instead of crashing the orchestrator.
- Prevents Windows `cp1252` `UnicodeDecodeError` during live CLI streaming.

### CLI write-permission hardening
- Claude Code real execution now uses non-interactive `acceptEdits` mode.
- Codex real execution now uses `--approve-for-me`; in Codex v0.160.1 this routes approval requests through the workspace-write sandbox and cannot be combined with `--sandbox`.
- Windows Node QA prefers `npm.cmd` to avoid PowerShell `npm.ps1` execution-policy failures.
- Real execution now performs a local workspace write probe before starting model tasks.

### Execution artifact validation
- A CLI exit code of `0` is no longer enough to mark implementation tasks successful.
- Implementation tasks must create real Git-detectable repository changes.
- No-change executions trigger the one allowed fallback when configured.
- Successful tasks must create a commit whose HEAD advances from the integration base.
- The task commit must be verified as contained in the integration branch after merge.
- Task prompts now explicitly require direct file creation/modification instead of prose-only responses.

### QA truthfulness + live progress
- `no QA command detected` is no longer reported as success.
- QA now fails closed when no deterministic check can actually run.
- Node projects detect available `lint`, `test`, and `build` scripts from `package.json`.
- Real Claude/Codex execution now streams output live to the terminal.
- Real execution prints task progress (`[current/total]`) before each task.

### Execution workflow refinement
- Added cumulative integration branch `ai/integration/<project>`.
- Each implementation task now branches from the latest integration state.
- Successful task changes are committed and merged into the integration branch.
- Failed-primary partial changes are discarded before fallback execution.
- Failed tasks are never merged.
- Deterministic QA runs against the cumulative integration branch.
- Real execution now performs CLI preflight for Git, Claude Code, and Codex.
- Existing dirty repositories are rejected before automation starts.
- Main/master is never automatically merged or pushed.

### Added
- Execution engine consuming the V0.5 routing plan.
- Dry-run mode as the default/safe validation path.
- Local CLI adapters for Claude Code (`claude`) and Codex (`codex`).
- One Git branch per task using `ai/task-*` branch naming.
- Project documentation is injected as task context.
- Deterministic QA runner.
- Bounded one-step fallback after primary failure.
- Execution reports stored outside the client project repository.
- `execute_project.py` CLI.

### Safety / workflow rules
- No automatic push to `main`.
- No automatic second-model review.
- Fallback is only attempted after primary execution failure.
- Operational execution reports stay under `runtime_data/`.
- Real execution requires explicit CLI confirmation.

### Preserved
- V0.5 routing engine.
- V0.4 documentation generator.
- V0.3 discovery engine.

### V0.8 blocker ownership hardening

- Added blocker ownership: `AUTO_RESOLVABLE_INTERNAL`, `CLIENT_INPUT_REQUIRED`, and `HARD_TECHNICAL_BLOCKER`.
- Added explicit-confirmation safe internal auto-resolution for unresolved Next.js deployment target -> Vercel.
- Auto-resolution is restricted to deployment-target placeholders, requires a clean `ai/integration/*` branch, commits the resolution, and reruns readiness.
- Client content remains non-auto-resolvable and cannot be invented by the system.
- Delivery reports now include blocker ownership counts and proposed resolutions.


### V0.8 Windows console compatibility

- Replaced em-dash characters in generated Markdown headings with ASCII hyphens.
- This prevents mojibake such as `¢‚¬€` when viewing generated reports with Windows PowerShell defaults.
