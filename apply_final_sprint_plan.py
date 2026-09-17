"""Apply the final Wave 0/1 and planner-to-BT sprint plan to ADO."""

from __future__ import annotations

from typing import Any

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import AdoConfig, get_clients
from create_items import ac_to_html, to_html


CURRENT_SPRINT = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1\\FY27Q1.2"
NEXT_SPRINT = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1\\FY27Q1.3"
QUARTER = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1"

CURRENT_TASKS = {
    590884,
    599232,
    599233,
    599234,
    599235,
    590830,
    590833,
    590836,
    590837,
    590887,
    590888,
    590889,
    590890,
    589180,
    589181,
    589190,
    589194,
    589198,
}

CURRENT_STORIES = {
    589178,  # Basic-Checks reliability/caching and fake-secret validation
    589182,  # Coverage/reproducible local command
    589193,  # Capability README completion
}

NEXT_TASKS = {
    # Runtime State
    588874,
    588875,
    588876,
    588877,
    588879,
    588880,
    588881,
    # Robot Abstraction
    588886,
    588891,
    588892,
    590892,
    590893,
    588894,
    590894,
    588896,
    590895,
    # Mission Planning
    588908,
    588909,
    588911,
    588912,
    588914,
    588915,
    # Mission Execution and BT
    588921,
    588923,
    588925,
    599243,
    599244,
    599245,
    588927,
    588928,
    588929,
    588931,
}

# Stories whose complete current child scope is committed to the next sprint.
NEXT_STORIES = {588873, 588878, 588885, 588893, 590891, 588907, 588910, 588920, 588926, 599242}
ROLLUP_FEATURES = {588872, 588883, 588906, 588916}

# Work previously placed in a sprint but explicitly excluded by the final plan.
UNSCHEDULE = {
    589131,  # Runtime State eventing feature
    588913,  # Real Fleet bridge; use a Planning-owned fake in this slice
    589146,  # Port-DTO locality activates when Wave 3 ports exist
}

# successor -> technical predecessors
DEPENDENCIES: dict[int, set[int]] = {
    # Current sprint
    590833: {590830},
    590836: {590830},
    590837: {590836},
    590888: {590887},
    590889: {590887},
    590890: {590887},
    # Runtime State
    588875: {588874},
    588881: {588879},
    588880: {588879},
    588876: {588875, 588879},
    588877: {588876},
    # Planning
    588909: {588908},
    588911: {588908},
    588912: {588908, 588911},
    588915: {588912},
    588914: {588876, 588912},
    # Robot Abstraction
    588891: {588886},
    590893: {590892},
    588892: {588891, 590893},
    588894: {588891, 590893},
    590894: {588894},
    588896: {590894},
    590895: {590836, 590894},
    # Mission Execution / BT
    588921: {588908},
    588923: {588921},
    599244: {599243},
    588925: {588923},
    588928: {588908, 588923},
    588927: {588876, 588925},
    599245: {588876, 599243},
    588929: {588892, 588925},
    588931: {588914, 588880, 588925, 588927, 588928, 588929, 588896, 599245},
}


def relation_value(relation_type: str, target_url: str, name: str) -> dict[str, Any]:
    return {"rel": relation_type, "url": target_url, "attributes": {"name": name}}


def create_or_get_story(
    wit: Any,
    cfg: AdoConfig,
    *,
    parent_id: int,
    title: str,
    description: str,
    wave: int,
) -> int:
    from azure.devops.v7_1.work_item_tracking.models import Wiql

    escaped = title.replace("'", "''")
    result = wit.query_by_wiql(
        wiql=Wiql(
            query=f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "
            f"AND [System.WorkItemType] = 'User Story' AND [System.Title] = '{escaped}'"
        )
    )
    if result.work_items:
        return result.work_items[0].id
    parent = wit.get_work_item(id=parent_id)
    story = wit.create_work_item(
        document=[
            JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
            JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(description)),
            JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=parent.fields.get("System.AreaPath")),
            JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=QUARTER),
            JsonPatchOperation(op="add", path="/fields/System.Tags", value=f"Implementation Wave {wave}"),
            JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Scheduling.StoryPoints", value=2),
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
    print(f"[CREATE] #{story.id} {title}")
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
    wit.update_work_item(document=patch, id=item_id)
    print(f"[MOVE] #{item_id} -> #{parent_id}")


