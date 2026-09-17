"""Reconcile the robotics ADO backlog with the verified 2026-07-23 baseline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import requests
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql
from requests.auth import HTTPBasicAuth

from ado_client import AdoConfig, get_clients
from create_items import ac_to_html, to_html


BASELINE = "29b16f320c4de17eaf8deb3926e7e64c4a79cd56"
ROOT_ITERATION = "graiteam"
CLOSING_ASSIGNEE = "Marianna Tzortzi"


def task_description(scope: str, criteria: list[str]) -> str:
    return f"{scope}\n\nAcceptance criteria:\n" + "\n".join(f"- {item}" for item in criteria)


@dataclass(frozen=True)
class Update:
    title: str | None = None
    state: str | None = None
    description: str | None = None
    acceptance_criteria: list[str] | None = None
    deferred: bool = False
    clear_assignee: bool = False


UPDATES: dict[int, Update] = {
    581343: Update(
        description=(
            "Define the six universal identifier NewTypes used across capabilities: RobotId, MissionId, ActionId, "
            "CommandId, CorrelationId, and CausationId. NewType provides static distinction with no runtime wrapper. "
            "Factories validate arguments; generators create UUID4 values. Correlation and causation are metadata "
            "identifiers, not evidence for a shared EventEnvelope."
        ),
        acceptance_criteria=[
            "shared_kernel/identifiers.py defines all six identifier NewTypes.",
            "Identifier values are immutable and hashable.",
            "Wrong argument types raise builtin TypeError with useful messages.",
            "Empty or whitespace-only strings raise builtin ValueError with useful messages.",
            "Type distinction is statically enforced by mypy; NewType values compare as wrapped strings at runtime.",
            "All six generators exist, including generate_robot_id(), and produce UUID4 values by default.",
            "Deterministic tests inject a UUID factory or construct explicit values; no unused override parameter is added.",
            "The package-root versus module-only helper export surface is documented.",
            "A committed static test proves RobotId cannot be passed where MissionId is required.",
            "Tests cover construction, equality, hashing, exception classes, and representative messages.",
            "No identifier is defined outside shared_kernel.",
        ],
    ),
    581357: Update(
        state="Closed",
        description=(
            "Implement the merged AST scan that rejects capability definitions shadowing CANON-1 shared-kernel "
            "primitives: RobotId, MissionId, ActionId, CommandId, CorrelationId, CausationId, Timestamp, Duration, "
            "Percentage, Result, SkynetError, and its shared subclasses. Ok, Err, and EventEnvelope are intentionally "
            "not reserved names. Delivered by PR #15 / commit 29b16f3; richer diagnostics are tracked separately."
        ),
    ),
    581490: Update(state="Active"),
    581491: Update(state="Closed"),
    581493: Update(state="Closed"),
    590883: Update(state="Closed"),
    590884: Update(
        state="Active",
        description=(
            "Complete the remaining governance gap in docs/adr/0001-use-newtype-for-minimal-si-units.md. The SI "
            "primitives are already merged and must not be reimplemented."
        ),
        acceptance_criteria=[
            "Add the mandatory Alternatives Considered and Related Documents sections required by docs/00.",
            "Record that validating factories use builtin TypeError and ValueError.",
            "Clarify that normalized Radians[-pi, pi] represents orientation angles.",
            "Record that a concrete multi-turn-joint consumer may require a separately owned type or revised semantics.",
            "Merge the documentation-only change with green checks.",
        ],
    ),
    590885: Update(state="Closed"),
    581347: Update(
        description=(
            "Own Timestamp, Duration, and Percentage as universal immutable value objects. Percentage uses the "
            "canonical ratio representation 0.0..1.0; from_percent() and as_percent() convert presentation-scale "
            "values. Timestamp is UTC-aware and direct real-time acquisition is restricted to clocks and adapters."
        ),
        acceptance_criteria=[
            "Timestamp rejects timezone-naive datetimes.",
            "Duration rejects negative and non-finite values.",
            "Percentage rejects values outside 0.0..1.0 and supports from_percent() and as_percent().",
            "All three values are immutable, hashable, ordered, and covered by unit tests.",
        ],
    ),
    581349: Update(
        description=(
            "Implement immutable Duration and canonical ratio-based Percentage values. Percentage is bounded to "
            "0.0..1.0; from_percent() and as_percent() provide presentation-scale conversion."
        )
    ),
    590828: Update(state="Active"),
    590829: Update(state="Active"),
    590830: Update(
        state="Active",
        description="Complete the existing Clock Protocol and package export. now() exists; monotonic() -> Duration remains.",
    ),
    590831: Update(
        title="Architecture rule against direct real-time acquisition",
        state="Closed",
        description=(
            "Delivered as an AST architecture test, not an import-linter contract. It rejects direct datetime.now(), "
            "datetime.utcnow(), time.time(), time.monotonic(), and Timestamp.now() acquisition in domain/application code."
        ),
    ),
    590832: Update(
        title="SystemClock adapter in bootstrap",
        state="Active",
        description=(
            "Complete the existing SystemClock implementation of Clock. It provides UTC wall time and monotonic elapsed "
            "time and is later injected by Bootstrap into services that need time."
        ),
    ),
    590833: Update(
        title="SystemClock wall/monotonic implementation + unit tests",
        state="Active",
        description="Extend the existing SystemClock: wall time exists; monotonic() using time.monotonic() and tests remain.",
    ),
    590835: Update(
        title="FakeClock deterministic test double",
        state="Active",
        description=(
            "Complete the existing test-only FakeClock. It exposes deterministic wall and monotonic readings and advances "
            "both explicitly using Duration."
        ),
    ),
    590836: Update(
        title="Complete FakeClock implementation",
        state="Active",
        description=(
            "Extend tests/fakes/clock.py with monotonic reading and Duration-based advancement while preserving the "
            "existing wall-time behavior."
        ),
    ),
    590837: Update(
        description="Publish and document the canonical test helper at tests/fakes/clock.py. Keep production test doubles out of src/."
    ),
    590838: Update(
        description=(
            "Deferred until a simulation harness requires accelerated, pausable, or rewindable time. Activation requires "
            "a concrete simulator consumer and approved semantics."
        ),
        deferred=True,
        clear_assignee=True,
    ),
    590886: Update(state="Active"),
    590890: Update(
        description=(
            "Enforce that domain/application code cannot acquire global randomness directly. Use an AST architecture rule "
            "when call-level detection is required; ordinary import-linter cannot inspect calls. Adapters, Bootstrap, and "
            "tests are the only permitted technical acquisition sites."
        )
    ),
    589177: Update(state="Active"),
    589178: Update(state="Active"),
    589179: Update(state="Closed"),
    589180: Update(title="Refresh pinned hooks and add uv/pre-commit cache"),
    589182: Update(state="Active"),
    589185: Update(state="Closed"),
    589191: Update(state="Closed"),
    589192: Update(state="Active"),
    589193: Update(state="Active"),
    589195: Update(state="Closed"),
    589197: Update(state="Closed"),
    589131: Update(
        title="Runtime State event publication and private transport ownership",
        description=(
            "Define event publication through Runtime State without a cross-capability EventEnvelope. Producers own their "
            "publication DTOs and versioned wire schemas. Runtime State accepts publication requests and privately maps "
            "them to TransportEnvelope for its event-transport port. Consumers validate supported versions and map into "
            "consumer-owned inbound DTOs. CorrelationId and CausationId remain shared identifiers."
        ),
        acceptance_criteria=[
            "No shared_kernel/envelope.py or shared generic EventEnvelope exists.",
            "Producer capabilities own payloads and versioned wire schemas.",
            "Runtime State exposes an inbound event-publication Protocol with a port-owned request DTO.",
            "Runtime State privately owns TransportEnvelope and the outbound event-transport Protocol.",
            "Consumer adapters reject unsupported versions and map supported messages into consumer-owned DTOs.",
            "Correlation and causation propagate across publication and consumption.",
            "In-memory transport defines subscription, unsubscription, shutdown, and delivery semantics.",
            "Producer, transport, and consumer compatibility contracts are tested.",
        ],
    ),
    578700: Update(
        title="Define Runtime State inbound publication request and private event-transport port",
        description=(
            "Define separate Runtime State inbound publication and private outbound transport contracts. Runtime State "
            "maps producer-owned versioned wire data and metadata into a private TransportEnvelope. Neither contract is "
            "exported through shared_kernel."
        ),
    ),
    591737: Update(
        title="Event publication and compatibility contract tests",
        description=(
            "Replace shared-envelope unit tests with producer wire-schema validation, Runtime State private-envelope "
            "mapping, metadata propagation, supported-version mapping, and deterministic unsupported-version rejection."
        ),
    ),
    590908: Update(
        description=(
            "Deferred until event-transport contracts and delivery semantics are approved. Record accepted private Runtime "
            "State transport messages through a Runtime-State-owned or explicitly approved observability boundary; never "
            "consume a shared EventEnvelope."
        ),
        deferred=True,
    ),
    590909: Update(
        title="Author EventRecorder port for private transport records",
        description="Define a recorder port over private transport records/messages, not a shared EventEnvelope.",
        deferred=True,
    ),
    590910: Update(
        description="Deferred JSONL/UPath adapter; activate after recorder ownership, lifecycle, delivery, and duplicate semantics are stable.",
        deferred=True,
    ),
    590911: Update(
        title="Contract test: every accepted transport message recorded with defined delivery semantics",
        description=(
            "Test the approved at-most-once or at-least-once recorder contract. Do not claim exactly-once until idempotency "
            "and deduplication are implemented. Preserve correlation and payload metadata and define duplicate/failure behavior."
        ),
        deferred=True,
    ),
    588872: Update(
        description=(
            "Deliver Runtime State projections through inbound contracts backed by a state-only StateBackend. Event "
            "publication uses Feature #589131. Blackboard state storage and event transport are separate private outbound ports."
        ),
        acceptance_criteria=[
            "Inbound contracts cover current_plan, robot_state, action_state, fleet_decision, and replan_state.",
            "event_publication is added when eventing is enabled.",
            "StateBackend contains state operations only and has no subscribe API.",
            "Event publication uses a separate private event-transport port.",
            "State and event adapters pass separate contract suites.",
            "Other capabilities use Runtime State inbound ports through consumer-owned bridges.",
        ],
    ),
    588873: Update(
        description=(
            "Define Runtime State inbound Protocols and projection-owned DTOs for current plan, robot state, action state, "
            "fleet decisions, replanning state, and event publication when enabled. Do not copy or import foreign domain models."
        )
    ),
    588874: Update(
        description="Define immutable Runtime-State-owned Plan, Robot, Action, Fleet, and Replan projection snapshots; import no foreign domain models."
    ),
    588875: Update(
        description="Define current_plan, robot_state, action_state, fleet_decision, replan_state, and conditional event_publication inbound contracts with port-owned DTOs and typed Results."
    ),
    588876: Update(
        description="Fan state updates only to the injected StateBackend; route event publication independently through the event-transport port."
    ),
    588877: Update(
        description="Test state behavior with a fake StateBackend and event publication independently with a fake event transport."
    ),
    588878: Update(
        description="Define the state-only StateBackend outbound Protocol and dict-backed in-memory adapter. Event subscription/publication belongs to Feature #589131.",
        acceptance_criteria=[
            "Protocol provides typed get, put, and delete or equivalent state operations.",
            "No subscribe or event API exists.",
            "In-memory adapter stores only state projections.",
            "Reusable contract tests cover state semantics.",
            "Bootstrap wiring waits for minimal composition.",
        ],
    ),
    588879: Update(
        description="Define typed state get/put/delete operations and explicitly exclude subscribe; specify missing-key and failure behavior."
    ),
    588880: Update(
        description="Implement dict-backed state storage only; pass the state contract suite and provide no observer/event behavior."
    ),
    588881: Update(
        description="Create the canonical state-only StateBackend contract suite; event transport has a separate suite."
    ),
    588882: Update(
        description="After minimal Bootstrap exists, wire state and event adapters separately in bootstrap/wiring/runtime_state.py."
    ),
    581477: Update(
        description="Provide the reusable side-effect-free Bootstrap composition API through compose.py and container.py. Container exposes inbound ports/services, never concrete adapters.",
        acceptance_criteria=[
            "compose(settings: Settings) -> Container is defined.",
            "Container exposes port-typed services, not concrete adapters.",
            "Composition is deterministic and side-effect-free.",
            "The first concrete composition is Runtime State, not an invented fake service.",
            "Unit tests verify wiring without concrete leaks.",
        ],
    ),
    581478: Update(
        description="Add only missing src/bootstrap/compose.py and src/bootstrap/container.py around the existing package and define the minimal public composition API."
    ),
    581479: Update(
        title="Compose the first real Runtime State slice",
        description="After Runtime State exists, compose its real service and adapters through ports. Do not invent a fake production application service solely to demonstrate Bootstrap.",
    ),
    581481: Update(
        description="Define the sole Settings hierarchy in src/bootstrap/settings.py using pydantic-settings. Add settings only for adapters that actually exist.",
        acceptance_criteria=[
            "Canonical module is src/bootstrap/settings.py.",
            "Top-level Settings composes only currently required sub-settings.",
            "Required values fail fast with clear validation errors.",
            ".env.dev.example contains placeholders only for supported settings.",
            "Tests cover valid, missing, and malformed values.",
        ],
    ),
    581482: Update(
        description="Create the top-level Settings class in src/bootstrap/settings.py using pydantic-settings."
    ),
    581483: Update(
        description="Add only sub-settings required by implemented adapters; do not predefine Redis, vendor, or other speculative settings."
    ),
    581484: Update(
        description="List only currently supported settings with safe placeholders and comments; include no real secrets."
    ),
    581485: Update(
        description="Add tests/unit/bootstrap/test_settings.py covering valid, missing, and malformed settings."
    ),
    581488: Update(
        description="Implement the first factory only when a real port and real alternative adapter exist; do not add a speculative NotImplementedError branch."
    ),
    588935: Update(
        description="Compose the complete thin slice through the reusable composition and Settings APIs, expose inbound ports, and verify it at the canonical end-to-end test location.",
        acceptance_criteria=[
            "compose(settings) wires all slice services through ports.",
            "No concrete adapter leaks from Container.",
            "tests/end_to_end/test_thin_slice.py completes under five seconds.",
            "README documents the canonical execution command.",
        ],
    ),
    588937: Update(title="Add tests/end_to_end/test_thin_slice.py"),
    590896: Update(
        title="Planning lifecycle aggregate with guarded transitions",
        description="Model only RECEIVED, PLANNING, PLANNED, and planning failure. Mission Execution owns execution lifecycle; Plan remains immutable and has no execution status.",
        acceptance_criteria=[
            "Mission Planning owns an explicit planning-state enum.",
            "Legal and illegal planning transitions are guard checked and fully tested.",
            "Illegal transitions use a planning-owned typed error.",
            "Planner publishes an immutable planning outcome/projection.",
            "Plan contains no execution lifecycle state.",
        ],
    ),
    590897: Update(
        title="PlanningStatus enum + guard predicates",
        description="Define PlanningStatus and guards for received, planning, planned, and planning-failed transitions; include no execution states.",
    ),
    590898: Update(
        description="Add a parametrized matrix covering every legal and illegal transition in the planning-only state machine."
    ),
    590899: Update(
        title="Publish planning outcome from MissionPlanner",
        description="Publish a planning outcome or Runtime State projection on success/failure; do not add mutable execution status to Plan.",
    ),
    588974: Update(
        description=(
            "Define a cohesive vendor-agnostic RobotDriver contract based on generic typed commands. execute(command) "
            "returns ActionHandle for long-running work; stop/cancellation is typed and asynchronous. Affordances advertise "
            "support, unsupported commands return a typed result, and adapters translate vendor SDK operations."
        ),
        acceptance_criteria=[
            "RobotDriver exposes generic execute and stop/cancellation operations.",
            "Long-running commands return ActionHandle.",
            "Commands/results are Robot-Abstraction-port-owned DTOs.",
            "Unsupported commands return UNSUPPORTED_OPERATION or an equivalent typed error.",
            "Affordance manifests identify supported command variants.",
            "No vendor SDK or vendor-specific verb appears in the port.",
            "Adapters satisfy the canonical RobotDriver contract suite.",
        ],
    ),
    588975: Update(
        title="Define generic locomotion/navigation commands and driver DTOs",
        description="Define port-owned generic locomotion/navigation variants submitted through RobotDriver.execute, with explicit Robot-Abstraction-owned frame semantics and affordances.",
    ),
    588976: Update(
        title="Define generic locomotion command variants",
        description="Define immutable typed locomotion variants consumed by execute; do not add walk/trot/fly/hover/lie_down Protocol methods.",
    ),
    588977: Update(
        title="Define generic navigation commands with explicit frame semantics",
        description="Define generic navigation target/path DTOs with Robot-Abstraction-owned frame semantics; do not import World Model domain types.",
    ),
    588978: Update(
        description="After the generic contract stabilizes, extend the logging fake to record commands and synthesize deterministic ActionHandle behavior; pass the canonical suite."
    ),
    588979: Update(
        title="Application unit tests and logging-fake contract tests",
        description="Test application services with a port fake and the concrete logging adapter through the canonical RobotDriver contract suite.",
    ),
    588981: Update(
        title="Define generic manipulation commands",
        description="Define port-owned generic manipulation variants submitted through execute, with affordance requirements and typed unsupported results.",
    ),
    588984: Update(
        description="Define immutable Robot-Driver-port-owned manipulation target/command DTOs with explicit units/frame semantics and no vendor SDK types."
    ),
    588986: Update(
        title="Add manipulation command variants to the generic contract",
        description="Add manipulation variants accepted by execute; do not add vendor-shaped grasp/release/bimanual Protocol methods.",
    ),
    588987: Update(
        description="Defer fake support until the manipulation command contract is approved; then cover supported and unsupported affordances in the canonical suite."
    ),
    588988: Update(
        title="Wire typed results, driver errors, and command affordance preconditions",
        description="Map command variants to required affordances and Robot-Abstraction-owned failures; vendor exceptions remain inside adapters.",
    ),
    588989: Update(
        title="Define RobotDriver error taxonomy in robot_abstraction",
        description="Define capability-owned errors for unsupported operation, precondition, hardware failure, timeout, and cancellation; add none to shared_kernel.",
    ),
    588990: Update(
        title="Map command variants to required affordances",
        description="Define a testable vendor-independent affordance requirement for every generic command variant.",
    ),
    588993: Update(
        description="Translate vendor exceptions into Robot-Abstraction-owned typed failures in adapter-local or genuinely reusable capability-local code."
    ),
    588994: Update(
        description="Test representative and unknown vendor-exception mappings and prove no vendor exception crosses the RobotDriver boundary."
    ),
    590850: Update(
        title="Fleet scheduling domain policies",
        description="Fleet Coordination owns the pure policy answering which eligible robot executes work. FirstFit is deterministic domain policy; add an outbound solver port only for a real external optimizer.",
        acceptance_criteria=[
            "Scheduling policy lives under fleet_coordination/domain/policies/.",
            "Inputs are Fleet-owned candidate/value objects; no Mission Planning domain type is imported.",
            "FirstFit is deterministic and pure.",
            "Empty candidates return a Fleet-owned typed failure.",
            "CostBased remains deferred until a concrete allocation case exists.",
        ],
    ),
    590851: Update(
        title="SchedulingPolicy domain strategy",
        description="Define a pure Fleet domain strategy under fleet_coordination/domain/policies/ using Fleet-owned inputs and outputs, with no I/O or cross-capability domain imports.",
    ),
    590852: Update(
        title="Author SchedulingPolicy domain strategy Protocol",
        description="Define the pure strategy Protocol in fleet_coordination/domain/policies/ using Fleet-owned candidates and Result with a Fleet-owned error.",
    ),
    590853: Update(
        title="FirstFit baseline domain policy",
        description="Implement deterministic first-candidate selection as a pure Fleet domain policy, not an infrastructure adapter.",
    ),
    590854: Update(
        description="Implement FirstFitSchedulingPolicy under fleet_coordination/domain/policies/: deterministic, pure, no I/O, typed failure for empty input."
    ),
    590855: Update(
        title="Unit tests for Fleet scheduling domain policies",
        description="Add pure unit tests for ordering, empty input, and deterministic repetition; do not create an adapter contract harness.",
    ),
    590856: Update(
        title="CostBased scheduling policy: deferred",
        description="Deferred until a concrete multi-robot allocation case provides validated cost inputs and criteria; create no external solver port without a selected optimizer.",
        deferred=True,
        clear_assignee=True,
    ),
    589175: Update(
        title="World Model (reserved until first concrete spatial consumer)",
        description="Reserved until a concrete consumer needs canonical cross-frame resolution, semantic target resolution, map registration, or transform history. Consumers use owned outbound ports and bridges; no capability imports world_model.domain directly.",
        deferred=True,
        clear_assignee=True,
    ),
    590813: Update(
        description="Deferred and not a Robot Abstraction blocker. Activate only for a concrete World Model consumer; provider functionality is an inbound query contract reached through consumer-owned outbound ports and bridges.",
        deferred=True,
        clear_assignee=True,
    ),
    590817: Update(
        title="Transform query contract + Identity adapter",
        description="When activated, World Model exposes an inbound transform-query port; consumers own outbound ports and bridge adapters. Identity is implemented only for a real consumer.",
        deferred=True,
        clear_assignee=True,
    ),
    590818: Update(
        title="Author World Model inbound transform-query Protocol",
        description="Deferred provider inbound query contract; consumer integration uses a consumer-owned outbound port and bridge with no direct World Model domain import.",
        deferred=True,
        clear_assignee=True,
    ),
    590827: Update(
        description="Write this ADR when #590813 is activated by a concrete consumer; record static/time-varying scope and the trigger for transform history/interpolation.",
        deferred=True,
        clear_assignee=True,
    ),
    589138: Update(state="Closed"),
    589144: Update(
        description="Governance roll-up linking one canonical contract suite per eligible port. RobotDriver links to #589049; this Feature creates no second RobotDriver harness."
    ),
    589136: Update(
        title="Kinematic fake RobotDriver adapter",
        description="Own only kinematic-fake scope; logging fake remains under #588883/#588893/#588894. Activate after Clock, framed commands, the canonical driver suite, and thin slice are stable.",
    ),
    589146: Update(
        description="Implement only architecture checks not already delivered, such as DTO locality and future boundary rules. Shadowing and adapter isolation remain under #581355/#581490 for diagnostics only."
    ),
    590900: Update(
        description="Mission Execution orchestrates abort through injected consumer-owned outbound ports and bridges for cancellation, reservation release, and publication; it never calls a shared EventBus."
    ),
    590901: Update(
        description="Implement sequential failure-isolated cleanup through consumer-owned outbound ports. Attempt cancellation, reservation release, and publication independently with typed observable results."
    ),
    590902: Update(
        description="Inject abort at deterministic pseudo-random tick indices using DeterministicRandom #590889; the same seed reproduces behavior and every path releases reservations."
    ),
    590903: Update(
        title="Dead-letter handling for failed mission-aborted publication",
        description="Runtime State event transport owns dead-letter behavior for accepted messages that cannot be delivered. Mission Execution only publishes through its outbound port.",
    ),
    590839: Update(
        description="HTTP/MCP authentication is inbound-adapter behavior. Authorization remains application/domain policy. Define an Operator-Interface-owned outbound principal-resolution port only if application services require current identity."
    ),
    590841: Update(
        title="Principal resolution port + TrustLan adapter",
        description="Conditional on an approved application-level identity need: define an Operator-Interface-owned outbound identity port and inject a TrustLan adapter. Keep transport authentication in inbound adapters and authorization in policy.",
    ),
    590842: Update(
        title="Principal resolution outbound port + Principal DTO",
        description="Create only after product confirms application-level principal resolution. Keep the outbound port and immutable minimal DTO in Operator Interface; expose no transport authentication objects.",
    ),
    589115: Update(
        description="HTTP calls the Operator Interface inbound ViewFleet use case, which calls an Operator-Interface-owned outbound Fleet query port implemented by a bridge to Fleet Coordination's inbound read port."
    ),
    589116: Update(
        title="ViewFleet inbound use case and Fleet query outbound port",
        description="Define distinct Operator Interface inbound ViewFleet and outbound Fleet query contracts with local DTOs. HTTP calls only inbound; application imports no Fleet internals.",
    ),
    589170: Update(
        state="Removed",
        description="Removed as a speculative placeholder. Create a concrete vendor Feature only after hardware, firmware, and onboarding scope are committed.",
    ),
    589171: Update(deferred=True, clear_assignee=True),
    589172: Update(
        description="Deferred until a concrete simulation requirement exists; select no engine before capability and fidelity requirements are known.",
        deferred=True,
        clear_assignee=True,
    ),
    589173: Update(deferred=True, clear_assignee=True),
    589174: Update(
        description="Deferred. Define no speculative sensor-fusion ports; activation requires a concrete perception use case, consumer, and derived DTO boundaries.",
        deferred=True,
        clear_assignee=True,
    ),
    589141: Update(
        description="Deferred until CI-controlled hardware is routinely available.", deferred=True, clear_assignee=True
    ),
    589162: Update(
        description="Deferred until real port surfaces exist and meaningful README drift can be detected.",
        deferred=True,
        clear_assignee=True,
    ),
}


for item_id in [590814, 590815, 590816, 590819, 590820, 590821, 590822, 590823, 590824, 590825, 590826]:
    UPDATES[item_id] = Update(
        description=(
            "Deferred until #590813 has a named concrete consumer and approved boundary contract. Other capabilities must "
            "not import World Model domain types directly; implementation and contract tests begin only after the contract stabilizes."
        ),
        deferred=True,
        clear_assignee=True,
    )

for item_id in [589058, 589059, 589060, 589061]:
    UPDATES[item_id] = Update(
        description=(
            "Deferred until ordinary pytest fixtures prove insufficient. Prefer standard fixtures; introduce registry or "
            "diagnostic helpers only when demonstrated duplication justifies them."
        ),
        deferred=True,
        clear_assignee=True,
    )

for item_id in [590913, 590914, 590915, 590916, 590917]:
    UPDATES[item_id] = Update(
        description=(
            "Deferred until Clock/SystemClock/FakeClock, Robot-Abstraction-owned framed command semantics, the canonical "
            "RobotDriver contract suite, and the thin vertical slice are stable."
        ),
        deferred=True,
        clear_assignee=True,
    )


CREATIONS: list[dict[str, Any]] = [
    {
        "key": "identifier_exceptions",
        "parent": 581343,
        "type": "Task",
        "title": "Align identifier factories with builtin exception semantics",
        "description": task_description(
            "Supersede only the validation semantics delivered by closed Task #581344 while preserving delivered identifiers and generators.",
            [
                "Non-string input raises builtin TypeError with a useful message.",
                "Empty or whitespace-only input raises builtin ValueError with a useful message.",
                "CorrelationId, CausationId, and all existing generators remain unchanged.",
                "AGENTS.md and Story #581343 state the same policy.",
                "Tests cover both exception classes and representative messages.",
                "Link this Task to #581344 as a superseding change and to GitHub PR #16.",
                "Close only after PR #16 merges and post-merge checks on main are green.",
            ],
        ),
    },
    {
        "key": "identifier_static",
        "parent": 581343,
        "type": "Task",
        "title": "Static type-safety and generator completeness for identifiers",
        "description": task_description(
            "Complete the NewType identifier contract without runtime wrappers or test-only override parameters.",
            [
                "Add generate_robot_id().",
                "Add a committed mypy/static test proving RobotId cannot be passed where MissionId is expected.",
                "Document runtime NewType erasure and wrapped-string equality.",
                "Document the deterministic generator seam and helper export surface.",
                "Tests and mypy pass.",
            ],
        ),
    },
    {
        "key": "shadow_diagnostics",
        "parent": 581355,
        "type": "Task",
        "title": "Add file/line/docs diagnostics to shared-primitive shadowing failures",
        "description": task_description(
            "Improve the merged detector without reopening or replacing it.",
            [
                "Structured findings contain path, line number, offending symbol, and canonical docs link.",
                "Formatting occurs only at assertion time.",
                "Negative self-tests assert the complete diagnostic.",
                "Reserved symbols match CANON-1 and exclude Ok, Err, and EventEnvelope.",
            ],
        ),
    },
    {
        "key": "adapter_diagnostics",
        "parent": 581490,
        "type": "Task",
        "title": "Add file/line/rule diagnostics to illegal adapter imports",
        "description": task_description(
            "Improve the merged detector while preserving Bootstrap's exemption.",
            [
                "Findings contain path, line number, offending import, violated rule, and canonical docs link.",
                "Formatting occurs only at assertion time.",
                "Negative self-tests assert the complete diagnostic.",
                "Bootstrap remains exempt.",
            ],
        ),
    },
    {
        "key": "whitespace_gate",
        "parent": 589177,
        "type": "Task",
        "title": "Remove merged .importlinter EOF whitespace defect and add git diff --check to CI",
        "description": task_description(
            "Remove the known whitespace defect and prevent recurrence.",
            [
                "Remove the existing .importlinter EOF whitespace defect.",
                "Run git diff --check as a CI or pre-commit gate.",
                "The gate fails on representative whitespace errors.",
                "Existing import-linter and architecture checks remain green.",
            ],
        ),
    },
    {
        "key": "baseline",
        "parent": 589177,
        "type": "Task",
        "title": "Establish post-foundation CI baseline on main",
        "description": task_description(
            f"Record verified main baseline {BASELINE} (29b16f3).",
            [
                "Record 142 passing tests and 100% current-code coverage.",
                "Record mypy passing 150 files and 18 passing import contracts.",
                "Record passing Ruff lint and format checks.",
                "Record the known .importlinter git diff --check defect and link its remediation Task.",
            ],
        ),
    },
    {
        "key": "event_story",
        "parent": 589131,
        "type": "User Story",
        "title": "Runtime State publication and in-memory event transport",
        "description": "Deliver Runtime State's inbound publication boundary, private transport boundary, lifecycle-safe in-memory transport, and compatibility contracts without exposing transport details.",
        "acceptance_criteria": [
            "Publication and transport are separate Protocols.",
            "Runtime State privately owns transport metadata.",
            "In-memory subscriptions can be removed and shut down safely.",
            "Publishing after shutdown and invalid unsubscription have typed outcomes.",
            "Producer, transport, and consumer compatibility tests pass.",
            "No shared generic envelope is introduced.",
        ],
    },
    {
        "key": "event_publication_port",
        "parent_key": "event_story",
        "type": "Task",
        "title": "Define event_publication inbound Protocol and request DTO",
        "description": task_description(
            "Define Runtime State's inbound publication contract for producer-owned versioned wire messages and metadata.",
            [
                "DTO is port-owned.",
                "API returns typed Result.",
                "No producer domain or private transport DTO leaks.",
                "Validation tests cover malformed requests.",
            ],
        ),
    },
    {
        "key": "event_transport_port",
        "parent_key": "event_story",
        "type": "Task",
        "title": "Define private event_transport outbound Protocol and TransportEnvelope",
        "description": task_description(
            "Define Runtime State's private transport Protocol, envelope, subscription, unsubscription, and lifecycle behavior.",
            [
                "Types remain private to Runtime State.",
                "Delivery ordering and failure behavior are explicit.",
                "No other capability imports TransportEnvelope.",
            ],
        ),
    },
    {
        "key": "event_transport_adapter",
        "parent_key": "event_story",
        "type": "Task",
        "title": "Implement in-memory event transport with unsubscribe/lifecycle semantics",
        "description": task_description(
            "Implement deterministic in-process transport against the private port.",
            [
                "Pass the transport contract suite.",
                "Unsubscribed consumers receive no later messages.",
                "Shutdown rejects later publication predictably.",
                "Tests use no sleeps or global mutable state.",
            ],
        ),
    },
    {
        "key": "event_compatibility",
        "parent_key": "event_story",
        "type": "Task",
        "title": "Add producer, transport, and consumer compatibility contract tests",
        "description": task_description(
            "Prove schema validation, private mapping, metadata propagation, version negotiation, and consumer mapping.",
            [
                "Supported versions pass end to end.",
                "Unsupported versions fail with typed results.",
                "Correlation and causation survive all mappings.",
                "Private transport DTOs do not cross boundaries.",
            ],
        ),
    },
    {
        "key": "execution_story",
        "parent": 588916,
        "type": "User Story",
        "title": "Execution lifecycle aggregate and guarded transitions",
        "description": "Create a Mission-Execution-owned lifecycle beginning at execution and owning EXECUTING, COMPLETED, FAILED, and cancellation/abortion. Publish projections through an explicit Runtime State bridge; never mutate Plan.",
        "acceptance_criteria": [
            "Execution lifecycle types live in Mission Execution.",
            "Every legal and illegal transition is explicit and tested.",
            "Terminal states cannot transition further.",
            "Cancellation/abortion terminology is selected and used consistently.",
            "Plan remains immutable and contains no execution status.",
            "Runtime State receives projections through explicit port DTOs and a bridge.",
        ],
    },
    {
        "key": "execution_state",
        "parent_key": "execution_story",
        "type": "Task",
        "title": "Define ExecutionState and transition guards",
        "description": task_description(
            "Define the execution aggregate and typed transition errors.",
            [
                "Initial and terminal states are explicit.",
                "All illegal transitions are rejected.",
                "Domain imports only stdlib and shared-kernel primitives.",
            ],
        ),
    },
    {
        "key": "execution_tests",
        "parent_key": "execution_story",
        "type": "Task",
        "title": "Test all legal and illegal execution transitions",
        "description": task_description(
            "Add a parametrized lifecycle transition matrix.",
            ["Every state pair is covered.", "Terminal behavior is verified.", "Typed errors are asserted."],
        ),
    },
    {
        "key": "execution_projection",
        "parent_key": "execution_story",
        "type": "Task",
        "title": "Publish execution-state projections through Runtime State bridge",
        "description": task_description(
            "Define a Mission Execution outbound projection port and bridge to Runtime State inbound state contracts.",
            [
                "Application depends only on its outbound port.",
                "Bridge translates to Runtime-State-owned DTOs.",
                "No cross-capability domain imports exist.",
                "Start and terminal projections are tested.",
            ],
        ),
    },
]

# Azure DevOps WIQL indexing can lag behind successful creates. These IDs make
# a resumed reconciliation idempotent immediately after a partial batch.
KNOWN_CREATIONS = {
    "identifier_exceptions": 599231,
    "identifier_static": 599232,
    "shadow_diagnostics": 599233,
    "adapter_diagnostics": 599234,
    "whitespace_gate": 599235,
    "baseline": 599236,
    "event_story": 599237,
    "event_publication_port": 599238,
    "event_transport_port": 599239,
    "event_transport_adapter": 599240,
    "event_compatibility": 599241,
    "execution_story": 599242,
    "execution_state": 599243,
    "execution_tests": 599244,
    "execution_projection": 599245,
}


DUPLICATES = {
    578633: 581481,
    578634: 581482,
    578635: 581484,
    578637: 581477,
    578638: 581477,
    578639: 588935,
    589138: 589049,
}


def add_op(patch: list[JsonPatchOperation], path: str, value: Any) -> None:
    patch.append(JsonPatchOperation(op="add", path=path, value=value))


def relation_exists(work_item: Any, relation_type: str, target_id: int) -> bool:
    suffix = f"/{target_id}"
    return any(rel.rel == relation_type and rel.url.rstrip("/").endswith(suffix) for rel in work_item.relations or [])


def relation_value(relation_type: str, target_url: str, name: str) -> dict[str, Any]:
    return {"rel": relation_type, "url": target_url, "attributes": {"name": name}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"=== {mode}: Wednesday ADO reconciliation ===")

    existing = {item.id: item for item in wit.get_work_items(ids=list(UPDATES), expand="Relations")}
    errors: list[str] = []

    for item_id, change in UPDATES.items():
        item = existing[item_id]
        patch: list[JsonPatchOperation] = []
        if change.title is not None and item.fields.get("System.Title") != change.title:
            add_op(patch, "/fields/System.Title", change.title)
        if change.state is not None and item.fields.get("System.State") != change.state:
            add_op(patch, "/fields/System.State", change.state)
            if change.state == "Closed" and item.fields.get("System.AssignedTo") is None:
                add_op(patch, "/fields/System.AssignedTo", CLOSING_ASSIGNEE)
        if change.description is not None:
            add_op(patch, "/fields/System.Description", to_html(change.description))
        if change.acceptance_criteria is not None:
            add_op(patch, "/fields/Microsoft.VSTS.Common.AcceptanceCriteria", ac_to_html(change.acceptance_criteria))
        if change.deferred:
            tags = [tag.strip() for tag in (item.fields.get("System.Tags") or "").split(";") if tag.strip()]
            if "Deferred" not in tags:
                tags.append("Deferred")
            add_op(patch, "/fields/System.Tags", "; ".join(tags))
            if item.fields.get("System.IterationPath") != ROOT_ITERATION:
                add_op(patch, "/fields/System.IterationPath", ROOT_ITERATION)
        if change.clear_assignee and item.fields.get("System.AssignedTo") is not None:
            patch.append(JsonPatchOperation(op="remove", path="/fields/System.AssignedTo"))
        if not patch:
            print(f"[SKIP] #{item_id} already aligned")
            continue
        print(f"[PLAN] #{item_id} {item.fields.get('System.WorkItemType')}: {len(patch)} field change(s)")
        if args.apply:
            try:
                wit.update_work_item(document=patch, id=item_id)
                print(f"[OK]   #{item_id}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"#{item_id}: {exc}")
                print(f"[ERR]  #{item_id}: {exc}")

    created: dict[str, int] = {}
    for spec in CREATIONS:
        known_id = KNOWN_CREATIONS.get(spec["key"])
        if known_id is not None:
            known_item = wit.get_work_item(id=known_id)
            if known_item.fields.get("System.Title") == spec["title"]:
                created[spec["key"]] = known_id
                print(f"[SKIP] existing #{known_id} {spec['title']}")
                continue
        query_title = spec["title"].replace("'", "''")
        result = wit.query_by_wiql(
            wiql=Wiql(
                query=f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.Title] = '{query_title}'"
            )
        )
        matches = [ref.id for ref in result.work_items or []]
        if matches:
            created[spec["key"]] = matches[0]
            print(f"[SKIP] existing #{matches[0]} {spec['title']}")
            continue
        parent_id = spec.get("parent") or created.get(spec.get("parent_key"))
        if parent_id is None:
            errors.append(f"Cannot resolve parent for {spec['title']}")
            continue
        print(f"[PLAN] create {spec['type']} under #{parent_id}: {spec['title']}")
        if not args.apply:
            created[spec["key"]] = -1
            continue
        parent = wit.get_work_item(id=parent_id)
        patch = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=spec["title"]),
            JsonPatchOperation(op="add", path="/fields/System.Description", value=to_html(spec["description"])),
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
        if spec["type"] == "User Story":
            add_op(patch, "/fields/Microsoft.VSTS.Scheduling.StoryPoints", 3)
            add_op(patch, "/fields/Microsoft.VSTS.Common.ValueArea", "Architectural")
            add_op(patch, "/fields/Microsoft.VSTS.Common.AcceptanceCriteria", ac_to_html(spec["acceptance_criteria"]))
        try:
            new_item = wit.create_work_item(document=patch, project=cfg.project, type=spec["type"])
            created[spec["key"]] = new_item.id
            print(f"[OK]   created #{new_item.id}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Create {spec['title']}: {exc}")
            print(f"[ERR]  create {spec['title']}: {exc}")

    if args.apply:
        # Supersession and PR linkage for the identifier exception decision.
        successor_id = created.get("identifier_exceptions")
        if successor_id is not None:
            successor = wit.get_work_item(id=successor_id, expand="Relations")
            predecessor = wit.get_work_item(id=581344)
            links: list[JsonPatchOperation] = []
            predecessor_added = False
            if not relation_exists(successor, "System.LinkTypes.Dependency-Reverse", 581344):
                add_op(
                    links,
                    "/relations/-",
                    relation_value("System.LinkTypes.Dependency-Reverse", predecessor.url, "Predecessor"),
                )
                predecessor_added = True
            pr_url = "https://github.com/ey-org/skynet-agnostic-robotic-framework/pull/16"
            if not any(rel.rel == "Hyperlink" and rel.url == pr_url for rel in successor.relations or []):
                add_op(links, "/relations/-", relation_value("Hyperlink", pr_url, "PR #16"))
            if links:
                wit.update_work_item(document=links, id=successor_id)
            if predecessor_added:
                comment_url = (
                    f"{cfg.org_url}/{cfg.project}/_apis/wit/workItems/581344/comments?api-version=7.1-preview.3"
                )
                response = requests.post(
                    comment_url,
                    auth=HTTPBasicAuth("", cfg.pat),
                    json={
                        "text": f"Validation semantics superseded by Task #{successor_id} / PR #16; CorrelationId and CausationId delivery remains valid."
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                response.raise_for_status()

        # Link the baseline to the whitespace remediation.
        baseline_id = created.get("baseline")
        whitespace_id = created.get("whitespace_gate")
        if baseline_id is not None and whitespace_id is not None:
            baseline = wit.get_work_item(id=baseline_id, expand="Relations")
            target = wit.get_work_item(id=whitespace_id)
            if not relation_exists(baseline, "System.LinkTypes.Related", whitespace_id):
                wit.update_work_item(
                    document=[
                        JsonPatchOperation(
                            op="add",
                            path="/relations/-",
                            value=relation_value("System.LinkTypes.Related", target.url, "Related"),
                        )
                    ],
                    id=baseline_id,
                )

        # Preserve duplicate history and point each duplicate to its canonical item.
        for duplicate_id, canonical_id in DUPLICATES.items():
            duplicate = wit.get_work_item(id=duplicate_id, expand="Relations")
            canonical = wit.get_work_item(id=canonical_id)
            patch: list[JsonPatchOperation] = []
            if duplicate.fields.get("System.State") != "Closed":
                add_op(patch, "/fields/System.State", "Closed")
                if duplicate.fields.get("System.AssignedTo") is None:
                    add_op(patch, "/fields/System.AssignedTo", CLOSING_ASSIGNEE)
            if not relation_exists(duplicate, "System.LinkTypes.Duplicate-Reverse", canonical_id):
                add_op(
                    patch,
                    "/relations/-",
                    relation_value("System.LinkTypes.Duplicate-Reverse", canonical.url, "Duplicate Of"),
                )
            if patch:
                wit.update_work_item(document=patch, id=duplicate_id)
                print(f"[OK]   duplicate #{duplicate_id} -> #{canonical_id}")

        # Runtime State owns dead-letter transport reliability; retain a related link from Mission Execution.
        dead_letter = wit.get_work_item(id=590903, expand="Relations")
        mission_abort = wit.get_work_item(id=590900)
        event_feature = wit.get_work_item(id=589131)
        move_patch: list[JsonPatchOperation] = []
        for index, relation in enumerate(dead_letter.relations or []):
            if relation.rel == "System.LinkTypes.Hierarchy-Reverse":
                if not relation.url.rstrip("/").endswith("/589131"):
                    move_patch.append(JsonPatchOperation(op="remove", path=f"/relations/{index}"))
                break
        if not relation_exists(dead_letter, "System.LinkTypes.Hierarchy-Reverse", 589131):
            add_op(
                move_patch,
                "/relations/-",
                relation_value("System.LinkTypes.Hierarchy-Reverse", event_feature.url, "Parent"),
            )
        if not relation_exists(dead_letter, "System.LinkTypes.Related", 590900):
            add_op(move_patch, "/relations/-", relation_value("System.LinkTypes.Related", mission_abort.url, "Related"))
        if move_patch:
            wit.update_work_item(document=move_patch, id=590903)
            print("[OK]   moved #590903 under #589131")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(2)
    print(f"\n=== {mode} complete: {len(UPDATES)} existing items, {len(CREATIONS)} creation specs ===")


if __name__ == "__main__":
    main()
