"""Delete the fully triaged legacy quarantine from the live ADO backlog."""

from __future__ import annotations

from ado_client import get_clients


FEATURE_ID = 600023
STORY_IDS = (600024, 600025)


def main() -> None:
    wit, _ = get_clients()
    task_ids: list[int] = []
    for story_id in STORY_IDS:
        story = wit.get_work_item(id=story_id, expand="Relations")
        task_ids.extend(
            int(relation.url.rstrip("/").rsplit("/", 1)[-1])
            for relation in story.relations or []
            if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        )

    if len(task_ids) != 368:
        raise RuntimeError(f"Expected 368 quarantined Tasks, found {len(task_ids)}")

    deleted = 0
    for task_id in sorted(task_ids):
        wit.delete_work_item(id=task_id, destroy=False)
        deleted += 1
        if deleted % 25 == 0 or deleted == len(task_ids):
            print(f"Deleted {deleted}/{len(task_ids)} legacy Tasks")

    for story_id in STORY_IDS:
        story = wit.get_work_item(id=story_id, expand="Relations")
        remaining = [
            relation for relation in story.relations or [] if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        ]
        if remaining:
            raise RuntimeError(f"Story #{story_id} still has {len(remaining)} children")
        wit.delete_work_item(id=story_id, destroy=False)
        print(f"Deleted legacy Story #{story_id}")

    feature = wit.get_work_item(id=FEATURE_ID, expand="Relations")
    remaining = [
        relation for relation in feature.relations or [] if relation.rel == "System.LinkTypes.Hierarchy-Forward"
    ]
    if remaining:
        raise RuntimeError(f"Feature #{FEATURE_ID} still has {len(remaining)} children")
    wit.delete_work_item(id=FEATURE_ID, destroy=False)
    print(f"Deleted legacy Feature #{FEATURE_ID}")


if __name__ == "__main__":
    main()
