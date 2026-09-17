"""Apply the Wave -> independent Story -> Task checklist model globally."""

from __future__ import annotations

from typing import Any

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql

from ado_client import AdoConfig, get_clients
from create_items import ac_to_html, to_html
from engagement_tree import fetch_tree


EPICS = {463420, 588871, 599251, 599252, 589062, 588973, 588939, 589173, 589175}
CURRENT_SPRINT = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1\\FY27Q1.2"
NEXT_SPRINT = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1\\FY27Q1.3"
QUARTER = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1"


STORY_WAVES: dict[int, int] = {
    581343: 0,
    581355: 0,
    581490: 0,
    590882: 0,
    599254: 0,
    589178: 1,
    589182: 1,
    589193: 1,
    590829: 1,
    590886: 1,
    581477: 2,
    581481: 2,
    588873: 3,
    599237: 3,
    588885: 4,
    588901: 4,
    588907: 5,
    590891: 5,
    590896: 5,
    588893: 6,
    588910: 7,
    599242: 7,
    600228: 7,
    581486: 8,
    588920: 8,
    600229: 8,
    588926: 9,
    588935: 10,
    578641: 11,
    588941: 11,
    588975: 11,
    588981: 11,
    588998: 11,
    589008: 11,
    589020: 11,
    589031: 11,
    589064: 11,
    589090: 11,
    590840: 11,
    588944: 12,
    588953: 12,
    588961: 12,
    588968: 12,
    588988: 12,
    589013: 12,
    589035: 12,
    589043: 12,
    589068: 12,
    589077: 12,
    589094: 12,
    590841: 12,
    590844: 12,
    578644: 13,
    589002: 13,
    589101: 13,
    589109: 13,
    590851: 13,
    590900: 13,
    590904: 13,
    589050: 14,
    599253: 14,
    590871: 15,
    590879: 16,
}

CURRENT_STORIES = {581343, 581355, 581490, 590882, 599254, 589178, 589182, 589193, 590829, 590886}
NEXT_STORIES = {588873, 588885, 588907, 590891, 590896, 588893, 588910, 599242, 588920, 588926}

MERGES: dict[int, int] = {
    590832: 590829,
    590835: 590829,
    588878: 588873,
    589085: 589077,
    590853: 590851,
    589026: 589020,
    590860: 589050,
    590862: 589050,
    590864: 589050,
    590866: 589050,
    590876: 590871,
}

TASK_MOVES: dict[int, int | str] = {
    590834: "runtime_clock_composition",
    581479: "runtime_clock_composition",
    581480: "runtime_clock_composition",
    588882: "runtime_clock_composition",
    588898: "robot_composition",
    588892: 588893,
    590899: 588910,
    581492: 588935,
    589116: 588941,
    589117: 588944,
    589118: 588961,
}

NEW_STORIES = {
    "runtime_clock_composition": {
        "parent": 588934,
        "title": "Compose Runtime State and Clock through the Bootstrap API",
        "description": "Compose the first real Runtime State service, in-memory StateBackend, and SystemClock through the reusable Bootstrap API. This is a separate thread because it depends on completed Bootstrap and Runtime State Stories.",
        "wave": 4,
    },
    "robot_composition": {
        "parent": 588934,
        "title": "Compose Robot Abstraction logging profile through Bootstrap",
        "description": "Compose the Robot Abstraction service and logging RobotDriver through Bootstrap after their contracts and adapter are stable.",
        "wave": 7,
    },
}

# Predecessor Stories -> successor Stories. Every relation crosses Waves.
STORY_DEPENDENCIES: dict[int | str, set[int | str]] = {
    590891: {588885},
    588893: {588885, 590891},
    "runtime_clock_composition": {581477, 581481, 588873},
    "robot_composition": {581477, 588893},
    588910: {588907, 588873},
    599242: {588907, 588873},
    600228: {588873, 588893},
    588920: {588907},
    600229: {588901, 588910},
    588926: {588873, 588893, 588920, 599242},
    588935: {588910, 588926, 599242, "runtime_clock_composition", "robot_composition"},
    589094: {589090},
    589068: {589064},
    589077: {588998},
    588988: {588975, 588981, 588998},
    589013: {588893, 589008},
    589035: {581481, 589031, 590829},
    589043: {588975, 588981, 588998},
    588944: {588941},
    588953: {588941},
    588961: {588941},
    588968: {588941},
    590841: {590840},
    590844: {588941},
    578644: {578641},
    589002: {588893, 588998, 588988},
    589101: {588998, 589094},
    589109: {589064, 589068, 599237},
    590851: {589077},
    590900: {599237},
    590904: {589013},
    589050: {589002, 589013, 589035, 589043, 590904},
    599253: {599237, 590900},
    590871: {589050},
    590879: {590871},
}


def relation_value(relation_type: str, target_url: str, name: str) -> dict[str, Any]:
    return {"rel": relation_type, "url": target_url, "attributes": {"name": name}}


