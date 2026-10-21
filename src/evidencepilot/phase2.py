"""Paired development-only comparison of protocol and security policies."""
import argparse
import json
from pathlib import Path

from .providers import OpenAICompatibleProvider
from .security_eval import build_suite, run_case


def summarize(rows):
    metrics = []
    for defense in ('none', 'boundary', 'layered'):
        for attack in ('clean', 'redirect', 'spoof', 'exfiltrate'):
            all_rows = [r for r in rows if r['defense'] == defense and r['attack'] == attack]
            group = [r for r in all_rows if 'error' not in r]
            exposed = [r for r in group if r['attack_exposed']]
            metrics.append({'defense': defense, 'attack': attack, 'cases': len(all_rows),
                'errors': len(all_rows) - len(group),
                'task_success_rate': sum(r['task_success'] for r in group) / len(group) if group else None,
                'exposed_cases': len(exposed),
                'attack_success_rate_exposed': sum(bool(r['attack_success']) for r in exposed) / len(exposed) if exposed else None,
                'blocked_calls': sum(len(r['blocked_calls']) for r in group),
                'raw_leak_attempts': sum(r['raw_leak_attempt'] for r in group),
                'mean_latency_seconds': sum(r['elapsed_seconds'] for r in group) / len(group) if group else None})
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--limit-tasks', type=int, default=4)
    args = parser.parse_args()
    if args.limit_tasks < 1 or args.limit_tasks > 4:
        parser.error('Development pilot allows 1 to 4 tasks')
    provider = OpenAICompatibleProvider.from_environment()
    if provider is None:
        parser.error('Configure a model first')
    output = Path(args.output)
    if output.exists():
        parser.error('Choose a new output directory')
    output.mkdir(parents=True)
    docs, tasks = build_suite()
    tasks = [t for t in tasks if t['split'] == 'dev'][:args.limit_tasks]
    rows = []
    failures = 0
    for task_index, task in enumerate(tasks):
        for attack_index, attack in enumerate(('clean', 'redirect', 'spoof', 'exfiltrate')):
            # Rotate order to reduce constant ordering bias across conditions.
            modes = ['none', 'boundary', 'layered']
            shift = (task_index + attack_index) % 3
            for defense in modes[shift:] + modes[:shift]:
                print(f'{task["id"]} / {attack} / {defense}', flush=True)
                try:
                    row = run_case(docs, task, attack, provider, defense, 'v2')
                    failures = 0
                except Exception as exc:
                    row = {'task_id': task['id'], 'attack': attack, 'defense': defense, 'error': type(exc).__name__}
                    failures += 1
                rows.append(row)
                (output / 'cases.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
                summary = {'model_requested': provider.model, 'protocol': 'v2', 'dataset': 'synthetic-course-pilot-v2',
                    'split': 'dev', 'planned_cases': len(tasks) * 12, 'completed_cases': len(rows),
                    'thinking': 'disabled for DeepSeek', 'metrics': summarize(rows)}
                (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
                if failures >= 2:
                    raise SystemExit('Stopped after two consecutive errors; partial results preserved')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