def set_iteration(wit: Any, item_id: int, iteration: str) -> None:
    item = wit.get_work_item(id=item_id)
    if item.fields.get("System.IterationPath") == iteration:
        return
    wit.update_work_item(
        document=[JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=iteration)],
        id=item_id,
    )
    print(f"[ITERATION] #{item_id} -> {iteration.rsplit('\\', 1)[-1]}")


def add_dependency(wit: Any, successor_id: int, predecessor_id: int) -> None:
    successor = wit.get_work_item(id=successor_id, expand="Relations")
    exists = any(
        relation.rel == "System.LinkTypes.Dependency-Reverse"
        and relation.url.rstrip("/").endswith(f"/{predecessor_id}")
        for relation in successor.relations or []
    )
    if exists:
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


def remove_dependency(wit: Any, successor_id: int, predecessor_id: int) -> None:
    successor = wit.get_work_item(id=successor_id, expand="Relations")
    relation = next(
        (
            (index, relation)
            for index, relation in enumerate(successor.relations or [])
            if relation.rel == "System.LinkTypes.Dependency-Reverse"
            and relation.url.rstrip("/").endswith(f"/{predecessor_id}")
        ),
        None,
    )
    if relation is None:
        return
    wit.update_work_item(
        document=[JsonPatchOperation(op="remove", path=f"/relations/{relation[0]}")],
        id=successor_id,
    )
    print(f"[REMOVE DEPENDENCY] #{predecessor_id} =/> #{successor_id}")


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)

    telemetry_story = create_or_get_story(
        wit,
        cfg,
        parent_id=588883,
        title="Publish normalized robot telemetry to Runtime State",
        description="Future Wave 4 integration for normalized robot-state publication through a Robot-Abstraction-owned outbound port and bridge to Runtime State inbound contracts.",
        wave=4,
    )
    fleet_story = create_or_get_story(
        wit,
        cfg,
        parent_id=588906,
        title="Integrate Mission Planning with real Fleet Coordination",
        description="Replace the thin-slice Planning-owned Fleet fake with a consumer-owned bridge to Fleet Coordination's inbound eligibility and reservation contracts.",
        wave=5,
    )
    move_item(wit, 588895, telemetry_story)
    move_item(wit, 588913, fleet_story)
    move_item(wit, 588882, 588935)
    move_item(wit, 588898, 588935)

    for item_id in sorted(CURRENT_TASKS):
        set_iteration(wit, item_id, CURRENT_SPRINT)
    for item_id in sorted(CURRENT_STORIES):
        set_iteration(wit, item_id, CURRENT_SPRINT)
    for item_id in sorted(NEXT_TASKS | NEXT_STORIES):
        set_iteration(wit, item_id, NEXT_SPRINT)
    for item_id in sorted(ROLLUP_FEATURES):
        set_iteration(wit, item_id, QUARTER)
    for item_id in sorted(UNSCHEDULE):
        set_iteration(wit, item_id, QUARTER)

    # Port-DTO locality needs real Wave 3 ports; it is not an Exit Gate 1 blocker.
    architecture_feature = wit.get_work_item(id=589146)
    architecture_tags = [
        tag.strip() for tag in (architecture_feature.fields.get("System.Tags") or "").split(";") if tag.strip()
    ]
    architecture_tags = [
        tag
        for tag in architecture_tags
        if not tag.startswith("Implementation Wave ") and not tag.startswith("Exit Gate ")
    ]
    if "Deferred" not in architecture_tags:
        architecture_tags.append("Deferred")
    architecture_patch = [
        JsonPatchOperation(
            op="replace",
            path="/fields/System.Tags",
            value="; ".join(architecture_tags),
        )
    ]
    if architecture_feature.fields.get("System.AssignedTo") is not None:
        architecture_patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))
    wit.update_work_item(document=architecture_patch, id=589146)

    # Make the integration outcome explicit and testable.
    wit.update_work_item(
        document=[
            JsonPatchOperation(
                op="add",
                path="/fields/System.Title",
                value="Planner-to-BT integration with in-memory Runtime State and logging RobotDriver",
            ),
            JsonPatchOperation(
                op="add",
                path="/fields/System.Description",
                value=to_html(
                    "Add BT node unit tests and one deterministic integration test. The real fixture Planner publishes "
                    "a valid immutable Plan through the Planning Runtime State bridge; real Runtime State stores it in "
                    "the in-memory StateBackend; real Mission Execution/BT reads and executes it through the Robot "
                    "Abstraction bridge; the real logging RobotDriver records and completes the command. A Planning-owned "
                    "Fleet fake returns one eligible robot."
                ),
            ),
            JsonPatchOperation(
                op="add",
                path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                value=ac_to_html(
                    [
                        "Test lives under tests/integration and runs without network, database, broker, simulator, or hardware.",
                        "The real fixture Planner creates a deterministic valid Plan from one fixture Mission.",
                        "Planning and Mission Execution use their own outbound Runtime State ports and bridge adapters.",
                        "The real Runtime State service and in-memory StateBackend publish and retrieve current_plan.",
                        "The real Mission Execution service and BT execute the Plan without importing Mission Planning domain types.",
                        "The real Robot Abstraction service, bridge, and logging RobotDriver execute and record the generic command.",
                        "A Planning-owned Fleet outbound-port fake returns one deterministic eligible robot; no real Fleet service is required.",
                        "Execution reaches COMPLETED and the expected command is recorded exactly once.",
                        "The test uses FakeClock or deterministic handles and contains no wall-clock sleeps.",
                        "BT node unit tests cover running, success, failure, and no duplicate redispatch while running.",
                    ]
                ),
            ),
        ],
        id=588931,
    )

    # Make the excluded real Fleet bridge explicit so sprint scheduling cannot be misread.
    wit.update_work_item(
        document=[
            JsonPatchOperation(
                op="add",
                path="/fields/System.Description",
                value=to_html(
                    "Implement the real Mission-Planning-owned Fleet outbound port bridge to Fleet Coordination's inbound "
                    "port after the planner-to-BT thin slice. The FY27Q1.3 integration uses a Planning-owned Fleet fake."
                ),
            )
        ],
        id=588913,
    )

    # Align roll-up Stories with the minimal integration scope after future work was separated.
    wit.update_work_item(
        document=[
            JsonPatchOperation(
                op="add", path="/fields/System.Title", value="Implement logging RobotDriver for the thin slice"
            ),
            JsonPatchOperation(
                op="add",
                path="/fields/System.Description",
                value=to_html(
                    "Implement the zero-dependency logging RobotDriver with deterministic ActionHandle behavior and prove it through the canonical RobotDriver contract suite. Telemetry publication and Bootstrap wiring are separate future Stories."
                ),
            ),
            JsonPatchOperation(
                op="add",
                path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                value=ac_to_html(
                    [
                        "Logging RobotDriver records generic commands.",
                        "It returns deterministic synthetic ActionHandles.",
                        "The canonical RobotDriver and cancellation contract tests pass.",
                        "No Runtime State or Bootstrap responsibility is included.",
                    ]
                ),
            ),
        ],
        id=588893,
    )
    wit.update_work_item(
        document=[
            JsonPatchOperation(
                op="add", path="/fields/System.Title", value="SubmitMission port and fixture planner thin slice"
            ),
            JsonPatchOperation(
                op="add",
                path="/fields/System.Description",
                value=to_html(
                    "Deliver SubmitMission and a deterministic fixture planner. Unit tests use fakes for every outbound port; the integration slice uses a Planning-owned Fleet fake and the real Planning Runtime State bridge. Real Fleet integration is a separate Story."
                ),
            ),
            JsonPatchOperation(
                op="add",
                path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                value=ac_to_html(
                    [
                        "Fixture Mission produces a deterministic valid Plan.",
                        "Application tests use outbound-port fakes.",
                        "Integration publishes current_plan through the real Runtime State bridge.",
                        "A Planning-owned Fleet fake returns one eligible robot.",
                        "No cross-capability domain import exists.",
                    ]
                ),
            ),
        ],
        id=588910,
    )

    for successor_id, predecessor_ids in sorted(DEPENDENCIES.items()):
        for predecessor_id in sorted(predecessor_ids):
            add_dependency(wit, successor_id, predecessor_id)
    remove_dependency(wit, 588880, 588881)

    print(
        f"Applied {len(CURRENT_TASKS)} current-sprint Tasks, {len(CURRENT_STORIES)} current-sprint Stories, "
        f"{len(NEXT_TASKS)} next-sprint Tasks, {len(NEXT_STORIES)} next-sprint Stories, "
        f"0 next-sprint Features, and {sum(map(len, DEPENDENCIES.values()))} dependencies."
    )


if __name__ == "__main__":
    main()