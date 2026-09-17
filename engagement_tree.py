"""Print the full Epic > Feature > User Story > Task tree under an engagement,
including Description and Acceptance Criteria.

Usage:
    uv run python engagement_tree.py 537616
    uv run python engagement_tree.py 537616 > tree.txt
"""

from __future__ import annotations

import html
import re
import sys
from collections import defaultdict

from azure.devops.v7_1.work_item_tracking.models import Wiql

from ado_client import AdoConfig, get_clients

BATCH_SIZE = 200
FIELDS = [
    "System.Id",
    "System.Title",
    "System.WorkItemType",
    "System.State",
    "System.AssignedTo",
    "System.IterationPath",
    "System.AreaPath",
    "System.Parent",
    "System.Tags",
    "Microsoft.VSTS.Scheduling.StoryPoints",
    "Microsoft.VSTS.Scheduling.RemainingWork",
    "System.Description",
    "Microsoft.VSTS.Common.AcceptanceCriteria",
]

# Rough ordering when siblings share a parent
TYPE_ORDER = {
    "Epic": 0,
    "Feature": 1,
    "User Story": 2,
    "Product Backlog Item": 2,
    "Task": 3,
    "Bug": 3,
}


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    # replace <br>, </p>, </div> with newlines
    s = re.sub(r"(?i)<\s*(br|/p|/div|/li)\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    # collapse >2 blank lines
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def fetch_tree(wit_client, root_id: int):
    """Return (nodes_by_id, children_of) using recursive hierarchy links."""
    wiql = Wiql(
        query=f"""
            SELECT [System.Id]
            FROM WorkItemLinks
            WHERE [Source].[System.Id] = {root_id}
              AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward'
            MODE (Recursive)
        """
    )
    result = wit_client.query_by_wiql(wiql)
    relations = result.work_item_relations or []

    all_ids: set[int] = {root_id}
    children_of: dict[int, list[int]] = defaultdict(list)
    for rel in relations:
        if rel.target and rel.target.id:
            all_ids.add(rel.target.id)
        if rel.source and rel.target and rel.source.id and rel.target.id:
            children_of[rel.source.id].append(rel.target.id)

    # fetch fields in batches
    ids = sorted(all_ids)
    items = []
    for i in range(0, len(ids), BATCH_SIZE):
        items.extend(
            wit_client.get_work_items(ids=ids[i : i + BATCH_SIZE], fields=FIELDS)
        )
    nodes = {wi.id: wi for wi in items}
    return nodes, children_of


def print_node(node, children_of, nodes, depth: int = 0) -> None:
    f = node.fields
    pad = "  " * depth
    wtype = f.get("System.WorkItemType", "?")
    state = f.get("System.State", "?")
    assignee = f.get("System.AssignedTo", {})
    name = (
        assignee.get("displayName") if isinstance(assignee, dict) else None
    ) or "Unassigned"
    title = f.get("System.Title", "")
    iteration_path = f.get("System.IterationPath", "Unscheduled")

    print(f"{pad}[{wtype}] #{node.id}  {state}  ({name})")
    print(f"{pad}  Title: {title}")
    print(f"{pad}  Iteration: {iteration_path}")

    desc = strip_html(f.get("System.Description"))
    if desc:
        print(f"{pad}  Description:")
        print(indent(desc, pad + "    "))

    ac = strip_html(f.get("Microsoft.VSTS.Common.AcceptanceCriteria"))
    if ac:
        print(f"{pad}  Acceptance Criteria:")
        print(indent(ac, pad + "    "))

    print()

    kids = children_of.get(node.id, [])
    kids_sorted = sorted(
        (nodes[k] for k in kids if k in nodes),
        key=lambda w: (
            TYPE_ORDER.get(w.fields.get("System.WorkItemType", ""), 99),
            w.fields.get("System.State", ""),
            w.id,
        ),
    )
    for child in kids_sorted:
        print_node(child, children_of, nodes, depth + 1)


def main() -> None:
    root_id = int(sys.argv[1]) if len(sys.argv) > 1 else 537616

    cfg = AdoConfig.from_env()
    wit_client, _ = get_clients(cfg)

    nodes, children_of = fetch_tree(wit_client, root_id)
    if root_id not in nodes:
        print(f"Root #{root_id} not found.")
        return

    total = len(nodes)
    print(f"Engagement tree rooted at #{root_id} — {total} work items total\n")
    print("=" * 80)
    print()
    print_node(nodes[root_id], children_of, nodes, depth=0)


if __name__ == "__main__":
    main()
