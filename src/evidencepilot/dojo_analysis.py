"""Analyze a completed frozen subset without changing experimental outcomes."""
import argparse
import json
import math
from pathlib import Path


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - half), min(1, center + half)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root, output = Path(args.run), Path(args.output)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if not manifest.get('formal_complete'):
        parser.error('Formal subset is incomplete; do not issue a final analysis')
    if output.exists():
        parser.error('Choose a new analysis directory')
    rows, groups = [], []
    for defense in ('none', 'boundary', 'scoped'):
        for attack in ('none', 'important_instructions_no_names'):
            path = root / (defense + '-' + attack) / 'cases.json'
            cases = json.loads(path.read_text(encoding='utf-8'))
            if len(cases) != 20 or len({r['task_id'] for r in cases}) != 20 or any('error' in r for r in cases):
                parser.error('Missing, duplicate or errored case in a completed group')
            if {r['task_id'] for r in cases} != {f'user_task_{index}' for index in range(2, 22)}:
                parser.error('Task IDs differ from the frozen plan')
            group = {'defense': defense, 'attack': attack, 'cases': len(cases),
                'utility_passes': sum(r['utility'] for r in cases),
                'attack_successes': sum(bool(r['attack_success']) for r in cases) if attack != 'none' else None,
                'attack_exposed': sum(r.get('attack_exposed', False) for r in cases),
                'blocked_calls': sum(len(r.get('blocked_calls', [])) for r in cases),
                'budget_exhaustions': sum(r['budget_exhausted'] for r in cases)}
            group['utility_wilson95'] = wilson(group['utility_passes'], 20)
            group['attack_wilson95'] = wilson(group['attack_successes'], 20) if attack != 'none' else None
            groups.append(group)
            rows.extend({'defense': defense, 'condition': attack, **r} for r in cases)
    metadata = [m for row in rows for m in row['metadata']]
    failures = [{'task': r['task_id'], 'defense': r['defense'], 'condition': r['condition'],
                 'budget_exhausted': r['budget_exhausted']} for r in rows if not r['utility']]
    summary = {'groups': groups, 'distinct_tasks': 20, 'cases': 120,
        'requests': len(metadata), 'prompt_tokens': sum(m['usage'].get('prompt_tokens', 0) for m in metadata),
        'completion_tokens': sum(m['usage'].get('completion_tokens', 0) for m in metadata),
        'response_models': sorted({str(m['model_returned']) for m in metadata}), 'utility_failures': failures,
        'original_error_cases': manifest.get('original_error_cases', 0),
        'failed_attempt_usage_incomplete': manifest.get('failed_attempt_usage_incomplete', False),
        'confidence_interval_note': 'Exploratory per-group Wilson intervals; fixed nonrandom task selection, related tasks, single suite/target/run limit inference.'}
    lines = ['# AgentDojo 冻结子集结果', '',
        '20 个预先固定用户任务，三组设置、正常/固定攻击两条件，共 120 cases。环境与评分器为 AgentDojo 0.1.35 workspace v1.2.2；不是全量 benchmark。', '',
        '| 设置 | 条件 | 官方任务成功 | 官方攻击目标达成 | 实际攻击暴露 | 拦截调用 | 轮数耗尽 |',
        '|---|---|---:|---:|---:|---:|---:|']
    for g in groups:
        count = f'{g["attack_successes"]}/20' if g['attack_successes'] is not None else '不适用'
        lines.append(f'| {g["defense"]} | {g["attack"]} | {g["utility_passes"]}/20 | {count} | {g["attack_exposed"]} | {g["blocked_calls"]} | {g["budget_exhaustions"]} |')
    lines += ['', '## 解释边界', '',
        '攻击指标以全部 20 个预定任务为分母，攻击暴露单列。置信区间保存在 summary.json；例如零次成功不能解释为零风险。',
        'scoped 是检索前由 LLM 选择工具名称的范围策略，没有参数级收件人/文件权限保证，也可能误拒正常操作。需同时查看 utility，而不能只看攻击指标。',
        '固定一个官方攻击目标和模板；没有多模型、多次重复或完整全部 suite。所有工具仅执行官方模拟环境操作。',
        '开发集 task_0/1 不包含在本表；正常任务失败和预算耗尽保留在结果中，不事后删除或替换。', '',
        '## 用量', '', f'有效案例已记录 {summary["requests"]} 个 API 请求，输入 {summary["prompt_tokens"]:,} token，输出 {summary["completion_tokens"]:,} token。响应模型名称：{", ".join(summary["response_models"])}。费用未推算。', '',
        '## 失败案例索引', '']
    lines += [f'- {f["task"]} / {f["defense"]} / {f["condition"]}; budget_exhausted={f["budget_exhausted"]}' for f in failures] or ['本轮未记录 utility 失败。']
    if summary['failed_attempt_usage_incomplete']:
        lines += ['', '## 技术恢复记录', '',
            '首次运行遇到一个 ProviderError 后停止；只重试该案例，并补完未运行的 13 个案例。原错误和原始文件保留，未依据效用结果删题或选择重跑。',
            '上面的请求/token 合计仅来自 120 个有效案例的 metadata。首次失败过程用量未完整记录，因此它是已记录用量，不是完整账单；实际使用以平台账单为准。']
    output.mkdir(parents=True)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
