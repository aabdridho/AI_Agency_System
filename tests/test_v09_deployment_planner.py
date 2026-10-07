import json, subprocess
from pathlib import Path
from app.deployment.planner import DeploymentPlanner

def _git(repo: Path,*args):
    return subprocess.run(["git",*args],cwd=repo,check=True,capture_output=True,text=True)

def _repo(tmp_path):
    _git(tmp_path,"init")
    _git(tmp_path,"config","user.email","test@example.com")
    _git(tmp_path,"config","user.name","Test")
    (tmp_path/"docs").mkdir()
    (tmp_path/"docs"/"deployment.md").write_text("deployment_target: vercel\n",encoding="utf-8")
    (tmp_path/"package.json").write_text(json.dumps({"dependencies":{"next":"16.4.0"}}),encoding="utf-8")
    _git(tmp_path,"add","-A"); _git(tmp_path,"commit","-m","baseline"); _git(tmp_path,"branch","-M","ai/integration/demo")
    return tmp_path

def test_planner_builds_vercel_plan(tmp_path,monkeypatch):
    repo=_repo(tmp_path)
    monkeypatch.setattr("shutil.which", lambda name: "npx.cmd" if "npx" in name else None)
    plan=DeploymentPlanner(repo).create_plan(project_name="demo",mode="dry-run")
    assert plan.provider=="vercel"
    assert plan.status=="ready"
    assert plan.source_branch=="ai/integration/demo"
    assert "vercel" in plan.commands[0].command

def test_planner_blocks_dirty_repo(tmp_path,monkeypatch):
    repo=_repo(tmp_path)
    (repo/"dirty.txt").write_text("x",encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda name:"npx.cmd")
    plan=DeploymentPlanner(repo).create_plan(project_name="demo")
    assert plan.status=="blocked"
