"""Report duplicate, deferred, removed, and implementation-gate ADO items."""

from __future__ import annotations

from ado_client import get_clients
from engagement_tree import fetch_tree


def item_id_from_url(url: str) -> int:
    return int(url.rstrip("/").rsplit("/", 1)[-1])


def main() -> None:
    wit, _ = get_clients()
    nodes, children = fetch_tree(wit, 537616)
    item_ids = sorted(nodes)
    expanded = []
    for start in range(0, len(item_ids), 200):
        expanded.extend(wit.get_work_items(ids=item_ids[start : start + 200], expand="Relations"))

    duplicates: list[tuple[int, int, str]] = []
    deferred: list[tuple[int, str, str, str]] = []
    removed: list[tuple[int, str, str]] = []
    untagged_children: list[tuple[int, int, str, str]] = []

    for item in expanded:
        fields = item.fields
        title = fields.get("System.Title", "")
        item_type = fields.get("System.WorkItemType", "")
        state = fields.get("System.State", "")
        tags = {tag.strip() for tag in (fields.get("System.Tags") or "").split(";") if tag.strip()}
        gate_tags = {tag for tag in tags if tag.startswith("Implementation Wave ")}

        if "Deferred" in tags:
            deferred.append((item.id, item_type, state, title))
        if state == "Removed":
            removed.append((item.id, item_type, title))
        for relation in item.relations or []:
            if relation.rel == "System.LinkTypes.Duplicate-Reverse":
                duplicates.append((item.id, item_id_from_url(relation.url), title))

        if gate_tags:
            for child_id in children.get(item.id, []):
                child = nodes.get(child_id)
                if child is None:
                    continue
                child_tags = {tag.strip() for tag in (child.fields.get("System.Tags") or "").split(";") if tag.strip()}
                missing = gate_tags - child_tags
                if missing and "Deferred" not in child_tags and child.fields.get("System.State") != "Removed":
                    untagged_children.append(
                        (item.id, child_id, ", ".join(sorted(missing)), child.fields.get("System.Title", ""))
                    )

    print("DUPLICATES")
    for duplicate_id, canonical_id, title in duplicates:
        print(f"#{duplicate_id} -> #{canonical_id} | {title}")
    print(f"count={len(duplicates)}\n")

    print("DEFERRED")
    for item_id, item_type, state, title in deferred:
        print(f"#{item_id} | {item_type} | {state} | {title}")
    print(f"count={len(deferred)}\n")

    print("REMOVED")
    for item_id, item_type, title in removed:
        print(f"#{item_id} | {item_type} | {title}")
    print(f"count={len(removed)}\n")

    print("UNTAGGED NON-DEFERRED CHILDREN OF GATED ITEMS")
    for parent_id, child_id, tags, title in untagged_children:
        print(f"#{parent_id} -> #{child_id} | {tags} | {title}")
    print(f"count={len(untagged_children)}")


if __name__ == "__main__":
    main()
