from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from PIL import ExifTags, Image

from .models import Evidence


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class ImageInspector:
    name = "image_inspector"

    def run(self, image_path: str) -> dict:
        path = Path(image_path)
        if not path.is_file():
            return {"available": False, "error": "image_not_found"}
        with Image.open(path) as image:
            exif = {
                ExifTags.TAGS.get(key, str(key)): str(value)
                for key, value in image.getexif().items()
            }
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            return {
                "available": True,
                "format": image.format,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "sha256": digest,
                "exif": exif,
                "warnings": self._warnings(image.width, image.height, exif),
            }

    @staticmethod
    def _warnings(width: int, height: int, exif: dict) -> list[str]:
        warnings = []
        if min(width, height) < 256:
            warnings.append("low_resolution")
        if not exif:
            warnings.append("missing_exif_not_proof_of_manipulation")
        return warnings


class EvidenceSearch:
    name = "evidence_search"

    def __init__(self, corpus_path: str | Path):
        self.corpus_path = Path(corpus_path)
        self.documents = json.loads(self.corpus_path.read_text(encoding="utf-8"))
        self.doc_tokens = [Counter(tokenize(doc["title"] + " " + doc["text"])) for doc in self.documents]
        self.document_frequency = Counter()
        for tokens in self.doc_tokens:
            self.document_frequency.update(tokens.keys())

    def run(self, query: str, limit: int = 5) -> list[Evidence]:
        query_tokens = Counter(tokenize(query))
        scored: list[tuple[float, dict]] = []
        document_count = max(len(self.documents), 1)
        for doc, tokens in zip(self.documents, self.doc_tokens):
            score = 0.0
            for token, query_count in query_tokens.items():
                if token not in tokens:
                    continue
                inverse_frequency = math.log((document_count + 1) / (self.document_frequency[token] + 1)) + 1
                score += min(query_count, tokens[token]) * inverse_frequency
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            Evidence(
                evidence_id=doc["id"],
                title=doc["title"],
                text=doc["text"],
                source=doc["source"],
                published_at=doc.get("published_at"),
                supports=doc.get("label"),
                score=round(score, 4),
            )
            for score, doc in scored[:limit]
        ]


class SourceRater:
    name = "source_rater"
    HIGH_TRUST_SUFFIXES = (".gov", ".edu", ".ac.uk", ".org")
    HIGH_TRUST_HOSTS = ("hku.hk",)

    def run(self, source: str) -> dict:
        source_lower = source.lower()
        high_trust = source_lower in self.HIGH_TRUST_HOSTS or any(
            suffix in source_lower for suffix in self.HIGH_TRUST_SUFFIXES
        )
        return {
            "source": source,
            "reliability": "high" if high_trust else "unrated",
            "reason": "institutional_domain" if high_trust else "requires_manual_source_review",
        }
