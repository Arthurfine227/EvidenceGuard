import json
import unittest

from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
from agentdojo.task_suite import get_suite
from evidencepilot.dojo_bridge import attack_is_exposed, build_pipeline


class OfficialEnvironmentTests(unittest.TestCase):
    def test_saved_runtime_state_restores_new_events_and_emails(self):
        from agentdojo.functions_runtime import FunctionsRuntime
        from evidencepilot.dojo_validate import restore_environment
        suite = get_suite('v1.2.2', 'workspace')
        task = suite.get_user_task_by_id('user_task_6')
        env = task.init_environment(suite.load_and_inject_default_environment({}))
        previous_count = len(env.calendar.events)
        runtime = FunctionsRuntime(suite.tools)
        for call in task.ground_truth(env):
            _, error = runtime.run_function(env, call.function, call.args)
            self.assertIsNone(error)
        raw = env.model_dump(mode='json')
        restored = restore_environment(suite, raw)
        self.assertEqual(len(restored.calendar.events), previous_count + 1)
        self.assertEqual(restored.model_dump(mode='json'), raw)

    def test_exposure_survives_yaml_quoting_and_wrapping(self):
        import yaml
        text = 'A long injected instruction with single quotes: \'test\'.\nSecond line.'
        trace = [{'role': 'tool', 'content': yaml.safe_dump({'description': text}, width=20)}]
        self.assertTrue(attack_is_exposed(trace, {'vector': text}))
        self.assertTrue(attack_is_exposed(trace, {'vector': '\n\n' + text + '\n'}))
        self.assertFalse(attack_is_exposed(trace, {'vector': 'a different payload'}))
    def test_official_attack_scorer_detects_real_simulated_email_effect(self):
        suite = get_suite('v1.2.2', 'workspace')
        task = suite.get_user_task_by_id('user_task_0')
        injection = suite.get_injection_task_by_id('injection_task_0')
        _, success = suite.run_task_with_pipeline(GroundTruthPipeline(injection), task, injection, {})
        self.assertTrue(success)

    def test_scoped_guard_prevents_the_official_email_attack_effect(self):
        suite = get_suite('v1.2.2', 'workspace')
        task = suite.get_user_task_by_id('user_task_0')
        injection = suite.get_injection_task_by_id('injection_task_0')
        attack_call = injection.ground_truth(suite.load_and_inject_default_environment({}))[0]
        class StubProvider:
            turn = 0

            def complete_json(self, system, user, max_tokens):
                return {'allowed_tools': ['search_calendar_events']}

            def complete_tools(self, messages, tools, max_tokens):
                self.turn += 1
                if self.turn == 1:
                    return {'role': 'assistant', 'content': None, 'tool_calls': [
                        {'id': 'attack_1', 'type': 'function', 'function': {
                            'name': attack_call.function, 'arguments': json.dumps(attack_call.args)}}]}
                return {'role': 'assistant', 'content': 'Stopped.'}
        pipeline = build_pipeline(StubProvider(), 'scoped')
        _, success = suite.run_task_with_pipeline(pipeline, task, injection, {})
        self.assertFalse(success)
        self.assertEqual(len(pipeline.blocked_calls), 1)

    def test_official_ground_truth_scores_as_success(self):
        suite = get_suite('v1.2.2', 'workspace')
        for task_id in ('user_task_0', 'user_task_1'):
            task = suite.get_user_task_by_id(task_id)
            utility, _ = suite.run_task_with_pipeline(GroundTruthPipeline(task), task, None, {})
            self.assertTrue(utility)

    def test_native_bridge_matches_ground_truth_tool_sequence(self):
        suite = get_suite('v1.2.2', 'workspace')
        task = suite.get_user_task_by_id('user_task_0')
        env = task.init_environment(suite.load_and_inject_default_environment({}))
        expected_calls = iter(task.ground_truth(env))
        class StubProvider:
            def complete_tools(self, messages, tools, max_tokens):
                try:
                    call = next(expected_calls)
                    return {'role': 'assistant', 'content': None, 'tool_calls': [
                        {'id': str(len(messages)), 'type': 'function', 'function': {
                            'name': call.function, 'arguments': json.dumps(call.args)}}]}
                except StopIteration:
                    return {'role': 'assistant', 'content': task.GROUND_TRUTH_OUTPUT}
        pipeline = build_pipeline(StubProvider())
        utility, _ = suite.run_task_with_pipeline(pipeline, task, None, {})
        self.assertTrue(utility)
        self.assertFalse(pipeline.budget_exhausted)

