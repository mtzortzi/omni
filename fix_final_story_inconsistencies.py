"""Fix final Story dependencies and hierarchy without changing sprint scope."""

from __future__ import annotations

from typing import Any

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql

from ado_client import AdoConfig, get_clients
from create_items import ac_to_html, to_html


def relation_value(relation_type: str, target_url: str, name: str) -> dict[str, Any]:
    return {"rel": relation_type, "url": target_url, "attributes": {"name": name}}


def add_dependency(wit: Any, successor_id: int, predecessor_id: int) -> None:
    successor = wit.get_work_item(id=successor_id, expand="Relations")
    if any(
        relation.rel == "System.LinkTypes.Dependency-Reverse"
        and relation.url.rstrip("/").endswith(f"/{predecessor_id}")
        for relation in successor.relations or []
    ):
        return
    predecessor = wit.get_work_item(id=predecessor_id)
    wit.update_work_item(
        document=[
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value=relation_value("System.LinkTypes.Dependency-Reverse", predecessor.url, "Predecessor"),
            )
        ],
        id=successor_id,
    )
    print(f"[DEPENDENCY] #{predecessor_id} => #{successor_id}")


def move_item(wit: Any, item_id: int, parent_id: int) -> None:
    item = wit.get_work_item(id=item_id, expand="Relations")
    parent = wit.get_work_item(id=parent_id)
    current = next(
        (
            (index, relation)
            for index, relation in enumerate(item.relations or [])
            if relation.rel == "System.LinkTypes.Hierarchy-Reverse"
        ),
        None,
    )
    if current is not None and current[1].url.rstrip("/").endswith(f"/{parent_id}"):
        return
    patch: list[JsonPatchOperation] = []
    if current is not None:
        patch.append(JsonPatchOperation(op="remove", path=f"/relations/{current[0]}"))
    patch.extend(
        [
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent.url, "Parent"),
            ),
            JsonPatchOperation(
                op="add",
                path="/fields/System.IterationPath",
                value=parent.fields.get("System.IterationPath"),
            ),
        ]
    )
    wit.update_work_item(document=patch, id=item_id)
    print(f"[MOVE] #{item_id} -> #{parent_id}")


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)

    add_dependency(wit, successor_id=588910, predecessor_id=590896)
    add_dependency(wit, successor_id=588926, predecessor_id=588910)
    move_item(wit, item_id=590894, parent_id=588893)

    title = "Author Operator Interface authentication and principal-resolution ADR"
    escaped = title.replace("'", "''")
    result = wit.query_by_wiql(
        wiql=Wiql(
            query=f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "
            f"AND [System.WorkItemType] = 'Task' AND [System.Title] = '{escaped}'"
        )
    )
    if result.work_items:
        task_id = result.work_items[0].id
    else:
        story = wit.get_work_item(id=590840)
        task = wit.create_work_item(
            document=[
                JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
                JsonPatchOperation(
                    op="add",
                    path="/fields/System.Description",
                    value=to_html(
                        "Record the evolution from trusted-LAN transport assumptions to token/OIDC authentication, "
                        "the optional Operator-Interface-owned outbound principal-resolution port, and the separation "
                        "between transport authentication and application/domain authorization."
                    ),
                ),
                JsonPatchOperation(
                    op="add",
                    path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                    value=ac_to_html(
                        [
                            "ADR distinguishes inbound transport authentication from application/domain authorization.",
                            "If application identity is required, principal resolution is an Operator Interface outbound port.",
                            "TrustLan, token, and OIDC stages and activation criteria are explicit.",
                            "Threat assumptions, rejected alternatives, and related canonical documents are recorded.",
                        ]
                    ),
                ),
                JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=story.fields.get("System.AreaPath")),
                JsonPatchOperation(
                    op="add", path="/fields/System.IterationPath", value=story.fields.get("System.IterationPath")
                ),
                JsonPatchOperation(
                    op="add",
                    path="/relations/-",
                    value=relation_value("System.LinkTypes.Hierarchy-Reverse", story.url, "Parent"),
                ),
            ],
            project=cfg.project,
            type="Task",
        )
        task_id = task.id
    print(f"[ADR TASK] #{task_id}")


if __name__ == "__main__":
    main()
