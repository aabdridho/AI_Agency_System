import json

from app.orchestration.orchestrator import (
    ProjectOrchestrator,
)
from app.orchestration.state import (
    OrchestrationStateStore,
)


def orchestrator(tmp_path):
    runtime = (
        tmp_path
        / "runtime_data"
    )

    output = (
        tmp_path
        / "AI_Output"
    )

    output.mkdir()

    return ProjectOrchestrator(
        runtime_root=runtime,
        output_root=output,
    )


def project(o, name="demo"):
    root = o.output_root / name
    root.mkdir(
        parents=True,
        exist_ok=True,
    )
    return root


def write_json(path, data):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )


def test_new_project_waits_for_client_brief(
    tmp_path,
):
    o = orchestrator(tmp_path)

    state = o.inspect("demo")

    assert state.status == "waiting_input"
    assert state.current_stage == "discovery"
    assert state.waiting_for == "client_brief"


def test_discovery_advances_to_documentation(
    tmp_path,
):
    o = orchestrator(tmp_path)
    root = project(o)

    docs = root / "docs"
    docs.mkdir()

    (
        docs / "requirement.md"
    ).write_text(
        "CLIENT_APPROVED\nReady for development: True",
        encoding="utf-8",
    )

    state = o.inspect("demo")

    assert state.current_stage == "documentation"
    assert state.completed_stages == [
        "discovery"
    ]


def test_task_document_advances_to_routing(
    tmp_path,
):
    o = orchestrator(tmp_path)
    root = project(o)

    docs = root / "docs"
    docs.mkdir()

    (
        docs / "requirement.md"
    ).write_text(
        "CLIENT_APPROVED\nReady for development: True",
        encoding="utf-8",
    )

    (
        docs / "task.md"
    ).write_text(
        "- [ ] build app",
        encoding="utf-8",
    )

    state = o.inspect("demo")

    assert state.current_stage == "routing"

    assert state.completed_stages == [
        "discovery",
        "documentation",
    ]


def test_saved_routing_requires_real_execution_approval(
    tmp_path,
):
    o = orchestrator(tmp_path)
    root = project(o)

    docs = root / "docs"
    docs.mkdir()

    (
        docs / "requirement.md"
    ).write_text(
        "CLIENT_APPROVED\nReady for development: True",
        encoding="utf-8",
    )

    (
        docs / "task.md"
    ).write_text(
        "- [ ] build app",
        encoding="utf-8",
    )

    write_json(
        (
            o.runtime_root
            / "routing"
            / "demo"
            / "routing_plan.json"
        ),
        {
            "project_name": "demo",
            "decisions": [],
        },
    )

    state = o.inspect("demo")

    assert state.status == "waiting_approval"
    assert state.current_stage == "execution"

    assert (
        state.waiting_for
        == "real_execution_approval"
    )


def test_failed_execution_is_not_marked_complete(
    tmp_path,
):
    o = orchestrator(tmp_path)
    project(o)

    write_json(
        (
            o.runtime_root
            / "execution"
            / "demo"
            / "execution_report.json"
        ),
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [
                {
                    "status": "failed"
                }
            ],
        },
    )

    state = o.inspect("demo")

    assert state.status == "failed"
    assert state.failed_stage == "execution"
    assert state.current_stage == "execution"


def test_client_delivery_blocker_waits_for_input(
    tmp_path,
):
    o = orchestrator(tmp_path)
    project(o)

    write_json(
        (
            o.runtime_root
            / "delivery"
            / "demo"
            / "delivery_report.json"
        ),
        {
            "overall_status": "blocked",
            "blocker_summary": {
                "CLIENT_INPUT_REQUIRED": 1
            },
        },
    )

    state = o.inspect("demo")

    assert state.status == "waiting_input"
    assert state.current_stage == "delivery"

    assert state.waiting_for == "client_input"


def test_economics_waits_for_deployment_approval(
    tmp_path,
):
    o = orchestrator(tmp_path)
    root = project(o)

    docs = root / "docs"
    docs.mkdir()

    (
        docs / "requirement.md"
    ).write_text(
        "CLIENT_APPROVED\nReady for development: True",
        encoding="utf-8",
    )

    (
        docs / "task.md"
    ).write_text(
        "- [ ] build",
        encoding="utf-8",
    )

    write_json(
        (
            o.runtime_root
            / "routing"
            / "demo"
            / "routing_plan.json"
        ),
        {
            "project_name": "demo",
            "decisions": [],
        },
    )

    write_json(
        (
            o.runtime_root
            / "execution"
            / "demo"
            / "execution_report.json"
        ),
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [
                {
                    "status": "success"
                }
            ],
        },
    )

    write_json(
        (
            o.runtime_root
            / "delivery"
            / "demo"
            / "delivery_report.json"
        ),
        {
            "overall_status": "ready",
            "blocker_summary": {},
        },
    )

    usage = (
        o.runtime_root
        / "usage"
        / "demo"
    )

    usage.mkdir(
        parents=True
    )

    for filename in (
        "cost_summary.json",
        "savings_summary.json",
        "billing_summary.json",
    ):
        (
            usage / filename
        ).write_text(
            "{}",
            encoding="utf-8",
        )

    state = o.inspect("demo")

    assert state.status == "waiting_approval"
    assert state.current_stage == "deployment"

    assert (
        state.waiting_for
        == "deployment_approval"
    )

    assert state.completed_stages == [
        "discovery",
        "documentation",
        "routing",
        "execution",
        "delivery",
        "economics",
    ]


