"""Resolve the remaining ADO architecture, hierarchy, and scheduling drift."""

from __future__ import annotations

from typing import Any

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql

from ado_client import AdoConfig, get_clients
from create_items import ac_to_html, to_html
from engagement_tree import fetch_tree


ROOT_ITERATION = "graiteam"


def relation_value(relation_type: str, target_url: str, name: str) -> dict[str, Any]:
    return {"rel": relation_type, "url": target_url, "attributes": {"name": name}}


def update_fields(
    wit: Any,
    item_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    acceptance_criteria: list[str] | None = None,
) -> None:
    patch: list[JsonPatchOperation] = []
    if title is not None:
        patch.append(JsonPatchOperation(op="add", path="/fields/System.Title", value=title))
    if description is not None:
        patch.append(JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(description)))
    if acceptance_criteria is not None:
        patch.append(
            JsonPatchOperation(
                op="add",
                path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                value=ac_to_html(acceptance_criteria),
            )
        )
    if patch:
        wit.update_work_item(document=patch, id=item_id)
        print(f"[FIELDS] #{item_id}")


def set_phase_tags(
    wit: Any,
    item_id: int,
    *,
    add: set[str] | None = None,
    remove_prefixes: tuple[str, ...] = (),
) -> None:
    item = wit.get_work_item(id=item_id)
    existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
    desired = [tag for tag in existing if not tag.startswith(remove_prefixes)]
    for tag in sorted(add or set()):
        if tag not in desired:
            desired.append(tag)
    if desired != existing:
        wit.update_work_item(
            document=[JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(desired))],
            id=item_id,
        )
        print(f"[TAGS] #{item_id}: {'; '.join(desired)}")


def defer_item(wit: Any, item_id: int) -> None:
    item = wit.get_work_item(id=item_id)
    existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
    desired = [
        tag
        for tag in existing
        if not tag.lower().startswith("wave ")
        and not tag.startswith("Implementation Wave ")
        and not tag.startswith("Exit Gate ")
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
        print(f"[DEFER] #{item_id}")


def create_or_get_story(
    wit: Any,
    cfg: AdoConfig,
    *,
    parent_id: int,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    tags: set[str],
) -> int:
    escaped = title.replace("'", "''")
    query = Wiql(
        query=f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "
        f"AND [System.WorkItemType] = 'User Story' AND [System.Title] = '{escaped}'"
    )
    result = wit.query_by_wiql(wiql=query)
    if result.work_items:
        story_id = result.work_items[0].id
        update_fields(
            wit,
            story_id,
            description=description,
            acceptance_criteria=acceptance_criteria,
        )
        set_phase_tags(wit, story_id, add=tags)
        return story_id

    parent = wit.get_work_item(id=parent_id)
    patch = [
        JsonPatchOperation(op="add", path="/fields/System.Title", value=title),
        JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(description)),
        JsonPatchOperation(
            op="add",
            path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
            value=ac_to_html(acceptance_criteria),
        ),
        JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=parent.fields.get("System.AreaPath")),
        JsonPatchOperation(
            op="add", path="/fields/System.IterationPath", value=parent.fields.get("System.IterationPath")
        ),
        JsonPatchOperation(op="add", path="/fields/System.Tags", value="; ".join(sorted(tags))),
        JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Scheduling.StoryPoints", value=1),
        JsonPatchOperation(op="add", path="/fields/Microsoft.VSTS.Common.ValueArea", value="Architectural"),
        JsonPatchOperation(
            op="add",
            path="/relations/-",
            value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent.url, "Parent"),
        ),
    ]
    story = wit.create_work_item(document=patch, project=cfg.project, type="User Story")
    print(f"[CREATE] #{story.id} {title}")
    return story.id


