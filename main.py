"""Sanity-check script: authenticate and list up to 20 recent work items.

Run:
    python main.py
"""

from __future__ import annotations

from azure.devops.v7_1.work_item_tracking.models import Wiql

from ado_client import AdoConfig, get_clients

BATCH_SIZE = 200
FIELDS = [
    "System.Id",
    "System.Title",
    "System.WorkItemType",
    "System.State",
    "System.AssignedTo",
]


def main() -> None:
    cfg = AdoConfig.from_env()
    wit_client, _ = get_clients(cfg)

    wiql = Wiql(
        query=f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.TeamProject] = '{cfg.project}'
            ORDER BY [System.ChangedDate] DESC
        """
    )
    result = wit_client.query_by_wiql(wiql, top=20)
    ids = [ref.id for ref in (result.work_items or [])]

    if not ids:
        print(f"No work items found in project '{cfg.project}'.")
        return

    items = []
    for i in range(0, len(ids), BATCH_SIZE):
        items.extend(
            wit_client.get_work_items(ids=ids[i : i + BATCH_SIZE], fields=FIELDS)
        )

    print(f"Found {len(items)} recent work items in '{cfg.project}':\n")
    for wi in items:
        f = wi.fields
        assignee = f.get("System.AssignedTo", {})
        assignee_name = (
            assignee.get("displayName") if isinstance(assignee, dict) else "Unassigned"
        ) or "Unassigned"
        print(
            f"  #{wi.id:<6} [{f.get('System.WorkItemType'):<12}] "
            f"{f.get('System.State'):<12} {assignee_name:<25} "
            f"{f.get('System.Title')}"
        )


if __name__ == "__main__":
    main()
