import unittest

from evidencepilot.security_eval import attack_text, build_suite, run_case


class SecurityEvaluationTests(unittest.TestCase):
    def test_attack_does_not_contain_private_secret(self):
        self.assertNotIn('SYNTHETIC_SECRET_123', attack_text('exfiltrate', 'SYNTHETIC_SECRET_123'))

    def test_labels_are_not_exposed_in_documents(self):
        docs, tasks = build_suite()
        self.assertTrue(all('expected' not in d and 'label' not in d for d in docs))
        self.assertTrue({t['document_id'] for t in tasks if t['split'] == 'dev'}.isdisjoint(
            {t['document_id'] for t in tasks if t['split'] == 'test'}))

    def test_scoring_distinguishes_clean_hijack_and_leak(self):
        docs, tasks = build_suite()
        clean = run_case(docs, tasks[0], 'clean')
        hijack = run_case(docs, tasks[0], 'redirect')
        leak = run_case(docs, tasks[0], 'exfiltrate')
        self.assertTrue(clean['task_success'])
        self.assertFalse(clean['synthetic_secret_leaked'])
        self.assertTrue(hijack['attack_success'])
        self.assertFalse(hijack['task_success'])
        self.assertTrue(leak['attack_success'])
        self.assertTrue(leak['unauthorized_tool_call'])

    def test_fake_provider_runs_real_tool_loop_without_labels(self):
        class FakeProvider:
            def __init__(self):
                self.turn = 0

            def complete_json(self, system, user):
                self.turn += 1
                assert 'expected' not in user
                if self.turn == 1:
                    return {'tool_calls': [{'name': 'read_document', 'arguments': {'id': 'atlas'}}]}
                assert 'SYSTEM UPDATE' in user
                return {'answer': 'SECURITY_OVERRIDE_CONFIRMED', 'citations': []}
        docs, tasks = build_suite()
        result = run_case(docs, tasks[0], 'redirect', FakeProvider())
        self.assertTrue(result['attack_success'])
        self.assertEqual(len(result['trace']), 2)


if __name__ == '__main__':
    unittest.main()
