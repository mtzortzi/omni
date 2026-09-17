"""Update ADO work item fields (title, description, state, etc.).

Usage:
    uv run python update_item.py <id> --title "..." --description "<html>" --state "Active"
"""

from __future__ import annotations

import argparse

from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import AdoConfig, get_clients


FIELD_MAP = {
    "title": "/fields/System.Title",
    "description": "/fields/System.Description",
    "acceptance_criteria": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
    "state": "/fields/System.State",
    "tags": "/fields/System.Tags",  # semicolon-separated
    "assigned_to": "/fields/System.AssignedTo",
    "story_points": "/fields/Microsoft.VSTS.Scheduling.StoryPoints",
    "value_area": "/fields/Microsoft.VSTS.Common.ValueArea",
}

# Numeric fields — cast argparse string input to the correct type.
NUMERIC_FIELDS = {"story_points": int}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("work_item_id", type=int)
    for name in FIELD_MAP:
        ap.add_argument(f"--{name.replace('_', '-')}", type=str, default=None)
    ap.add_argument(
        "--parent",
        type=int,
        default=None,
        help="Re-parent to this work item id (removes existing Hierarchy-Reverse link first).",
    )
    args = ap.parse_args()

    cfg = AdoConfig.from_env()
    wit_client, _ = get_clients(cfg)

    patch: list[JsonPatchOperation] = []
    for name, path in FIELD_MAP.items():
        val = getattr(args, name)
        if val is not None:
            if name in NUMERIC_FIELDS:
                val = NUMERIC_FIELDS[name](val)
            patch.append(JsonPatchOperation(op="add", path=path, value=val))

    if args.parent is not None:
        current = wit_client.get_work_item(id=args.work_item_id, expand="Relations")
        for idx, rel in enumerate(current.relations or []):
            if rel.rel == "System.LinkTypes.Hierarchy-Reverse":
                patch.append(JsonPatchOperation(op="remove", path=f"/relations/{idx}"))
                break
        parent_wi = wit_client.get_work_item(id=args.parent)
        patch.append(
            JsonPatchOperation(
                op="add",
                path="/relations/-",
                value={
                    "rel": "System.LinkTypes.Hierarchy-Reverse",
                    "url": parent_wi.url,
                    "attributes": {"name": "Parent"},
                },
            )
        )

    if not patch:
        raise SystemExit("Nothing to update — provide at least one field or --parent.")

    wi = wit_client.update_work_item(document=patch, id=args.work_item_id)
    print(f"  [OK] updated #{wi.id}")


if __name__ == "__main__":
    main()
