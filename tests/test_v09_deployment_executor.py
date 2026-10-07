import pytest
from app.deployment.executor import DeploymentExecutor, DeploymentExecutionError
from app.deployment.models import DeploymentCommand, DeploymentPlan

def _plan(mode="execute"):
    return DeploymentPlan(project_name="demo",project_root=".",provider="vercel",mode=mode,status="ready",commands=[DeploymentCommand(label="deploy",command=["echo","https://demo.example"],destructive_or_remote=True)])

def test_executor_requires_explicit_approval(tmp_path):
    with pytest.raises(DeploymentExecutionError):
        DeploymentExecutor(tmp_path).execute(_plan(),approved=False)

def test_executor_dry_run_does_not_execute(tmp_path):
    assert DeploymentExecutor(tmp_path).execute(_plan("dry-run"),approved=False).status=="planned"