def create_story(wit: Any, cfg: AdoConfig, spec: dict[str, Any]) -> int:
    escaped = spec["title"].replace("'", "''")
    result = wit.query_by_wiql(
        wiql=Wiql(
            query=f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "
            f"AND [System.WorkItemType] = 'User Story' AND [System.Title] = '{escaped}'"
        )
    )
    if result.work_items:
        return result.work_items[0].id
    parent = wit.get_work_item(id=spec["parent"])
    story = wit.create_work_item(
        document=[
            JsonPatchOperation(op="add", path="/fields/System.Title", value=spec["title"]),
            JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(spec["description"])),
            JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=parent.fields.get("System.AreaPath")),
            JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=QUARTER),
            JsonPatchOperation(op="add", path="/fields/System.Tags", value=f"Implementation Wave {spec['wave']}"),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Scheduling.StoryPoints", value=3),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.ValueArea", value="Architectural"),
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent.url, "Parent"),
            ),
        ],
        project=cfg.project,
        type="User Story",
    )
    print(f"[CREATE STORY] #{story.id} {spec['title']}")
    return story.id


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
    patch.append(
        JsonPatchOperation(
            op="add",
            path="/relations/-",
            value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent.url, "Parent"),
        )
    )
    try:
        wit.update_work_item(document=patch, id=item_id)
    except Exception as exc:
        if "Assigned To" not in str(exc):
            raise
        patch.insert(0, JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value="Marianna Tzortzi"))
        wit.update_work_item(document=patch, id=item_id)
    print(f"[MOVE] #{item_id} -> #{parent_id}")


def remove_all_dependencies(wit: Any, item_id: int) -> None:
    item = wit.get_work_item(id=item_id, expand="Relations")
    indices = [index for index, relation in enumerate(item.relations or []) if "Dependency" in relation.rel]
    if not indices:
        return
    patch = [JsonPatchOperation(op="remove", path=f"/relations/{index}") for index in sorted(indices, reverse=True)]
    wit.update_work_item(document=patch, id=item_id)


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
    print(f"[STORY DEP] #{predecessor_id} => #{successor_id}")


def descendants(children: dict[int, list[int]], roots: set[int]) -> set[int]:
    result: set[int] = set()
    pending = list(roots)
    while pending:
        item_id = pending.pop()
        if item_id in result:
            continue
        result.add(item_id)
        pending.extend(children.get(item_id, []))
    return result


