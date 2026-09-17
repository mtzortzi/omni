"""Assign current-sprint owner-sized Stories to the four available owners."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients


ASSIGNMENTS = {
    "Marianna Tzortzi": {581343, 590882, 589193},
    "Antonis Daniil": {590886, 589182},
    "Artemis Lazanaki": {599254, 581355, 581490, 589178},
    "Dimitris Chatzakis": {590829},
}


def main() -> None:
    wit, _ = get_clients()
    for owner, story_ids in ASSIGNMENTS.items():
        for story_id in sorted(story_ids):
            wit.update_work_item(
                document=[JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value=owner)],
                id=story_id,
            )
            print(f"#{story_id} -> {owner}")


if __name__ == "__main__":
    main()
