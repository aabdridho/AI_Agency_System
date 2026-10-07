import json, pytest
from app.deployment.guard import DeploymentGuard, DeploymentGuardError

def test_guard_blocks_non_ready_delivery(tmp_path):
    p = tmp_path/"delivery_report.json"
    p.write_text(json.dumps({"overall_status":"blocked","checks":[{"status":"blocker"}]}), encoding="utf-8")
    with pytest.raises(DeploymentGuardError):
        DeploymentGuard(p).validate()

def test_guard_accepts_ready_delivery(tmp_path):
    p = tmp_path/"delivery_report.json"
    p.write_text(json.dumps({"overall_status":"ready","checks":[{"status":"pass"}]}), encoding="utf-8")
    assert DeploymentGuard(p).validate()["overall_status"] == "ready"
