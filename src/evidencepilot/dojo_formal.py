"""Execute the frozen 20-task plan; never substitutes tasks after outcomes."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, help='Frozen plan directory')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    plan_dir, output = Path(args.plan), Path(args.output)
    raw = (plan_dir / 'plan.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != (plan_dir / 'plan.sha256').read_text(encoding='utf-8').strip():
        parser.error('Plan checksum mismatch')
    plan = json.loads(raw)
    if importlib.metadata.version('agentdojo') != plan['agentdojo_version']:
        parser.error('AgentDojo version mismatch')
    import agentdojo
    upstream_root = Path(agentdojo.__file__).parent
    for entry in json.loads((plan_dir / 'upstream-files.json').read_text(encoding='utf-8')):
        if hashlib.sha256((upstream_root / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            parser.error('Upstream source/data checksum mismatch')
    for line in (plan_dir / 'requirements.lock.txt').read_text(encoding='utf-8').splitlines():
        name, version = line.split('==', 1)
        if importlib.metadata.version(name) != version:
            parser.error('Dependency version mismatch: ' + name)
    if output.exists():
        parser.error('Choose a new output directory')
    output.mkdir(parents=True)
    manifest = {'plan_sha256': digest, 'planned_cases': plan['planned_cases'],
                'source': 'unmodified AgentDojo workspace environment/scorers plus custom DeepSeek bridge',
                'formal_complete': False, 'not_full_benchmark': True}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    all_rows = []
    for defense in plan['defenses']:
        for attack in plan['conditions']:
            group = output / (defense + '-' + attack)
            command = [sys.executable, '-m', 'evidencepilot.dojo_bridge', '--defense', defense,
                       '--attack', attack, '--output', str(group)]
            for task in plan['heldout_tasks']:
                command += ['--task', task['task_id']]
            print(f'Running formal group: {defense} / {attack}', flush=True)
            completed = subprocess.run(command, check=False)
            if (group / 'cases.json').exists():
                for row in json.loads((group / 'cases.json').read_text(encoding='utf-8')):
                    all_rows.append({'defense': defense, 'attack': attack, **row})
            summary = {**manifest, 'completed_cases': len(all_rows), 'groups': []}
            for mode in plan['defenses']:
                for condition in plan['conditions']:
                    rows = [r for r in all_rows if r['defense'] == mode and r['attack'] == condition]
                    summary['groups'].append({'defense': mode, 'condition': condition, 'cases': len(rows),
                        'errors': sum('error' in r for r in rows),
                        'utility_passes': sum(r.get('utility', False) for r in rows),
                        'attack_exposed': sum(r.get('attack_exposed', False) for r in rows),
                        'attack_successes': sum(bool(r.get('attack_success')) for r in rows) if condition != 'none' else None})
            (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
            if completed.returncode:
                raise SystemExit('Formal run stopped on error; preserve partial results and diagnose. Do not score errors as safe cases.')
    manifest['formal_complete'] = len(all_rows) == plan['planned_cases']
    summary.update(manifest)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
