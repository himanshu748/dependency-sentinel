from urllib.parse import quote

import httpx

from app.domain.models import EvidenceSource, ReleaseEvidence, utc_now
from app.evidence.common import EvidenceUnavailable


class PypiReleaseProvider:
    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=10.0)

    def release_for(self, package: str, version: str) -> ReleaseEvidence:
        normalized_package = package.lower()
        api_url = (
            f"https://pypi.org/pypi/{quote(normalized_package)}/{quote(version)}/json"
        )
        try:
            response = self.client.get(api_url)
            response.raise_for_status()
            info = response.json()["info"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise EvidenceUnavailable("PyPI release lookup failed") from error

        summary = str(info.get("summary") or "No release summary supplied by PyPI")
        canonical_url = f"https://pypi.org/project/{normalized_package}/{version}/"
        return ReleaseEvidence(
            package=normalized_package,
            version=str(info.get("version") or version),
            summary=summary,
            source=EvidenceSource(
                publisher="PyPI",
                url=canonical_url,
                title=f"{package} {version}",
                excerpt=summary,
                retrieved_at=utc_now(),
            ),
        )
