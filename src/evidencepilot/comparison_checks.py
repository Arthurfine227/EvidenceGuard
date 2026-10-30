"""Save actual offline test output for the second-model reproducibility record."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Choose a new output directory')
    output.mkdir(parents=True)
    suites = []
    for name in ('tests', 'tests_dojo'):
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', name, '-v']
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        (output / (name + '.txt')).write_text(result.stdout + result.stderr, encoding='utf-8')
        suites.append({'suite': name, 'returncode': result.returncode,
                       'command': ['python', *command[1:]], 'api_calls': 0})
    (output / 'checks.json').write_text(json.dumps(suites, indent=2), encoding='utf-8')
    print(json.dumps(suites, indent=2))
    if any(s['returncode'] for s in suites):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
