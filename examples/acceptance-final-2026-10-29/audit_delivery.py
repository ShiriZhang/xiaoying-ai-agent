"""Read-only delivery, links and spec matrix checks; no model requests."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
paths = subprocess.check_output(
    ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT
).decode().rstrip('\0').split('\0')
paths = [p for p in paths if (ROOT / p).is_file()]
required = ['README.md', 'pyproject.toml', 'uv.lock', '.env.example'] + [
    'docs/' + name for name in ['01-requirements.md', '02-solution.md',
    '03-evaluation.md', '04-ai-usage.md', '05-retrospective.md']]
forbidden = [p for p in paths if p == '.env' or p.startswith(
    ('.venv/', 'models/', 'runtime/', '.cache/')) or p.endswith(('.sqlite3', '.pyc'))]
key = dotenv_values(ROOT / '.env').get('DEEPSEEK_API_KEY')
secret_files = [p for p in paths if key and key.encode() in (ROOT / p).read_bytes()]
matrix = json.loads((ROOT / 'examples/batch-11/acceptance-matrix.json').read_text(encoding='utf-8'))['scenarios']
spec_scenarios = []
for spec in sorted((ROOT / 'docs/specs').glob('*.md')):
    spec_scenarios.extend((spec.stem, s) for s in re.findall(
        r'^#### Scenario: (.+)$', spec.read_text(encoding='utf-8'), re.M))
matrix_scenarios = [(r['capability'], r['scenario']) for r in matrix]
missing_evidence = sorted({p for row in matrix for p in row['tests'] + row['evidence'] if not (ROOT / p).is_file()})
missing_links = []
link_count = 0
for name in ['README.md'] + [p for p in paths if p.startswith('docs/') and p.endswith('.md')]:
    path = ROOT / name
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        if '://' in target or target.startswith(('#', 'mailto:')):
            continue
        target = unquote(target.split('#', 1)[0].strip('<>'))
        if not target:
            continue
        link_count += 1
        if not (path.parent / target).exists():
            missing_links.append({'file': name, 'target': target})
checks = {
    'required_files_present': all(p in paths for p in required),
    'required_directories_present': all(any(p.startswith(d + '/') for p in paths)
        for d in ['src', 'tests', 'examples', 'data']),
    'no_forbidden_delivery_files': not forbidden,
    'configured_key_not_in_delivery': bool(key) and not secret_files,
    'matrix_matches_all_spec_scenarios': sorted(spec_scenarios) == sorted(matrix_scenarios),
    'all_matrix_test_and_evidence_paths_exist': not missing_evidence,
    'readme_and_docs_links_resolve': not missing_links,
}
report = {'passed': all(checks.values()), 'checks': checks, 'scenario_count': len(spec_scenarios),
    'delivery_file_count': len(paths), 'checked_local_links': link_count,
    'forbidden_files': forbidden, 'secret_files': secret_files, 'missing_links': missing_links,
    'missing_evidence': missing_evidence, 'key_available_for_exact_scan': bool(key),
    'working_document_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        for p in ['README.md', 'docs/04-ai-usage.md', 'docs/05-retrospective.md']},
    'limits': 'Exact configured-key and filename scan only; not universal secret/PII detection. Matrix mapping is not semantic proof.'}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=OUT / 'delivery-audit.json')
output = parser.parse_args().output
if output.exists():
    raise SystemExit('Use a new output; preserve prior evidence')
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'passed': report['passed'], 'checks': checks, 'scenario_count': len(spec_scenarios)}))
