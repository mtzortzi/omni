"""Rename implementation Gate tags to Wave tags across the engagement."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients
from engagement_tree import fetch_tree


def main() -> None:
    wit, _ = get_clients()
    nodes, _ = fetch_tree(wit, 537616)
    item_ids = sorted(nodes)
    items = []
    for start in range(0, len(item_ids), 200):
        items.extend(wit.get_work_items(ids=item_ids[start : start + 200]))

    updated = 0
    for item in items:
        existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        renamed = [
            tag.replace("Implementation Gate ", "Implementation Wave ", 1)
            if tag.startswith("Implementation Gate ")
            else tag
            for tag in existing
        ]
        deduplicated = list(dict.fromkeys(renamed))
        if deduplicated == existing:
            continue
        wit.update_work_item(
            document=[JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(deduplicated))],
            id=item.id,
        )
        updated += 1

    print(f"Renamed implementation tags on {updated} work items.")


if __name__ == "__main__":
    main()
