"""Fail closed on personal runtime paths, credentials or files in a source tree."""
import re
import sys
from pathlib import Path

PATTERNS={
    'credential':r'(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)',
    'private_runtime':r'(?:/Users/[^/\s]+/|/home/admin/|wxid_[a-z0-9]{8,})',
}


def scan(root):
    findings=[]
    for p in Path(root).rglob('*'):
        rel=p.relative_to(root)
        # Tool-managed/test-generated directories are never publish inputs.
        if any(x in ('.git','.venv','__pycache__','.companion-state','.setup-demo-state') for x in rel.parts):continue
        if not p.is_file():continue
        if p.suffix in ('.sqlite','.db','.log','.zip','.png','.jpg','.gif') or p.name.startswith('.env') or p.name=='config.local.json':
            findings.append((str(rel),'runtime_or_binary_file'));continue
        try:text=p.read_text(encoding='utf-8')
        except UnicodeDecodeError:findings.append((str(rel),'unexpected_binary'));continue
        # Patterns are in this scanner by design; never exempt other sources.
        if rel.as_posix()=='tools/scan_public.py':continue
        for name,pattern in PATTERNS.items():
            if re.search(pattern,text):findings.append((str(rel),name))
    return findings


if __name__=='__main__':
    findings=scan(Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve())
    if findings:
        for path,kind in findings:print(kind,path)
        raise SystemExit(1)
    print('Public source scan passed (heuristic; manual manifest review still required).')
