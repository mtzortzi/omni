"""Normalize framework ADO tags to phases and legacy-triage semantics."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients
from engagement_tree import fetch_tree


FRAMEWORK_EPICS = {463420, 588871, 588939, 588973, 589062, 589173, 589175, 599251, 599252}
LEGACY_FEATURE = 600023
LEGACY_ARCHIVE = 600024
LEGACY_TRIAGE = 600025


def descendants(children: dict[int, list[int]], root: int) -> set[int]:
    result: set[int] = set()
    pending = [root]
    while pending:
        item_id = pending.pop()
        if item_id in result:
            continue
        result.add(item_id)
        pending.extend(children.get(item_id, []))
    return result


def main() -> None:
    wit, _ = get_clients()
    nodes, children = fetch_tree(wit, 537616)
    framework_ids: set[int] = set()
    for epic_id in FRAMEWORK_EPICS:
        framework_ids.update(descendants(children, epic_id))

    archive_ids = descendants(children, LEGACY_ARCHIVE)
    triage_ids = descendants(children, LEGACY_TRIAGE)
    legacy_ids = descendants(children, LEGACY_FEATURE)

    item_ids = sorted(framework_ids)
    items = []
    for start in range(0, len(item_ids), 200):
        items.extend(wit.get_work_items(ids=item_ids[start : start + 200]))

    updated = 0
    skipped_closed = 0
    removed_counts: dict[str, int] = {}
    for item in items:
        existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        if item.fields.get("System.State") == "Closed" and item.fields.get("System.AssignedTo") is None:
            skipped_closed += 1
            continue
        if item.id == LEGACY_FEATURE:
            desired = ["Backlog Migration", "Deferred", "Legacy Backlog"]
        elif item.id in archive_ids:
            desired = ["Historical", "Legacy Backlog"]
        elif item.id in triage_ids:
            desired = ["Deferred", "Legacy Backlog", "Needs Triage"]
        elif item.id in legacy_ids:
            desired = ["Deferred", "Legacy Backlog"]
        else:
            desired = [
                tag
                for tag in existing
                if tag == "Deferred" or tag.startswith("Implementation Wave ") or tag.startswith("Exit Gate ")
            ]
            desired = list(dict.fromkeys(desired))

        for tag in set(existing) - set(desired):
            removed_counts[tag] = removed_counts.get(tag, 0) + 1
        if desired == existing:
            continue
        operation = "replace" if existing else "add"
        wit.update_work_item(
            document=[JsonPatchOperation(op=operation, path="/fields/System.Tags", value="; ".join(desired))],
            id=item.id,
        )
        updated += 1

    print(f"Normalized {updated} framework work items.")
    print(f"Skipped {skipped_closed} unassigned historical Closed items to preserve ownership history.")
    print("Removed irrelevant tags:")
    for tag, count in sorted(removed_counts.items()):
        print(f"- {tag}: {count}")


if __name__ == "__main__":
    main()
