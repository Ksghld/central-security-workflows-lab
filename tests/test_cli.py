import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_missing_policy_fails_closed(tmp_path):
    output = tmp_path / 'result.json'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate.py'),
        '--target', str(tmp_path), '--policy', str(tmp_path / 'missing.json'),
        '--application-id', 'APP-00427', '--repository', 'synthetic/sample',
        '--repository-id', '10001', '--mode', 'enforce', '--output', str(output)], capture_output=True)
    assert result.returncode == 3
    assert json.loads(output.read_text())['result'] == 'tool_error'


def test_malformed_policy_fails_closed(tmp_path):
    policy = tmp_path / 'policy.json'
    policy.write_text('{')
    output = tmp_path / 'result.json'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate.py'),
        '--target', str(tmp_path), '--policy', str(policy), '--application-id', 'APP-00427',
        '--repository', 'synthetic/sample', '--repository-id', '10001', '--mode', 'monitor',
        '--output', str(output)], capture_output=True)
    assert result.returncode == 3
    assert json.loads(output.read_text())['result'] == 'tool_error'


def test_same_name_can_hide_missing_central_call():
    # Offline negative demonstration only; GitHub acceptance is unverified.
    import yaml
    tampered = yaml.load('jobs:\n  gate:\n    name: appsec-pr-gate\n    runs-on: ubuntu-latest\n    steps:\n      - run: "true"\n', Loader=yaml.BaseLoader)
    job = tampered['jobs']['gate']
    assert job['name'] == 'appsec-pr-gate'
    assert 'uses' not in job
    assert all('validate.py' not in step.get('run', '') for step in job['steps'])
