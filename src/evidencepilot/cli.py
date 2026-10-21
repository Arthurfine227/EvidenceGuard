from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import VerificationAgent
from .providers import OpenAICompatibleProvider


def default_corpus() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evidence.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify a claim with an auditable tool-use trace")
    parser.add_argument("claim", help="Claim to verify")
    parser.add_argument("--image", help="Optional image file")
    parser.add_argument("--corpus", default=str(default_corpus()), help="JSON evidence corpus")
    parser.add_argument("--output", help="Write the JSON report to this file")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    provider = OpenAICompatibleProvider.from_environment()
    report = VerificationAgent(args.corpus, provider).verify(args.claim, args.image)
    payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(payload)


if __name__ == "__main__":
    main()

