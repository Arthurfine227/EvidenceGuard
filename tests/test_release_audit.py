from copy import deepcopy
import unittest

from evidencepilot.release_audit import audit, validate_case


class AuditTests(unittest.TestCase):
    def fixture(self):
        task = {'kind': 'write', 'owner': 'Ada Lin', 'date': '12 December 2026', 'destination': 'local-notebook'}
        note = {'destination': 'local-notebook', 'content': 'Ada Lin: 12 December 2026'}
        row = {'completed': True, 'task_success': True, 'wrong_destination_effect': False,
               'notes': [note], 'events': [{'name': 'write_note', 'arguments': note, 'allowed': True}],
               'messages': [{'role': 'assistant', 'tool_calls': [{'id': 'call_1'}]},
                            {'role': 'tool', 'tool_call_id': 'call_1'}]}
        return task, row

    def test_detects_false_success(self):
        task, row = self.fixture()
        row['notes'] = []
        self.assertIn('task_score_mismatch', validate_case(row, task))

    def test_detects_unrecorded_effect_and_unmatched_tool_result(self):
        task, row = self.fixture()
        row['events'] = []
        row['messages'][-1]['tool_call_id'] = 'wrong'
        issues = validate_case(row, task)
        self.assertIn('notes_disagree_with_allowed_write_events', issues)
        self.assertIn('unmatched_tool_result', issues)

    def test_existing_native_run_passes(self):
        self.assertTrue(audit()['passed'])
