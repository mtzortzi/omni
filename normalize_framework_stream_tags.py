"""Normalize Central Framework and standalone capability tags.

Planner work is deliberately outside this script's scope.

Usage:
    uv run python normalize_framework_stream_tags.py --dry-run
    uv run python normalize_framework_stream_tags.py
"""

from __future__ import annotations

import argparse

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients
from engagement_tree import fetch_tree


ENGAGEMENT_ID = 537616
FRAMEWORK_EPICS = {463420, 588871, 588939, 588973, 589062, 589173, 589175, 599251, 599252}
STANDALONE_MISSION_EXECUTION_FEATURE = 658774
TARGET_TYPES = {"User Story", "Task"}
STREAM_TAGS = {"Central Framework", "Standalone Capability", "Mission Execution"}


def descendants(children: dict[int, list[int]], root_id: int) -> set[int]:
    result: set[int] = set()
    stack = [root_id]
    while stack:
        item_id = stack.pop()
        if item_id in result:
            continue
        result.add(item_id)
        stack.extend(children.get(item_id, []))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    wit, _ = get_clients()
    nodes, children = fetch_tree(wit, ENGAGEMENT_ID)
    framework_ids = set().union(*(descendants(children, epic_id) for epic_id in FRAMEWORK_EPICS))
    standalone_ids = descendants(children, STANDALONE_MISSION_EXECUTION_FEATURE)

    changed = 0
    unchanged = 0
    for item_id in sorted(framework_ids):
        item = nodes.get(item_id)
        if item is None or item.fields.get("System.WorkItemType") not in TARGET_TYPES:
            continue

        current_tags = {
            tag.strip()
            for tag in (item.fields.get("System.Tags") or "").split(";")
            if tag.strip()
        }
        tags = current_tags - STREAM_TAGS
        if item_id in standalone_ids:
            tags.update({"Standalone Capability", "Mission Execution"})
        else:
            tags.add("Central Framework")

        if tags == current_tags:
            unchanged += 1
            continue

        tag_value = "; ".join(sorted(tags))
        if args.dry_run:
            print(f"[DRY] #{item_id}: {tag_value}")
        else:
            operation = "replace" if current_tags else "add"
            wit.update_work_item(
                document=[
                    JsonPatchOperation(
                        op=operation,
                        path="/fields/System.Tags",
                        value=tag_value,
                    )
                ],
                id=item_id,
            )
            print(f"[OK] #{item_id}: {tag_value}")
        changed += 1

    mode = "would update" if args.dry_run else "updated"
    print(f"{mode.capitalize()} {changed} items; {unchanged} already correct.")


if __name__ == "__main__":
    main()
