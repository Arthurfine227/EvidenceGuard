import tempfile
import unittest
from pathlib import Path

from evidencepilot.model_comparison import SpendingGuard
from evidencepilot.providers import ProviderError


class ComparisonBudgetTests(unittest.TestCase):
    def test_reserve_persist_and_settle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ledger.json'
            guard = SpendingGuard(path)
            item = guard.reserve({'messages': ['hello']}, 1024)
            reserved = guard.data['reserved_or_accounted_rmb']
            self.assertGreater(reserved, 0)
            guard.finish(item, {'usage': {'prompt_tokens': 100, 'completion_tokens': 20}, 'model_returned': 'test'})
            self.assertAlmostEqual(guard.data['reserved_or_accounted_rmb'], .00144)
            self.assertEqual(SpendingGuard(path).data, guard.data)

    def test_unknown_usage_keeps_reservation_and_limit_prevents_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            guard = SpendingGuard(Path(tmp) / 'ledger.json', 6)
            item = guard.reserve({'x': 'hello'}, 1024)
            amount = guard.data['reserved_or_accounted_rmb']
            guard.finish(item, None, TimeoutError())
            self.assertEqual(guard.data['reserved_or_accounted_rmb'], amount)
            with self.assertRaises(ProviderError):
                guard.reserve({'x': 'x' * 1000000}, 1024)
            self.assertEqual(len(guard.data['requests']), 1)
