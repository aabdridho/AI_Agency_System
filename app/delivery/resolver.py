from __future__ import annotations
import re,subprocess
from pathlib import Path
class InternalResolutionError(RuntimeError): pass
class InternalResolver:
    def __init__(self,repo): self.repo=Path(repo)
    def _run(self,args): return subprocess.run(args,cwd=self.repo,capture_output=True,text=True,encoding='utf-8',errors='replace')
    def _require_clean_integration_branch(self):
        s=self._run(['git','status','--porcelain'])
        if s.returncode!=0 or s.stdout.strip(): raise InternalResolutionError('Safe internal resolution requires a clean Git working tree.')
        b=self._run(['git','branch','--show-current']).stdout.strip()
        if not b.startswith('ai/integration/'): raise InternalResolutionError(f'Safe internal resolution requires ai/integration/* branch; current={b!r}.')
    def resolve_deployment_target_to_vercel(self):
        self._require_clean_integration_branch(); changed=[]
        for name in ('requirement.md','architecture.md','deployment.md'):
            p=self.repo/'docs'/name
            if not p.exists(): continue
            original=p.read_text(encoding='utf-8',errors='replace'); lines=[]; touched=False
            for line in original.splitlines(keepends=True):
                if (
                    name == 'architecture.md'
                    and line.strip().lower() == '- deployment target'
                ):
                    touched = True
                    continue

                if re.search(r'(?i)deployment(?:_target|\s+target)?',line):
                    new=re.sub(r'(?i)to[_ -]be[_ -]decided(?:[_ -]internally)?|\btbd\b','vercel',line)
                    touched |= new!=line; lines.append(new)
                else: lines.append(line)
            updated=''.join(lines)
            if touched:
                p.write_text(updated,encoding='utf-8'); changed.append(p)
        if not changed: raise InternalResolutionError('No safe deployment-target placeholder could be resolved automatically.')
        proc=self._run(['git','status','--porcelain']); dirty=[]
        for line in proc.stdout.splitlines():
            if line.strip(): dirty.append(line[3:].strip().replace('\\','/'))
        expected={p.relative_to(self.repo).as_posix() for p in changed}; unexpected=[x for x in dirty if x not in expected]
        if unexpected:
            self._run(['git','restore','--']+[str(p.relative_to(self.repo)) for p in changed]); raise InternalResolutionError('Unexpected dirty paths detected; automatic resolution aborted: '+', '.join(unexpected))
        rel=[str(p.relative_to(self.repo)) for p in changed]; self._run(['git','add','--']+rel)
        c=self._run(['git','commit','-m','chore: resolve internal deployment target to Vercel'])
        if c.returncode!=0:
            self._run(['git','restore','--staged','.']); self._run(['git','restore','--']+rel); raise InternalResolutionError('Failed to commit automatic internal resolution: '+(c.stderr or c.stdout).strip())
        return {'resolution':'deployment_target=vercel','changed_files':sorted(expected),'commit_message':'chore: resolve internal deployment target to Vercel'}

    def resolve_nextjs_deployment_target_to_vercel(self):
        # Backward-compatible alias for older delivery CLI.
        return self.resolve_deployment_target_to_vercel()
