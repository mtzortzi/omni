"""List all Tasks under an engagement work item (recursive WIQL).

Usage:
    uv run python engagement_tasks.py 537616
"""

from __future__ import annotations

import sys

from azure.devops.v7_1.work_item_tracking.models import Wiql

from ado_client import AdoConfig, get_clients

BATCH_SIZE = 200
FIELDS = [
    "System.Id",
    "System.Title",
    "System.WorkItemType",
    "System.State",
    "System.AssignedTo",
    "System.IterationPath",
    "Microsoft.VSTS.Common.ClosedDate",
]


def get_descendant_task_ids(wit_client, engagement_id: int) -> list[int]:
    wiql = Wiql(
        query=f"""
            SELECT [System.Id]
            FROM WorkItemLinks
            WHERE [Source].[System.Id] = {engagement_id}
              AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'
              AND [Target].[System.WorkItemType] = 'Task'
            MODE (Recursive)
        """
    )
    result = wit_client.query_by_wiql(wiql)
    return list(
        {
            rel.target.id
            for rel in (result.work_item_relations or [])
            if rel.target and rel.target.id != engagement_id
        }
    )


def main() -> None:
    engagement_id = int(sys.argv[1]) if len(sys.argv) > 1 else 537616

    cfg = AdoConfig.from_env()
    wit_client, _ = get_clients(cfg)

    ids = get_descendant_task_ids(wit_client, engagement_id)
    if not ids:
        print(f"No Tasks found under work item #{engagement_id}.")
        return

    items = []
    for i in range(0, len(ids), BATCH_SIZE):
        items.extend(
            wit_client.get_work_items(ids=ids[i : i + BATCH_SIZE], fields=FIELDS)
        )

    print(f"Engagement #{engagement_id}: {len(items)} Tasks\n")
    for wi in sorted(items, key=lambda w: w.fields.get("System.State", "")):
        f = wi.fields
        assignee = f.get("System.AssignedTo", {})
        name = (
            assignee.get("displayName") if isinstance(assignee, dict) else "Unassigned"
        ) or "Unassigned"
        print(
            f"  #{wi.id:<7} {f.get('System.State'):<12} {name:<25} "
            f"{f.get('System.Title')}"
        )


if __name__ == "__main__":
    main()
