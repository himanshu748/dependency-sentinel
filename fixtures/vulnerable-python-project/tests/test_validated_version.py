from pathlib import Path


def test_jinja2_security_fix_is_declared() -> None:
    manifest = (Path(__file__).parents[1] / "pyproject.toml").read_text()

    assert '"jinja2==3.1.5"' in manifest


def test_jinja2_security_fix_is_locked() -> None:
    lockfile = (Path(__file__).parents[1] / "uv.lock").read_text()

    assert 'name = "jinja2"\nversion = "3.1.5"' in lockfile
