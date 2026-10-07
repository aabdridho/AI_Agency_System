from app.execution.models import ExecutionRecord


def test_execution_record_can_store_qa_profile():
    rec = ExecutionRecord(
        task_id="TASK-020",
        owner="deterministic_qa",
        branch="ai/integration/demo",
        status="success",
        qa_profile="responsive_audit",
    )
    assert rec.qa_profile == "responsive_audit"
