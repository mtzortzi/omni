"""Parent legacy Physical AI orphan Tasks without claiming canonical ownership."""

from __future__ import annotations

from typing import Any

import requests
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql
from requests.auth import HTTPBasicAuth

from ado_client import AdoConfig, get_clients
from create_items import ac_to_html, to_html


FOUNDATIONS_EPIC = 463420
ROOT_ITERATION = "graiteam"
AREA_PREFIX = "graiteam\\Physical AI"
CLOSING_ASSIGNEE = "Marianna Tzortzi"


def relation_value(relation_type: str, target_url: str, name: str) -> dict[str, Any]:
    return {"rel": relation_type, "url": target_url, "attributes": {"name": name}}


def create_or_get(
    wit: Any,
    cfg: AdoConfig,
    *,
    item_type: str,
    parent_id: int,
    title: str,
    description: str,
    acceptance_criteria: list[str] | None = None,
    tags: list[str] | None = None,
) -> int:
    escaped = title.replace("'", "''")
    result = wit.query_by_wiql(
        wiql=Wiql(
            query=f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "
            f"AND [System.WorkItemType] = '{item_type}' AND [System.Title] = '{escaped}'"
        )
    )
    if result.work_items:
        return result.work_items[0].id

    parent = wit.get_work_item(id=parent_id)
    patch = [
        JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
        JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(description)),
        JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=parent.fields.get("System.AreaPath")),
        JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=ROOT_ITERATION),
        JsonPatchOperation(
            op="add",
            path="/relations/-",
            value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent.url, "Parent"),
        ),
    ]
    if tags:
        patch.append(JsonPatchOperation(op="add", path="/fields/System.Tags", value="; ".join(tags)))
    if item_type == "User Story":
        patch.append(JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Scheduling.StoryPoints", value=0))
        patch.append(
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.ValueArea", value="Architectural")
        )
        if acceptance_criteria:
            patch.append(
                JsonPatchOperation(
                    op="add",
                    path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                    value=ac_to_html(acceptance_criteria),
                )
            )
    created = wit.create_work_item(document=patch, project=cfg.project, type=item_type)
    return created.id


def query_orphans(cfg: AdoConfig, wit: Any) -> list[Any]:
    query = (
        "SELECT [System.Id] FROM WorkItems "
        "WHERE [System.TeamProject] = @project "
        "AND [System.WorkItemType] = 'Task' "
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
    item_ids = [int(item["id"]) for item in response.json().get("workItems", [])]
    items = []
    for start in range(0, len(item_ids), 200):
        items.extend(wit.get_work_items(ids=item_ids[start : start + 200], expand="Relations"))
    return [
        item
        for item in items
        if (item.fields.get("System.AreaPath") or "").startswith(AREA_PREFIX)
        and not any(relation.rel == "System.LinkTypes.Hierarchy-Reverse" for relation in item.relations or [])
    ]


def parent_items(wit: Any, items: list[Any], parent_url: str, *, unschedule: bool) -> None:
    completed = 0
    for item in items:
        patch: list[JsonPatchOperation] = [
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent_url, "Parent"),
            )
        ]
        if unschedule:
            tags = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
            tags = [
                tag
                for tag in tags
                if not tag.lower().startswith("wave ")
                and not tag.startswith("Implementation Wave ")
                and not tag.startswith("Exit Gate ")
            ]
            for tag in ("Legacy Backlog", "Needs Triage", "Deferred"):
                if tag not in tags:
                    tags.append(tag)
            patch.append(JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=ROOT_ITERATION))
            patch.append(JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(tags)))
            if item.fields.get("System.AssignedTo") is not None:
                patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))
        wit.update_work_item(document=patch, id=item.id)
        completed += 1
        if completed % 25 == 0 or completed == len(items):
            print(f"Parented {completed}/{len(items)}")


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)
    feature_id = create_or_get(
        wit,
        cfg,
        item_type="Feature",
        parent_id=FOUNDATIONS_EPIC,
        title="Legacy Physical AI backlog migration and disposition",
        description=(
            "Temporary governance container for parentless work created before the canonical capability backlog. "
            "It does not authorize implementation. Every open item must be deleted, mapped to one canonical item, "
            "or rewritten under the owning capability before activation."
        ),
        tags=["Legacy Backlog", "Backlog Migration", "Deferred"],
    )
    archive_story_id = create_or_get(
        wit,
        cfg,
        item_type="User Story",
        parent_id=feature_id,
        title="Historical delivered Physical AI work archive",
        description="Preserve hierarchy and traceability for closed parentless Tasks created before the canonical framework backlog.",
        acceptance_criteria=[
            "Every closed legacy Task has a hierarchy parent.",
            "Archival parenting does not claim that a current canonical Story is complete.",
        ],
        tags=["Legacy Backlog", "Historical"],
    )
    triage_story_id = create_or_get(
        wit,
        cfg,
        item_type="User Story",
        parent_id=feature_id,
        title="Triage parentless legacy Physical AI tasks",
        description=(
            "Quarantine open parentless Tasks from pre-canonical backlogs. Each item must be compared with the repository "
            "and implementation guide, then deleted as obsolete/duplicate or migrated to one owning capability Story."
        ),
        acceptance_criteria=[
            "No live Physical AI Task remains parentless.",
            "No quarantined item is scheduled or assigned.",
            "Each item receives a documented DELETE, MERGE, MOVE, or KEEP decision before implementation.",
            "Canonical capability hierarchy remains the only executable backlog.",
        ],
        tags=["Legacy Backlog", "Needs Triage", "Deferred"],
    )

    orphans = query_orphans(cfg, wit)
    closed = [item for item in orphans if item.fields.get("System.State") == "Closed"]
    open_items = [item for item in orphans if item.fields.get("System.State") != "Closed"]
    print(f"Found {len(closed)} closed and {len(open_items)} open Physical AI orphan Tasks")
    parent_items(wit, closed, wit.get_work_item(id=archive_story_id).url, unschedule=False)
    parent_items(wit, open_items, wit.get_work_item(id=triage_story_id).url, unschedule=True)

    archive = wit.get_work_item(id=archive_story_id)
    if archive.fields.get("System.State") != "Closed":
        wit.update_work_item(
            document=[
                JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value=CLOSING_ASSIGNEE),
                JsonPatchOperation(op="add", path="/fields/System.State", value="Closed"),
            ],
            id=archive_story_id,
        )
    print(f"Feature #{feature_id}; archive Story #{archive_story_id}; triage Story #{triage_story_id}")


if __name__ == "__main__":
    main()
