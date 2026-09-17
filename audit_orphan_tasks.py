"""Audit every live ADO Task for a missing hierarchy parent."""

from __future__ import annotations

import requests
from requests.auth import HTTPBasicAuth

from ado_client import AdoConfig
from azure.devops.v7_1.work_item_tracking.models import Wiql

from ado_client import get_clients


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)
    query = (
        "SELECT [System.Id], [System.Parent] FROM WorkItems "
        "WHERE [System.TeamProject] = @project "
        "AND [System.WorkItemType] = 'Task' "
        "AND [System.State] <> 'Removed' "
        "ORDER BY [System.Id]"
    )
    response = requests.post(
        f"{cfg.org_url}/{cfg.project}/_apis/wit/wiql?api-version=7.1",
        auth=HTTPBasicAuth("", cfg.pat),
        json={"query": query},
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()
    item_ids = [int(item["id"]) for item in response.json().get("workItems", [])]
    items = []
    for start in range(0, len(item_ids), 200):
        items.extend(wit.get_work_items(ids=item_ids[start : start + 200], expand="Relations"))

    orphans = []
    for item in items:
        parent = next(
            (relation for relation in item.relations or [] if relation.rel == "System.LinkTypes.Hierarchy-Reverse"),
            None,
        )
        if parent is None:
            orphans.append(item)

    physical_ai = [
        item for item in orphans if (item.fields.get("System.AreaPath") or "").startswith("graiteam\\Physical AI")
    ]
    state_counts: dict[str, int] = {}
    for item in physical_ai:
        state = item.fields.get("System.State", "Unknown")
        state_counts[state] = state_counts.get(state, 0) + 1

    print(
        f"project_tasks={len(items)} parentless={len(orphans)} "
        f"physical_ai_parentless={len(physical_ai)} states={state_counts}"
    )
    for item in physical_ai:
        print(
            f"#{item.id}|{item.fields.get('System.State')}|{item.fields.get('System.AreaPath')}|"
            f"{item.fields.get('System.IterationPath')}|custom_parent={item.fields.get('Custom.ParentStoryID')}|"
            f"{item.fields.get('System.Title')}"
        )


if __name__ == "__main__":
    main()
