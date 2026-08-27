"""Trigger a Cloudflare Pages production deployment of this repo.

    python tools/deploy.py

WHY THIS EXISTS. The Pages project is Git-connected and builds from GitHub, but a push to main does
NOT currently trigger a build. The project was created through the Cloudflare API rather than the
dashboard's Connect-to-Git flow, and while Cloudflare can clone the repo (the project's source config
carries the credentials), the GitHub App's push events do not reach it. Measured 2026-08-27: a push
produced no deployment, and an API-triggered build of the same commit succeeded.

The real fix is one click on GitHub: Settings > Applications > Cloudflare Pages > Repository access,
add VTAtlas-Docs. Once that is done, pushes deploy on their own and this script is redundant rather
than wrong.

No secret to manage: it reuses the OAuth token wrangler already stores, so it works on the machine
that is already logged in and nowhere else, which is the right blast radius for a deploy button.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ACCOUNT = "418f8af4bf80b3186465e9ebcee68a5d"
PROJECT = "vtatlas-docs"
API = "https://api.cloudflare.com/client/v4"


def token() -> str:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise SystemExit("deploy: APPDATA is unset; cannot find the wrangler config.")
    config = pathlib.Path(appdata) / "xdg.config" / ".wrangler" / "config" / "default.toml"
    if not config.is_file():
        raise SystemExit(f"deploy: {config} not found. Run `npx wrangler login` first.")
    found = re.search(r'(?m)^oauth_token\s*=\s*"([^"]+)"', config.read_text(encoding="utf-8"))
    if not found:
        raise SystemExit("deploy: no oauth_token in the wrangler config. Run `npx wrangler login`.")
    return found.group(1)


def api(method: str, path: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        return json.loads(error.read())


def main() -> int:
    started = api("POST", f"/accounts/{ACCOUNT}/pages/projects/{PROJECT}/deployments", {})
    if not started.get("success"):
        print("deploy: could not start:", started.get("errors"))
        return 1

    deployment = started["result"]
    short = deployment.get("short_id")
    commit = ((deployment.get("deployment_trigger") or {}).get("metadata") or {}).get("commit_hash", "")
    print(f"deploy: started {short} from {commit[:8]}")

    # Poll rather than fire and forget. A deploy that fails silently is the same failure this whole
    # repo keeps guarding against: green-looking output that means nothing was checked.
    seen = None
    for _ in range(90):
        time.sleep(10)
        listing = api("GET", f"/accounts/{ACCOUNT}/pages/projects/{PROJECT}/deployments")
        current = next((d for d in (listing.get("result") or []) if d.get("short_id") == short), None)
        if current is None:
            continue
        stage = current.get("latest_stage") or {}
        key = (stage.get("name"), stage.get("status"))
        if key != seen:
            seen = key
            print(f"  {stage.get('name')}: {stage.get('status')}")
        if stage.get("status") in {"failure", "canceled"}:
            print(f"deploy: FAILED at stage {stage.get('name')}")
            return 1
        if stage.get("name") == "deploy" and stage.get("status") == "success":
            print(f"deploy: live at {current.get('url')}")
            return 0

    print("deploy: timed out waiting for the build")
    return 1


if __name__ == "__main__":
    sys.exit(main())
