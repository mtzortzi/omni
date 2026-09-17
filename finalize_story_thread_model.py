"""Finalize tags, iterations, and duplicate cleanup after Story migration."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients
from apply_story_thread_model import (
    CURRENT_SPRINT,
    CURRENT_STORIES,
    EPICS,
    NEXT_SPRINT,
    NEXT_STORIES,
    QUARTER,
    STORY_WAVES,
    descendants,
)
from engagement_tree import fetch_tree


STORY_WAVES.update({600319: 4, 600320: 7})
EMPTY_DUPLICATES = {600314, 600315}


def update_with_required_assignee(wit: object, item_id: int, patch: list[JsonPatchOperation]) -> None:
    try:
        wit.update_work_item(document=patch, id=item_id)
    except Exception as exc:
        if "Assigned To" not in str(exc):
            raise
        wit.update_work_item(
            document=[
                JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value="Marianna Tzortzi"),
                *patch,
            ],
            id=item_id,
        )


def main() -> None:
    wit, _ = get_clients()

    for item_id in sorted(EMPTY_DUPLICATES):
        try:
            item = wit.get_work_item(id=item_id, expand="Relations")
        except Exception:
            continue
        children = [
            relation for relation in item.relations or [] if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        ]
        if children:
            raise RuntimeError(f"Duplicate Story #{item_id} unexpectedly has children")
        wit.delete_work_item(id=item_id, destroy=False)
        print(f"[DELETE EMPTY DUPLICATE] #{item_id}")

    nodes, children = fetch_tree(wit, 537616)
    framework_ids = descendants(children, EPICS)
    legacy_roots = {
        item_id for item_id in framework_ids if "Legacy Backlog" in (nodes[item_id].fields.get("System.Tags") or "")
    }
    legacy_ids = descendants(children, legacy_roots)
    framework_ids -= legacy_ids

    deferred_roots = {
        item_id
        for item_id in framework_ids
        if "Deferred"
        in {tag.strip() for tag in (nodes[item_id].fields.get("System.Tags") or "").split(";") if tag.strip()}
    }
    deferred_ids = descendants(children, deferred_roots)

    item_ids = sorted(framework_ids)
    fetched = []
    for start in range(0, len(item_ids), 200):
        fetched.extend(wit.get_work_items(ids=item_ids[start : start + 200]))
    items = {item.id: item for item in fetched}

    parent_by_child = {
        child_id: parent_id for parent_id, child_ids in children.items() for child_id in child_ids if parent_id in items
    }

    updated = 0
    for item_id, item in sorted(items.items()):
        item_type = item.fields.get("System.WorkItemType")
        existing_tags = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        is_deferred = item_id in deferred_ids

        if is_deferred:
            desired_tags = ["Deferred"]
        elif item_type == "User Story" and item_id in STORY_WAVES:
            desired_tags = [f"Implementation Wave {STORY_WAVES[item_id]}"]
        else:
            desired_tags = []

        patch: list[JsonPatchOperation] = []
        if existing_tags != desired_tags:
            operation = "replace" if existing_tags else "add"
            patch.append(JsonPatchOperation(op=operation, path="/fields/System.Tags", value="; ".join(desired_tags)))

        if is_deferred:
            desired_iteration = "graiteam"
        elif item_type == "User Story":
            desired_iteration = (
                CURRENT_SPRINT if item_id in CURRENT_STORIES else NEXT_SPRINT if item_id in NEXT_STORIES else QUARTER
            )
        elif item_type == "Task":
            parent = items.get(parent_by_child.get(item_id))
            desired_iteration = parent.fields.get("System.IterationPath") if parent is not None else None
        else:
            desired_iteration = QUARTER if item_type in {"Epic", "Feature"} else None

        if desired_iteration and item.fields.get("System.IterationPath") != desired_iteration:
            patch.append(JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=desired_iteration))
        if is_deferred and item.fields.get("System.AssignedTo") is not None:
            patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))

        if patch:
            update_with_required_assignee(wit, item_id, patch)
            updated += 1

    print(f"Normalized {updated} canonical framework items; executable Stories={len(STORY_WAVES)}.")


if __name__ == "__main__":
    main()
