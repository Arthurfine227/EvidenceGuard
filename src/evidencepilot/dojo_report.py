"""Summarize fixed development runs without making any model calls."""
import argparse
import json
from pathlib import Path

from .dojo_bridge import attack_is_exposed

ROOT = Path(__file__).resolve().parents[2]
RUNS = ['dojo-clean-dev-20261020', 'dojo-none-attacked-dev-20261020',
        'dojo-boundary-clean-dev-20261020', 'dojo-boundary-attacked-dev-20261020',
        'dojo-scoped-clean-dev-20261020', 'dojo-scoped-attacked-dev-20261020']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error('Choose a new output directory')
    groups, metadata = [], []
    for run in RUNS:
        path = ROOT / 'results' / run
        config = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
        rows = json.loads((path / 'cases.json').read_text(encoding='utf-8'))
        groups.append({'run': run, 'defense': config['defense'], 'condition': config['condition'],
            'cases': len(rows), 'utility_passes': sum(r.get('utility', False) for r in rows),
            'attack_successes': sum(bool(r.get('attack_success')) for r in rows) if config['condition'] != 'clean-integration-only' and config['condition'] != 'none' else None,
            'exposure_recomputed_from_decoded_tool_results': sum(attack_is_exposed(r['trace'], r.get('injections', {})) for r in rows),
            'blocked_calls': sum(len(r.get('blocked_calls', [])) for r in rows),
            'errors': sum('error' in r for r in rows)})
        metadata.extend(m for row in rows for m in row.get('metadata', []))
    summary = {'split': 'development only; official workspace tasks 0 and 1', 'distinct_tasks': 2,
        'groups': groups, 'requests': len(metadata),
        'prompt_tokens': sum(m['usage'].get('prompt_tokens', 0) for m in metadata),
        'completion_tokens': sum(m['usage'].get('completion_tokens', 0) for m in metadata),
        'response_models': sorted({str(m['model_returned']) for m in metadata}),
        'formal_results_complete': False, 'heldout_model_calls_made': 0}
    output.mkdir(parents=True)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
