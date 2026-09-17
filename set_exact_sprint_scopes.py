"""Set exact current, next, and planner-to-BT sprint scopes."""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import get_clients


CURRENT_SPRINT = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1\\FY27Q1.2"
NEXT_SPRINT = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1\\FY27Q1.3"
THIN_SLICE_SPRINT = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1\\FY27Q1.4"

CURRENT_STORIES = {581343, 581355, 581490, 590882, 599254, 589178, 589182, 589193, 590829, 590886}
NEXT_STORIES = {588873, 588885, 588907, 590891, 590896, 588893}
THIN_SLICE_STORIES = {588910, 599242, 588920, 588926}


def set_story_and_tasks(wit: object, story_id: int, iteration: str) -> int:
    story = wit.get_work_item(id=story_id, expand="Relations")
    wit.update_work_item(
        document=[JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=iteration)],
        id=story_id,
    )
    task_ids = [
        int(relation.url.rstrip("/").rsplit("/", 1)[-1])
        for relation in story.relations or []
        if relation.rel == "System.LinkTypes.Hierarchy-Forward"
    ]
    for task_id in task_ids:
        wit.update_work_item(
            document=[JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=iteration)],
            id=task_id,
        )
    print(f"#{story_id} + {len(task_ids)} Tasks -> {iteration.rsplit(chr(92), 1)[-1]}")
    return len(task_ids)


def main() -> None:
    wit, _ = get_clients()
    totals = {"current": 0, "next": 0, "thin": 0}
    for story_id in sorted(CURRENT_STORIES):
        totals["current"] += set_story_and_tasks(wit, story_id, CURRENT_SPRINT)
    for story_id in sorted(NEXT_STORIES):
        totals["next"] += set_story_and_tasks(wit, story_id, NEXT_SPRINT)
    for story_id in sorted(THIN_SLICE_STORIES):
        totals["thin"] += set_story_and_tasks(wit, story_id, THIN_SLICE_SPRINT)
    print(
        f"Current: {len(CURRENT_STORIES)} Stories/{totals['current']} Tasks; "
        f"next: {len(NEXT_STORIES)} Stories/{totals['next']} Tasks; "
        f"thin slice: {len(THIN_SLICE_STORIES)} Stories/{totals['thin']} Tasks."
    )


if __name__ == "__main__":
    main()
