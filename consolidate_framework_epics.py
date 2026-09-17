"""Consolidate framework ADO Epics around canonical capability ownership."""

from __future__ import annotations

from typing import Any

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql

from ado_client import AdoConfig, get_clients
from create_items import to_html


ENGAGEMENT_ID = 537616
ROOT_ITERATION = "graiteam"

EPICS = {
    "mission_planning": {
        "title": "Mission Planning",
        "description": (
            "Owns mission intent, decomposition, plan creation, validation, versioning, and replanning. "
            "Planning consumes Fleet, World Model, persistence, and publication through Mission-Planning-owned ports."
        ),
    },
    "mission_execution": {
        "title": "Mission Execution",
        "description": (
            "Owns execution sessions, action attempts, plan progression, Behavior Tree execution, recovery, "
            "cancellation, and replan requests. The Behavior Tree is an inbound adapter of this capability."
        ),
    },
}

EPIC_UPDATES = {
    463420: (
        "Framework Foundations & Governance",
        "Owns Shared Kernel, Bootstrap composition, CI, architecture enforcement, system-level verification, and repository governance. It contains no capability-specific business behavior.",
    ),
    588871: (
        "Runtime State",
        "Owns typed current operational projections, inbound state/event boundaries, private StateBackend contracts, and private event transport. Blackboard is an adapter, not a capability.",
    ),
    588939: (
        "Operator Interface",
        "Owns operator-facing use cases, projections, and HTTP/CLI/MCP inbound adapters. Cross-capability calls use Operator-Interface-owned outbound ports and bridges.",
    ),
    588973: (
        "Robot Abstraction",
        "Owns vendor-agnostic robot commands, normalized telemetry, RobotDriver contracts, affordances, safety boundaries, and concrete robot/simulator adapters.",
    ),
    589062: (
        "Fleet Coordination",
        "Owns robot eligibility, reservations, allocation validity, scheduling policies, and Fleet decisions; it never creates or mutates Mission Plans.",
    ),
    589173: (
        "Perception (reserved capability)",
        "Reserved capability for sensor fusion and operational observations. Activate only for a concrete use case and consumer-owned boundary.",
    ),
    589175: (
        "World Model (reserved capability)",
        "Reserved capability for environmental projections, semantic target resolution, maps, zones, and canonical transforms. Activate only for a concrete spatial consumer.",
    ),
}

MOVES_BY_TARGET: dict[int | str, set[int]] = {
    463420: {
        588934,
        589125,
        589134,
        589142,
        589144,
        589146,
        589147,
        589150,
        589151,
        589160,
        589162,
    },
    588871: {589120, 589121, 589131, 589133},
    "mission_planning": {588906, 589123},
    "mission_execution": {588916, 589089},
    589062: {588899},
    588973: {
        588883,
        589136,
        589140,
        589141,
        589165,
        589166,
        589167,
        589168,
        589169,
        590870,
        589172,
    },
    588940: {589115},
    589049: {590860, 590862, 590864, 590866},
}

DEFER_ITEMS = {
    589125,
    589134,
    589140,
    589142,
    589147,
    589150,
    589151,
    589160,
}

# Delete child-first. Scope is duplicate, already canonical documentation, or
# unsupported speculation; unique safety cases are moved before deletion.
DELETE_ITEMS = [
    590859,
    590858,
    590869,
    590857,
    589122,
    589126,
    589127,
    589128,
    589132,
    589137,
    589139,
    589145,
    589149,
    589152,
    589156,
    589157,
    589158,
    589170,
]

DISSOLVE_EPICS = [589119, 589124, 589130, 589135, 589143, 589148, 589153, 589164, 589171]


def relation_value(relation_type: str, target_url: str, name: str) -> dict[str, Any]:
    return {"rel": relation_type, "url": target_url, "attributes": {"name": name}}


