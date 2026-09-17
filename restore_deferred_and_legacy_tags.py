"""Restore explicit deferred and canonical legacy-quarantine markers."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients
from engagement_tree import fetch_tree
from finalize_implementation_waves import DEFERRED_ROOTS, subtree


DELETE_EMPTY = [600020, 600021, 600019, 600316, 600317]


def main() -> None:
    wit, _ = get_clients()
    for item_id in DELETE_EMPTY:
        try:
            item = wit.get_work_item(id=item_id, expand="Relations")
        except Exception:
            continue
        children = [
            relation for relation in item.relations or [] if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        ]
        if children:
            raise RuntimeError(f"Cannot delete #{item_id}; children remain")
        wit.delete_work_item(id=item_id, destroy=False)
        print(f"[DELETE EMPTY DUPLICATE] #{item_id}")

    nodes, children = fetch_tree(wit, 537616)
    deferred_ids = subtree(children, DEFERRED_ROOTS & set(nodes))
    for item_id in sorted(deferred_ids):
        item = wit.get_work_item(id=item_id)
        patch = [
            JsonPatchOperation(op="add", path="/fields/System.Tags", value="Deferred"),
            JsonPatchOperation(op="add", path="/fields/System.IterationPath", value="graiteam"),
        ]
        if item.fields.get("System.AssignedTo") is not None:
            patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))
        wit.update_work_item(document=patch, id=item_id)

    legacy = {
        600023: "Backlog Migration; Deferred; Legacy Backlog",
        600024: "Historical; Legacy Backlog",
        600025: "Deferred; Legacy Backlog; Needs Triage",
    }
    for item_id, tags in legacy.items():
        item = wit.get_work_item(id=item_id)
        patch = [
            JsonPatchOperation(op="add", path="/fields/System.Tags", value=tags),
            JsonPatchOperation(op="add", path="/fields/System.IterationPath", value="graiteam"),
        ]
        if item_id in {600023, 600025} and item.fields.get("System.AssignedTo") is not None:
            patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))
        wit.update_work_item(document=patch, id=item_id)

    print(f"Restored Deferred on {len(deferred_ids)} items and canonical legacy markers.")


if __name__ == "__main__":
    main()
