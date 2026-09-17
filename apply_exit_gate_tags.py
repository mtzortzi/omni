"""Tag ADO checkpoint owners for each implementation-wave exit gate."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients


EXIT_GATE_OWNERS: dict[int, set[int]] = {
    0: {581343, 581355, 581490, 589177, 599236},
    1: {590828, 590886, 589177, 589192},
    2: {581477, 581481},
    3: {588872, 589131, 599237},
    4: {588883, 588899, 590891},
    5: {588906, 590896},
    6: {588916, 599242, 590900},
    7: {581486, 581490, 588934},
    8: {588939},
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
        590870,
    },
}


def main() -> None:
    wit, _ = get_clients()
    gates_by_item: dict[int, set[str]] = {}
    for gate, item_ids in EXIT_GATE_OWNERS.items():
        for item_id in item_ids:
            gates_by_item.setdefault(item_id, set()).add(f"Exit Gate {gate}")

    item_ids = sorted(gates_by_item)
    items = {item.id: item for item in wit.get_work_items(ids=item_ids)}
    missing = set(item_ids) - set(items)
    if missing:
        raise RuntimeError(f"Could not fetch exit-gate owners: {sorted(missing)}")

    updated = 0
    for item_id, exit_tags in sorted(gates_by_item.items()):
        item = items[item_id]
        existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        desired = existing.copy()
        for exit_tag in sorted(exit_tags, key=lambda value: int(value.rsplit(" ", 1)[-1])):
            if exit_tag not in desired:
                desired.append(exit_tag)
        if desired == existing:
            continue
        wit.update_work_item(
            document=[JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(desired))],
            id=item_id,
        )
        updated += 1
        print(f"[OK] #{item_id}: {', '.join(sorted(exit_tags))}")

    print(f"Tagged {updated} exit-gate owners; {len(gates_by_item) - updated} already aligned.")


if __name__ == "__main__":
    main()
