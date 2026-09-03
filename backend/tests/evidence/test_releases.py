from pathlib import Path

import httpx
import pytest


def _release_api():
    try:
        from app.evidence.fixtures import FixtureEvidenceStore
        from app.evidence.releases import PypiReleaseProvider
    except ImportError:
        pytest.fail("release evidence providers are not implemented")
    return FixtureEvidenceStore, PypiReleaseProvider


def test_fixture_store_returns_release_summary_for_target_version() -> None:
    """Catch an upgrade report that names a version without release evidence."""
    FixtureEvidenceStore, _ = _release_api()
    fixtures = Path(__file__).parents[3] / "fixtures" / "evidence"

    release = FixtureEvidenceStore(fixtures).release_for("jinja2", "3.1.5")

    assert release.package == "jinja2"
    assert release.version == "3.1.5"
    assert "security" in release.summary.lower()
    assert release.source.publisher == "PyPI"
    assert release.source.retrieved_at.tzinfo is not None


def test_pypi_provider_maps_package_metadata_to_release_evidence() -> None:
    """Catch a PyPI adapter that drops the requested version or canonical URL."""
    _, PypiReleaseProvider = _release_api()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://pypi.org/pypi/jinja2/3.1.5/json"
        return httpx.Response(
            200,
            json={
                "info": {
                    "name": "Jinja2",
                    "version": "3.1.5",
                    "summary": "A very fast and expressive template engine.",
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    release = PypiReleaseProvider(client=client).release_for("jinja2", "3.1.5")

    assert release.package == "jinja2"
    assert release.version == "3.1.5"
    assert release.source.url == "https://pypi.org/project/jinja2/3.1.5/"
