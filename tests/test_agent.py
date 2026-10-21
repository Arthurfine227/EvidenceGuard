import tempfile
import unittest
from pathlib import Path

from PIL import Image

from evidencepilot.agent import VerificationAgent


ROOT = Path(__file__).resolve().parents[1]


class VerificationAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = VerificationAgent(ROOT / "data" / "evidence.json")

    def test_retrieves_course_evidence(self):
        report = self.agent.verify("COMP7608A is offered in Shanghai Block 4")
        self.assertEqual(report.verdict, "supported")
        self.assertGreaterEqual(len(report.evidence), 1)
        self.assertTrue(any(event.tool == "evidence_search" for event in report.trace))

    def test_abstains_without_evidence(self):
        report = self.agent.verify("A completely unknown claim about object ZXQ-991")
        self.assertEqual(report.verdict, "not_enough_evidence")

    def test_inspects_supplied_image(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.png"
            Image.new("RGB", (320, 240), "white").save(path)
            report = self.agent.verify("An image was supplied", str(path))
        event = next(event for event in report.trace if event.tool == "image_inspector")
        self.assertEqual(event.output["width"], 320)


if __name__ == "__main__":
    unittest.main()