def normalize_tags_and_iterations(wit: Any, framework_ids: set[int], children: dict[int, list[int]]) -> None:
    item_ids = sorted(framework_ids)
    items = []
    for start in range(0, len(item_ids), 200):
        items.extend(wit.get_work_items(ids=item_ids[start : start + 200]))
    item_by_id = {item.id: item for item in items}

    deferred_roots = {
        item.id
        for item in items
        if "Deferred" in {tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()}
    }
    deferred_ids = descendants(children, deferred_roots)
    legacy_ids = {item.id for item in items if "Legacy Backlog" in (item.fields.get("System.Tags") or "")}

    for item in items:
        if item.id in legacy_ids:
            continue
        item_type = item.fields.get("System.WorkItemType")
        is_deferred = item.id in deferred_ids
        if is_deferred:
            desired_tags = ["Deferred"]
        elif item_type == "User Story" and item.id in STORY_WAVES:
            desired_tags = [f"Implementation Wave {STORY_WAVES[item.id]}"]
        else:
            desired_tags = []

        existing_tags = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        patch: list[JsonPatchOperation] = []
        if existing_tags != desired_tags:
            operation = "replace" if existing_tags else "add"
            patch.append(JsonPatchOperation(op=operation, path="/fields/System.Tags", value="; ".join(desired_tags)))

        if item_type == "User Story" and not is_deferred:
            desired_iteration = (
                CURRENT_SPRINT if item.id in CURRENT_STORIES else NEXT_SPRINT if item.id in NEXT_STORIES else QUARTER
            )
            if item.fields.get("System.IterationPath") != desired_iteration:
                patch.append(JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=desired_iteration))
        elif item_type == "Task":
            parent_id = next(
                (parent for parent, child_ids in children.items() if item.id in child_ids and parent in item_by_id),
                None,
            )
            parent = item_by_id.get(parent_id)
            if parent is not None and item.fields.get("System.State") not in ("Closed", "Removed"):
                parent_iteration = parent.fields.get("System.IterationPath")
                if parent_iteration and item.fields.get("System.IterationPath") != parent_iteration:
                    patch.append(
                        JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=parent_iteration)
                    )
        elif is_deferred:
            if item.fields.get("System.IterationPath") != "graiteam":
                patch.append(JsonPatchOperation(op="add", path="/fields/System.IterationPath", value="graiteam"))
            if item.fields.get("System.AssignedTo") is not None:
                patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))

        if patch:
            try:
                wit.update_work_item(document=patch, id=item.id)
            except Exception as exc:
                if "Assigned To" not in str(exc) or any(
                    operation.path == "/fields/System.AssignedTo" for operation in patch
                ):
                    raise
                patch.insert(
                    0, JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value="Marianna Tzortzi")
                )
                wit.update_work_item(document=patch, id=item.id)


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)
    nodes, children = fetch_tree(wit, 537616)

    created = {key: create_story(wit, cfg, spec) for key, spec in NEW_STORIES.items()}
    STORY_WAVES[created["runtime_clock_composition"]] = 4
    STORY_WAVES[created["robot_composition"]] = 7

    # Merge cohesive Stories by moving all child Tasks.
    for source_id, target_id in MERGES.items():
        source = wit.get_work_item(id=source_id, expand="Relations")
        child_ids = [
            int(relation.url.rstrip("/").rsplit("/", 1)[-1])
            for relation in source.relations or []
            if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        ]
        for child_id in child_ids:
            move_item(wit, child_id, target_id)

    # Split tasks that belong to later, independently assignable outcomes.
    for task_id, target in TASK_MOVES.items():
        target_id = created[target] if isinstance(target, str) else target
        move_item(wit, task_id, target_id)

    # Split ViewFleet across the existing contract, bridge, and HTTP Stories.
    move_item(wit, 589116, 588941)
    move_item(wit, 589117, 588944)
    move_item(wit, 589118, 588961)

    # Core owner-sized Story descriptions.
    updates = {
        590829: (
            "Complete deterministic Clock capability",
            "One owner delivers the complete deterministic Clock thread: shared Clock Protocol, production SystemClock, test-only FakeClock, ownership-aligned tests, and FakeClock usage documentation. Bootstrap injection is a separate later Story.",
            [
                "Clock exposes UTC wall time and monotonic elapsed time.",
                "SystemClock implements both readings using technical system APIs.",
                "FakeClock advances wall and monotonic readings deterministically with Duration.",
                "FakeClock behavior tests live under tests/unit/fakes/test_clock.py.",
                "No direct real-time acquisition is introduced in domain or application code.",
            ],
        ),
        588873: (
            "Implement Runtime State projections and in-memory state service",
            "One owner delivers Runtime-State-owned snapshots, inbound state contracts, the state-only StateBackend port, application service, in-memory adapter, and tests. Event transport remains a separate parallel Story.",
            [
                "Runtime State owns all projection DTOs.",
                "StateBackend has state operations only and no subscribe/event API.",
                "Application and in-memory adapter pass unit and contract tests.",
                "No foreign capability domain model is imported.",
            ],
        ),
        588885: (
            "Define Robot Abstraction command and driver contracts",
            "Define the minimum Robot-Abstraction-owned command types and stable inbound/outbound ports needed by the thin slice. Concrete ActionHandle and logging-driver implementation remain later Stories.",
            [
                "Generic command and result DTOs are Robot-Abstraction-owned.",
                "RobotDriver and application-facing ports are stable and vendor-neutral.",
                "No concrete adapter or vendor type appears in application or port code.",
            ],
        ),
        588893: (
            "Implement Robot Abstraction command service and logging RobotDriver",
            "Implement the Robot Abstraction application service and deterministic logging RobotDriver after command/driver and ActionHandle contracts are stable.",
            [
                "Application service depends only on ports.",
                "Logging driver records generic commands and returns deterministic ActionHandles.",
                "Canonical RobotDriver and cancellation contracts pass.",
            ],
        ),
    }
    for story_id, (title, description, criteria) in updates.items():
        wit.update_work_item(
            document=[
                JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
                JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(description)),
                JsonPatchOperation(
                    op="add", path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria", value=ac_to_html(criteria)
                ),
            ],
            id=story_id,
        )

    # Remove all dependency relations from canonical items, then add only Story links.
    nodes, children = fetch_tree(wit, 537616)
    framework_ids = descendants(children, EPICS)
    legacy_roots = {
        item_id for item_id in framework_ids if "Legacy Backlog" in (nodes[item_id].fields.get("System.Tags") or "")
    }
    framework_ids -= descendants(children, legacy_roots)
    for item_id in sorted(framework_ids):
        remove_all_dependencies(wit, item_id)

    for successor, predecessors in STORY_DEPENDENCIES.items():
        successor_id = created[successor] if isinstance(successor, str) else successor
        for predecessor in predecessors:
            predecessor_id = created[predecessor] if isinstance(predecessor, str) else predecessor
            add_dependency(wit, successor_id, predecessor_id)

    # Remove now-empty merged/split Stories.
    delete_ids = set(MERGES) | {589115}
    for story_id in sorted(delete_ids):
        story = wit.get_work_item(id=story_id, expand="Relations")
        remaining_children = [
            relation for relation in story.relations or [] if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        ]
        if remaining_children:
            raise RuntimeError(f"Cannot delete Story #{story_id}; children remain")
        wit.delete_work_item(id=story_id, destroy=False)
        print(f"[DELETE STORY] #{story_id}")

    nodes, children = fetch_tree(wit, 537616)
    framework_ids = descendants(children, EPICS)
    normalize_tags_and_iterations(wit, framework_ids, children)

    print(
        f"Applied {len(STORY_WAVES)} executable Story Waves, consolidated {len(MERGES) + 1} Stories, "
        f"and added {sum(map(len, STORY_DEPENDENCIES.values()))} critical Story dependencies."
    )


if __name__ == "__main__":
    main()