def create_or_get_epic(wit: Any, cfg: AdoConfig, parent: Any, title: str, description: str) -> int:
    escaped = title.replace("'", "''")
    result = wit.query_by_wiql(
        wiql=Wiql(
            query=f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "
            f"AND [System.WorkItemType] = 'Epic' AND [System.Title] = '{escaped}'"
        )
    )
    if result.work_items:
        return result.work_items[0].id
    patch = [
        JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
        JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(description)),
        JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=parent.fields.get("System.AreaPath")),
        JsonPatchOperation(
            op="add", path="/fields/System.IterationPath", value=parent.fields.get("System.IterationPath")
        ),
        JsonPatchOperation(
            op="add",
            path="/relations/-",
            value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent.url, "Parent"),
        ),
    ]
    return wit.create_work_item(document=patch, project=cfg.project, type="Epic").id


def move_item(wit: Any, item_id: int, parent_id: int) -> None:
    item = wit.get_work_item(id=item_id, expand="Relations")
    parent = wit.get_work_item(id=parent_id)
    current_parent = next(
        (
            (index, relation)
            for index, relation in enumerate(item.relations or [])
            if relation.rel == "System.LinkTypes.Hierarchy-Reverse"
        ),
        None,
    )
    if current_parent is not None and current_parent[1].url.rstrip("/").endswith(f"/{parent_id}"):
        return
    patch: list[JsonPatchOperation] = []
    if current_parent is not None:
        patch.append(JsonPatchOperation(op="remove", path=f"/relations/{current_parent[0]}"))
    patch.append(
        JsonPatchOperation(
            op="add",
            path="/relations/-",
            value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent.url, "Parent"),
        )
    )
    wit.update_work_item(document=patch, id=item_id)
    print(f"[MOVE] #{item_id} -> #{parent_id}")


def defer_item(wit: Any, item_id: int) -> None:
    item = wit.get_work_item(id=item_id)
    existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
    desired = [
        tag for tag in existing if not tag.startswith("Implementation Wave ") and not tag.startswith("Exit Gate ")
    ]
    if "Deferred" not in desired:
        desired.append("Deferred")
    patch: list[JsonPatchOperation] = []
    if desired != existing:
        patch.append(JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(desired)))
    if item.fields.get("System.IterationPath") != ROOT_ITERATION:
        patch.append(JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=ROOT_ITERATION))
    if item.fields.get("System.AssignedTo") is not None:
        patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))
    if patch:
        wit.update_work_item(document=patch, id=item_id)


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)
    engagement = wit.get_work_item(id=ENGAGEMENT_ID)

    created_epics: dict[str, int] = {}
    for key, spec in EPICS.items():
        epic_id = create_or_get_epic(wit, cfg, engagement, spec["title"], spec["description"])
        created_epics[key] = epic_id
        print(f"[EPIC] {spec['title']} = #{epic_id}")

    for epic_id, (title, description) in EPIC_UPDATES.items():
        item = wit.get_work_item(id=epic_id)
        patch: list[JsonPatchOperation] = []
        if item.fields.get("System.Title") != title:
            patch.append(JsonPatchOperation(op="add", path="/fields/System.Title", value=title))
        patch.append(JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(description)))
        wit.update_work_item(document=patch, id=epic_id)
        print(f"[ALIGN] #{epic_id} {title}")

    for target, item_ids in MOVES_BY_TARGET.items():
        parent_id = created_epics[target] if isinstance(target, str) else target
        for item_id in sorted(item_ids):
            move_item(wit, item_id, parent_id)

    for item_id in sorted(DEFER_ITEMS):
        defer_item(wit, item_id)

    for item_id in DELETE_ITEMS:
        wit.delete_work_item(id=item_id, destroy=False)
        print(f"[DELETE] #{item_id}")

    for epic_id in DISSOLVE_EPICS:
        epic = wit.get_work_item(id=epic_id, expand="Relations")
        children = [
            relation for relation in epic.relations or [] if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        ]
        if children:
            child_ids = [relation.url.rstrip("/").rsplit("/", 1)[-1] for relation in children]
            raise RuntimeError(f"Cannot delete Epic #{epic_id}; children remain: {child_ids}")
        wit.delete_work_item(id=epic_id, destroy=False)
        print(f"[DELETE EPIC] #{epic_id}")

    print("Epic consolidation complete.")


if __name__ == "__main__":
    main()
