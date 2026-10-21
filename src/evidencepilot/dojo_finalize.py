"""Create a provenance-preserving completed view after one provider-error recovery."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True)
    parser.add_argument('--recovery', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    original, recovery, output = Path(args.original), Path(args.recovery), Path(args.output)
    if output.exists():
        parser.error('Choose a new output directory')
    recovered = json.loads((recovery / 'cases.json').read_text(encoding='utf-8'))
    if len(recovered) != 14 or any('error' in row for row in recovered):
        parser.error('Expected 14 successful recovery records')
    expected = {f'user_task_{index}' for index in range(2, 22)}
    records, failures = {}, []
    for defense in ('none', 'boundary', 'scoped'):
        for attack in ('none', 'important_instructions_no_names'):
            name = defense + '-' + attack
            rows = json.loads((original / name / 'cases.json').read_text(encoding='utf-8'))
            good = []
            for row in rows:
                if 'error' in row:
                    failures.append({'group': name, 'record': row, 'source': str(original / name / 'cases.json')})
                else:
                    good.append({**row, 'source_record': str(original / name / 'cases.json')})
            if defense == 'scoped' and attack != 'none':
                good += [{**row, 'source_record': str(recovery / 'cases.json')} for row in recovered]
            if len(good) != 20 or {r['task_id'] for r in good} != expected:
                parser.error('Missing or duplicate task records')
            records[name] = sorted(good, key=lambda row: int(row['task_id'].split('_')[-1]))
    if len(failures) != 1 or failures[0]['record']['task_id'] != 'user_task_8':
        parser.error('Unexpected error history; investigate rather than silently dropping it')
    output.mkdir(parents=True)
    source_manifest = json.loads((original / 'manifest.json').read_text(encoding='utf-8'))
    manifest = {**source_manifest, 'formal_complete': True,
        'view': 'completed subset with one explicitly recorded error retry',
        'source_original': str(original), 'source_recovery': str(recovery),
        'original_error_cases': 1, 'retry_cases': 1, 'previously_unrun_cases_completed': 13,
        'failed_attempt_usage_incomplete': True}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (output / 'error-history.json').write_text(json.dumps(failures, indent=2), encoding='utf-8')
    for group, rows in records.items():
        path = output / group
        path.mkdir()
        (path / 'cases.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print(json.dumps({'complete_cases': sum(len(rows) for rows in records.values()),
                      'preserved_original_errors': len(failures), 'original_files_modified': False}, indent=2))


if __name__ == '__main__':
    main()
