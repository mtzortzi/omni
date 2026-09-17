"""Reconcile Sprint FY27Q1.4 Mission Execution work into two streams.

The script is intentionally scoped to Mission Execution and the central-framework
enablers needed to integrate it later. It does not query or modify Planner work.

Usage:
    uv run python reconcile_mission_execution_14.py --dry-run
    uv run python reconcile_mission_execution_14.py
"""

from __future__ import annotations

import argparse
import html
from dataclasses import dataclass
from typing import Any

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import AdoConfig, get_clients
from engagement_tree import strip_html


AREA = "graiteam\\Physical AI"
QUARTER = "graiteam\\Global Calendar\\Fiscal Year 2027\\FY27Q1"
SPRINT = f"{QUARTER}\\FY27Q1.4"

MARIANNA = "Marianna.Tzortzi@gr.ey.com"
KONSTANTINOS = "Konstantinos.Sardelis@gr.ey.com"
DIMITRIS = "Dimitris.Chatzakis@gr.ey.com"
COSTAS = "Costas.Bampos@gr.ey.com"

MISSION_EXECUTION_EPIC = 599252
CENTRAL_EXECUTION_FEATURE = 588916
BOOTSTRAP_FEATURE = 588934

PRIORITY_TAGS = {"must", "should", "could"}
STREAM_TAGS = {"Mission Execution PoC", "Central Framework", "Standalone Capability", "Mission Execution"}


def text_to_html(text: str) -> str:
    paragraphs = [part.strip() for part in text.strip().split("\n\n") if part.strip()]
    return "".join(f"<div>{html.escape(part).replace(chr(10), '<br>')}</div>" for part in paragraphs)


def criteria_to_html(criteria: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in criteria) + "</ul>"


@dataclass(frozen=True)
class ItemSpec:
    item_type: str
    title: str
    description: str
    criteria: list[str]
    owner: str
    iteration: str
    priority: str
    stream: str
    story_points: int | None = None
    remaining_work: int | None = None


class Reconciler:
    def __init__(self, *, dry_run: bool) -> None:
        self.config = AdoConfig.from_env()
        self.wit, _ = get_clients(self.config)
        self.dry_run = dry_run
        self._next_fake_id = -1

    def _item_url(self, item_id: int) -> str:
        return f"{self.config.org_url}/{self.config.project}/_apis/wit/workItems/{item_id}"

    def _new_fake_id(self) -> int:
        result = self._next_fake_id
        self._next_fake_id -= 1
        return result

    def _direct_children(self, parent_id: int) -> list[Any]:
        if parent_id < 0:
            return []
        parent = self.wit.get_work_item(id=parent_id, expand="Relations")
        child_ids = [
            int(relation.url.rstrip("/").rsplit("/", 1)[-1])
            for relation in parent.relations or []
            if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        ]
        if not child_ids:
            return []
        return self.wit.get_work_items(
            ids=child_ids,
            fields=["System.Id", "System.Title", "System.WorkItemType"],
        )

    def find_child(self, *, parent_id: int, item_type: str, title: str) -> int | None:
        for child in self._direct_children(parent_id):
            if child.fields.get("System.WorkItemType") == item_type and child.fields.get("System.Title") == title:
                return child.id
        return None

    def create_item(self, *, parent_id: int, spec: ItemSpec) -> int:
        existing_id = self.find_child(parent_id=parent_id, item_type=spec.item_type, title=spec.title)
        if existing_id is not None:
            print(f"[KEEP] #{existing_id} {spec.item_type}: {spec.title}")
            self.update_item(existing_id, spec)
            return existing_id

        if self.dry_run:
            fake_id = self._new_fake_id()
            print(f"[DRY CREATE] {spec.item_type} under #{parent_id}: {spec.title}")
            return fake_id

        patch = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=spec.title),
            JsonPatchOperation(op="add", path="/fields/System.Description", value=text_to_html(spec.description)),
            JsonPatchOperation(
                op="add",
                path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                value=criteria_to_html(spec.criteria),
            ),
            JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=AREA),
            JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=spec.iteration),
            JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value=spec.owner),
            JsonPatchOperation(
                op="add",
                path="/fields/System.Tags",
                value="; ".join(
                    sorted(
                        {spec.priority, spec.stream}
                        | ({"Standalone Capability", "Mission Execution"} if spec.stream == "Mission Execution PoC" else set())
                    )
                ),
            ),
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value={
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": self._item_url(parent_id),
                    "attributes": {"name": "Parent"},
                },
            ),
        ]
        if spec.item_type == "Feature":
            patch.append(
                JsonPatchOperation(
                    op="add",
                    path="/fields/Microsoft.VSTS.Common.ValueArea",
                    value="Business",
                )
            )
        if spec.item_type == "User Story":
            patch.extend(
                [
                    JsonPatchOperation(
                        op="add",
                        path="/fields/Microsoft.VSTS.Common.ValueArea",
                        value="Architectural",
                    ),
                    JsonPatchOperation(
                        op="add",
                        path="/fields/Microsoft.VSTS.Scheduling.StoryPoints",
                        value=spec.story_points,
                    ),
                ]
            )
        if spec.item_type == "Task" and spec.remaining_work is not None:
            patch.append(
                JsonPatchOperation(
                    op="add",
                    path="/fields/Microsoft.VSTS.Scheduling.RemainingWork",
                    value=spec.remaining_work,
                )
            )
        item = self.wit.create_work_item(document=patch, project=self.config.project, type=spec.item_type)
        print(f"[CREATED] #{item.id} {spec.item_type}: {spec.title}")
        return item.id

    def update_item(self, item_id: int, spec: ItemSpec) -> None:
        if item_id < 0:
            return
        current = self.wit.get_work_item(id=item_id)
        current_tags = {
            tag.strip()
            for tag in (current.fields.get("System.Tags") or "").split(";")
            if tag.strip()
        }
        tags = current_tags - PRIORITY_TAGS - STREAM_TAGS
        tags.update({spec.priority, spec.stream})
        if spec.stream == "Mission Execution PoC":
            tags.update({"Standalone Capability", "Mission Execution"})
        patch = [
            JsonPatchOperation(op="add", path="/fields/System.Title", value=spec.title),
            JsonPatchOperation(op="add", path="/fields/System.Description", value=text_to_html(spec.description)),
            JsonPatchOperation(
                op="add",
                path="/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                value=criteria_to_html(spec.criteria),
            ),
            JsonPatchOperation(op="add", path="/fields/System.AreaPath", value=AREA),
            JsonPatchOperation(op="add", path="/fields/System.IterationPath", value=spec.iteration),
            JsonPatchOperation(op="add", path="/fields/System.AssignedTo", value=spec.owner),
            JsonPatchOperation(op="replace", path="/fields/System.Tags", value="; ".join(sorted(tags))),
        ]
        if spec.item_type == "User Story" and spec.story_points is not None:
            patch.extend(
                [
                    JsonPatchOperation(
                        op="add",
                        path="/fields/Microsoft.VSTS.Common.ValueArea",
                        value="Architectural",
                    ),
                    JsonPatchOperation(
                        op="add",
                        path="/fields/Microsoft.VSTS.Scheduling.StoryPoints",
                        value=spec.story_points,
                    ),
                ]
            )
        if spec.item_type == "Task" and spec.remaining_work is not None:
            patch.append(
                JsonPatchOperation(
                    op="add",
                    path="/fields/Microsoft.VSTS.Scheduling.RemainingWork",
                    value=spec.remaining_work,
                )
            )
        if self.dry_run:
            print(
                f"[DRY UPDATE] #{item_id} {spec.item_type}: owner={spec.owner}, "
                f"iteration={spec.iteration.rsplit(chr(92), 1)[-1]}, tags={sorted(tags)}"
            )
            return
        self.wit.update_work_item(document=patch, id=item_id)
        print(f"[UPDATED] #{item_id} {spec.item_type}: {spec.title}")

    def reparent(self, *, item_id: int, parent_id: int) -> None:
        if item_id < 0 or parent_id < 0:
            if self.dry_run:
                print(f"[DRY REPARENT] #{item_id} -> #{parent_id}")
            return
        item = self.wit.get_work_item(id=item_id, expand="Relations")
        current_parent = item.fields.get("System.Parent")
        if current_parent == parent_id:
            print(f"[KEEP PARENT] #{item_id} -> #{parent_id}")
            return
        patch: list[JsonPatchOperation] = []
        for index, relation in reversed(list(enumerate(item.relations or []))):
            if relation.rel == "System.LinkTypes.Hierarchy-Reverse":
                patch.append(JsonPatchOperation(op="remove", path=f"/relations/{index}"))
        patch.append(
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value={
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": self._item_url(parent_id),
                    "attributes": {"name": "Parent"},
                },
            )
        )
        if self.dry_run:
            print(f"[DRY REPARENT] #{item_id} -> #{parent_id}")
            return
        self.wit.update_work_item(document=patch, id=item_id)
        print(f"[REPARENTED] #{item_id} -> #{parent_id}")

    def set_predecessors(self, *, successor_id: int, predecessor_ids: set[int]) -> None:
        if successor_id < 0 or any(item_id < 0 for item_id in predecessor_ids):
            if self.dry_run:
                print(f"[DRY DEPENDENCIES] #{successor_id} <- {sorted(predecessor_ids)}")
            return
        item = self.wit.get_work_item(id=successor_id, expand="Relations")
        current: dict[int, int] = {}
        for index, relation in enumerate(item.relations or []):
            if relation.rel == "System.LinkTypes.Dependency-Reverse":
                current[int(relation.url.rstrip("/").rsplit("/", 1)[-1])] = index
        if set(current) == predecessor_ids:
            print(f"[KEEP DEPENDENCIES] #{successor_id} <- {sorted(predecessor_ids)}")
            return
        patch: list[JsonPatchOperation] = []
        for predecessor_id, index in sorted(current.items(), key=lambda pair: pair[1], reverse=True):
            if predecessor_id not in predecessor_ids:
                patch.append(JsonPatchOperation(op="remove", path=f"/relations/{index}"))
        for predecessor_id in sorted(predecessor_ids - set(current)):
            patch.append(
                JsonPatchOperation(
                    op="add",
                    path="/relations/-",
                    value={
                        "rel": "System.LinkTypes.Dependency-Reverse",
                        "url": self._item_url(predecessor_id),
                        "attributes": {"name": "Predecessor"},
                    },
                )
            )
        if self.dry_run:
            print(f"[DRY DEPENDENCIES] #{successor_id} <- {sorted(predecessor_ids)}")
            return
        self.wit.update_work_item(document=patch, id=successor_id)
        print(f"[DEPENDENCIES] #{successor_id} <- {sorted(predecessor_ids)}")


