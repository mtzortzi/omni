"""Create ADO work items from a gap-analysis YAML.

YAML shape (subset):

    new_epics:
      - title: str
        description: str
        acceptance_criteria: [str, ...]     # rendered as bullet list
        features:
          - title, description, acceptance_criteria, user_stories: [...]
            user_stories:
              - title, description, acceptance_criteria, tasks: [...]
                tasks:
                  - title, description                     # AC optional

    new_features:
      - parent_epic_id: int
        title, description, acceptance_criteria, user_stories: [...]

    additions_to_existing:
      - parent_id: int
        new_children:
          - type: "Epic" | "Feature" | "User Story" | "Task"
            title, description, acceptance_criteria?      # optional
            user_stories? / tasks?                         # optional nested

Usage:

    uv run python create_items.py path/to/gap_analysis.yaml --dry-run
    uv run python create_items.py path/to/gap_analysis.yaml            # actually creates

Requires PAT with **Work Items → Read & Write**.
"""

from __future__ import annotations

import argparse
import html
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import AdoConfig, get_clients


DEFAULT_ENGAGEMENT_ID = 537616  # EY - Robots in Action


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def to_html(text: str | None) -> str:
    """Convert plain-text description/AC into minimal safe HTML for ADO."""
    if not text:
        return ""
    escaped = html.escape(text.strip())
    # preserve paragraph-ish line breaks
    paragraphs = [p.strip() for p in escaped.split("\n\n") if p.strip()]
    return "".join(f"<div>{p.replace(chr(10), '<br>')}</div>" for p in paragraphs)


def ac_to_html(items: list[str] | None) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{html.escape(str(i).strip())}</li>" for i in items)
    return f"<ul>{lis}</ul>"


def add(patch: list[JsonPatchOperation], path: str, value: Any) -> None:
    patch.append(JsonPatchOperation(op="add", path=path, value=value))


def build_patch(
    title: str,
    description: str | None,
    acceptance_criteria: list[str] | None,
    parent_url: str | None,
) -> list[JsonPatchOperation]:
    patch: list[JsonPatchOperation] = []
    add(patch, "/fields/System.Title", title)
    if description:
        add(patch, "/fields/System.Description", to_html(description))
    if acceptance_criteria:
        add(
            patch,
            "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
            ac_to_html(acceptance_criteria),
        )
    if parent_url:
        add(
            patch,
            "/relations/-",
            {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": parent_url,
                "attributes": {"name": "Parent"},
            },
        )
    return patch


@dataclass
class Ctx:
    wit_client: Any
    project: str
    org_url: str
    dry_run: bool
    created: list[tuple[str, str, int | None, str]]  # (type, title, id, parent)
    area_path: str | None = None
    iteration_path: str | None = None

    def item_url(self, item_id: int) -> str:
        # Full REST URL required by relations
        return f"{self.org_url}/{self.project}/_apis/wit/workItems/{item_id}"


# Fields expected to be non-empty by many ADO process templates.
# Add safe defaults per work item type to survive validation rules.
TYPE_DEFAULT_FIELDS: dict[str, dict[str, Any]] = {
    "User Story": {
        "Microsoft.VSTS.Scheduling.StoryPoints": 3,
        "Microsoft.VSTS.Common.ValueArea": "Architectural",
    },
    "Product Backlog Item": {
        "Microsoft.VSTS.Scheduling.Effort": 0,
        "Microsoft.VSTS.Common.ValueArea": "Business",
    },
    "Feature": {"Microsoft.VSTS.Common.ValueArea": "Business"},
    "Epic": {"Microsoft.VSTS.Common.ValueArea": "Business"},
}


def create(
    ctx: Ctx,
    wi_type: str,
    title: str,
    description: str | None,
    acceptance_criteria: list[str] | None,
    parent_id: int | None,
    field_overrides: dict[str, Any] | None = None,
) -> int | None:
    parent_desc = f"#{parent_id}" if parent_id else "-"
    if ctx.dry_run:
        ctx.created.append((wi_type, title, None, parent_desc))
        extra = ""
        if field_overrides:
            extra = "  " + " ".join(f"{k.split('.')[-1]}={v}" for k, v in field_overrides.items())
        print(f"  [DRY]  create {wi_type:<11} under {parent_desc:<8}  {title[:80]}{extra}")
        return None

    parent_url = ctx.item_url(parent_id) if parent_id else None
    patch = build_patch(title, description, acceptance_criteria, parent_url)
    if ctx.area_path:
        add(patch, "/fields/System.AreaPath", ctx.area_path)
    if ctx.iteration_path:
        add(patch, "/fields/System.IterationPath", ctx.iteration_path)
    # Type defaults first; overrides win.
    merged_fields: dict[str, Any] = dict(TYPE_DEFAULT_FIELDS.get(wi_type, {}))
    if field_overrides:
        merged_fields.update(field_overrides)
    for fname, fval in merged_fields.items():
        add(patch, f"/fields/{fname}", fval)
    try:
        wi = ctx.wit_client.create_work_item(document=patch, project=ctx.project, type=wi_type)
    except Exception as e:  # noqa: BLE001
        print(f"  [ERROR] {wi_type} '{title[:60]}': {e}", file=sys.stderr)
        return None
    ctx.created.append((wi_type, title, wi.id, parent_desc))
    print(f"  [OK]   #{wi.id:<7} {wi_type:<11} under {parent_desc:<8}  {title[:80]}")
    return wi.id


# ---------------------------------------------------------------------------
# YAML walkers
# ---------------------------------------------------------------------------


