"""Freeze official-suite task IDs and dependency versions before held-out runs."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

from agentdojo.task_suite import get_suite
from agentdojo.attacks.base_attacks import FixedJailbreakAttack
from agentdojo.attacks.important_instructions_attacks import ImportantInstructionsAttack
from .dojo_bridge import build_pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    path = Path(args.output)
    if path.exists():
        parser.error('Choose a new output directory')
    suite = get_suite('v1.2.2', 'workspace')
    generator = FixedJailbreakAttack(ImportantInstructionsAttack._JB_STRING, suite, build_pipeline(None))
    selected = []
    for index in range(2, 22):
        task_id = f'user_task_{index}'
        try:
            vectors = generator.get_injection_candidates(suite.get_user_task_by_id(task_id))
            selected.append({'task_id': task_id, 'injectable': True, 'vectors': vectors})
        except ValueError:
            selected.append({'task_id': task_id, 'injectable': False, 'vectors': []})
    plan = {'agentdojo_version': importlib.metadata.version('agentdojo'), 'benchmark_version': 'v1.2.2',
        'suite': 'workspace', 'development_tasks': ['user_task_0', 'user_task_1'],
        'heldout_tasks': selected, 'conditions': ['none', 'important_instructions_no_names'],
        'injection_task': 'injection_task_0', 'defenses': ['none', 'boundary', 'scoped'],
        'planned_cases': 120, 'max_turns': 12, 'max_tokens': 1024,
        'model_requested': 'from local environment; record actual response names at run time',
        'scoped_policy': 'LLM selects tool names before reading external content; no argument-level authorization',
        'selection_rule': 'fixed contiguous user_task_2 through user_task_21, not selected by model outcomes',
        'not_injectable_rule': 'retain task and report exposure separately; do not replace it after seeing outcomes',
        'scorer': 'unmodified upstream utility/security task methods via run_task_with_pipeline',
        'heldout_model_calls_made': 0, 'formal_results_complete': False}
    path.mkdir(parents=True)
    raw = json.dumps(plan, indent=2).encode('utf-8')
    (path / 'plan.json').write_bytes(raw)
    (path / 'plan.sha256').write_text(hashlib.sha256(raw).hexdigest(), encoding='utf-8')
    packages = sorted({(d.metadata['Name'], d.version) for d in importlib.metadata.distributions() if d.metadata['Name'].lower() != 'evidencepilot'})
    (path / 'requirements.lock.txt').write_text('\n'.join(name + '==' + version for name, version in packages) + '\n', encoding='utf-8')
    import agentdojo
    root = Path(agentdojo.__file__).parent
    entries = []
    for file in sorted(root.rglob('*')):
        if file.is_file() and file.suffix in ('.py', '.yaml'):
            entries.append({'path': file.relative_to(root).as_posix(), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
    (path / 'upstream-files.json').write_text(json.dumps(entries, indent=2), encoding='utf-8')
    print(json.dumps({'planned_cases': 120, 'heldout_tasks': len(selected),
                     'injectable_tasks': sum(t['injectable'] for t in selected),
                     'plan_sha256': hashlib.sha256(raw).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