def test_state_is_persisted_and_reloadable(
    tmp_path,
):
    o = orchestrator(tmp_path)

    state = o.inspect("demo")

    store = OrchestrationStateStore(
        o.runtime_root
    )

    loaded = store.load("demo")

    assert loaded is not None

    assert (
        loaded.project_name
        == state.project_name
    )

    assert (
        loaded.current_stage
        == state.current_stage
    )

    assert loaded.updated_at is not None


def test_deployed_project_is_completed(
    tmp_path,
):
    o = orchestrator(tmp_path)
    project(o)

    # Prefix artifacts.
    root = o.output_root / "demo"
    docs = root / "docs"
    docs.mkdir()

    (
        docs / "requirement.md"
    ).write_text(
        "CLIENT_APPROVED\nReady for development: True",
        encoding="utf-8",
    )

    (
        docs / "task.md"
    ).write_text(
        "- [ ] build",
        encoding="utf-8",
    )

    write_json(
        (
            o.runtime_root
            / "routing"
            / "demo"
            / "routing_plan.json"
        ),
        {
            "decisions": []
        },
    )

    write_json(
        (
            o.runtime_root
            / "execution"
            / "demo"
            / "execution_report.json"
        ),
        {
            "dry_run": False,
            "records": [],
        },
    )

    write_json(
        (
            o.runtime_root
            / "delivery"
            / "demo"
            / "delivery_report.json"
        ),
        {
            "overall_status": "ready",
            "blocker_summary": {},
        },
    )

    usage = (
        o.runtime_root
        / "usage"
        / "demo"
    )

    usage.mkdir(
        parents=True
    )

    for filename in (
        "cost_summary.json",
        "savings_summary.json",
        "billing_summary.json",
    ):
        (
            usage / filename
        ).write_text(
            "{}",
            encoding="utf-8",
        )

    write_json(
        (
            o.runtime_root
            / "deployment"
            / "demo"
            / "deployment_result.json"
        ),
        {
            "status": "deployed"
        },
    )

    state = o.inspect("demo")

    assert state.status == "completed"
    assert state.current_stage is None

    assert (
        state.completed_stages
        == [
            "discovery",
            "documentation",
            "routing",
            "execution",
            "delivery",
            "economics",
            "deployment",
        ]
    )

def test_out_of_order_economics_does_not_skip_pipeline(
    tmp_path,
):
    o = orchestrator(tmp_path)

    usage = (
        o.runtime_root
        / "usage"
        / "demo"
    )

    usage.mkdir(
        parents=True
    )

    for filename in (
        "cost_summary.json",
        "savings_summary.json",
        "billing_summary.json",
    ):
        (
            usage / filename
        ).write_text(
            "{}",
            encoding="utf-8",
        )

    state = o.inspect("demo")

    assert state.status == "waiting_input"
    assert state.current_stage == "discovery"
    assert state.waiting_for == "client_brief"
    assert state.completed_stages == []

def test_unapproved_requirement_cannot_reach_routing(
    tmp_path,
):
    o = orchestrator(tmp_path)

    root = project(o)

    docs = root / "docs"
    docs.mkdir()

    (
        docs / "requirement.md"
    ).write_text(
        "# Draft requirement",
        encoding="utf-8",
    )

    (
        docs / "task.md"
    ).write_text(
        "- [ ] build app",
        encoding="utf-8",
    )

    write_json(
        (
            o.runtime_root
            / "routing"
            / "demo"
            / "routing_plan.json"
        ),
        {
            "project_name": "demo",
            "decisions": [],
        },
    )

    state = o.inspect("demo")

    assert state.status == "waiting_input"
    assert state.current_stage == "discovery"
    assert state.waiting_for == "client_brief"
    assert state.completed_stages == []


def test_hard_delivery_blocker_outranks_client_input(
    tmp_path,
):
    o = orchestrator(tmp_path)
    root = project(o)

    docs = root / "docs"
    docs.mkdir()

    (
        docs / "requirement.md"
    ).write_text(
        "CLIENT_APPROVED\n"
        "Ready for development: True\n",
        encoding="utf-8",
    )

    (
        docs / "task.md"
    ).write_text(
        "- [ ] build app",
        encoding="utf-8",
    )

    write_json(
        (
            o.runtime_root
            / "routing"
            / "demo"
            / "routing_plan.json"
        ),
        {
            "project_name": "demo",
            "decisions": [],
        },
    )

    write_json(
        (
            o.runtime_root
            / "execution"
            / "demo"
            / "execution_report.json"
        ),
        {
            "project_name": "demo",
            "dry_run": False,
            "records": [
                {
                    "status": "success"
                }
            ],
        },
    )

    write_json(
        (
            o.runtime_root
            / "delivery"
            / "demo"
            / "delivery_report.json"
        ),
        {
            "overall_status": "blocked",
            "blocker_summary": {
                "CLIENT_INPUT_REQUIRED": 1,
                "HARD_TECHNICAL_BLOCKER": 1,
            },
        },
    )

    state = o.inspect("demo")

    assert state.status == "failed"
    assert state.current_stage == "delivery"
    assert state.failed_stage == "delivery"
    assert state.waiting_for is None
