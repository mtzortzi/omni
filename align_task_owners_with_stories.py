"""Assign open Tasks to their canonical parent Story owner."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients
from apply_story_thread_model import EPICS, descendants
from engagement_tree import fetch_tree


def main() -> None:
    wit, _ = get_clients()
    nodes, children = fetch_tree(wit, 537616)
    framework_ids = descendants(children, EPICS)

    changed = 0
    skipped_closed = 0
    skipped_unowned = 0

    for story_id in sorted(framework_ids):
        story = nodes.get(story_id)
        if story is None or story.fields.get("System.WorkItemType") != "User Story":
            continue
        owner = story.fields.get("System.AssignedTo")
        if owner is None:
            skipped_unowned += len(children.get(story_id, []))
            continue
        owner_name = owner.get("displayName") if isinstance(owner, dict) else owner

        task_ids = [
            task_id
            for task_id in children.get(story_id, [])
            if nodes.get(task_id) is not None and nodes[task_id].fields.get("System.WorkItemType") == "Task"
        ]
        if not task_ids:
            continue
        tasks = wit.get_work_items(ids=task_ids)
        for task in tasks:
            if task.fields.get("System.State") in {"Closed", "Removed"}:
                skipped_closed += 1
                continue
            current = task.fields.get("System.AssignedTo")
            current_name = current.get("displayName") if isinstance(current, dict) else current
            if current_name == owner_name:
                continue
            wit.update_work_item(
                document=[JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value=owner_name)],
                id=task.id,
            )
            changed += 1
            print(f"#{task.id} -> {owner_name} (Story #{story_id})")

    print(
        f"Aligned {changed} open Tasks; preserved {skipped_closed} Closed/Removed Tasks; "
        f"left {skipped_unowned} Tasks under unowned Stories unchanged."
    )


if __name__ == "__main__":
    main()
