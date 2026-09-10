"""Functional checks for an owned fixture; not an exploit or a complete security audit."""

from importlib.metadata import version
from pathlib import Path

from jinja2 import Environment


def test_installed_upgrade_matches_declaration_and_lock():
    root = Path(__file__).parents[1]
    installed = version("jinja2")
    assert installed != "3.1.4"
    assert f'"jinja2=={installed}"' in (root / "pyproject.toml").read_text()
    assert f'name = "jinja2"\nversion = "{installed}"' in (root / "uv.lock").read_text()


def test_html_rendering_preserves_escaping():
    template = Environment(autoescape=True).from_string("Hello {{ name }}")
    assert template.render(name="<Ada>") == "Hello &lt;Ada&gt;"
