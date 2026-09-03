import json
from pathlib import Path

from app.domain.models import AdvisoryEvidence, ReleaseEvidence
from app.evidence.common import EvidenceUnavailable


class FixtureEvidenceStore:
    def __init__(self, fixture_directory: Path) -> None:
        self.fixture_directory = Path(fixture_directory)

    def advisories_for(self, package: str, version: str) -> list[AdvisoryEvidence]:
        raw_records = self._load_json("advisories.json")
        return [
            AdvisoryEvidence.model_validate(record)
            for record in raw_records
            if str(record.get("package", "")).lower() == package.lower()
            and str(record.get("affected_version", "")) == version
        ]

    def release_for(self, package: str, version: str) -> ReleaseEvidence:
        raw_records = self._load_json("releases.json")
        for record in raw_records:
            if (
                str(record.get("package", "")).lower() == package.lower()
                and str(record.get("version", "")) == version
            ):
                return ReleaseEvidence.model_validate(record)
        raise EvidenceUnavailable(f"no fixture release evidence for {package} {version}")

    def _load_json(self, filename: str) -> list[dict]:
        path = self.fixture_directory / filename
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise EvidenceUnavailable(f"cannot load evidence fixture {filename}") from error
        if not isinstance(loaded, list):
            raise EvidenceUnavailable(f"evidence fixture {filename} must contain a list")
        return loaded
