"""Finalize recursive wave and deferred tags for the Wednesday ADO plan."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients
from engagement_tree import fetch_tree


ROOT_ITERATION = "graiteam"

# These branches are explicitly excluded from current implementation waves.
DEFERRED_ROOTS = {
    589058,  # advanced RobotDriver fixture helpers
    589120,  # durable-state technology ADR
    589121,  # durable StateBackend adapter
    589123,  # vector store
    589141,  # HIL hooks
    589162,  # README currency automation
    589165,  # conditional vendor adapters
    589166,
    589167,
    589168,
    589169,
    589171,  # physics simulator
    589173,  # perception
    589175,  # world model
    590838,  # SimClock
    590849,  # token auth
    590856,  # CostBased scheduling
    590908,  # EventRecorder
    590913,  # kinematic fake
}

WAVE_SUBTREES = {
    8: {588940, 588951, 588959, 588967, 590839},
    9: {
        588974,
        588996,
        589007,
        589030,
        589049,
        590857,
        589063,
        589076,
        590850,
        589089,
        589108,
        589136,
        590870,
    },
}


def subtree(children: dict[int, list[int]], roots: set[int]) -> set[int]:
    result: set[int] = set()
    pending = list(roots)
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
    deferred_ids = subtree(children, DEFERRED_ROOTS)

    wave_by_item: dict[int, set[str]] = {}
    for gate, roots in WAVE_SUBTREES.items():
        for item_id in subtree(children, roots) - deferred_ids:
            wave_by_item.setdefault(item_id, set()).add(f"Implementation Wave {gate}")

    target_ids = sorted(deferred_ids | set(wave_by_item))
    fetched = []
    for start in range(0, len(target_ids), 200):
        fetched.extend(wit.get_work_items(ids=target_ids[start : start + 200]))
    items = {item.id: item for item in fetched}

    updated = 0
    for item_id in target_ids:
        item = items[item_id]
        existing_tags = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        if item_id in deferred_ids:
            desired_tags = [
                tag
                for tag in existing_tags
                if not tag.startswith("Implementation Wave ") and not tag.startswith("Exit Gate ")
            ]
            if "Deferred" not in desired_tags:
                desired_tags.append("Deferred")
        else:
            desired_tags = existing_tags.copy()
        for wave_tag in sorted(wave_by_item.get(item_id, set())):
            if wave_tag not in desired_tags:
                desired_tags.append(wave_tag)

        patch: list[JsonPatchOperation] = []
        if desired_tags != existing_tags:
            patch.append(JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(desired_tags)))
        if item_id in deferred_ids:
            if item.fields.get("System.IterationPath") != ROOT_ITERATION:
                patch.append(JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=ROOT_ITERATION))
            if item.fields.get("System.AssignedTo") is not None:
                patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))
        if patch:
            wit.update_work_item(document=patch, id=item_id)
            updated += 1
            label = "Deferred" if item_id in deferred_ids else ", ".join(sorted(wave_by_item[item_id]))
            print(f"[OK] #{item_id}: {label}")

    print(f"Updated {updated} items; deferred branches contain {len(deferred_ids)} items.")


if __name__ == "__main__":
    main()
