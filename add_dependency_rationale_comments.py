"""Create or replace dependency rationale comments in English."""

from __future__ import annotations

import html
import re

import requests
from requests.auth import HTTPBasicAuth

from add_comment import add_comment
from ado_client import AdoConfig, get_clients
from engagement_tree import fetch_tree


ENGAGEMENT_ID = 537616
SCOPED_ROOTS = {658774, 588916, 588934, 589089}
HEADING = "Dependency rationale"
LEGACY_HEADING = "Αιτιολόγηση εξάρτησης"
GREEK_TEXT = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")

ROOT_RATIONALES = {
    581492: "This task has no predecessor. It independently verifies that Bootstrap remains correctly exempt from the adapter-import architecture rule.",
    659586: "This task has no predecessor and can start immediately. It is a read-only inventory of the existing Mission Planning public contracts and identified gaps.",
    659587: "This task has no predecessor and can start immediately. It is a read-only inventory of the existing Runtime State public contracts and identified gaps.",
    659588: "This task has no predecessor and can start immediately. It is a read-only inventory of the existing Robot Operations public contracts and identified gaps.",
    659590: "This task has no predecessor and is the first standalone-capability step. The canonical GitHub repository and team access must be established before package initialization.",
}

TASK_RATIONALES = {
    581479: "The real Runtime State application service must exist before Bootstrap can compose it.",
    581480: "The Runtime State composition path must be implemented before its object graph and port-typed wiring can be tested.",
    588882: "Runtime State services and public ports must be stable before their Bootstrap wiring is added.",
    588898: "The Robot Abstraction service and logging profile must be complete before Bootstrap can compose them.",
    588921: "The Plan identity objects must be implemented inside the agreed package and hexagonal structure of the new repository.",
    588923: "The activation Protocol uses the Plan identity and activation value objects, so those types must be stable first.",
    588925: "Activation orchestration consumes the published activation contract, PlanReader bridge, Runtime State bridge, and ExecutionRepository semantics.",
    588927: "The asynchronous tick loop requires both the executable BT nodes and the Mission Execution action-orchestration boundary.",
    588928: "BT action leaves must delegate to the stable action-consumption service rather than owning dispatch or queue logic.",
    588929: "The Robot Operations bridge requires both the central Robot Abstraction provider and the approved execution-to-robot mapping contract.",
    588931: "The canonical demonstration requires the failure-control branches and the complete scenario runner before it can prove recovery behavior.",
    588936: "The complete composition can only be assembled after activation, all three bridges, and both provider Bootstrap profiles are available.",
    588937: "The end-to-end test requires a complete composition plus PlanReady consumption and guarded activation recovery.",
    588938: "The documented command must be based on the execution path already verified by the end-to-end test.",
    589091: "The Parallel node extends the basic BT node model and shared status semantics.",
    589092: "Parallel policy configuration must align with the established BT node and result semantics.",
    589093: "Policy tests require both the Parallel node implementation and the policy configuration model.",
    589095: "Per-robot subtree construction requires the Parallel-node model and the stable executable Plan contract with robot assignments.",
    589096: "The two-robot fixture must conform to the published ExecutablePlanView contract.",
    589098: "Isolation assertions require both the implemented subtree factory and the two-robot fixture.",
    589100: "Parallel subtree wiring requires the stable production Bootstrap pattern and an implemented subtree factory.",
    589103: "The affordance decorator extends the base BT node model and requires the stable AffordanceManifest model.",
    589105: "Failure-propagation plumbing requires the policy model and the per-robot subtree structure through which the policy is propagated.",
    589107: "These tests exercise the completed affordance-gate and propagation-policy implementations.",
    590834: "The composition root can be updated only after the real Runtime State slice has been composed.",
    590901: "Abort cleanup requires the Fleet release boundary, robot cancellation bridge, and event-publication boundary.",
    590902: "The chaos test must exercise the completed abort cascade and its failure-isolation guarantees.",
    599243: "Execution sessions and action attempts must reference a stable exact Plan identity.",
    599244: "Transition tests require the actual state guards and typed errors they are intended to verify.",
    599245: "The Runtime State bridge requires the Mission-Execution-owned projection port and a reviewed inventory of the provider contract.",
    624266: "Bridge implementation must follow the approved and compatibility-tested PlanReader mapping contract.",
    624267: "PlanReady consumption requires the public event-publication and versioned transport-message boundary.",
    624268: "The repository and global queue must persist the agreed execution state model and implement the published queue contract.",
    624269: "Guarded recovery requires activation orchestration, Runtime State CAS mapping, and repository support for PREPARING recovery and atomic promotion.",
    658775: "ExecutablePlanView, PlanReader requests, and queue entries must use the same stable exact Plan identity objects.",
    658776: "Retry, abort, and replan branches extend the basic BT failure model and must apply legal execution-state transitions.",
    658778: "The runnable simulation command must be implemented inside the initialized standalone package structure.",
    658779: "The simulator must implement the consumer-owned robot-operation boundary used by the action-orchestration service.",
    658780: "The scenario runner requires the BT loop, in-memory queue, runnable profile, and asynchronous simulator to be functional.",
    658781: "The business-value report must be generated from the canonical demonstration trace and actual execution outcomes.",
    658783: "Deterministic providers must be placed in the initialized package's shared test-support structure.",
    658784: "Concurrency and duplicate-effect tests require the real repository/queue and action-orchestration implementations.",
    658785: "Race-condition tests require the real failure branches, asynchronous simulator, and attempt/result orchestration.",
    658786: "Compatibility tests must verify the approved GetMissionPlan-to-ExecutablePlanView mapping contract.",
    658788: "The central mapping must combine the published Mission Execution robot-operation boundary with the inventoried Robot Operations provider surface.",
    658789: "Central bridge contract tests require all three concrete bridge implementations.",
    658795: "The projection port must be based on the stable execution state model and informed by the reviewed Runtime State provider surface.",
    658797: "The central Plan mapping requires both the published ExecutablePlanView contract and the Mission Planning Plan-read contract inventory.",
    659425: "Action consumption requires atomic repository/queue operations and the published get-next, claim, running, and completion semantics.",
    659591: "The package can be initialized only after the canonical repository exists and team access is available.",
    659592: "CI and required checks must use the actual pyproject, package layout, and test commands created during package initialization.",
    659593: "Repository documentation must describe the actual package structure and quality commands created during initialization.",
}


