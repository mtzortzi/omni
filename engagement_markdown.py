"""Export the engagement tree as Markdown.

Usage:
    uv run python engagement_markdown.py 537616 > engagement.md
"""

from __future__ import annotations

import sys

from ado_client import AdoConfig, get_clients
from engagement_tree import (
    TYPE_ORDER,
    fetch_tree,
    strip_html,
)

# Map work item type -> markdown heading level (H1 reserved for engagement)
HEADING_LEVEL = {
    "Engagement": 1,
    "Epic": 2,
    "Feature": 3,
    "User Story": 4,
    "Product Backlog Item": 4,
    "Task": 5,
    "Bug": 5,
}


def render_node(
    node, children_of, nodes, org_url: str, project: str, out: list[str]
) -> None:
    f = node.fields
    wtype = f.get("System.WorkItemType", "Item")
    level = HEADING_LEVEL.get(wtype, 6)
    state = f.get("System.State", "?")
    assignee = f.get("System.AssignedTo", {})
    name = (
        assignee.get("displayName") if isinstance(assignee, dict) else None
    ) or "Unassigned"
    title = f.get("System.Title", "")
    iteration_path = f.get("System.IterationPath", "Unscheduled")
    link = f"{org_url}/{project}/_workitems/edit/{node.id}"

    out.append(f"{'#' * level} [{wtype}] {title}")
    out.append("")
    out.append(f"- **ID:** [#{node.id}]({link})")
    out.append(f"- **State:** {state}")
    out.append(f"- **Assignee:** {name}")
    out.append(f"- **Iteration:** `{iteration_path}`")
    out.append("")

    desc = strip_html(f.get("System.Description"))
    if desc:
        out.append("**Description**")
        out.append("")
        out.append(desc)
        out.append("")

    ac = strip_html(f.get("Microsoft.VSTS.Common.AcceptanceCriteria"))
    if ac:
        out.append("**Acceptance Criteria**")
        out.append("")
        out.append(ac)
        out.append("")

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
        render_node(child, children_of, nodes, org_url, project, out)


def main() -> None:
    root_id = int(sys.argv[1]) if len(sys.argv) > 1 else 537616

    cfg = AdoConfig.from_env()
    wit_client, _ = get_clients(cfg)
    nodes, children_of = fetch_tree(wit_client, root_id)
    if root_id not in nodes:
        print(f"Root #{root_id} not found.")
        return

    out: list[str] = []
    render_node(nodes[root_id], children_of, nodes, cfg.org_url, cfg.project, out)
    print("\n".join(out))


if __name__ == "__main__":
    main()