def spec(
    item_type: str,
    title: str,
    description: str,
    criteria: list[str],
    owner: str,
    iteration: str,
    priority: str,
    stream: str,
    *,
    story_points: int | None = None,
    remaining_work: int | None = None,
) -> ItemSpec:
    return ItemSpec(
        item_type=item_type,
        title=title,
        description=description,
        criteria=criteria,
        owner=owner,
        iteration=iteration,
        priority=priority,
        stream=stream,
        story_points=story_points,
        remaining_work=remaining_work,
    )


def reconcile(dry_run: bool) -> None:
    r = Reconciler(dry_run=dry_run)

    poc_feature = r.create_item(
        parent_id=MISSION_EXECUTION_EPIC,
        spec=spec(
            "Feature",
            "Standalone Mission Execution PoC - realistic multi-robot simulation",
            "Deliver an independently runnable Mission Execution PoC with visible business value. The PoC consumes a validated executable Plan input, owns one global fleet action sequence, executes actions through a Behavior Tree, and drives asynchronous simulated robots with live progress, success, failure, retry, abort, and replan-required outcomes. A deterministic test mode verifies repeatability, concurrency, and idempotency without replacing the realistic simulation used for the demonstration.",
            [
                "A standalone command runs a realistic time-evolving multi-robot execution scenario.",
                "The Behavior Tree is visible in the runtime flow and controls success/failure branches without owning durable execution state.",
                "The PoC records a live timeline and final execution report that demonstrate operational business value.",
                "The same core supports deterministic automated tests with scripted outcomes, controlled time, and stable IDs.",
                "The standalone PoC is not blocked by central-framework bridges, network services, hardware, or production persistence.",
            ],
            MARIANNA,
            QUARTER,
            "must",
            "Mission Execution PoC",
        ),
    )

    r.update_item(
        CENTRAL_EXECUTION_FEATURE,
        spec(
            "Feature",
            "Mission Execution central-framework contracts and integration",
            "Deliver the central-framework contracts, bridges, activation boundary, and composition needed to connect the standalone Mission Execution capability to Mission Planning, Runtime State, Robot Abstraction, and Bootstrap. This stream progresses independently and must not block the standalone Mission Execution PoC.",
            [
                "Mission Execution owns its consumer-facing outbound ports and DTOs.",
                "Cross-capability calls use provider inbound contracts through consumer-owned bridge adapters.",
                "Central integration can use fakes while provider services are incomplete.",
                "Production eventing, durable recovery, and the complete E2E composition remain backlog unless explicitly marked must.",
            ],
            COSTAS,
            QUARTER,
            "must",
            "Central Framework",
        ),
    )
    provider_audit_story = r.create_item(
        parent_id=CENTRAL_EXECUTION_FEATURE,
        spec=spec(
            "User Story",
            "Audit and pin central provider contracts for Mission Execution integration",
            "Establish the central-framework source-of-truth inputs for later Mission Execution mappings without waiting for the standalone capability implementation. Inventory the public Mission Planning, Runtime State, and Robot Abstraction inbound contracts, record versions/owners/gaps, and prepare a reviewed integration baseline.",
            [
                "The audit references only public inbound contracts and canonical documentation.",
                "Current versus required fields and typed errors are recorded for each provider boundary.",
                "Missing or unstable provider contracts become explicit follow-up dependencies rather than duplicate DTOs.",
                "The result is usable by later mapping and bridge Tasks and does not depend on standalone implementation code.",
            ],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            story_points=2,
        ),
    )
    for task_spec in [
        spec(
            "Task",
            "Inventory Mission Planning Plan-read public contracts",
            "Review the current Mission Planning public Plan-read Protocols, DTOs, typed results, schemas, and canonical documentation needed by Mission Execution. Record the current GetMissionPlan gap without defining Execution-owned types.",
            [
                "The inventory records paths, owner, Plan identity/version fields, action/assignment/dependency fields, error semantics, maturity, and known gaps.",
                "The task can complete against the current central repository even if GetMissionPlan implementation is unfinished.",
            ],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            remaining_work=4,
        ),
        spec(
            "Task",
            "Inventory Runtime State activation and projection public contracts",
            "Review Runtime State's public current-plan, session/action projection, revision, and typed-result contracts needed by Mission Execution, without defining a consumer port or implementing a bridge.",
            [
                "The inventory records ABSENT/exact-revision semantics, identities, DTO ownership, result errors, maturity, and application-service gaps.",
                "No StateBackend, blackboard, or private adapter contract is treated as public integration API.",
            ],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            remaining_work=4,
        ),
        spec(
            "Task",
            "Inventory Robot Operations lifecycle public contracts",
            "Review Robot Abstraction's public Robot Operations acceptance, feedback/result, cancellation, correlation, and route-command surfaces needed by Mission Execution, without defining a consumer port or implementing a bridge.",
            [
                "The inventory records available and missing lifecycle operations, identities, typed outcomes, and contract maturity.",
                "RobotDriver and ActionHandle internals are documented only as non-public implementation details.",
            ],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            remaining_work=4,
        ),
    ]:
        r.create_item(parent_id=provider_audit_story, spec=task_spec)

    repository_story = r.create_item(
        parent_id=poc_feature,
        spec=spec(
            "User Story",
            "Create standalone Mission Execution GitHub repository",
            "Create the independent GitHub repository that will own the Mission Execution capability, following the same standalone ownership principle as the Planner PoC while preserving the framework's ports-and-adapters architecture and quality baseline.",
            [
                "The repository is created under the agreed GitHub organization with team access and branch protection.",
                "Python, uv, src/test layout, licensing, ownership, and contribution metadata are configured.",
                "Basic CI runs formatting, linting, typing, unit tests, architecture checks, and secret/dependency scanning.",
                "The README explains capability ownership, local setup, test commands, and the initial realistic simulation goal.",
                "No central-framework implementation or Planner source code is copied into the repository.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            story_points=3,
        ),
    )
    for task_spec in [
        spec(
            "Task",
            "Request and create the Mission Execution GitHub repository",
            "Agree the repository name, request/create it under the GitHub organization, configure visibility and team permissions, and record its canonical URL in the work item and central documentation index.",
            [
                "Marianna and Konstantinos have the required contributor access.",
                "Default branch protection and required pull-request review are enabled.",
                "Repository ownership is unambiguous and no credentials are committed.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=3,
        ),
        spec(
            "Task",
            "Initialize uv Python package and hexagonal capability structure",
            "Initialize Python 3.12+, uv, pyproject metadata, src/tests packages, and the domain/application/ports/adapters/bootstrap test-profile structure needed by the standalone capability.",
            [
                "The package installs and imports in a clean uv environment.",
                "Core layers contain no concrete adapter imports.",
                "A minimal test proves the package and architecture scaffold run.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=4,
        ),
        spec(
            "Task",
            "Configure CI, branch protection, CODEOWNERS, and repository checks",
            "Configure the repository's required pull-request checks, CODEOWNERS, pre-commit/CI quality commands, secret scanning, and dependency review using the established project conventions.",
            [
                "A pull request cannot merge when required checks fail.",
                "CI runs without project secrets and uses pinned/reproducible dependencies.",
                "The default branch is protected and ownership/review rules are documented.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=5,
        ),
        spec(
            "Task",
            "Document standalone repository setup and local PoC commands",
            "Add the README, architecture summary, local setup, quality commands, contribution workflow, scope boundaries, and placeholder command for the realistic Mission Execution simulation.",
            [
                "A new developer can install, run checks, and understand the capability boundary from the README.",
                "The document distinguishes standalone capability code from future central-framework bridges.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=4,
        ),
    ]:
        r.create_item(parent_id=repository_story, spec=task_spec)

    input_boundary_story = r.create_item(
        parent_id=poc_feature,
        spec=spec(
            "User Story",
            "Standalone Plan input and execution activation boundary",
            "Define how the standalone Mission Execution capability receives an exact validated Plan view and starts an execution session. The capability owns its inbound activation Protocol, PlanReader outbound port, DTOs, and errors; central-framework adapters map to these published contracts later.",
            [
                "The capability accepts exact mission_id, plan_id, and plan_version identity.",
                "ExecutablePlanView contains only execution-required sequence, action, robot, route, and duration metadata.",
                "The fixture-backed PlanReader used by the PoC satisfies the same outbound port as the future central bridge.",
                "Availability remains distinct from activation and no foreign domain or adapter type crosses the boundary.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            story_points=5,
        ),
    )
    standalone_boundary_tasks = {
        588921: spec(
            "Task",
            "Define available Plan identity and activation request value objects",
            "Define immutable Mission Execution value objects for exact Plan identity, candidate availability, activation request, and activation result without importing a provider domain model.",
            ["Candidate availability remains distinct from active execution state."],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=6,
        ),
        588923: spec(
            "Task",
            "Define activation inbound Protocol and typed DTOs",
            "Define the standalone capability's activation inbound Protocol and port-owned request/result DTOs with typed not-found, stale, precondition, and conflicting-session outcomes.",
            ["Malformed boundary input follows ValidationError semantics and no provider type leaks."],
            KONSTANTINOS,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=6,
        ),
        658775: spec(
            "Task",
            "Define ExecutablePlanView, PlanReader port, and global queue contract",
            "Define the Mission-Execution-owned validated Plan input, PlanReader outbound port, and queue semantics: exact Plan identity, sequence index, ActionId, robot assignment, immutable action parameters, optional validated route metadata, and estimated_duration_s.",
            [
                "The DTO imports no foreign capability domain model.",
                "The standalone fixture reader implements the PlanReader port without changing the application service.",
                "Array/index order is the sole global fleet execution order in the first profile.",
                "The queue defines peek/get-next, claim, running, completion, retry, and terminal semantics.",
                "Getting the next action never performs planning or route calculation.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=10,
        ),
    }
    for item_id, item_spec in standalone_boundary_tasks.items():
        r.reparent(item_id=item_id, parent_id=input_boundary_story)
        r.update_item(item_id, item_spec)

    core_story = 599242
    r.reparent(item_id=core_story, parent_id=poc_feature)
    r.update_item(
        core_story,
        spec(
            "User Story",
            "Mission Execution core lifecycle, global queue, and action attempts",
            "Implement the standalone capability's authoritative ExecutionSession, logical mission-action state, physical ActionExecution attempts, and one global serial fleet queue. The queue advances exactly once after success, remains on the current action while running or retrying, and uses a new ActionExecutionId for every physical retry.",
            [
                "ExecutionSession, logical action state, and physical attempts have distinct typed identities and transitions.",
                "Exactly one global sequence is consumed in order and at most one action is in flight in the first PoC profile.",
                "Duplicate ticks, dispatch requests, feedback, and terminal results do not duplicate commands or queue advancement.",
                "Retry creates a new ActionExecutionId without replacing the logical ActionId.",
                "Route metadata is preserved separately from immutable action parameters.",
                "estimated_duration_s remains planning metadata and is not silently treated as a runtime timeout.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            story_points=8,
        ),
    )

    existing_core_tasks = {
        599243: spec(
            "Task",
            "Define ExecutionSession, logical action, and attempt transition guards",
            "Define the minimum PoC state machines and typed transition errors. Session states cover preparing, active, completed, aborted, and replan-required. Logical action state remains stable across physical attempts.",
            [
                "Illegal and terminal transitions return typed domain errors.",
                "Each retry creates a new ActionExecutionId.",
                "Domain code imports only stdlib and shared-kernel primitives.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=6,
        ),
        599244: spec(
            "Task",
            "Test lifecycle, retry, and terminal transition matrices",
            "Add deterministic transition matrices for sessions, logical actions, and attempts, including retry, abort, replan-required, and duplicate terminal-result behavior.",
            [
                "Every legal and illegal transition is covered.",
                "Duplicate terminal results are idempotent.",
                "Retry preserves ActionId and creates a new ActionExecutionId.",
            ],
            KONSTANTINOS,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=8,
        ),
        624268: spec(
            "Task",
            "Implement ExecutionRepository and in-memory global queue",
            "Define the private semantic repository port and implement an in-memory adapter for sessions, logical actions, attempts, queue position, in-flight state, and processed-result idempotency.",
            [
                "Repository operations expose execution semantics rather than storage models.",
                "Queue claim, completion, failure, retry, and terminal behavior are atomic within the adapter.",
                "Concurrent duplicate operations return the existing effect or a typed conflict.",
                "The in-memory adapter passes reusable repository contract tests.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=12,
        ),
    }
    for item_id, item_spec in existing_core_tasks.items():
        r.reparent(item_id=item_id, parent_id=core_story)
        r.update_item(item_id, item_spec)

    r.create_item(
        parent_id=core_story,
        spec=spec(
            "Task",
            "Implement action consumption and attempt orchestration service",
            "Define the consumer-owned robot-operation lifecycle port, then implement the Mission Execution application service that gets and claims the next global queue item, creates one physical attempt, dispatches it, applies feedback/results, and advances or retains the queue according to the outcome.",
            [
                "get_next_action reads only the Execution-owned queue and never calls a Planner.",
                "The robot-operation port exposes no RobotDriver, ActionHandle, vendor, or concrete adapter type.",
                "One claimed queue item creates at most one dispatch for its ActionExecutionId.",
                "RUNNING retains the current item without redispatch.",
                "SUCCESS advances exactly once; failure retains the item for BT retry/abort/replan disposition.",
                "Duplicate feedback and terminal results are idempotent.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=12,
        ),
    )

    bt_story = 588926
    r.reparent(item_id=bt_story, parent_id=poc_feature)
    r.update_item(
        bt_story,
        spec(
            "User Story",
            "Minimal Behavior Tree runtime for the standalone Mission Execution PoC",
            "Implement a small robot-agnostic Behavior Tree runtime as an inbound adapter of Mission Execution. It ticks the active action, observes asynchronous feedback/results through Mission Execution application ports, and selects explicit success or failure branches. It does not own the queue, session state, or persistence.",
            [
                "The initial node set supports Sequence, Fallback, ExecuteAction, Retry, Abort, and RequestReplan behavior.",
                "RUNNING retains the current queue item and never redispatches it.",
                "SUCCESS advances the queue exactly once through the application boundary.",
                "FAILURE selects retry, abort, or replan-required according to the scenario policy.",
                "No node imports central-framework adapters or foreign capability internals.",
            ],
            KONSTANTINOS,
            SPRINT,
            "must",
            "Mission Execution PoC",
            story_points=5,
        ),
    )
    r.update_item(
        588927,
        spec(
            "Task",
            "Implement asynchronous BT tick loop over Mission Execution ports",
            "Implement a time-evolving asynchronous tick loop over Mission Execution application ports. The loop observes the current attempt, emits visible node/status transitions, and refuses to redispatch a running action.",
            [
                "RUNNING actions are observed rather than redispatched.",
                "One tick has a typed result and no hidden global state.",
                "The loop can run against realistic simulated time and deterministic test time.",
            ],
            KONSTANTINOS,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=10,
        ),
    )
    r.update_item(
        588928,
        spec(
            "Task",
            "Implement Sequence, Fallback, and ExecuteAction nodes",
            "Implement the minimum composable BT node set with explicit RUNNING, SUCCESS, and FAILURE semantics and no durable state ownership inside nodes.",
            [
                "Sequence and Fallback propagation is covered by unit tests.",
                "ExecuteAction delegates every state mutation to Mission Execution application ports.",
                "Node evaluation remains robot-vendor agnostic.",
            ],
            KONSTANTINOS,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=8,
        ),
    )
    r.create_item(
        parent_id=bt_story,
        spec=spec(
            "Task",
            "Implement Retry, Abort, and RequestReplan failure branches",
            "Implement explicit failure-control branches for bounded retry, safe session abort, and replan-required outcome. The PoC records a replan request but does not create a replacement Plan.",
            [
                "Retry is bounded and creates a new physical attempt.",
                "Abort prevents every later queue item from dispatching.",
                "RequestReplan terminates the active execution path with a typed traceable outcome.",
            ],
            KONSTANTINOS,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=8,
        ),
    )

    simulation_story = r.create_item(
        parent_id=poc_feature,
        spec=spec(
            "User Story",
            "Realistic multi-robot simulation and business-value demonstration",
            "Provide the primary Sprint 1.4 demonstration: an independently runnable, asynchronous multi-robot mission execution simulation with visible BT decisions, time-evolving progress, controlled failure/recovery, and a final execution report.",
            [
                "At least two simulated robots execute actions from one global fleet sequence.",
                "Feedback evolves through ACCEPTED, RUNNING/progress, and a terminal result rather than returning immediately.",
                "The demonstration includes one successful action, one failed attempt followed by retry and success, and one abort or replan-required variant.",
                "A live timeline exposes session, queue, BT node, robot, ActionId, and ActionExecutionId transitions.",
                "The final report shows planned versus actual duration, attempts, outcomes, and the reason for recovery decisions.",
                "The scenario runs locally without physical hardware or external infrastructure.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            story_points=8,
        ),
    )
    for task_spec in [
        spec(
            "Task",
            "Scaffold the standalone PoC package, command, and quality gates",
            "Implement the independently runnable Mission Execution simulation command and test-profile composition inside the initialized standalone repository.",
            [
                "One documented command starts the local simulation.",
                "The command composes core/application services with simulation adapters only at the profile composition boundary.",
                "No central-framework bridge or production adapter is required to run the command.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=6,
        ),
        spec(
            "Task",
            "Implement asynchronous simulated robot runtime",
            "Implement a Mission-Execution-facing simulated robot adapter that accepts commands, emits time-evolving progress, resolves scripted success/failure/cancellation, and supports multiple robot identities.",
            [
                "Progress is asynchronous and observable.",
                "Failure and cancellation are typed and correlated by ActionExecutionId.",
                "Simulation behavior is configurable per scenario without changing core execution logic.",
            ],
            KONSTANTINOS,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=14,
        ),
        spec(
            "Task",
            "Build the standalone scenario runner and live execution timeline",
            "Load a validated executable-plan fixture, start the execution session, run the BT and simulated robots, and render live queue/action/progress/failure transitions.",
            [
                "The runner shows strict global sequence ordering across robots.",
                "Every transition includes stable session, action, attempt, and robot correlation.",
                "The runner exits with a typed completed, aborted, or replan-required outcome.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=12,
        ),
        spec(
            "Task",
            "Generate the business-value execution report",
            "Produce a concise machine-readable and human-readable report covering the action sequence, actual progress, retries, failures, recovery decisions, completion status, and planned-versus-actual duration.",
            [
                "The report makes successful completion and controlled failure behavior auditable.",
                "No command is counted twice after duplicate ticks or results.",
                "The report can be attached to the Sprint demonstration evidence.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=8,
        ),
    ]:
        r.create_item(parent_id=simulation_story, spec=task_spec)

    r.reparent(item_id=588931, parent_id=simulation_story)
    r.update_item(
        588931,
        spec(
            "Task",
            "Demonstrate realistic multi-robot execution with failure and recovery",
            "Create the canonical business demonstration: actions assigned to different simulated robots execute in one global order; one action fails, the BT selects bounded retry, the next attempt succeeds, and the mission reaches a traceable terminal outcome.",
            [
                "The demonstration uses asynchronous progress and no immediate all-success shortcut.",
                "A running action is dispatched exactly once.",
                "Retry creates a new ActionExecutionId and the queue advances only after success.",
                "A second scenario proves abort or replan-required prevents later dispatch.",
                "The execution timeline and final report are retained as Sprint evidence.",
            ],
            MARIANNA,
            SPRINT,
            "must",
            "Mission Execution PoC",
            remaining_work=8,
        ),
    )

    deterministic_story = r.create_item(
        parent_id=poc_feature,
        spec=spec(
            "User Story",
            "Extended deterministic concurrency and idempotency verification",
            "Extend the mandatory core tests into a complete deterministic test profile for race conditions, duplicate delivery, cancellation/result ordering, and reproducible scenario replay. The realistic simulation remains the primary Sprint 1.4 demonstration.",
            [
                "Fake time, stable IDs, and scripted results reproduce identical traces.",
                "Concurrent duplicate tick/result tests prove exactly-once queue effects.",
                "Cancellation/result and retry/result races have explicit outcomes.",
            ],
            KONSTANTINOS,
            QUARTER,
            "should",
            "Mission Execution PoC",
            story_points=5,
        ),
    )
    for task_spec in [
        spec(
            "Task",
            "Add deterministic providers and reproducible scenario scripts",
            "Add fake clock, deterministic IDs, and scripted robot outcomes that reproduce the same execution trace across runs.",
            ["The same seed/input produces the same IDs, transitions, and report."],
            KONSTANTINOS,
            QUARTER,
            "should",
            "Mission Execution PoC",
            remaining_work=8,
        ),
        spec(
            "Task",
            "Test duplicate and concurrent queue effects",
            "Test concurrent ticks, duplicate feedback/results, and duplicate retry requests against the repository contract.",
            ["Every logical effect is applied once and conflicts are typed."],
            KONSTANTINOS,
            QUARTER,
            "should",
            "Mission Execution PoC",
            remaining_work=10,
        ),
        spec(
            "Task",
            "Test cancellation, terminal-result, and retry races",
            "Define and verify deterministic outcomes when cancellation, late results, and retries overlap.",
            ["Late or conflicting outcomes never advance or reopen a terminal queue item."],
            KONSTANTINOS,
            QUARTER,
            "should",
            "Mission Execution PoC",
            remaining_work=10,
        ),
    ]:
        r.create_item(parent_id=deterministic_story, spec=task_spec)

    production_state_story = r.create_item(
        parent_id=poc_feature,
        spec=spec(
            "User Story",
            "Production Runtime State projection boundary",
            "After the standalone simulation profile is proven, define the Mission-Execution-owned outbound port used to publish active Plan, session, logical action, and attempt projections to an external runtime-state provider. The standalone PoC continues to use its own repository and does not depend on this boundary.",
            [
                "The outbound port and DTOs are owned by Mission Execution.",
                "Revision expectations, idempotency, and typed failures are explicit.",
                "No Runtime State domain, StateBackend, blackboard, or concrete adapter type leaks into the capability.",
                "The Story is mandatory for full central integration but remains outside Sprint 1.4.",
            ],
            MARIANNA,
            QUARTER,
            "must",
            "Mission Execution PoC",
            story_points=3,
        ),
    )
    r.reparent(item_id=658795, parent_id=production_state_story)
    r.update_item(
        658795,
        spec(
            "Task",
            "Define Mission Execution Runtime State projection port",
            "Define consumer-owned DTOs and Protocols for guarded active-Plan access and execution/session/action projection updates after the standalone core model is stable.",
            [
                "The contract exposes no StateBackend, Runtime State domain, adapter, or blackboard type.",
                "Expected ABSENT, exact revision, duplicate update, and infrastructure outcomes are typed.",
            ],
            MARIANNA,
            QUARTER,
            "must",
            "Mission Execution PoC",
            remaining_work=10,
        ),
    )

    activation_story = 588920
    r.reparent(item_id=activation_story, parent_id=CENTRAL_EXECUTION_FEATURE)
    r.update_item(
        activation_story,
        spec(
            "User Story",
            "Define central Plan read mapping and compatibility contracts",
            "Define how the central framework maps an exact persisted Mission Planning Plan into the standalone Mission Execution PlanReader/ExecutablePlanView boundary. Concrete provider bridges and activation orchestration remain follow-on backlog implementation and do not block the standalone PoC.",
            [
                "PlanReader requests exact mission_id, plan_id, and plan_version and returns an Execution-owned DTO.",
                "The DTO carries only execution-required action, assignment, sequence, route, and duration metadata.",
                "The mapping does not duplicate or redefine Mission Execution-owned DTOs.",
                "Central adapter code will import only provider and consumer public port contracts.",
                "Compatibility tests cover DTO shape, missing Plan, invalid references, and error mapping with fakes.",
            ],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            story_points=5,
        ),
    )
    r.update_item(
        658797,
        spec(
            "Task",
            "Define central GetMissionPlan-to-ExecutablePlanView mapping contract",
            "Define the exact central-framework mapping contract from Mission Planning's public GetMissionPlan DTO into the already published Mission-Execution-owned PlanReader/ExecutablePlanView contract, without redefining the target DTO or implementing the bridge.",
            [
                "Only execution-required Plan identity, sequence, actions, assignments, routes, and duration metadata cross the boundary.",
                "Missing Plan, invalid mapping, and infrastructure outcomes are typed and Execution-owned.",
                "No duplicate ExecutablePlanView or PlanReader Protocol is introduced in the central framework.",
                "The contract imports no Mission Planning domain, repository, or adapter type.",
            ],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            remaining_work=8,
        ),
    )
    r.update_item(
        658786,
        spec(
            "Task",
            "Add PlanReader mapping compatibility tests with fakes",
            "Add provider-independent compatibility tests for exact Plan reads, DTO mapping, missing/invalid Plan references, and error translation.",
            ["Tests require no network, event broker, database, or concrete provider adapter."],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            remaining_work=8,
        ),
    )

    bridge_story = 658787
    r.reparent(item_id=bridge_story, parent_id=CENTRAL_EXECUTION_FEATURE)
    r.update_item(
        bridge_story,
        spec(
            "User Story",
            "Define central Robot Operations mapping contract",
            "Define how the central framework will map between the standalone Mission Execution robot-operation port and Robot Abstraction's public inbound boundary. Concrete bridge implementation remains follow-on backlog work.",
            [
                "The Robot Operations mapping covers dispatch, asynchronous feedback, terminal result, and cancellation using ActionExecutionId correlation.",
                "Route metadata is represented without mutating action parameters.",
                "Port contract tests cover typed success, failure, duplicate, and cancellation outcomes with fakes.",
                "The standalone PoC continues to run against its own simulation adapters without these bridges.",
            ],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            story_points=3,
        ),
    )
    central_mapping_tasks = {
        658788: spec(
            "Task",
            "Define central Robot Operations-to-Mission Execution mapping contract",
            "Define the dispatch, feedback, terminal result, cancellation, and ActionExecutionId mapping between Robot Abstraction's public inbound contract and the published Mission Execution robot-operation port.",
            ["The mapping exposes no ActionHandle, RobotDriver, vendor, or concrete adapter type."],
            COSTAS,
            SPRINT,
            "must",
            "Central Framework",
            remaining_work=10,
        ),
    }
    for item_id, item_spec in central_mapping_tasks.items():
        r.reparent(item_id=item_id, parent_id=bridge_story)
        r.update_item(item_id, item_spec)

    implementation_bridge_story = r.create_item(
        parent_id=CENTRAL_EXECUTION_FEATURE,
        spec=spec(
            "User Story",
            "Implement Mission Execution central bridge adapters",
            "After the consumer-owned contracts are stable, implement the PlanReader, Runtime State, and Robot Operations bridge adapters and their mapping tests in the central framework.",
            [
                "Every bridge calls only the provider's public inbound contract.",
                "Provider DTOs and errors are translated at the consumer boundary.",
                "Bridge tests cover success, failure, duplicates, route preservation, and cancellation.",
                "The Story remains FY27Q1 backlog and does not block the standalone Sprint 1.4 PoC.",
            ],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            story_points=8,
        ),
    )
    implementation_bridge_tasks = {
        624266: spec(
            "Task",
            "Implement PlanReader Mission Planning query bridge",
            "Implement the consumer-owned bridge from the approved PlanReader contract to the central Mission Planning exact-version query boundary.",
            ["Only execution-required fields cross the bridge and provider errors map to Execution-owned errors."],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            remaining_work=16,
        ),
        599245: spec(
            "Task",
            "Implement active-Plan and execution projection Runtime State bridge",
            "Implement the bridge from the approved Mission Execution state contract to Runtime State inbound contracts with typed revision and infrastructure outcomes.",
            ["The bridge imports no Runtime State internals or outbound ports."],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            remaining_work=16,
        ),
        588929: spec(
            "Task",
            "Implement Robot Operations bridge for execution attempts",
            "Implement the bridge from the approved Mission Execution robot lifecycle contract to Robot Abstraction while preserving ActionExecutionId and route metadata.",
            ["No RobotDriver or concrete robot adapter is imported."],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            remaining_work=16,
        ),
        658789: spec(
            "Task",
            "Add central bridge adapter contract tests",
            "Add reusable mapping tests for Plan reads, state revisions, dispatch, feedback, terminal results, duplicate delivery, route preservation, and cancellation.",
            ["Every provider outcome maps to one typed Mission Execution outcome."],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            remaining_work=12,
        ),
    }
    for item_id, item_spec in implementation_bridge_tasks.items():
        r.reparent(item_id=item_id, parent_id=implementation_bridge_story)
        r.update_item(item_id, item_spec)

    deferred_story = r.create_item(
        parent_id=CENTRAL_EXECUTION_FEATURE,
        spec=spec(
            "User Story",
            "PlanReady consumption and durable activation recovery",
            "Complete production-oriented event consumption, durable PREPARING-session recovery, and outbox behavior after the first standalone PoC and synchronous central integration contracts are stable.",
            [
                "PlanReady consumption records availability without activating execution.",
                "Duplicate messages are idempotent by stable message identity.",
                "Activation recovery reconciles crash-after-CAS and atomically records the session-started outbox entry.",
                "This backlog Story does not block the Sprint 1.4 standalone demonstration.",
            ],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            story_points=5,
        ),
    )
    deferred_tasks = {
        588925: spec(
            "Task",
            "Implement Plan read and activation orchestration over owned ports",
            "Implement activation orchestration against PlanReader, ExecutionRepository, Runtime State activation, Clock, and event-publication abstractions after the contracts and bridges are stable.",
            [
                "Failed reads or preconditions create no executable session.",
                "Exact activation retries are idempotent.",
            ],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            remaining_work=16,
        ),
        624267: spec(
            "Task",
            "Consume PlanReady into available Plan candidates",
            "Implement the event consumer after the publication/transport contract is available. Deduplicate by message identity and record availability without activation side effects.",
            ["Duplicate delivery produces one candidate and no session or BT tick."],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            remaining_work=12,
        ),
        624269: spec(
            "Task",
            "Implement guarded activation recovery and session-started outbox",
            "Implement crash recovery around PREPARING, Runtime State CAS, session promotion, and atomic session-started outbox insertion.",
            ["Crash-after-CAS resumes safely and no incomplete session can dispatch."],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            remaining_work=20,
        ),
    }
    for item_id, item_spec in deferred_tasks.items():
        r.reparent(item_id=item_id, parent_id=deferred_story)
        r.update_item(item_id, item_spec)

    bootstrap_specs = {
        600319: spec(
            "User Story",
            "Compose Runtime State and Clock through the Bootstrap API",
            "Compose the implemented Runtime State application service, in-memory StateBackend, and SystemClock through the central Bootstrap API so Mission Execution bridge tests can use a real in-memory provider.",
            [
                "Container exposes Runtime State inbound ports rather than concrete adapters.",
                "The in-memory profile builds without network or external storage.",
                "Composition tests verify revision-guarded current-plan operations.",
            ],
            DIMITRIS,
            QUARTER,
            "must",
            "Central Framework",
            story_points=5,
        ),
        600320: spec(
            "User Story",
            "Compose Robot Abstraction logging profile through Bootstrap",
            "Compose Robot Operations, the dispatch ledger, and the logging RobotDriver through Bootstrap so central Mission Execution integration can dispatch and observe commands through port-typed boundaries.",
            [
                "The default in-memory profile exposes Robot Operations as an inbound port.",
                "Logging driver and ledger remain concrete only inside Bootstrap.",
                "Composition tests prove one dispatch effect for one ActionExecutionId.",
            ],
            COSTAS,
            QUARTER,
            "must",
            "Central Framework",
            story_points=3,
        ),
    }
    for item_id, item_spec in bootstrap_specs.items():
        r.reparent(item_id=item_id, parent_id=BOOTSTRAP_FEATURE)
        r.update_item(item_id, item_spec)

    bootstrap_tasks = {
        581479: (600319, DIMITRIS, 10),
        581480: (600319, DIMITRIS, 8),
        588882: (600319, DIMITRIS, 10),
        590834: (600319, DIMITRIS, 6),
        588898: (600320, COSTAS, 14),
    }
    for item_id, (parent_id, owner, hours) in bootstrap_tasks.items():
        current = r.wit.get_work_item(id=item_id)
        r.reparent(item_id=item_id, parent_id=parent_id)
        r.update_item(
            item_id,
            spec(
                "Task",
                current.fields.get("System.Title"),
                strip_html(current.fields.get("System.Description"))
                or "Implement and verify the central Bootstrap composition task.",
                ["The composition uses port-typed boundaries and leaks no concrete adapter from the Container API."],
                owner,
                QUARTER,
                "must",
                "Central Framework",
                remaining_work=hours,
            ),
        )

    r.update_item(
        588935,
        spec(
            "User Story",
            "Compose Mission Execution central integration and add E2E harness",
            "After the standalone capability and central bridges are stable, compose Mission Execution with Mission Planning, Runtime State, Robot Abstraction, and Bootstrap in the default in-memory profile and prove the complete validated-Plan-to-execution flow.",
            [
                "Bootstrap wires every service through ports and exposes no concrete adapter.",
                "The E2E harness reaches a terminal execution outcome with each command recorded once.",
                "The harness documents the canonical local integration command.",
                "This must-level project Story remains in FY27Q1 backlog and does not block the standalone Sprint 1.4 demonstration.",
            ],
            COSTAS,
            QUARTER,
            "must",
            "Central Framework",
            story_points=5,
        ),
    )
    for item_id, hours in {581492: 4, 588936: 20, 588937: 16, 588938: 6}.items():
        current = r.wit.get_work_item(id=item_id)
        r.update_item(
            item_id,
            spec(
                "Task",
                current.fields.get("System.Title"),
                strip_html(current.fields.get("System.Description"))
                or "Complete the central-framework E2E composition task.",
                ["The work remains in FY27Q1 backlog until all must-level integration contracts are stable."],
                COSTAS,
                QUARTER,
                "must",
                "Central Framework",
                remaining_work=hours,
            ),
        )

    r.update_item(
        590900,
        spec(
            "User Story",
            "Mission abort cascade with guaranteed cleanup",
            "After the initial PoC, orchestrate production cleanup through injected cancellation, reservation-release, and publication ports while isolating individual cleanup failures.",
            [
                "Cancellation, reservation release, and publication are attempted independently.",
                "Cleanup failures remain observable and do not skip later cleanup steps.",
                "The Story remains in FY27Q1 backlog and does not block Sprint 1.4.",
            ],
            COSTAS,
            QUARTER,
            "should",
            "Central Framework",
            story_points=5,
        ),
    )
    for item_id, hours in {590901: 12, 590902: 10}.items():
        current = r.wit.get_work_item(id=item_id)
        r.update_item(
            item_id,
            spec(
                "Task",
                current.fields.get("System.Title"),
                strip_html(current.fields.get("System.Description")) or "Implement and verify abort cleanup behavior.",
                ["The task remains a should-level FY27Q1 backlog item."],
                COSTAS,
                QUARTER,
                "should",
                "Central Framework",
                remaining_work=hours,
            ),
        )

    future_execution = {
        589090: (KONSTANTINOS, 3),
        589094: (MARIANNA, 5),
        589101: (KONSTANTINOS, 3),
    }
    r.update_item(
        589089,
        spec(
            "Feature",
            "Heterogeneous BT node semantics",
            "Future Mission Execution extensions for parallel decorators, isolated per-robot subtrees, affordance gating, and configurable failure propagation after the initial global serial PoC is proven.",
            ["The Feature remains could-level FY27Q1 backlog and does not expand Sprint 1.4 scope."],
            KONSTANTINOS,
            QUARTER,
            "could",
            "Central Framework",
        ),
    )
    for story_id, (owner, points) in future_execution.items():
        story = r.wit.get_work_item(id=story_id, expand="Relations")
        r.update_item(
            story_id,
            spec(
                "User Story",
                story.fields.get("System.Title"),
                strip_html(story.fields.get("System.Description")) or "Future heterogeneous Mission Execution behavior.",
                ["The Story remains could-level FY27Q1 backlog until the serial execution profile is complete."],
                owner,
                QUARTER,
                "could",
                "Central Framework",
                story_points=points,
            ),
        )
        task_ids = [
            int(relation.url.rstrip("/").rsplit("/", 1)[-1])
            for relation in story.relations or []
            if relation.rel == "System.LinkTypes.Hierarchy-Forward"
        ]
        for task_id in task_ids:
            task = r.wit.get_work_item(id=task_id)
            r.update_item(
                task_id,
                spec(
                    "Task",
                    task.fields.get("System.Title"),
                    strip_html(task.fields.get("System.Description"))
                    or "Implement the future Mission Execution extension.",
                    ["The Task remains could-level FY27Q1 backlog."],
                    owner,
                    QUARTER,
                    "could",
                    "Central Framework",
                    remaining_work=8,
                ),
            )

    r.set_predecessors(successor_id=repository_story, predecessor_ids=set())
    r.set_predecessors(successor_id=input_boundary_story, predecessor_ids={repository_story})
    r.set_predecessors(successor_id=core_story, predecessor_ids={input_boundary_story})
    r.set_predecessors(successor_id=bt_story, predecessor_ids={core_story})
    r.set_predecessors(successor_id=simulation_story, predecessor_ids={core_story, bt_story})
    r.set_predecessors(successor_id=production_state_story, predecessor_ids={core_story})
    r.set_predecessors(successor_id=activation_story, predecessor_ids={provider_audit_story, input_boundary_story})
    r.set_predecessors(successor_id=bridge_story, predecessor_ids={provider_audit_story, core_story})
    r.set_predecessors(successor_id=658797, predecessor_ids={659586, 658775})
    r.set_predecessors(successor_id=658786, predecessor_ids={658797})
    r.set_predecessors(successor_id=658788, predecessor_ids={659588, 659425})
    r.set_predecessors(successor_id=658795, predecessor_ids={659587, core_story})
    r.set_predecessors(
        successor_id=implementation_bridge_story,
        predecessor_ids={activation_story, bridge_story, production_state_story, 588873, 588893},
    )
    r.set_predecessors(successor_id=deferred_story, predecessor_ids={activation_story})
    r.set_predecessors(
        successor_id=588935,
        predecessor_ids={
            activation_story,
            implementation_bridge_story,
            600319,
            600320,
            core_story,
            bt_story,
            simulation_story,
        },
    )

    # Standalone repository and capability task-level critical path.
    task_predecessors: dict[int, set[int]] = {
        659590: set(),
        659591: {659590},
        659592: {659591},
        659593: {659591},
        588921: {659591},
        588923: {588921},
        658775: {588921},
        599243: {588921},
        599244: {599243},
        624268: {599243, 658775},
        659425: {624268, 658775},
        588928: {659425},
        588927: {588928, 659425},
        658776: {588928, 599243},
        658778: {659591},
        658779: {659425},
        658780: {588927, 624268, 658778, 658779},
        588931: {658776, 658780},
        658781: {588931},
        658783: {659591},
        658784: {624268, 659425},
        658785: {658776, 658779, 659425},
        658795: {599243, 659587},
        # The provider inventories are intentionally independent and can start now.
        659586: set(),
        659587: set(),
        659588: set(),
        # Central mappings wait for both provider and consumer contract inputs.
        658797: {658775, 659586},
        658786: {658797},
        658788: {659425, 659588},
        # Concrete bridges and recovery are mandatory follow-on backlog work.
        624266: {658786},
        599245: {658795, 659587},
        588929: {588893, 658788},
        658789: {588929, 599245, 624266},
        588925: {588923, 599245, 624266, 624268},
        624267: {590899, 599238},
        624269: {588925, 599245, 624268},
        # Bootstrap and complete central E2E composition.
        581479: {588876},
        581480: {581479},
        588882: {588876},
        590834: {581479},
        588898: {588893},
        581492: set(),
        588936: {588925, 588929, 599245, 600319, 600320, 624266},
        588937: {588936, 624267, 624269},
        588938: {588937},
        # Production abort cleanup.
        590901: {588902, 588929, 599238},
        590902: {590901},
        # Future parallel and heterogeneous BT extensions.
        589091: {588928},
        589092: {588928},
        589093: {589091, 589092},
        589095: {589091, 658775},
        589096: {658775},
        589098: {589095, 589096},
        589100: {588935, 589095},
        589103: {588928, 588998},
        589105: {589092, 589095},
        589107: {589103, 589105},
    }
    for task_id, predecessor_ids in task_predecessors.items():
        r.set_predecessors(successor_id=task_id, predecessor_ids=predecessor_ids)

    print("\nReconciliation complete.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    reconcile(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
