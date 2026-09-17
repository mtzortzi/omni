"""Audit every live ADO User Story for a missing hierarchy parent."""

from __future__ import annotations

import requests
from requests.auth import HTTPBasicAuth

from ado_client import AdoConfig, get_clients


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)
    query = (
        "SELECT [System.Id] FROM WorkItems "
        "WHERE [System.TeamProject] = @project "
        "AND [System.WorkItemType] = 'User Story' "
        "AND [System.State] <> 'Removed' ORDER BY [System.Id]"
    )
    response = requests.post(
        f"{cfg.org_url}/{cfg.project}/_apis/wit/wiql?api-version=7.1",
        auth=HTTPBasicAuth("", cfg.pat),
        json={"query": query},
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()
    ids = [int(item["id"]) for item in response.json().get("workItems", [])]
    items = []
    for start in range(0, len(ids), 200):
        items.extend(wit.get_work_items(ids=ids[start : start + 200], expand="Relations"))
    orphans = [
        item
        for item in items
        if not any(relation.rel == "System.LinkTypes.Hierarchy-Reverse" for relation in item.relations or [])
    ]
    physical_ai = [
        item for item in orphans if (item.fields.get("System.AreaPath") or "").startswith("graiteam\\Physical AI")
    ]
    print(f"project_stories={len(items)} parentless={len(orphans)} physical_ai_parentless={len(physical_ai)}")
    for item in physical_ai:
        owner = item.fields.get("System.AssignedTo")
        owner_name = owner.get("displayName") if isinstance(owner, dict) else owner
        print(f"#{item.id}|{item.fields.get('System.State')}|{owner_name}|{item.fields.get('System.Title')}")


if __name__ == "__main__":
    main()
