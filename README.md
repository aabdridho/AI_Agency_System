# AI Agency System V0.14

AI Agency System is a local-first AI project orchestration system for turning client briefs into approved requirements, documentation, GOAT-routed tasks, implementation, deterministic QA, delivery readiness, economics, and controlled deployment approval.

## Current Release

- Version: `0.14.0`
- Git tag: `v0.14`
- Primary CLI: `python agency.py`
- Runtime state: `runtime_data/`
- Production deployment requires explicit approval.

## Run

```powershell
python agency.py
```

## V0.14 Pipeline

```text
discovery
-> documentation
-> routing
-> execution
-> delivery
-> economics
-> deployment
```

Resumable orchestration state is stored under:

`runtime_data/orchestration/<project>/state.json`

Real model execution requires explicit approval. Production deployment also remains approval-gated.

## Requirement Gate

Development cannot begin until the final requirement baseline is client-approved and ready for development.

Discovery distinguishes `CONFIRMED`, `INFERRED`, `UNKNOWN`, `INTERNAL_DECISION`, and `PROPOSED`.

## GOAT Routing

Each task has one primary model owner. Fallback is bounded to one escalation after an explicit execution failure or qualifying risk condition.

## Execution and QA

Implementation uses `ai/integration/<project>` with isolated `ai/task-*` branches.

Deterministic QA fails closed when no valid check exists. Windows-controlled Node execution prefers `npm.cmd`.

## Delivery

Delivery validates Git cleanliness, approved requirements, unresolved decisions, placeholders, secrets, environment documentation, deployment documentation, and production validation.

Blocker classes:

```text
AUTO_RESOLVABLE_INTERNAL
CLIENT_INPUT_REQUIRED
HARD_TECHNICAL_BLOCKER
```

Client-owned facts must never be invented automatically.

## Economics

V0.13 introduced usage telemetry, model attribution, equivalent/list-price cost, estimated GOAT counterfactual savings, and billing support.

V0.14 integrates economics directly into project orchestration.

Token usage, equivalent/list-price cost, and actual provider cash cost are separate concepts.

Equivalent cost must not be presented as an actual provider charge when billing evidence is unavailable.

## Control Room

For V0.14 projects, orchestration state is authoritative for pipeline-stage status.

Stages: `discovery`, `documentation`, `routing`, `execution`, `delivery`, `economics`, `deployment`.

## Repository Boundaries

Operational routing, execution, delivery, deployment, handoff, usage, and orchestration data remain under `runtime_data/` and outside client repositories.

## Release History

### V0.14 - Project Orchestrator

- Stateful and resumable project orchestration
- `agency.py` primary entry point
- Explicit execution and deployment approval gates
- Integrated discovery through economics and deployment approval
- Real Control Room orchestration state
- Delivery internal auto-resolution hardening
- Discovery negation and display-only contact fixes
- Windows and interrupt resilience hardening
- Version consistency `0.14.0`

### V0.13 - Observability, Cost and Billing

- Token usage and model attribution
- GOAT runtime configuration
- Equivalent/list-price cost engine
- Estimated GOAT savings
- Commercial billing summaries
- Economics surfaces for Control Room

Detailed historical release notes are preserved in `CHANGELOG.md`.