def handle_tasks(ctx: Ctx, parent_id: int | None, tasks: list[dict] | None) -> None:
    for t in tasks or []:
        create(
            ctx,
            wi_type="Task",
            title=t["title"],
            description=t.get("description"),
            acceptance_criteria=t.get("acceptance_criteria"),
            parent_id=parent_id,
        )


def handle_user_stories(ctx: Ctx, parent_id: int | None, stories: list[dict] | None) -> None:
    for s in stories or []:
        overrides: dict[str, Any] = {}
        sp = s.get("story_points")
        if sp is not None:
            if sp not in (1, 2, 3, 5, 8):
                print(f"  [WARN] story_points={sp} not in {{1,2,3,5,8}} for '{s['title'][:60]}'", file=sys.stderr)
            overrides["Microsoft.VSTS.Scheduling.StoryPoints"] = sp
        va = s.get("value_area")
        if va:
            overrides["Microsoft.VSTS.Common.ValueArea"] = va
        story_id = create(
            ctx,
            wi_type="User Story",
            title=s["title"],
            description=s.get("description"),
            acceptance_criteria=s.get("acceptance_criteria"),
            parent_id=parent_id,
            field_overrides=overrides or None,
        )
        handle_tasks(ctx, story_id, s.get("tasks"))


def handle_features(ctx: Ctx, parent_id: int | None, features: list[dict] | None) -> None:
    for f in features or []:
        feat_id = create(
            ctx,
            wi_type="Feature",
            title=f["title"],
            description=f.get("description"),
            acceptance_criteria=f.get("acceptance_criteria"),
            parent_id=parent_id,
        )
        handle_user_stories(ctx, feat_id, f.get("user_stories"))


def handle_new_epics(ctx: Ctx, engagement_id: int, epics: list[dict] | None) -> None:
    for e in epics or []:
        epic_id = create(
            ctx,
            wi_type="Epic",
            title=e["title"],
            description=e.get("description"),
            acceptance_criteria=e.get("acceptance_criteria"),
            parent_id=engagement_id,
        )
        handle_features(ctx, epic_id, e.get("features"))


def handle_new_features(ctx: Ctx, features: list[dict] | None) -> None:
    for f in features or []:
        parent_epic_id = int(f["parent_epic_id"])
        feat_id = create(
            ctx,
            wi_type="Feature",
            title=f["title"],
            description=f.get("description"),
            acceptance_criteria=f.get("acceptance_criteria"),
            parent_id=parent_epic_id,
        )
        handle_user_stories(ctx, feat_id, f.get("user_stories"))


def handle_addition_child(ctx: Ctx, parent_id: int, child: dict) -> None:
    wi_type = child["type"]
    child_id = create(
        ctx,
        wi_type=wi_type,
        title=child["title"],
        description=child.get("description"),
        acceptance_criteria=child.get("acceptance_criteria"),
        parent_id=parent_id,
    )
    # nested — supports "user_stories" or "tasks" (or generic "new_children")
    handle_user_stories(ctx, child_id, child.get("user_stories"))
    handle_tasks(ctx, child_id, child.get("tasks"))
    for grand in child.get("new_children") or []:
        handle_addition_child(ctx, child_id, grand) if child_id else None


def handle_additions(ctx: Ctx, additions: list[dict] | None) -> None:
    for a in additions or []:
        parent_id = int(a["parent_id"])
        for child in a.get("new_children") or []:
            handle_addition_child(ctx, parent_id, child)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("yaml_path", type=Path)
    ap.add_argument(
        "--engagement-id",
        type=int,
        default=DEFAULT_ENGAGEMENT_ID,
        help="Parent engagement work item ID (default: %(default)s)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without hitting the API",
    )
    ap.add_argument(
        "--only",
        choices=["epics", "features", "additions"],
        help="Run only one section",
    )
    ap.add_argument(
        "--epic-title-contains",
        type=str,
        default=None,
        help="Only new_epics whose title contains this substring (case-insensitive)",
    )
    args = ap.parse_args()

    if not args.yaml_path.is_file():
        sys.exit(f"YAML not found: {args.yaml_path}")

    with args.yaml_path.open() as fh:
        data = yaml.safe_load(fh)

    cfg = AdoConfig.from_env()
    wit_client, _ = get_clients(cfg)

    # Inherit area/iteration path from the engagement so children land in the
    # right team area and pass area-path permission checks.
    engagement = wit_client.get_work_item(id=args.engagement_id)
    area_path = engagement.fields.get("System.AreaPath")
    iteration_path = engagement.fields.get("System.IterationPath")

    ctx = Ctx(
        wit_client=wit_client,
        project=cfg.project,
        org_url=cfg.org_url,
        dry_run=args.dry_run,
        created=[],
        area_path=area_path,
        iteration_path=iteration_path,
    )

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"=== {mode} — engagement #{args.engagement_id} — {args.yaml_path.name} ===\n")
    print(f"AreaPath      : {area_path}")
    print(f"IterationPath : {iteration_path}\n")

    if args.only in (None, "epics"):
        print("-- new_epics --")
        epics = data.get("new_epics") or []
        if args.epic_title_contains:
            needle = args.epic_title_contains.lower()
            epics = [e for e in epics if needle in e.get("title", "").lower()]
            print(f"  (filtered to {len(epics)} epic(s) matching '{args.epic_title_contains}')")
        handle_new_epics(ctx, args.engagement_id, epics)
    if args.only in (None, "features"):
        print("\n-- new_features --")
        handle_new_features(ctx, data.get("new_features"))
    if args.only in (None, "additions"):
        print("\n-- additions_to_existing --")
        handle_additions(ctx, data.get("additions_to_existing"))

    print(f"\n=== {mode} DONE — {len(ctx.created)} items ===")


if __name__ == "__main__":
    main()
