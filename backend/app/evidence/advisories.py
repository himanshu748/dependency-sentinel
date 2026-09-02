from typing import Any

import httpx

from app.domain.models import AdvisoryEvidence, EvidenceSource, utc_now
from app.evidence.common import EvidenceUnavailable

OSV_QUERY_URL = "https://api.osv.dev/v1/query"


class OsvAdvisoryProvider:
    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=10.0)

    def advisories_for(self, package: str, version: str) -> list[AdvisoryEvidence]:
        try:
            response = self.client.post(
                OSV_QUERY_URL,
                json={
                    "package": {"ecosystem": "PyPI", "name": package},
                    "version": version,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise EvidenceUnavailable("OSV advisory lookup failed") from error

        vulnerabilities = payload.get("vulns", [])
        if not isinstance(vulnerabilities, list):
            raise EvidenceUnavailable("OSV advisory lookup returned malformed data")
        return [self._map_vulnerability(item, package, version) for item in vulnerabilities]

    @staticmethod
    def _map_vulnerability(
        vulnerability: dict[str, Any], package: str, version: str
    ) -> AdvisoryEvidence:
        identifier = str(vulnerability.get("id", "unknown"))
        summary = str(vulnerability.get("summary", "No summary supplied by OSV"))
        fixed_versions: set[str] = set()
        for affected in vulnerability.get("affected", []):
            for version_range in affected.get("ranges", []):
                for event in version_range.get("events", []):
                    if event.get("fixed"):
                        fixed_versions.add(str(event["fixed"]))

        source_url = f"https://osv.dev/vulnerability/{identifier}"
        for reference in vulnerability.get("references", []):
            if reference.get("type") == "ADVISORY" and reference.get("url"):
                source_url = str(reference["url"])
                break

        severity = None
        database_specific = vulnerability.get("database_specific")
        if isinstance(database_specific, dict) and database_specific.get("severity"):
            severity = str(database_specific["severity"]).lower()

        return AdvisoryEvidence(
            identifier=identifier,
            package=package.lower(),
            affected_version=version,
            fixed_versions=sorted(fixed_versions),
            summary=summary,
            severity=severity,
            source=EvidenceSource(
                publisher="OSV",
                url=source_url,
                title=identifier,
                excerpt=summary,
                retrieved_at=utc_now(),
            ),
        )

