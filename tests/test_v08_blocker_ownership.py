import json,subprocess
from pathlib import Path
from app.delivery.checker import DeliveryChecker
from app.delivery.resolver import InternalResolver
def git(repo,*args): return subprocess.run(['git',*args],cwd=repo,check=True,capture_output=True,text=True)
def init(repo): git(repo,'init'); git(repo,'config','user.email','test@example.com'); git(repo,'config','user.name','Test')
def test_nextjs_deployment_tbd_is_auto_resolvable_internal(tmp_path):
    (tmp_path/'docs').mkdir(); (tmp_path/'docs'/'architecture.md').write_text('deployment_target: to_be_decided_internally\n'); (tmp_path/'package.json').write_text(json.dumps({'dependencies':{'next':'16.4.0'}})); c=DeliveryChecker(tmp_path).unresolved_project_decisions(); assert c.blocker_class=='AUTO_RESOLVABLE_INTERNAL' and c.auto_resolvable and 'Vercel' in c.proposed_resolution
def test_placeholder_content_requires_client_input(tmp_path):
    (tmp_path/'src'/'content').mkdir(parents=True); (tmp_path/'src'/'content'/'about.ts').write_text('export const x="Placeholder biography"'); c=DeliveryChecker(tmp_path).placeholder_content(); assert c.blocker_class=='CLIENT_INPUT_REQUIRED' and not c.auto_resolvable
def test_missing_env_contract_is_hard_technical_blocker(tmp_path):
    (tmp_path/'src').mkdir(); (tmp_path/'src'/'route.ts').write_text('const x=process.env.API_SECRET;'); (tmp_path/'.env.example').write_text(''); assert DeliveryChecker(tmp_path).environment_contract().blocker_class=='HARD_TECHNICAL_BLOCKER'
def test_internal_resolver_updates_only_deployment_placeholders_and_commits(tmp_path):
    init(tmp_path); (tmp_path/'docs').mkdir()
    for n in ('requirement.md','architecture.md','deployment.md'): (tmp_path/'docs'/n).write_text('deployment_target: to_be_decided_internally\nclient_name: Placeholder\n')
    (tmp_path/'package.json').write_text(json.dumps({'dependencies':{'next':'16.4.0'}})); git(tmp_path,'add','-A'); git(tmp_path,'commit','-m','baseline'); git(tmp_path,'branch','-M','ai/integration/demo'); result=InternalResolver(tmp_path).resolve_nextjs_deployment_target_to_vercel(); assert result['resolution']=='deployment_target=vercel'
    for n in ('requirement.md','architecture.md','deployment.md'):
        t=(tmp_path/'docs'/n).read_text(); assert 'deployment_target: vercel' in t and 'client_name: Placeholder' in t
    assert git(tmp_path,'status','--porcelain').stdout.strip()==''; assert git(tmp_path,'log','-1','--pretty=%s').stdout.strip()=='chore: resolve internal deployment target to Vercel'
