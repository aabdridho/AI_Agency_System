import json
from pathlib import Path

from app.routing.classifier import TaskClassifier
from app.routing.engine import RoutingEngine
from app.routing.policy import RoutingPolicy
from app.routing.goat_config import GoatConfig
from app.routing.storage import RoutingStorage


def test_frontend_routes_to_claude_code():
    category, confidence = TaskClassifier().classify("Implement `hero` section")
    assert category == "frontend"

def test_backend_routes_to_codex(tmp_path):
    project = tmp_path / "p"
    (project / "docs").mkdir(parents=True)
    (project / "docs/task.md").write_text(
        "- [ ] Submit form data to `email`\n",
        encoding="utf-8",
    )
    engine = RoutingEngine(
        policy=RoutingPolicy(
            goat_config=GoatConfig(tmp_path / "missing-tiers.json")
        )
    )
    plan = engine.build_plan(project)
    assert plan.decisions[0].primary_owner == "codex"

def test_qa_routes_to_deterministic_first(tmp_path):
    project = tmp_path / "p"
    (project / "docs").mkdir(parents=True)
    (project / "docs/task.md").write_text(
        "- [ ] Run deterministic validation/lint/tests\n",
        encoding="utf-8",
    )
    plan = RoutingEngine().build_plan(project)
    decision = plan.decisions[0]
    assert decision.primary_owner == "deterministic_qa"
    assert decision.fallback_owner == "codex"

def test_frontend_task_resolves_through_goat_build_tier(tmp_path):
    project = tmp_path / "p"
    (project / "docs").mkdir(parents=True)
    (project / "docs/task.md").write_text(
        "- [ ] Implement `hero` section\n",
        encoding="utf-8",
    )
    engine = RoutingEngine(
        policy=RoutingPolicy(
            goat_config=GoatConfig(tmp_path / "missing-tiers.json")
        )
    )
    plan = engine.build_plan(project)

    assert plan.decisions[0].goat_tier == "build"
    assert plan.decisions[0].primary_owner == "codex"
    assert plan.decisions[0].primary_model == "gpt-6.1-sol"
    assert plan.decisions[0].fallback_owner == "codex"

def test_max_escalation_is_one(tmp_path):
    project = tmp_path / "p"
    (project / "docs").mkdir(parents=True)
    (project / "docs/task.md").write_text(
        "- [ ] Implement `hero` section\n",
        encoding="utf-8",
    )
    plan = RoutingEngine().build_plan(project)
    assert all(d.max_escalations == 1 for d in plan.decisions)

def test_storage_is_outside_project_repo(tmp_path):
    project = tmp_path / "generated_projects" / "p"
    (project / "docs").mkdir(parents=True)
    (project / "docs/task.md").write_text(
        "- [ ] Implement `hero` section\n",
        encoding="utf-8",
    )
    plan = RoutingEngine().build_plan(project)
    runtime = tmp_path / "runtime_data"
    saved = RoutingStorage().save(plan, runtime)

    assert runtime in saved.parents
    assert project not in saved.parents
    assert saved.exists()

def test_routing_plan_contains_reason(tmp_path):
    project = tmp_path / "p"
    (project / "docs").mkdir(parents=True)
    (project / "docs/task.md").write_text(
        "- [ ] Implement `hero` section\n",
        encoding="utf-8",
    )
    plan = RoutingEngine().build_plan(project)
    assert plan.decisions[0].reason
    assert plan.decisions[0].escalation_trigger
