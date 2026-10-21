"""Fetch a pinned upstream dataset without executing any upstream code."""
import hashlib
import json
import urllib.request
from pathlib import Path

REVISION = 'f19c9f2c79a41046eb13c03c51a24c567a8ffa07'
ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / 'data' / 'injecagent'
FILES = ['LICENCE', 'README.md', 'data/tools.json', 'data/test_cases_dh_base.json', 'data/test_cases_ds_base.json']


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    entries = []
    for relative in FILES:
        url = f'https://raw.githubusercontent.com/uiuc-kang-lab/InjecAgent/{REVISION}/{relative}'
        target = DESTINATION / relative
        if target.exists():
            payload = target.read_bytes()
        else:
            payload = urllib.request.urlopen(url, timeout=30).read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        entries.append({'path': relative, 'url': url, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)})
    manifest = {'repository': 'https://github.com/uiuc-kang-lab/InjecAgent', 'revision': REVISION,
                'license': 'MIT; see LICENCE', 'files': entries}
    path = DESTINATION / 'manifest.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8')) != manifest:
        raise RuntimeError('Existing manifest mismatch; do not overwrite upstream data')
    path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Pinned {len(entries)} files at {REVISION}; retained upstream license.')


if __name__ == '__main__':
    main()
