from app.execution.prompt_builder import TaskPromptBuilder


def _docs(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    files = {
        "requirement.md": "REQ_MARKER",
        "task.md": "TASK_MD_MARKER",
        "architecture.md": "ARCH_MARKER",
        "frontend.md": "FRONTEND_MARKER",
        "backend.md": "BACKEND_MARKER",
    }
    for name, content in files.items():
        (docs / name).write_text(content, encoding="utf-8")
    return tmp_path


def test_frontend_task_receives_only_frontend_domain_context(tmp_path):
    root = _docs(tmp_path)
    prompt = TaskPromptBuilder().build(
        root,
        "Build responsive landing page hero component",
    )

    assert "REQ_MARKER" in prompt
    assert "ARCH_MARKER" in prompt
    assert "FRONTEND_MARKER" in prompt
    assert "BACKEND_MARKER" not in prompt
    assert "TASK_MD_MARKER" not in prompt


def test_backend_task_receives_only_backend_domain_context(tmp_path):
    root = _docs(tmp_path)
    prompt = TaskPromptBuilder().build(
        root,
        "Implement API endpoint and database persistence",
    )

    assert "REQ_MARKER" in prompt
    assert "ARCH_MARKER" in prompt
    assert "BACKEND_MARKER" in prompt
    assert "FRONTEND_MARKER" not in prompt
    assert "TASK_MD_MARKER" not in prompt


def test_cross_stack_task_receives_both_domain_contexts(tmp_path):
    root = _docs(tmp_path)
    prompt = TaskPromptBuilder().build(
        root,
        "Connect contact form UI to API endpoint",
    )

    assert "FRONTEND_MARKER" in prompt
    assert "BACKEND_MARKER" in prompt


def test_ambiguous_task_fails_safe_with_both_domain_contexts(tmp_path):
    root = _docs(tmp_path)
    prompt = TaskPromptBuilder().build(
        root,
        "Implement the approved project change",
    )

    assert "FRONTEND_MARKER" in prompt
    assert "BACKEND_MARKER" in prompt


def test_assigned_task_is_always_preserved(tmp_path):
    root = _docs(tmp_path)
    task = "Create a minimal health check endpoint"
    prompt = TaskPromptBuilder().build(root, task)

    assert f"ASSIGNED TASK:\n{task}" in prompt
