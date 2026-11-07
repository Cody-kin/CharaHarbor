"""Validate bilingual navigation, Markdown structure and local documentation links."""
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    'index', 'user-guide', 'wechat-bridge', 'onboarding', 'character-profiles',
    'character-states', 'source-updates', 'features', 'security', 'platform-validation',
)


def check(root=ROOT):
    errors = []
    docs = [root / 'README.md', root / 'README.zh-CN.md', *sorted((root / 'docs').rglob('*.md'))]
    docs += [root / name for name in ('ONBOARDING.md', 'ROLE_GUIDE.md', 'CHARACTER_STATES.md', 'RESEARCH.md')]
    for path in docs:
        relative = path.relative_to(root)
        if not str(relative).isascii(): errors.append(f'Non-English filename: {relative}')
        if not path.is_file(): errors.append(f'Missing document: {relative}'); continue
        text = path.read_text(encoding='utf-8')
        if text.count('```') % 2: errors.append(f'Unclosed fenced block: {relative}')
        # Ignore fenced examples; actual Markdown links must resolve within the package.
        prose = re.sub(r'```.*?```', '', text, flags=re.S)
        for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', prose):
            parts = urlsplit(target)
            if parts.scheme or parts.netloc: continue
            if not parts.path: continue
            resolved = (path.parent / unquote(parts.path)).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append(f'Broken/outside local link: {relative}: {target}')
    for page in PAGES:
        for language, other in (('en', 'zh-CN'), ('zh-CN', 'en')):
            path = root / 'docs' / language / f'{page}.md'
            if not path.is_file(): errors.append(f'Missing language page: {language}/{page}'); continue
            text = path.read_text(encoding='utf-8')
            if f'../{other}/{page}.md' not in text.split('\n', 2)[0]:
                errors.append(f'Missing matching language switch: {language}/{page}')
            if page != 'index' and len(text) < 700:
                errors.append(f'Incomplete language page: {language}/{page}')
    for filename, target in (('README.md', 'README.zh-CN.md'), ('README.zh-CN.md', 'README.md')):
        if f']({target})' not in (root / filename).read_text(encoding='utf-8'):
            errors.append(f'Missing README language switch: {filename}')
    for path in root.rglob('*'):
        if any(part in ('.git', '.venv', '__pycache__', '.companion-state', '.setup-demo-state') for part in path.relative_to(root).parts): continue
        if not str(path.relative_to(root)).isascii(): errors.append(f'Non-English path: {path.relative_to(root)}')
    return errors


if __name__ == '__main__':
    failures = check()
    for failure in failures: print(failure)
    if failures: raise SystemExit(1)
    print('Bilingual documentation passed: 10 matched page pairs, README switches, local links, fences and English filenames.')
