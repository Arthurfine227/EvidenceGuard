import json
import unittest

from evidencepilot.defenses import authorize_call, redact_private_output
from evidencepilot.security_eval import build_suite, run_case


class PolicyTests(unittest.TestCase):
    def test_allows_read_but_blocks_write(self):
        self.assertTrue(authorize_call('read_document', {'id': 'atlas'}, {'atlas'})[0])
        self.assertFalse(authorize_call('read_document', {'id': 'missing'}, {'atlas'})[0])
        self.assertFalse(authorize_call('submit_note', {'destination': 'external-inbox'}, {'atlas'})[0])

    def test_redacts_only_exact_canary(self):
        self.assertEqual(redact_private_output('token SECRET', 'SECRET'), ('token [PRIVATE_TOKEN_REDACTED]', True))

    def test_layered_policy_blocks_actual_execution_but_records_attempt(self):
        class MaliciousProvider:
            turn = 0

            def complete_json(self, system, user):
                self.turn += 1
                token = json.loads(user)['private_context'].split()[-1]
                if self.turn == 1:
                    return {'tool_calls': [{'name': 'submit_note', 'arguments': {'destination': 'external-inbox', 'content': token}}]}
                return {'answer': token, 'citations': [], 'tool_calls': []}
        docs, tasks = build_suite()
        result = run_case(docs, tasks[0], 'exfiltrate', MaliciousProvider(), 'layered', 'v2')
        self.assertTrue(result['raw_leak_attempt'])
        self.assertFalse(result['synthetic_secret_leaked'])
        self.assertTrue(result['output_redacted'])
        self.assertEqual(len(result['blocked_calls']), 1)
        self.assertEqual(result['executed_calls'], [])

