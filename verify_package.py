"""Offline integrity, arithmetic and synthetic engineering tests."""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent

def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text('utf-8'))
    for item in manifest['files']:
        path = ROOT / item['path']
        assert path.is_file(), item['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], item['path']
    from recompute import calculate
    assert calculate() == json.loads((ROOT / 'recomputed_summary.json').read_text('utf-8'))
    sys.path.insert(0, str(ROOT / 'code'))
    import direct_controls
    import crosspage_parent_dev_v1
    checks = direct_controls.tests() + crosspage_parent_dev_v1.tests()
    assert len(checks) == 62 and all(c['passed'] for c in checks)
    print(json.dumps({'file_hashes': 'passed', 'aggregate_recomputation': 'passed',
                      'synthetic_checks_passed': len(checks)}, indent=2))

if __name__ == '__main__':
    main()
