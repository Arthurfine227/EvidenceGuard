import unittest

from evidencepilot.phase3 import authorization_controls, load_public_cases, prepare_input, run_public_case, tool_definitions


class PublicAdapterTests(unittest.TestCase):
    def test_pinned_subset_and_no_labels_in_model_input(self):
        cases, definitions = load_public_cases(8), tool_definitions()
        self.assertEqual(len(cases), 8)
        self.assertEqual(sum(c['category'] == 'dh' for c in cases), 4)
        self.assertEqual(sum(c['category'] == 'ds' for c in cases), 4)
        for category in ('dh', 'ds'):
            group = [c for c in cases if c['category'] == category]
            self.assertEqual(len({c['row']['Attacker Instruction'] for c in group}), 4)
            self.assertEqual(len({c['row']['User Tool'] for c in group}), 4)
        for case in cases:
            prompt = prepare_input(case, False, definitions)
            self.assertNotIn('Expected Achievements', prompt)
            self.assertNotIn('Attacker Tools', prompt)
            self.assertNotIn('<Attacker Instruction>', prompt['tool_result'])

    def test_legitimate_write_and_mutations(self):
        results = authorization_controls()
        self.assertEqual(len(results), 5)
        self.assertTrue(all(r['allowed'] == r['expected'] for r in results))
        self.assertTrue(results[0]['allowed'])

    def test_attempt_and_enforcement_are_distinct(self):
        cases, definitions = load_public_cases(2), tool_definitions()
        case = cases[0]
        class Stub:
            request_metadata = []

            def complete_json(self, system, user, max_tokens):
                return {'answer': '', 'tool_calls': [{'name': case['row']['Attacker Tools'][0], 'arguments': {}}]}
        baseline = run_public_case(case, True, 'none', Stub(), definitions)
        defended = run_public_case(case, True, 'layered', Stub(), definitions)
        self.assertTrue(baseline['proposed_attacker_tool'])
        self.assertTrue(baseline['permitted_attacker_tool'])
        self.assertTrue(defended['proposed_attacker_tool'])
        self.assertFalse(defended['permitted_attacker_tool'])
        self.assertEqual(len(defended['blocked_calls']), 1)
