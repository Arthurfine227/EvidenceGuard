"""Recompute upstream scores from stored final states and native traces, offline."""
import argparse
import json
from pathlib import Path


def restore_environment(suite, raw):
    """Preserve runtime stores reset by upstream after-validation initializers."""
    from agentdojo.default_suites.v1.tools.types import CalendarEvent, CloudDriveFile, Email
    after = suite.environment_type.model_validate(raw)
    after.calendar.events = {key: CalendarEvent.model_validate(value) for key, value in raw['calendar']['events'].items()}
    after.inbox.emails = {key: Email.model_validate(value) for key, value in raw['inbox']['emails'].items()}
    after.inbox.trash = {key: Email.model_validate(value) for key, value in raw['inbox']['trash'].items()}
    after.cloud_drive.files = {key: CloudDriveFile.model_validate(value) for key, value in raw['cloud_drive']['files'].items()}
    if after.model_dump(mode='json') != raw:
        raise ValueError('Restored state does not match stored state')
    return after


def validate_case(suite, task_id, row, attacked):
    from agentdojo.functions_runtime import FunctionCall
    from agentdojo.types import text_content_block_from_string as block
    task = suite.get_user_task_by_id(task_id)
    before = task.init_environment(suite.load_and_inject_default_environment(row.get('injections', {})))
    after = restore_environment(suite, row['final_environment'])
    trace = row['trace']
    calls = [FunctionCall(function=call['function']['name'], args=json.loads(call['function']['arguments']), id=call['id'])
             for message in trace if message['role'] == 'assistant' for call in (message.get('tool_calls') or [])]
    text = 'Execution stopped: turn budget exhausted.' if row['budget_exhausted'] else (trace[-1].get('content') or '')
    utility = suite._check_task_result(task, [block(text)], before, after, calls)
    issues = []
    if utility != row['utility']:
        issues.append('utility_mismatch')
    if attacked:
        injection = suite.get_injection_task_by_id('injection_task_0')
        success = suite._check_task_result(injection, [block(text)], before, after, calls)
        if success != row['attack_success']:
            issues.append('attack_score_mismatch')
    return issues


def main():
    from agentdojo.task_suite import get_suite
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root, output = Path(args.run), Path(args.output)
    if not json.loads((root / 'manifest.json').read_text(encoding='utf-8')).get('formal_complete'):
        parser.error('Formal run is incomplete')
    if output.exists():
        parser.error('Choose a new output directory')
    suite = get_suite('v1.2.2', 'workspace')
    issues, checked = [], 0
    for defense in ('none', 'boundary', 'scoped'):
        for attack in ('none', 'important_instructions_no_names'):
            rows = json.loads((root / (defense + '-' + attack) / 'cases.json').read_text(encoding='utf-8'))
            for row in rows:
                checked += 1
                for issue in validate_case(suite, row['task_id'], row, attack != 'none'):
                    issues.append({'task': row['task_id'], 'defense': defense, 'attack': attack, 'issue': issue})
    result = {'checked_cases': checked, 'score_recomputation_passed': checked == 120 and not issues,
              'issues': issues, 'api_calls': 0,
              'scope': 'recompute upstream utility/security from saved final states and proposed-call traces; not independent semantic ground truth'}
    output.mkdir(parents=True)
    (output / 'audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    if not result['score_recomputation_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
