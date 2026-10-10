from __future__ import annotations
from app.command_resolver import resolve_node_cli
import json,re,shutil,subprocess,sys
from pathlib import Path
from .models import ReadinessCheck
class DeliveryChecker:
    SECRET_FILE_NAMES={'.env','.env.local','.env.production','.env.development.local','.npmrc'}
    CONTENT_PLACEHOLDER_PATTERNS=[re.compile(r'\bplaceholder\b',re.I),re.compile(r'\breplace me\b',re.I),re.compile(r'\byour[_ -](name|email|domain|company)\b',re.I),re.compile(r'\bexample-(a|b|c)\.com\b',re.I)]
    DECISION_PLACEHOLDER_RE=re.compile(r'\b(?:to[_ -]be[_ -]decided(?:[_ -]internally)?|tbd)\b',re.I)
    DEPLOYMENT_KEY_RE=re.compile(r'(deployment(?:_target|\s+target)?|hosting|deploy(?:ment)? provider)',re.I)
    def __init__(self,repo): self.repo=Path(repo)
    def _run(self,args): return subprocess.run(args,cwd=self.repo,capture_output=True,text=True,encoding='utf-8',errors='replace')
    def _is_nextjs_project(self):
        p=self.repo/'package.json'
        if not p.exists(): return False
        try: data=json.loads(p.read_text(encoding='utf-8'))
        except Exception: return False
        deps={}; deps.update(data.get('dependencies') or {}); deps.update(data.get('devDependencies') or {})
        return 'next' in deps
    def _decision_placeholders(self):
        hits=[]
        for name in ('requirement.md','architecture.md','deployment.md'):
            p=self.repo/'docs'/name
            if not p.exists(): continue
            for n,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
                if self.DECISION_PLACEHOLDER_RE.search(line): hits.append({'file':name,'line':n,'text':line.strip(),'deployment_related':bool(self.DEPLOYMENT_KEY_RE.search(line))})
        return hits
    def git_clean(self):
        p=self._run(['git','status','--porcelain'])
        if p.returncode!=0: return ReadinessCheck(check_id='git_clean',title='Git working tree',status='blocker',detail='Unable to inspect Git working tree.',remediation='Initialize/fix Git before delivery.',blocker_class='HARD_TECHNICAL_BLOCKER')
        dirty=[x for x in p.stdout.splitlines() if x.strip()]
        if dirty: return ReadinessCheck(check_id='git_clean',title='Git working tree',status='blocker',detail=f'Working tree has {len(dirty)} uncommitted path(s).',remediation='Commit, revert, or intentionally exclude all pending changes.',blocker_class='HARD_TECHNICAL_BLOCKER')
        return ReadinessCheck(check_id='git_clean',title='Git working tree',status='pass',detail='Working tree is clean.')
    def integration_branch(self):
        p=self._run(['git','branch','--show-current']); b=p.stdout.strip()
        if p.returncode!=0 or not b: return ReadinessCheck(check_id='integration_branch',title='Delivery branch',status='blocker',detail='Current Git branch could not be determined.',blocker_class='HARD_TECHNICAL_BLOCKER')
        if not b.startswith('ai/integration/'): return ReadinessCheck(check_id='integration_branch',title='Delivery branch',status='warning',detail=f'Current branch is `{b}`, not an AI integration branch.',remediation='Review whether this is the intended delivery source branch.')
        return ReadinessCheck(check_id='integration_branch',title='Delivery branch',status='pass',detail=f'Delivery source branch: `{b}`.')
    def approved_requirement_gate(self):
        p=self.repo/'docs'/'requirement.md'
        if not p.exists(): return ReadinessCheck(check_id='requirement_gate',title='Requirement approval gate',status='blocker',detail='docs/requirement.md is missing.',blocker_class='CLIENT_INPUT_REQUIRED',remediation='Create/approve requirements before delivery.')
        t=p.read_text(encoding='utf-8',errors='replace'); ok='CLIENT_APPROVED' in t and 'Ready for development: True' in t
        if not ok: return ReadinessCheck(check_id='requirement_gate',title='Requirement approval gate',status='blocker',detail='Approved implementation gate is not present.',remediation='Resolve requirements and obtain approval before delivery.',blocker_class='CLIENT_INPUT_REQUIRED')
        return ReadinessCheck(check_id='requirement_gate',title='Requirement approval gate',status='pass',detail='Approved requirement gate is present.')
    def unresolved_project_decisions(self):
        hits=self._decision_placeholders()
        if not hits: return ReadinessCheck(check_id='unresolved_decisions',title='Unresolved project decisions',status='pass',detail='No TBD/to-be-decided markers found in delivery-critical docs.')
        details=', '.join(f"{h['file']}:{h['line']}" for h in hits)
        if all(h['deployment_related'] for h in hits):
            return ReadinessCheck(
                check_id='unresolved_decisions',
                title='Unresolved project decisions',
                status='blocker',
                detail=f'Deployment target is unresolved at {details}.',
                remediation='Resolve the internal deployment decision before delivery.',
                blocker_class='AUTO_RESOLVABLE_INTERNAL',
                auto_resolvable=True,
                proposed_resolution='Use Vercel as the deployment target under internal agency policy.',
            )
        return ReadinessCheck(check_id='unresolved_decisions',title='Unresolved project decisions',status='blocker',detail=f'Unresolved delivery-impacting decisions found at {details}.',remediation='Resolve the remaining decisions before delivery.',blocker_class='CLIENT_INPUT_REQUIRED')
    def placeholder_content(self):
        hits=[]
        for base in (self.repo/'src'/'content',self.repo/'public'):
            if not base.exists(): continue
            for p in base.rglob('*'):
                if not p.is_file() or p.suffix.lower() not in {'.ts','.tsx','.js','.jsx','.json','.md','.txt'}: continue
                t=p.read_text(encoding='utf-8',errors='replace')
                if any(x.search(t) for x in self.CONTENT_PLACEHOLDER_PATTERNS): hits.append(p.relative_to(self.repo).as_posix())
        if hits: return ReadinessCheck(check_id='placeholder_content',title='Placeholder/client content',status='blocker',detail=f'Potential placeholder content found in {len(hits)} file(s): '+', '.join(hits[:8]),remediation='Replace placeholders with approved client content or explicitly approve placeholder delivery.',blocker_class='CLIENT_INPUT_REQUIRED')
        return ReadinessCheck(check_id='placeholder_content',title='Placeholder/client content',status='pass',detail='No obvious placeholder markers found in content/assets.')
    def tracked_secret_files(self):
        p=self._run(['git','ls-files']); tracked={x.strip().replace('\\','/') for x in p.stdout.splitlines() if x.strip()}; risky=[]
        for path in tracked:
            name=Path(path).name
            if name in self.SECRET_FILE_NAMES or (name.startswith('.env.') and name!='.env.example'): risky.append(path)
        if risky: return ReadinessCheck(check_id='secret_files',title='Tracked secret files',status='blocker',detail='Potential secret-bearing file(s) are tracked: '+', '.join(sorted(risky)),remediation='Remove real secret files from Git and rotate exposed credentials.',blocker_class='HARD_TECHNICAL_BLOCKER')
        return ReadinessCheck(check_id='secret_files',title='Tracked secret files',status='pass',detail='No real .env/secret-bearing configuration files are tracked.')
    def environment_contract(self):
        source=''
        for base in (self.repo/'src',self.repo/'app'):
            if not base.exists(): continue
            for p in base.rglob('*'):
                if p.is_file() and p.suffix.lower() in {'.ts','.tsx','.js','.jsx','.mjs','.cjs'}: source+='\n'+p.read_text(encoding='utf-8',errors='replace')
        required=sorted(set(re.findall(r'process\.env\.([A-Z][A-Z0-9_]*)',source))); example=self.repo/'.env.example'; documented=set()
        if example.exists():
            for line in example.read_text(encoding='utf-8',errors='replace').splitlines():
                m=re.match(r'\s*([A-Z][A-Z0-9_]*)\s*=',line)
                if m: documented.add(m.group(1))
        missing=[x for x in required if x not in documented]
        if missing: return ReadinessCheck(check_id='environment_contract',title='Environment contract',status='blocker',detail='Required environment variable(s) missing from .env.example: '+', '.join(missing),remediation='Document every required runtime environment variable in .env.example.',blocker_class='HARD_TECHNICAL_BLOCKER')
        if required and not example.exists(): return ReadinessCheck(check_id='environment_contract',title='Environment contract',status='blocker',detail='Runtime environment variables are used but .env.example is missing.',blocker_class='HARD_TECHNICAL_BLOCKER')
        return ReadinessCheck(check_id='environment_contract',title='Environment contract',status='pass',detail='Runtime environment contract is documented'+(f' ({len(required)} variable(s)).' if required else '.'))
    def deployment_documentation(self):
        p=self.repo/'docs'/'deployment.md'
        if not p.exists(): return ReadinessCheck(check_id='deployment_docs',title='Deployment documentation',status='warning',detail='docs/deployment.md is missing.',remediation='Document the intended deployment flow before handoff.')
        if len(p.read_text(encoding='utf-8',errors='replace').strip())<80: return ReadinessCheck(check_id='deployment_docs',title='Deployment documentation',status='warning',detail='docs/deployment.md exists but is very limited.',remediation='Add runtime, environment, build, deploy, and rollback notes.')
        return ReadinessCheck(check_id='deployment_docs',title='Deployment documentation',status='pass',detail='Deployment documentation exists.')
    def production_commands(self):
        p=self.repo/'package.json'
        if p.exists():
            try: scripts=json.loads(p.read_text(encoding='utf-8')).get('scripts',{}) or {}
            except Exception: scripts={}
            npm=resolve_node_cli('npm')
            if npm:
                out=[]
                for s in ('lint','typecheck','test','build'):
                    if s in scripts: out.append([npm, "test"] if s == "test" else [npm, "run", s])
                return out
        if (self.repo/'pyproject.toml').exists(): return [[sys.executable,'-m','pytest','-q']]
        return []
    def run_production_validation(self):
        cmds=self.production_commands()
        if not cmds: return ReadinessCheck(check_id='production_validation',title='Production validation',status='blocker',detail='No deterministic production validation command was detected.',remediation='Define build/test validation before delivery.',blocker_class='HARD_TECHNICAL_BLOCKER'),[]
        rendered=[]
        for cmd in cmds:
            rendered.append(' '.join(cmd)); p=self._run(cmd)
            if p.returncode!=0: return ReadinessCheck(check_id='production_validation',title='Production validation',status='blocker',detail=f"`{' '.join(cmd)}` failed.\n"+(p.stderr or p.stdout or '').strip()[-1200:],remediation='Fix validation failure before delivery.',blocker_class='HARD_TECHNICAL_BLOCKER'),rendered
        return ReadinessCheck(check_id='production_validation',title='Production validation',status='pass',detail=f'All {len(cmds)} deterministic production validation command(s) passed.'),rendered
    def all_static_checks(self): return [self.git_clean(),self.integration_branch(),self.approved_requirement_gate(),self.unresolved_project_decisions(),self.placeholder_content(),self.tracked_secret_files(),self.environment_contract(),self.deployment_documentation()]
