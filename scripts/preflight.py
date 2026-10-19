"""Read-only Git checks and local evidence; never stage, commit, push or open PRs."""
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_baseline import hashes, verify


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, encoding='utf-8').strip()


def cells(line):
    return [x.strip() for x in line.strip().strip('|').split('|')]


def run():
    protected = json.loads((ROOT / 'results/logs/00_protected_sha256.json')
                           .read_text(encoding='utf-8'))
    for name, expected in protected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    assert not git('diff', '--name-only', 'HEAD', '--', 'grading', '.github/workflows')
    assert not git('ls-files', '--others', '--exclude-standard', '--',
                   'grading', '.github/workflows')
    signatures = {}
    allowed = {'src/part1_circuit.py': 'serve_circuit',
               'src/part2_packet.py': 'serve_packet', 'src/metrics.py': 'summarize'}
    changed_src = set(git('diff', '--name-only', 'HEAD', '--', 'src').splitlines())
    assert changed_src == set(allowed)
    for path, function in allowed.items():
        old = ast.parse(git('show', f'HEAD:{path}'))
        new = ast.parse((ROOT / path).read_text(encoding='utf-8'))
        old_fn = next(n for n in old.body if isinstance(n, ast.FunctionDef))
        new_fn = next(n for n in new.body if isinstance(n, ast.FunctionDef))
        assert old_fn.name == new_fn.name == function
        assert ast.dump(old_fn.args) == ast.dump(new_fn.args)
        assert ast.dump(old_fn.body[0]) == ast.dump(new_fn.body[0])  # Original docstring.
        new_fn.body = old_fn.body
        assert ast.dump(old) == ast.dump(new), f'Changes outside TODO body: {path}'
        signatures[function] = ast.unparse(old_fn.args)
    assert git('branch', '--show-current') == 'main'
    assert git('remote', 'get-url', 'origin') == (
        'https://github.com/erjimeidianle/modern-switching-experiment-01.git')
    assert git('rev-parse', 'HEAD') == git('rev-parse', 'bc9099e')
    assert not git('diff', '--cached', '--name-only'), 'Index is not empty'
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)

    baseline = json.loads((ROOT / 'results/comparison.json').read_text(encoding='utf-8'))
    verify(ROOT / 'results', ROOT / '.build/repro')
    original_hashes = json.loads((ROOT / 'results/logs/05_artifact_verification.json')
                                .read_text(encoding='utf-8'))['sha256']
    assert hashes(ROOT / 'results') == original_hashes
    report = (ROOT / 'REPORT.md').read_text(encoding='utf-8')
    baseline_table = [cells(line) for line in report.split('原始payload守恒复核')[0].splitlines()
                      if re.match(r'\| (continuous|staggered_burst|synchronized_burst|light_random) \|', line)]
    assert len(baseline_table) == 8
    keys = ('payload_utilization', 'wire_utilization', 'mean_delay_ms',
            'max_delay_ms', 'loss_ratio', 'backlog_payload_bits')
    for row, rendered in zip(baseline['rows'], baseline_table):
        assert rendered[:2] == [row['scenario'], row['mode']]
        for key, text in zip(keys, rendered[2:]):
            expected = row[key] * (100 if key in ('payload_utilization',
                                                  'wire_utilization', 'loss_ratio') else 1)
            assert math.isclose(float(text), expected, abs_tol=.00005), (key, text, expected)
    extra = json.loads((ROOT / 'results/extra/header_sweep.json').read_text(encoding='utf-8'))
    extra_table = [cells(line) for line in report.split('## 包头参数变化实验')[1].splitlines()
                   if re.match(r'\| (continuous|staggered_burst|synchronized_burst|light_random) \|', line)]
    assert len(extra_table) == 12
    for rendered in extra_table:
        scenario, header = rendered[:2]
        run_data = next(r for r in extra['runs'] if r['config']['header_bits'] == int(header))
        row = next(r for r in run_data['rows'] if r['scenario'] == scenario and r['mode'] == 'packet')
        for key, text in zip(('payload_utilization', 'mean_delay_ms', 'loss_ratio',
                              'backlog_payload_bits'), rendered[2:]):
            expected = row[key] * (100 if key in ('payload_utilization', 'loss_ratio') else 1)
            assert math.isclose(float(text), expected, abs_tol=.00005)

    for name in ('REPORT.md', 'AI_LOG.md'):
        body = (ROOT / name).read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)', body):
            if '://' not in target and not target.startswith('#'):
                assert (ROOT / target).is_file(), (name, target)
        assert all(x not in body for x in ('姓名：填写', '学号：填写', 'GitHub：填写',
                                           '需求与输入：填写', '待补充'))
    grade = json.loads((ROOT / 'grade_report.json').read_text(encoding='utf-8'))
    assert grade['status'] == 'ok' and grade['automatic_score'] == 70

    required = list(allowed) + ['REPORT.md', 'AI_LOG.md', 'student_tests/test_my_case.py',
        'results/comparison.json', 'results/comparison.csv', 'results/comparison_metrics.png',
        'results/queue_occupancy.png', 'results/pcm_frame_view.png',
        'results/extra/header_sweep.json', 'results/extra/header_sweep.csv',
        'results/extra/header_sweep.png']
    supporting = ['requirements-lock.txt', '.vscode/settings.json', 'docs/execution_log.md',
                  'docs/submission_checklist.md', 'scripts/verify_baseline.py',
                  'scripts/header_experiment.py', 'scripts/preflight.py',
                  'codex_tasks/实验一_PRD_电路交换与分组交换.md']
    candidates = required + supporting
    secrets = re.compile(r'(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_\-]{20,}'
                         r'|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
    for name in candidates:
        path = ROOT / name
        assert path.is_file(), name
        assert not any(part in name for part in ('.venv/', '.build/', 'course_management/'))
        if path.suffix in ('.py', '.md', '.json', '.txt', '.csv'):
            assert not secrets.search(path.read_text(encoding='utf-8-sig')), name
    result = dict(status='passed', protected_files=len(protected),
                  signatures_unchanged=signatures, branch='main', head=git('rev-parse', 'HEAD'),
                  origin=git('remote', 'get-url', 'origin'), index_empty=True,
                  baseline_sha256_unchanged=True, report_tables_match=True,
                  report_links_exist=True, credential_pattern_scan='no matches in candidates',
                  automatic_score=70, manual_pending=30,
                  required_files=required, supporting_files=supporting,
                  evidence_logs='results/logs/ (original runs and diagnosed initial attempts)',
                  human_review='User stated review complete and authorized submission on 2026-10-19; this check runs before staging.')
    (ROOT / 'results/logs/08_preflight.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
