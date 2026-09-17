"""Apply implementation-wave and exit-gate tags to durable framework Epics."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients


EPIC_PHASES: dict[int, set[str]] = {
    463420: {
        "Implementation Wave 0",
        "Implementation Wave 1",
        "Implementation Wave 2",
        "Implementation Wave 7",
        "Exit Gate 0",
        "Exit Gate 1",
        "Exit Gate 2",
        "Exit Gate 7",
    },
    588871: {"Implementation Wave 3", "Exit Gate 3"},
    588939: {"Implementation Wave 8", "Exit Gate 8"},
    588973: {"Implementation Wave 4", "Implementation Wave 9", "Exit Gate 4", "Exit Gate 9"},
    589062: {"Implementation Wave 4", "Implementation Wave 9", "Exit Gate 4", "Exit Gate 9"},
    599251: {"Implementation Wave 5", "Exit Gate 5"},
    599252: {"Implementation Wave 6", "Implementation Wave 9", "Exit Gate 6", "Exit Gate 9"},
}


def phase_key(tag: str) -> tuple[int, int]:
    return (0 if tag.startswith("Implementation Wave ") else 1, int(tag.rsplit(" ", 1)[-1]))


def main() -> None:
    wit, _ = get_clients()
    items = {item.id: item for item in wit.get_work_items(ids=sorted(EPIC_PHASES))}
    for item_id, phases in sorted(EPIC_PHASES.items()):
        item = items[item_id]
        existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        desired = existing.copy()
        for phase in sorted(phases, key=phase_key):
            if phase not in desired:
                desired.append(phase)
        if desired == existing:
            continue
        wit.update_work_item(
            document=[JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(desired))],
            id=item_id,
        )
        print(f"[OK] #{item_id}: {', '.join(sorted(phases, key=phase_key))}")


if __name__ == "__main__":
    main()