def descendants(children: dict[int, list[int]], root_ids: set[int]) -> set[int]:
    result: set[int] = set()
    stack = list(root_ids)
    while stack:
        item_id = stack.pop()
        if item_id in result:
            continue
        result.add(item_id)
        stack.extend(children.get(item_id, []))
    return result


def comments_url(cfg: AdoConfig, task_id: int) -> str:
    return f"{cfg.org_url}/{cfg.project}/_apis/wit/workItems/{task_id}/comments"


def get_comments(cfg: AdoConfig, task_id: int) -> list[dict[str, object]]:
    response = requests.get(
        comments_url(cfg, task_id),
        params={"api-version": "7.1-preview.4"},
        auth=HTTPBasicAuth("", cfg.pat),
        timeout=30,
    )
    response.raise_for_status()
    return list(response.json().get("comments", []))


def update_comment(cfg: AdoConfig, task_id: int, comment_id: int, text: str) -> None:
    response = requests.patch(
        f"{comments_url(cfg, task_id)}/{comment_id}",
        params={"api-version": "7.1-preview.4"},
        auth=HTTPBasicAuth("", cfg.pat),
        json={"text": text},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()


def build_comment(task_id: int, title: str, predecessors: set[int], nodes: dict[int, object], wit: object) -> str:
    if not predecessors:
        return f"<b>{HEADING}</b><br>{html.escape(ROOT_RATIONALES[task_id])}"

    items = []
    for predecessor_id in sorted(predecessors):
        predecessor = nodes.get(predecessor_id)
        predecessor_title = (
            predecessor.fields.get("System.Title")
            if predecessor is not None
            else wit.get_work_item(id=predecessor_id).fields.get("System.Title")
        )
        items.append(f"<li><b>#{predecessor_id} - {html.escape(predecessor_title)}</b></li>")
    return (
        f"<b>{HEADING}</b><br>Task <b>#{task_id} - {html.escape(title)}</b> depends on the following "
        f"immediate predecessor work items:<ul>{''.join(items)}</ul>"
        f"<b>Reason:</b> {html.escape(TASK_RATIONALES[task_id])}<br>"
        "Implementation should begin after these predecessor deliverables are stable to avoid duplicate contracts, "
        "temporary mappings, and rework."
    )


def main() -> None:
    cfg = AdoConfig.from_env()
    wit, _ = get_clients(cfg)
    nodes, children = fetch_tree(wit, ENGAGEMENT_ID)
    scoped_ids = descendants(children, SCOPED_ROOTS)
    task_ids = {
        item_id
        for item_id in scoped_ids
        if nodes.get(item_id) is not None and nodes[item_id].fields.get("System.WorkItemType") == "Task"
    }

    predecessors: dict[int, set[int]] = {}
    for task_id in sorted(task_ids):
        item = wit.get_work_item(id=task_id, expand="Relations")
        predecessors[task_id] = {
            int(relation.url.rstrip("/").rsplit("/", 1)[-1])
            for relation in item.relations or []
            if relation.rel == "System.LinkTypes.Dependency-Reverse"
        }

    errors = []
    for task_id, task_predecessors in predecessors.items():
        if task_predecessors and task_id not in TASK_RATIONALES:
            errors.append(f"#{task_id} has predecessors but no English rationale")
        if not task_predecessors and task_id not in ROOT_RATIONALES:
            errors.append(f"#{task_id} has no predecessor and no English root rationale")
    if errors:
        raise RuntimeError("Dependency rationale validation failed:\n" + "\n".join(errors))

    created = 0
    updated = 0
    unchanged = 0
    for task_id in sorted(task_ids):
        title = nodes[task_id].fields.get("System.Title")
        expected = build_comment(task_id, title, predecessors[task_id], nodes, wit)
        comments = get_comments(cfg, task_id)
        rationale_comments = [
            comment
            for comment in comments
            if HEADING in str(comment.get("text") or "") or LEGACY_HEADING in str(comment.get("text") or "")
        ]
        if not rationale_comments:
            add_comment(cfg, task_id, expected)
            created += 1
            continue

        current = rationale_comments[0]
        current_text = str(current.get("text") or "")
        if current_text == expected and GREEK_TEXT.search(current_text) is None:
            unchanged += 1
            continue
        update_comment(cfg, task_id, int(current["id"]), expected)
        print(f"  [OK] dependency rationale updated for #{task_id}")
        updated += 1

    print(f"Created {created}, updated {updated}, unchanged {unchanged} dependency rationale comments.")


if __name__ == "__main__":
    main()