def move_item(wit: Any, item_id: int, parent_id: int) -> None:
    item = wit.get_work_item(id=item_id, expand="Relations")
    parent = wit.get_work_item(id=parent_id)
    parent_relation = next(
        (
            (index, relation)
            for index, relation in enumerate(item.relations or [])
            if relation.rel == "System.LinkTypes.Hierarchy-Reverse"
        ),
        None,
    )
    if parent_relation is not None and parent_relation[1].url.rstrip("/").endswith(f"/{parent_id}"):
        return
    patch: list[JsonPatchOperation] = []
    if parent_relation is not None:
        patch.append(JsonPatchOperation(op="remove", path=f"/relations/{parent_relation[0]}"))
    patch.append(
        JsonPatchOperation(
            op="add",
            path="/relations/-",
            value=relation_value("System.LinkTypes.Hierarchy-Reverse", parent.url, "Parent"),
        )
    )
    wit.update_work_item(document=patch, id=item_id)
    print(f"[MOVE] #{item_id} -> #{parent_id}")


def add_predecessor(wit: Any, item_id: int, predecessor_id: int) -> None:
    item = wit.get_work_item(id=item_id, expand="Relations")
    if any(
        relation.rel == "System.LinkTypes.Dependency-Reverse"
        and relation.url.rstrip("/").endswith(f"/{predecessor_id}")
        for relation in item.relations or []
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
        id=item_id,
    )


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)

    # Operator Interface: transports -> inbound use cases -> outbound provider ports -> bridges.
    update_fields(
        wit,
        588940,
        title="Operator Interface use cases, provider ports, and contract mapping",
        description=(
            "Define the transport-neutral Operator Interface boundary. HTTP, CLI, and MCP adapters call Operator "
            "Interface inbound use cases. Those use cases depend on Operator-Interface-owned outbound provider ports "
            "for Mission Planning, Mission Execution, Runtime State, and Fleet Coordination. Consumer-owned bridge "
            "adapters translate those contracts to provider-owned inbound ports."
        ),
        acceptance_criteria=[
            "Inbound ports exist for SubmitMission, ViewMissionStatus, AbortMission, and ViewFleet.",
            "Outbound provider ports exist for Mission Planning submission, Runtime State status reads, Mission Execution abort, and Fleet reads.",
            "Every port owns transport-neutral DTOs and typed failure semantics.",
            "Application services depend only on Operator Interface ports.",
            "HTTP, CLI, and MCP schemas and mappers remain inside their inbound adapters.",
            "Cross-capability imports occur only in Operator Interface outbound bridge adapters and target provider inbound ports.",
        ],
    )
    update_fields(
        wit,
        588941,
        title="Define Operator Interface inbound use cases and outbound provider contracts",
        description=(
            "Define separate Operator Interface inbound contracts called by transports and outbound provider contracts "
            "called by application use cases: transport -> inbound port -> use case -> outbound provider port -> bridge -> provider inbound port."
        ),
        acceptance_criteria=[
            "Inbound contracts cover SubmitMission, ViewMissionStatus, and AbortMission.",
            "Outbound contracts cover submission to Mission Planning, status reads from Runtime State, and abort through Mission Execution.",
            "Commands, queries, results, views, and errors use explicit semantic names.",
            "DTOs are immutable, transport-neutral, and port-owned.",
            "Unit tests use outbound-port fakes.",
        ],
    )
    update_fields(
        wit,
        588942,
        title="Define Operator Interface ports, DTOs, and errors",
        description="Define the inbound use-case and outbound provider contracts with immutable port-owned DTOs and explicit failure semantics.",
        acceptance_criteria=[
            "Contracts live under operator_interface/ports/inbound and operator_interface/ports/outbound.",
            "No HTTP, CLI, Pydantic, or provider implementation types appear in the contracts.",
            "Shared identifiers are imported from shared_kernel.",
            "Read repeatability and abort idempotency semantics are explicit.",
        ],
    )
    update_fields(
        wit,
        588943,
        title="Implement Operator Interface use cases and contract mapping tests",
        description="Implement transport-neutral application use cases that map inbound requests to injected outbound provider contracts and map provider results to Operator Interface responses.",
        acceptance_criteria=[
            "Each use case receives its outbound port through constructor injection.",
            "No concrete adapter is instantiated or imported.",
            "Unit tests cover successful and failed provider results using fakes.",
            "Transport-specific mapping remains in each inbound adapter.",
        ],
    )
    update_fields(
        wit,
        588944,
        title="Implement Operator Interface provider bridge adapters",
        description="Implement consumer-owned bridges from Operator Interface outbound ports to Mission Planning, Mission Execution, and Runtime State inbound ports.",
        acceptance_criteria=[
            "Each bridge imports only its Operator Interface outbound contract and the provider inbound contract it connects.",
            "Bridges translate requests, responses, and errors without business decisions.",
            "Bootstrap performs all concrete wiring.",
            "Bridge contract tests live under tests/contract/module_bridges.",
        ],
    )
    update_fields(wit, 588945, title="Implement Mission Planning submission bridge")
    update_fields(wit, 588946, title="Implement Mission Execution abort bridge")
    update_fields(wit, 588947, title="Implement Runtime State mission-status bridge")
    update_fields(wit, 588948, title="Add Operator Interface bridge contract tests")
    update_fields(
        wit,
        588951,
        title="Operator Interface CLI inbound adapter",
        description="Provide submit, status, and abort commands that parse CLI input, call only Operator Interface inbound ports, and render results.",
        acceptance_criteria=[
            "Commands call only Operator Interface inbound ports.",
            "No cross-capability imports or business logic exist in the CLI.",
            "Failures use stable documented non-zero exit codes and useful stderr messages.",
            "Bootstrap assembles the CLI and its dependencies.",
        ],
    )
    update_fields(
        wit,
        588953,
        title="Implement CLI submit, status, and abort commands",
        acceptance_criteria=[
            "Submit returns a MissionId through the Operator Interface inbound port.",
            "Status renders the Operator Interface mission-status view.",
            "Abort reports accepted, already aborted, not found, or rejected outcomes.",
            "Unit tests use fake Operator Interface inbound ports.",
            "An end-to-end test enters through the bootstrap-composed CLI.",
        ],
    )
    update_fields(
        wit,
        588959,
        title="Operator Interface HTTP inbound adapter",
        description="Expose FastAPI routes for Operator Interface inbound use cases. HTTP schemas and mappers are adapter-local; Bootstrap mounts and launches the application but owns no routes.",
        acceptance_criteria=[
            "Routes include POST /missions, GET /missions/{mission_id}, and POST /missions/{mission_id}/abort.",
            "Routes call only Operator Interface inbound ports.",
            "Pydantic schemas are not port DTOs or domain entities.",
            "Typed failures map to stable HTTP status codes without leaking implementation details.",
            "Correlation IDs use request/response metadata and do not depend on a shared EventEnvelope.",
            "OpenAPI and route behavior are tested with an in-process client.",
        ],
    )
    update_fields(
        wit,
        588961,
        title="Implement FastAPI routes, schemas, and transport mapping",
        description="Implement mission HTTP routes under the Operator Interface inbound adapter and map HTTP schemas to Operator Interface inbound DTOs.",
        acceptance_criteria=[
            "Routes delegate to SubmitMission, ViewMissionStatus, and AbortMission inbound ports.",
            "Request validation is distinct from application/domain validation.",
            "HTTP schemas and mappers remain inside the HTTP adapter.",
            "Typed error-to-status and correlation-header behavior are tested.",
            "No shared EventEnvelope is referenced.",
            "Uvicorn startup and route mounting remain Bootstrap responsibilities.",
        ],
    )
    update_fields(
        wit,
        589115,
        title="Operator Interface ViewFleet use case and Fleet provider bridge",
        description=(
            "Add an Operator Interface ViewFleet inbound query. Its application use case calls an Operator-Interface-owned "
            "outbound Fleet query port, and a consumer-owned bridge translates to Fleet Coordination's inbound read port. "
            "The HTTP adapter exposes the view as GET /fleet."
        ),
        acceptance_criteria=[
            "Operator Interface owns ViewFleet and its operator-facing view DTO.",
            "Operator Interface owns the outbound Fleet query port.",
            "Fleet Coordination owns provider projection semantics and its inbound read contract.",
            "GET /fleet calls ViewFleet, not Fleet Coordination directly.",
            "Bridge and HTTP tests cover success, empty fleet, provider failure, and stale projection.",
            "No Runtime State backend or event transport is accessed by Operator Interface.",
        ],
    )
    update_fields(
        wit,
        589116,
        title="Define ViewFleet inbound use case and outbound Fleet query contract",
        description="Define Operator Interface inbound ViewFleet and outbound ReadFleet contracts, independently owned DTOs/errors, and the application use case connecting them.",
        acceptance_criteria=[
            "ViewFleet is under operator_interface/ports/inbound.",
            "ReadFleet is under operator_interface/ports/outbound.",
            "The application service receives ReadFleet by constructor injection.",
            "DTOs expose only the operator-required fleet view and import no Fleet internals.",
            "Unit tests use a fake ReadFleet port.",
        ],
    )
    for item_id in (589115, 589116, 589117, 589118):
        set_phase_tags(wit, item_id, add={"Implementation Wave 8", "Implementation Wave 9"})
    move_item(wit, 589118, 588961)

    # Fleet, Runtime State, and Mission Execution boundaries.
    update_fields(
        wit,
        589108,
        description=(
            "Provide Fleet-owned projections and provider inbound read APIs. Reservation truth remains in Fleet. Runtime "
            "context is obtained through Fleet-owned outbound ports and bridges to typed Runtime State inbound contracts; "
            "optional event-triggered refresh uses Fleet inbound event adapters, never Runtime State private ports."
        ),
        acceptance_criteria=[
            "Fleet owns projection DTOs, reservation truth, and provider inbound read contracts.",
            "Runtime context is read through Fleet-owned outbound ports and bridges.",
            "Event-triggered refresh maps supported wire schemas into Fleet-owned inbound DTOs.",
            "No Fleet code imports StateBackend, TransportEnvelope, Runtime State outbound ports, or concrete adapters.",
            "Operator Interface consumes Fleet through its own outbound query port and bridge.",
        ],
    )
    update_fields(
        wit,
        589109,
        title="Per-robot occupancy and reservation read projection",
        description=(
            "Implement a Fleet-owned read projection for per-robot occupancy and reservation status. Runtime context is "
            "obtained through Fleet-owned outbound query ports and bridges. Events may trigger refreshes but are not the "
            "source of truth and never expose Runtime State private transport/backend contracts."
        ),
        acceptance_criteria=[
            "Projection DTO and updater are Fleet-owned.",
            "Reservation state comes from Fleet-owned domain/repository boundaries.",
            "Runtime context uses Fleet-owned outbound ports and Runtime State inbound contracts.",
            "Event-triggered refresh uses a Fleet inbound adapter and Fleet-owned DTO.",
            "Duplicate delivery does not duplicate projection effects; stale revisions cannot overwrite newer state.",
            "No StateBackend, TransportEnvelope, Runtime State outbound port, or concrete adapter is imported.",
        ],
    )
    update_fields(
        wit,
        589112,
        title="Implement Fleet event-consumer adapter and subscription wiring",
        description=(
            "Implement a Fleet-owned inbound event adapter that validates supported producer wire schemas, maps them to "
            "Fleet-owned inbound DTOs, and invokes projection refresh. Bootstrap registers subscriptions with the selected "
            "transport; Fleet never imports Runtime State's private event-transport port or StateBackend."
        ),
        acceptance_criteria=[
            "Adapter lives under fleet_coordination/adapters/inbound/events.",
            "Supported event types and schema versions are explicit.",
            "Duplicate message delivery produces at most one projection effect per consumer.",
            "Bootstrap owns subscription registration, unsubscription, and shutdown wiring.",
            "No producer publication DTO, Runtime State TransportEnvelope, StateBackend, or Runtime State outbound port is imported.",
            "Contract tests verify canonical wire examples and Fleet DTO mapping.",
        ],
    )
    update_fields(
        wit,
        589133,
        title="Runtime State event-transport backpressure and per-stream ordering",
        description=(
            "Define bounded buffering, overload behavior, consumer isolation, and per-stream ordering for Runtime State's "
            "private event transport. StateBackend remains state-only and has no subscribe or FIFO-subscription API."
        ),
        acceptance_criteria=[
            "Event-transport buffers are bounded and queue capacity is configurable.",
            "Slow consumers do not block unrelated consumer groups.",
            "Critical messages are never silently dropped; overload has explicit typed failure, retry, or dead-letter behavior.",
            "Non-critical telemetry may be coalesced or sampled while preserving the newest valid revision.",
            "Ordering is FIFO only within a declared stream or aggregate, not globally.",
            "Duplicate delivery remains possible and consumers remain idempotent.",
            "Shutdown, cancellation, and queued-message disposition are explicit and tested.",
            "StateBackend has typed state operations only and no subscription API.",
        ],
    )
    defer_item(wit, 589133)
    add_predecessor(wit, 589133, 589131)
    update_fields(
        wit,
        588926,
        description="Implement the Behavior Tree as a Mission Execution inbound adapter using typed application and outbound boundaries; no node accesses Blackboard or provider internals.",
        acceptance_criteria=[
            "Nodes provide running, success, and failure control-flow semantics without owning execution lifecycle.",
            "Robot operations use Mission-Execution-owned outbound ports and bridges.",
            "Runtime reads/writes use typed Mission Execution outbound contracts and a Runtime State bridge.",
            "No Blackboard keys, StateBackend, Runtime State outbound ports, or concrete provider adapters are imported.",
        ],
    )
    update_fields(
        wit,
        588927,
        title="Tick loop with typed Runtime State access through Mission Execution bridge",
        description=(
            "Implement the Mission Execution tick loop against Mission-Execution-owned outbound Runtime State contracts. "
            "A bridge translates to Runtime State typed inbound projection contracts. Neither the BT adapter nor application "
            "code accesses Blackboard keys, StateBackend, or Runtime State adapters."
        ),
        acceptance_criteria=[
            "Tick loop is an inbound adapter calling Mission Execution inbound/application ports.",
            "Runtime reads and writes use Mission-Execution-owned outbound DTOs and a bridge to Runtime State inbound ports.",
            "One tick evaluates a coherent snapshot revision; concurrent updates appear on a later tick.",
            "Running actions are not redispatched on every tick.",
            "Missing, stale, and conflicting state returns typed outcomes.",
            "No Blackboard keys, StateBackend, Runtime State outbound ports, or concrete Runtime State adapters are imported.",
            "Unit tests use fakes and integration tests exercise the bridge against the in-memory Runtime State adapter.",
        ],
    )

    # Deferred contracts must remain internally correct even before activation.
    update_fields(
        wit,
        590813,
        title="Deferred World Model spatial primitives and transform query boundary",
        description=(
            "Deferred until a named consumer needs canonical cross-frame resolution, semantic target resolution, map "
            "registration, or transform history. World Model owns canonical spatial concepts and exposes transform lookup "
            "through an inbound query port. Consumers own outbound query ports and bridge adapters and never import World Model internals."
        ),
        acceptance_criteria=[
            "Feature remains Deferred, unscheduled, unassigned, and blocks no Robot Abstraction work.",
            "Activation requires a named consumer and approved use case.",
            "Frame and FramedPose remain outside shared_kernel.",
            "World Model exposes transform lookup through an inbound query port with World-Model-owned DTOs.",
            "Every consumer defines its own outbound query port and bridge.",
            "Request/result contracts define source frame, target frame, composition order, identity, validity, revision, and typed failures.",
            "Successful output is tagged with the requested target frame.",
            "Contract tests cover identity, inverse direction, chain composition, missing frame, cycles, and disconnected frames.",
            "Time-varying transforms, interpolation, and TF buffering remain deferred by ADR.",
        ],
    )
    update_fields(
        wit,
        590817,
        title="World Model inbound transform-query contract and identity implementation",
        description="When activated, define a World Model provider inbound transform-query port; consumers integrate through their own outbound ports and bridges.",
        acceptance_criteria=[
            "World Model owns an inbound query contract, not an outbound provider port.",
            "Identity behavior and frame direction are explicit.",
            "Consumer ports and DTOs remain consumer-owned.",
            "Implementation begins only after a named consumer activates the Feature.",
        ],
    )
    update_fields(
        wit,
        590818,
        title="Author World Model inbound transform-query Protocol",
        description="Define the deferred provider inbound transform query with World-Model-owned request, result, and typed failure DTOs.",
        acceptance_criteria=[
            "Protocol is under world_model/ports/inbound.",
            "Source and target frame direction and result frame are explicit.",
            "No consumer imports world_model domain or application classes.",
            "A consumer-owned outbound port and bridge are required for each integration.",
        ],
    )
    update_fields(
        wit,
        590908,
        title="Deferred Runtime State transport-message recorder",
        description=(
            "Optional Runtime State-private diagnostic/audit sink for accepted transport messages. It consumes a private "
            "transport record, uses at-least-once semantics, permits detectable duplicates by stable message_id, and is not "
            "an event store or replay mechanism."
        ),
        acceptance_criteria=[
            "Story remains Deferred until Runtime State publication and event-transport contracts are stable.",
            "Recorder port belongs to Runtime State and accepts a private transport record/message.",
            "No shared EventEnvelope or producer publication DTO is used.",
            "Acceptance and recording invocation points are defined precisely.",
            "Stable message identity, type/version, timestamps, producer, correlation, causation, and payload are preserved.",
            "Delivery is at-least-once; duplicate records are valid and detectable by message_id.",
            "Recorder failures return typed errors and transport policy defines retry or degradation behavior.",
            "JSONL order is append order only, not global causal order.",
            "Replay remains separately deferred.",
        ],
    )
    update_fields(
        wit,
        590909,
        title="Define recorder port for private Runtime State transport records",
        description="Define a Runtime-State-owned recorder contract over private transport records, with at-least-once and duplicate semantics.",
    )
    update_fields(
        wit,
        590910,
        title="Implement deferred JSONL transport-record adapter",
        description="After recorder semantics stabilize, append private transport records to JSONL through UPath with typed write and shutdown failures.",
    )
    update_fields(
        wit,
        590911,
        title="Contract test private transport recording semantics",
        description="Test successful append, retry with stable identity, detectable duplicate append, partial/write failure, and shutdown behavior under at-least-once semantics.",
    )

    # Correct hierarchy for direct Tasks under Features.
    reliability_story = create_or_get_story(
        wit,
        cfg,
        parent_id=589131,
        title="Event-transport delivery failure and dead-letter handling",
        description="Define observable typed behavior for accepted messages that cannot be delivered, including retry exhaustion and dead-letter handling owned by Runtime State transport reliability.",
        acceptance_criteria=[
            "Dead-letter handling belongs to Runtime State event transport, not Mission Execution or a shared EventBus.",
            "Original message identity, schema metadata, correlation, and causation are preserved.",
            "Retry exhaustion and dead-letter outcomes are typed and observable.",
            "Mission Execution only publishes through its outbound port.",
        ],
        tags={"Implementation Wave 6"},
    )
    ci_story = create_or_get_story(
        wit,
        cfg,
        parent_id=589177,
        title="Foundation baseline and repository hygiene",
        description="Record the verified post-foundation baseline and close repository hygiene gaps that can otherwise bypass the required CI checks.",
        acceptance_criteria=[
            "The verified main commit and test/type/import/format baseline are recorded.",
            "The known .importlinter whitespace defect is removed.",
            "CI or pre-commit runs git diff --check against committed changes.",
            "This Story owns Exit Gate 0 evidence; child Tasks do not carry Exit Gate tags.",
        ],
        tags={"Implementation Wave 0", "Exit Gate 0"},
    )
    move_item(wit, 590903, reliability_story)
    move_item(wit, 599235, ci_story)
    move_item(wit, 599236, ci_story)
    set_phase_tags(wit, 599236, remove_prefixes=("Exit Gate ",))

    # Scheduling and governance.
    defer_item(wit, 589136)
    set_phase_tags(wit, 589019, add={"Implementation Wave 9"})
    update_fields(
        wit,
        589144,
        title="Canonical contract-suite registry and governance",
        description="Deferred governance roll-up that links each stable port to its single capability-owned canonical contract suite; it creates no generic duplicate harness.",
        acceptance_criteria=[
            "Every listed port links to exactly one canonical suite and identifies its capability owner.",
            "Adapter Features link to the owner suite rather than creating another harness.",
            "No one-file registration convention or fake framework is imposed globally.",
            "Activate after multiple stable ports make a registry useful.",
        ],
    )
    defer_item(wit, 589144)
    update_fields(
        wit,
        589146,
        description="Implement only remaining enforceable architecture checks, beginning with port-DTO locality and diagnostics not already owned by targeted remediation Tasks.",
        acceptance_criteria=[
            "Do not duplicate delivered name-shadowing or adapter-isolation detectors.",
            "Port DTO locality checks report path, line, symbol/import, rule, and canonical documentation link.",
            "Rules reflect domain -> stdlib/shared_kernel only; domain never imports ports.",
            "Negative self-tests prove each new detector before repository-wide enforcement.",
        ],
    )
    set_phase_tags(wit, 589146, add={"Implementation Wave 1"})

    # Remove legacy lowercase wave tags across the engagement.
    nodes, _ = fetch_tree(wit, 537616)
    item_ids = sorted(nodes)
    fetched = []
    for start in range(0, len(item_ids), 200):
        fetched.extend(wit.get_work_items(ids=item_ids[start : start + 200]))
    for item in fetched:
        existing = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
        desired = [tag for tag in existing if not tag.lower().startswith("wave ")]
        if desired != existing:
            wit.update_work_item(
                document=[JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(desired))],
                id=item.id,
            )
            print(f"[LEGACY TAG] #{item.id}")

    # Canonical Clock/test names and end-to-end path in all affected live fields.
    replace_ids = [590828, 590832, 590834, 590835, 590863, 590867, 590895, 590904, 590907, 590913, 588934]
    for item in wit.get_work_items(ids=replace_ids):
        patch: list[JsonPatchOperation] = []
        for field_name, field_path in (
            ("System.Title", "/fields/System.Title"),
            ("System.Description", "/fields/System.Description"),
            ("Microsoft.VSTS.Common.AcceptanceCriteria", "/fields/Microsoft.VSTS.Common.AcceptanceCriteria"),
        ):
            value = item.fields.get(field_name)
            if not isinstance(value, str):
                continue
            replaced = (
                value.replace("WallClock", "SystemClock")
                .replace("FrozenClock", "FakeClock")
                .replace("tests/e2e/", "tests/end_to_end/")
            )
            if replaced != value:
                patch.append(JsonPatchOperation(op="replace", path=field_path, value=replaced))
        if patch:
            wit.update_work_item(document=patch, id=item.id)
            print(f"[TERMS] #{item.id}")

    print(f"Created/used hierarchy Stories: reliability #{reliability_story}, CI #{ci_story}")


if __name__ == "__main__":
    main()
