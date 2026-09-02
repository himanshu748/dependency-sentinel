import json
from pathlib import Path

import httpx
import pytest


def _advisory_api():
    try:
        from app.evidence.advisories import EvidenceUnavailable, OsvAdvisoryProvider
        from app.evidence.fixtures import FixtureEvidenceStore
    except ImportError:
        pytest.fail("advisory evidence providers are not implemented")
    return EvidenceUnavailable, OsvAdvisoryProvider, FixtureEvidenceStore


def test_fixture_store_returns_timestamped_advisory_evidence() -> None:
    """Catch demo evidence that omits its source or retrieval time."""
    _, _, FixtureEvidenceStore = _advisory_api()
    fixtures = Path(__file__).parents[3] / "fixtures" / "evidence"

    records = FixtureEvidenceStore(fixtures).advisories_for("jinja2", "3.1.4")

    assert len(records) == 1
    assert records[0].identifier == "CVE-2024-56326"
    assert records[0].fixed_versions == ["3.1.5"]
    assert records[0].source.publisher == "NVD"
    assert records[0].source.url == "https://nvd.nist.gov/vuln/detail/CVE-2024-56326"
    assert records[0].source.retrieved_at.tzinfo is not None


def test_osv_provider_maps_query_response_to_domain_evidence() -> None:
    """Catch a live advisory response that loses fixed-version or source evidence."""
    _, OsvAdvisoryProvider, _ = _advisory_api()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.osv.dev/v1/query"
        assert json.loads(request.content) == {
            "package": {"ecosystem": "PyPI", "name": "jinja2"},
            "version": "3.1.4",
        }
        return httpx.Response(
            200,
            json={
                "vulns": [
                    {
                        "id": "CVE-2024-56326",
                        "summary": "Sandbox breakout through indirect calls",
                        "affected": [
                            {
                                "package": {"ecosystem": "PyPI", "name": "Jinja2"},
                                "ranges": [
                                    {
                                        "type": "ECOSYSTEM",
                                        "events": [
                                            {"introduced": "0"},
                                            {"fixed": "3.1.5"},
                                        ],
                                    }
                                ],
                            }
                        ],
                        "references": [
                            {
                                "type": "ADVISORY",
                                "url": "https://osv.dev/vulnerability/CVE-2024-56326",
                            }
                        ],
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    records = OsvAdvisoryProvider(client=client).advisories_for("jinja2", "3.1.4")

    assert len(records) == 1
    assert records[0].fixed_versions == ["3.1.5"]
    assert records[0].source.publisher == "OSV"
    assert records[0].source.url == "https://osv.dev/vulnerability/CVE-2024-56326"


def test_osv_provider_exposes_unavailable_evidence(tmp_path: Path) -> None:
    """Catch network failure being misrepresented as no known vulnerabilities."""
    EvidenceUnavailable, OsvAdvisoryProvider, _ = _advisory_api()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="temporarily unavailable")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(EvidenceUnavailable, match="OSV advisory lookup failed"):
        OsvAdvisoryProvider(client=client).advisories_for("jinja2", "3.1.4")

