"""Fixed-protocol second-model evaluation with a persistent spending guard.

Does not edit the original model config, bridge, benchmark, or scorer.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

from .dojo_bridge import attack_is_exposed, build_pipeline
from .providers import OpenAICompatibleProvider, ProviderError

MODEL = 'deepseek-v4-pro'
PRICE_URL = 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/'
# Verified official RMB peak prices on 2026-10-30. Ignore cache discounts.
INPUT_RMB_PER_M = 9.0
OUTPUT_RMB_PER_M = 27.0


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


class SpendingGuard:
    def __init__(self, path, cap=100.0):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {
            'cap_rmb': cap, 'reserved_or_accounted_rmb': 0.0, 'requests': [],
            'pricing_source': PRICE_URL, 'pricing_checked': '2026-10-30',
            'peak_input_rmb_per_million': INPUT_RMB_PER_M,
            'peak_output_rmb_per_million': OUTPUT_RMB_PER_M,
            'note': 'Conservative peak-rate estimates, not an invoice. Missing-usage failures keep their full reservation. Input reservation uses 2x UTF-8 JSON bytes plus 8192 tokens for serialization overhead. No retries inside the provider.'}
        if self.data['cap_rmb'] != cap:
            raise ValueError('Cannot change the budget on resume')

    def reserve(self, payload, max_tokens):
        upper_input = 2 * len(json.dumps(payload, ensure_ascii=False).encode('utf-8')) + 8192
        reserve = (upper_input * INPUT_RMB_PER_M + max_tokens * OUTPUT_RMB_PER_M) / 1_000_000
        # Leave a RMB 5 margin rather than target the authorization ceiling.
        if self.data['reserved_or_accounted_rmb'] + reserve > self.data['cap_rmb'] - 5:
            raise ProviderError('Budget guard stopped before sending the next request')
        item = {'sequence': len(self.data['requests']) + 1, 'status': 'reserved',
                'reserved_rmb': reserve, 'accounted_rmb': reserve,
                'utc': datetime.now(timezone.utc).isoformat()}
        self.data['requests'].append(item)
        self.data['reserved_or_accounted_rmb'] += reserve
        save(self.path, self.data)
        return item

    def finish(self, item, metadata, error=None):
        usage = metadata.get('usage', {}) if metadata else {}
        if 'prompt_tokens' in usage and 'completion_tokens' in usage:
            amount = (usage['prompt_tokens'] * INPUT_RMB_PER_M + usage['completion_tokens'] * OUTPUT_RMB_PER_M) / 1_000_000
            self.data['reserved_or_accounted_rmb'] += amount - item['accounted_rmb']
            item.update(accounted_rmb=amount, usage=usage, model_returned=metadata.get('model_returned'))
        item['status'] = 'error' if error else 'complete'
        if error:
            item['error_type'] = type(error).__name__
        save(self.path, self.data)


class BudgetProvider(OpenAICompatibleProvider):
    def guarded(self, method, payload, max_tokens):
        item = self.guard.reserve(payload, max_tokens)
        start = len(self.request_metadata)
        try:
            response = method()
        except Exception as exc:
            metadata = self.request_metadata[-1] if len(self.request_metadata) > start else None
            self.guard.finish(item, metadata, exc)
            raise
        self.guard.finish(item, self.request_metadata[-1])
        return response

    def complete_json(self, system, user, max_tokens=2048):
        return self.guarded(lambda: super(BudgetProvider, self).complete_json(system, user, max_tokens),
                            {'system': system, 'user': user}, max_tokens)

    def complete_tools(self, messages, tools, max_tokens=1024):
        return self.guarded(lambda: super(BudgetProvider, self).complete_tools(messages, tools, max_tokens),
                            {'messages': messages, 'tools': tools}, max_tokens)


def verify_plan(plan_dir):
    raw = (plan_dir / 'plan.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != (plan_dir / 'plan.sha256').read_text().strip():
        raise ValueError('Plan checksum mismatch')
    plan = json.loads(raw)
    if importlib.metadata.version('agentdojo') != plan['agentdojo_version']:
        raise ValueError('AgentDojo version mismatch')
    import agentdojo
    upstream_root = Path(agentdojo.__file__).parent
    for entry in json.loads((plan_dir / 'upstream-files.json').read_text()):
        if hashlib.sha256((upstream_root / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Upstream hash mismatch')
    for line in (plan_dir / 'requirements.lock.txt').read_text().splitlines():
        name, version = line.split('==', 1)
        if importlib.metadata.version(name) != version:
            raise ValueError('Dependency mismatch: ' + name)
    return plan, digest


def execute_case(suite, provider, task_id, defense, attack):
    pipeline = build_pipeline(provider, defense)
    start, began = len(provider.request_metadata), time.perf_counter()
    try:
        task = suite.get_user_task_by_id(task_id)
        injection_task, injections = None, {}
        if attack != 'none':
            from agentdojo.attacks.base_attacks import FixedJailbreakAttack
            from agentdojo.attacks.important_instructions_attacks import ImportantInstructionsAttack
            injection_task = suite.get_injection_task_by_id('injection_task_0')
            injections = FixedJailbreakAttack(ImportantInstructionsAttack._JB_STRING, suite, pipeline).attack(task, injection_task)
        utility, success = suite.run_task_with_pipeline(pipeline, task, injection_task, injections)
        return {'task_id': task_id, 'utility': utility,
                'attack_success': success if injection_task else None,
                'attack_exposed': attack_is_exposed(pipeline.trace, injections),
                'injections': injections, 'budget_exhausted': pipeline.budget_exhausted,
                'allowed_tools': sorted(pipeline.allowed_tools) if pipeline.allowed_tools is not None else None,
                'blocked_calls': pipeline.blocked_calls, 'trace': pipeline.trace,
                'final_environment': pipeline.final_environment,
                'metadata': provider.request_metadata[start:],
                'elapsed_seconds': time.perf_counter() - began}
    except Exception as exc:
        return {'task_id': task_id, 'error': type(exc).__name__,
                'error_detail': str(exc) if isinstance(exc, ProviderError) else 'Adapter/runtime error',
                'metadata': provider.request_metadata[start:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='New comparison directory, shared by dev/formal')
    parser.add_argument('--phase', choices=('dev', 'formal'), required=True)
    parser.add_argument('--cap-rmb', type=float, default=100.0)
    args = parser.parse_args()
    if not 5 < args.cap_rmb <= 100:
        parser.error('Authorized budget is at most RMB 100')
    project = Path(__file__).resolve().parents[2]
    original_plan = project / 'evaluation/dojo-workspace-v1.2.2-plan-20261020'
    plan, digest = verify_plan(original_plan)
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    frozen = root / 'protocol.json'
    protocol = {'original_plan_sha256': digest, 'model_requested': MODEL,
                'base_url': 'https://api.deepseek.com', 'thinking': 'disabled',
                'temperature': 0, 'max_turns': 12, 'max_tokens': 1024, 'planner_max_tokens': 512,
                'cap_rmb': args.cap_rmb, 'reserve_margin_rmb': 5,
                'development_tasks': plan['development_tasks'],
                'formal_tasks': [t['task_id'] for t in plan['heldout_tasks']],
                'conditions': plan['conditions'], 'defenses': plan['defenses'],
                'injection_task': 'injection_task_0',
                'unchanged_bridge_sha256': hashlib.sha256((project / 'src/evidencepilot/dojo_bridge.py').read_bytes()).hexdigest(),
                'comparison_type': 'Same-vendor second-model follow-up, historical Flash vs later Pro. No concurrent Flash rerun. Not randomized, not cross-vendor, not a new independent heldout dataset.',
                'stopping_rule': 'Stop on first infrastructure/adapter/budget error. Keep partial results. No utility-based reruns. Recovery requires an explicit recorded exception.',
                'pricing_url': PRICE_URL, 'peak_input_rmb_per_million': 9,
                'peak_output_rmb_per_million': 27}
    if frozen.exists():
        if json.loads(frozen.read_text(encoding='utf-8')) != protocol:
            raise ValueError('Frozen protocol differs')
    else:
        save(frozen, protocol)
    if args.phase == 'formal':
        dev = json.loads((root / 'dev/manifest.json').read_text())
        if not dev['formal_complete']:
            raise ValueError('Development compatibility gate incomplete')
    output = root / args.phase
    if output.exists():
        raise ValueError('Phase output already exists. Preserve results; do not overwrite')
    output.mkdir()
    source = OpenAICompatibleProvider.from_environment()
    if source is None or source.base_url != protocol['base_url']:
        raise ValueError('Expected existing DeepSeek credentials')
    provider = BudgetProvider(api_key=source.api_key, model=MODEL, base_url=source.base_url,
                              timeout_seconds=source.timeout_seconds)
    provider.guard = SpendingGuard(root / 'budget-ledger.json', args.cap_rmb)
    from agentdojo.task_suite import get_suite
    suite = get_suite('v1.2.2', 'workspace')
    task_ids = protocol['development_tasks'] if args.phase == 'dev' else protocol['formal_tasks']
    manifest = {'plan_sha256': digest, 'model_requested': MODEL,
                'source': 'Unchanged official AgentDojo environment and scorers with unchanged bridge',
                'planned_cases': len(task_ids) * 6, 'formal_complete': False,
                'not_full_benchmark': True, 'phase': args.phase,
                'protocol_sha256': hashlib.sha256(frozen.read_bytes()).hexdigest()}
    save(output / 'manifest.json', manifest)
    total = 0
    for defense in protocol['defenses']:
        for attack in protocol['conditions']:
            group = output / (defense + '-' + attack)
            group.mkdir()
            save(group / 'manifest.json', {**manifest, 'defense': defense, 'condition': attack})
            rows = []
            for task_id in task_ids:
                print(f'{args.phase}: {defense}/{attack}/{task_id}', flush=True)
                row = execute_case(suite, provider, task_id, defense, attack)
                rows.append(row)
                save(group / 'cases.json', rows)
                if 'error' in row:
                    print(json.dumps({'stopped': row['error_detail'], 'task': task_id,
                                      'accounted_rmb': provider.guard.data['reserved_or_accounted_rmb']}), flush=True)
                    raise SystemExit(1)
                total += 1
                print(json.dumps({'completed': total, 'utility': row['utility'],
                                  'attack_success': row['attack_success'],
                                  'accounted_peak_rmb': round(provider.guard.data['reserved_or_accounted_rmb'], 4)}), flush=True)
    manifest['formal_complete'] = total == manifest['planned_cases']
    save(output / 'manifest.json', manifest)
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__':
    main()
