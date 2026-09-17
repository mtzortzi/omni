"""Delete a list of ADO work items (destructive; sends to recycle bin).

Usage:
    uv run python delete_items.py 578544 578545 578546 ...
"""

from __future__ import annotations

import sys

from ado_client import AdoConfig, get_clients


def main() -> None:
    ids = [int(x) for x in sys.argv[1:]]
    if not ids:
        sys.exit("usage: delete_items.py <id> [<id> ...]")
    cfg = AdoConfig.from_env()
    wit_client, _ = get_clients(cfg)
    for wid in ids:
        try:
            wit_client.delete_work_item(id=wid, destroy=False)
            print(f"  [OK]   deleted #{wid}")
        except Exception as e:  # noqa: BLE001
            print(f"  [ERROR] #{wid}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
