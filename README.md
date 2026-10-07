# AI Agency Router V0.8

V0.8 adds the execution layer on top of the stable discovery, documentation,
and routing workflow.

## Test

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
pytest -q
```

## Run execution layer

```powershell
python execute_project.py
```

Start with **Dry-run**. This validates which owner, branch and command would be
used without calling Claude Code or Codex.

For real execution, the local machine must provide the relevant CLI binaries:

```powershell
claude --version
codex --version
```

V0.8 never automatically pushes to `main`.


## Real execution branch model

Real execution does not run every task from the same base commit.

```text
main / existing baseline
        |
        v
ai/integration/<project>
        |
        +-- ai/task-001-* -- execute -- commit -- merge back
        |
        +-- ai/task-002-* -- execute -- commit -- merge back
        |
        +-- ai/task-003-* -- ...
```

Therefore later tasks can see the successful output of earlier tasks while each task
still has its own isolated branch.

The integration branch is intentionally separate from `main`/`master`.


## QA behavior

V0.8 never treats "nothing was checked" as a successful QA result.

If no deterministic command is available, the QA task fails with a clear
`no deterministic QA command detected` message. For Node projects, available
`lint`, `test`, and `build` scripts are detected from `package.json`.

Real Claude/Codex execution streams progress live to the terminal.


## V0.8 — Task-aware QA

V0.8 stops treating every QA task as the same lint/test/build job. QA tasks are mapped to specialized deterministic profiles for submission flow, requirements, engineering validation, responsive evidence, and scope control. Failed profiles remain compatible with the bounded automatic repair loop introduced in V0.6.


## V0.8 — Delivery / Production Readiness Layer

Run `python prepare_delivery.py` only after execution/QA is green. V0.8 does not deploy automatically. It creates a deterministic delivery gate covering Git cleanliness, requirement approval, unresolved delivery decisions, placeholder client content, tracked secret files, environment-variable documentation, deployment documentation, and production validation. Reports are stored outside the client repository under `runtime_data/delivery/<project>/`.

### Blocker ownership and safe internal resolution

V0.8 classifies delivery blockers as `AUTO_RESOLVABLE_INTERNAL`, `CLIENT_INPUT_REQUIRED`, or `HARD_TECHNICAL_BLOCKER`. For a Next.js project whose only unresolved delivery decision is the deployment target, V0.8 may propose Vercel. The CLI requires explicit confirmation, edits only deployment-target placeholders in delivery-critical docs, commits on the current `ai/integration/*` branch, then reruns readiness. Client biography/contact/project content is never auto-filled.


### Client Input Request Packet

When readiness is blocked by `CLIENT_INPUT_REQUIRED`, V0.8 now generates:

`runtime_data/delivery/<project>/client_input_request.md`

The packet converts detected client-owned placeholders into a concise request list by section (for example Hero, About, Contact, Experience, Projects, Skills, and Certifications). It does not modify the project repository and does not infer or invent client facts. When all client-input blockers are gone, stale request packets are removed automatically.


## V0.9 - Controlled Deployment & Handoff Layer

Run `python deploy_project.py` only after V0.8 reports `READY`.

V0.9 adds a fail-closed deployment guard, deterministic deployment plan generation, explicit approval before any remote production deployment, and handoff reports. The first supported deployment path is validated Next.js -> Vercel.

Safety rules:

- A non-READY V0.8 delivery report blocks deployment.
- The project must be clean and on `ai/integration/*`.
- V0.9 does not merge or push `main`/`master`.
- `dry-run` is the default mode.
- Remote production deployment requires typing `DEPLOY`.
- Handoff reports contain environment variable names only, never values.
- Operational reports remain under `runtime_data/`, outside the client project repository.
