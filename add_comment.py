"""Add a comment (discussion note) to an ADO work item.

Usage:
    uv run python add_comment.py <work_item_id> "comment text (HTML allowed)"
"""

from __future__ import annotations

import sys

import requests
from requests.auth import HTTPBasicAuth

from ado_client import AdoConfig


def add_comment(cfg: AdoConfig, work_item_id: int, html_text: str) -> None:
    url = (
        f"{cfg.org_url}/{cfg.project}/_apis/wit/workItems/{work_item_id}"
        f"/comments?api-version=7.1-preview.3"
    )
    resp = requests.post(
        url,
        auth=HTTPBasicAuth("", cfg.pat),
        json={"text": html_text},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    print(f"  [OK] comment added to #{work_item_id}")


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: add_comment.py <id> <text>")
    work_item_id = int(sys.argv[1])
    text = sys.argv[2]
    cfg = AdoConfig.from_env()
    add_comment(cfg, work_item_id, text)


if __name__ == "__main__":
    main()
