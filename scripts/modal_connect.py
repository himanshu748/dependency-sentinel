"""Connect an existing private Modal endpoint; never print inference credentials."""

import argparse
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--reuse-env", type=Path)
    parser.add_argument(
        "--configure",
        action="store_true",
        help="Write server configuration and create a proxy token if needed",
    )
    args = parser.parse_args()
    url = urlsplit(args.base_url)
    if (
        url.scheme != "https"
        or not url.hostname
        or not url.hostname.endswith((".modal.direct", ".modal.run"))
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        parser.error("Use the HTTPS URL returned for your private Modal server")
    if not args.configure:
        parser.error("--configure is required; this writes backend/.env")
    prefix = {
        "studypilot": "STUDYPILOT",
        "dependency-sentinel": "DEPENDENCY_SENTINEL",
        "scamshield": "SCAMSHIELD",
    }.get(ROOT.name)
    if not prefix:
        parser.error("Unrecognized product directory")
    target = ROOT / "backend/.env"
    ignored = subprocess.run(["git", "check-ignore", "-q", str(target)], cwd=ROOT, check=False)
    if ignored.returncode:
        parser.error("backend/.env must be ignored by Git before storing a credential")
    target_values = dotenv_values(target)
    if target_values.get("LLM_API_KEY") and target_values.get("LLM_BASE_URL") != args.base_url:
        parser.error("Target has another external provider; not overwriting")
    existing = dotenv_values(args.reuse_env or target)
    key = existing.get("LLM_API_KEY")
    if key and existing.get("LLM_BASE_URL") != args.base_url:
        parser.error("Existing external credential belongs to another endpoint; not overwriting")
    if args.reuse_env and not key:
        parser.error("The selected existing environment has no inference credential")
    if not key:
        result = subprocess.run(
            [
                "modal",
                "workspace",
                "proxy-tokens",
                "create",
                "--profile",
                args.profile,
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            parser.error("Modal proxy token creation failed; no credential output shown")
        token = json.loads(result.stdout)
        key = token["Modal-Key"] + "." + token["Modal-Secret"]
    # python-dotenv performs a mechanical configuration update, preserving other settings.
    # Restrict permissions before the update so the generated credential is never world-readable.
    target.touch(mode=0o600, exist_ok=True)
    os.chmod(target, 0o600)
    values = {
        "LLM_PROVIDER": "openai-compatible",
        "LLM_MODEL_ID": "Qwen/Qwen3-8B",
        "LLM_BASE_URL": args.base_url,
        "LLM_API_KEY": key,
        prefix + "_FIXTURE_MODE": "false",
        prefix + "_AGENTCORE_RUNTIME_ARN": "",
    }
    for name, value in values.items():
        set_key(target, name, value)
    os.chmod(target, 0o600)
    print(
        json.dumps(
            {
                "project": ROOT.name,
                "configured": True,
                "provider": "openai-compatible",
                "model": "Qwen/Qwen3-8B",
                "inference_verified": False,
                "credential": "saved privately",
            }
        )
    )


if __name__ == "__main__":
    main()
