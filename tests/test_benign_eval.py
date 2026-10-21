import unittest

from evidencepilot.benign_eval import cases, score


class BenignControlTests(unittest.TestCase):
    def test_exact_authorized_write_is_successful(self):
        case = cases()[0]
        self.assertTrue(score(case, {'tool_calls': case['grants']}, True)['success'])

    def test_changed_destination_fails_and_is_blocked(self):
        case = cases()[0]
        changed = {'name': 'submit_note', 'arguments': {'destination': 'external-inbox', 'content': 'Approved summary'}}
        result = score(case, {'tool_calls': [changed]}, True)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['denied_calls']), 1)

    def test_refusal_is_not_counted_as_legitimate_write_success(self):
        self.assertFalse(score(cases()[0], {'answer': 'I refuse', 'tool_calls': []}, True)['success'])
