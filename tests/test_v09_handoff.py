from app.deployment.handoff import HandoffBuilder
from app.deployment.models import DeploymentPlan, DeploymentResult

def test_handoff_lists_env_names_without_values(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir()
    (repo/".env.example").write_text("RESEND_API_KEY=\nCONTACT_EMAIL_TO=\n",encoding="utf-8")
    (repo/"README.md").write_text("demo",encoding="utf-8")
    plan=DeploymentPlan(project_name="demo",project_root=str(repo),provider="vercel",mode="dry-run",status="ready",source_branch="ai/integration/demo",commit_sha="abc123")
    out=tmp_path/"handoff"
    report=HandoffBuilder(repo).build(plan=plan,result=DeploymentResult(status="planned"),delivery_report={"overall_status":"ready","production_commands":["npm.cmd run build"],"client_input_request":None},output_dir=out)
    assert report.environment_variables==["CONTACT_EMAIL_TO","RESEND_API_KEY"]
    text=(out/"handoff_report.md").read_text(encoding="utf-8")
    assert "RESEND_API_KEY" in text
    assert "CONTACT_EMAIL_TO" in text
    assert "=" not in "\n".join([line for line in text.splitlines() if "RESEND_API_KEY" in line or "CONTACT_EMAIL_TO" in line])
