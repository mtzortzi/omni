"""Batch-apply modifications to existing ADO work items.

Reads modifications.yaml, patches each item via the ADO SDK. Supports
--dry-run to print intended patches without hitting the API.

Usage:
    uv run python apply_modifications.py [--dry-run] [--file modifications.yaml]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from azure.devops.exceptions import AzureDevOpsServiceError
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation

from ado_client import AdoConfig, get_clients
from create_items import to_html, ac_to_html


ALLOWED_TYPES = {"Epic", "Feature", "User Story"}
ALLOWED_SP = {1, 2, 3, 5, 8}
ALLOWED_VA = {"Architectural"}


def build_patch(entry: dict) -> list[JsonPatchOperation]:
    patch: list[JsonPatchOperation] = []

    def add(path: str, value: Any) -> None:
        patch.append(JsonPatchOperation(op="add", path=path, value=value))

    if "title" in entry and entry["title"] is not None:
        add("/fields/System.Title", entry["title"])
    if "description" in entry and entry["description"] is not None:
        add("/fields/System.Description", to_html(entry["description"]))
    if "acceptance_criteria" in entry and entry["acceptance_criteria"]:
        add(
            "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
            ac_to_html(entry["acceptance_criteria"]),
        )
    if "story_points" in entry and entry["story_points"] is not None:
        add("/fields/Microsoft.VSTS.Scheduling.StoryPoints", int(entry["story_points"]))
    if "value_area" in entry and entry["value_area"] is not None:
        add("/fields/Microsoft.VSTS.Common.ValueArea", entry["value_area"])
    return patch


def validate_entry(entry: dict) -> str | None:
    """Return an error string if invalid; None if OK."""
    if "id" not in entry:
        return "missing 'id'"
    if entry.get("type") not in ALLOWED_TYPES:
        return f"type must be one of {ALLOWED_TYPES}, got {entry.get('type')!r}"
    if "story_points" in entry and entry["story_points"] not in ALLOWED_SP:
        return f"story_points must be in {ALLOWED_SP}, got {entry['story_points']}"
    if "value_area" in entry and entry["value_area"] not in ALLOWED_VA:
        return f"value_area must be in {ALLOWED_VA}, got {entry['value_area']!r}"
    return None


def summarize_patch(entry: dict) -> str:
    fields = []
    for k in ("title", "description", "acceptance_criteria", "story_points", "value_area"):
        if k in entry and entry[k] is not None and entry[k] != "":
            if k == "description":
                fields.append(f"description({len(entry[k])} chars)")
            elif k == "acceptance_criteria":
                fields.append(f"AC({len(entry[k])} items)")
            else:
                fields.append(f"{k}={entry[k]!r}")
    return ", ".join(fields) if fields else "(no fields)"


def verify_item_type(wit_client, item_id: int, expected_type: str) -> tuple[bool, str]:
    try:
        wi = wit_client.get_work_item(id=item_id)
    except AzureDevOpsServiceError as exc:
        return False, f"fetch failed: {exc}"
    actual_type = wi.fields.get("System.WorkItemType", "?")
    if actual_type != expected_type:
        return False, f"type mismatch (expected {expected_type}, is {actual_type})"
    return True, actual_type


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=Path("/home/marianna/azure_tokens_programmatic/modifications.yaml"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--skip-type-check", action="store_true", help="Skip the pre-flight get_work_item type verification"
    )
    args = ap.parse_args()

    data = yaml.safe_load(args.file.read_text())
    mods = data.get("modifications", [])
    if not mods:
        print(f"No modifications found in {args.file}")
        return 1

    cfg = AdoConfig.from_env()
    wit_client, _ = get_clients(cfg)

    ok_count = 0
    err_count = 0
    skip_count = 0

    for entry in mods:
        item_id = entry.get("id", "?")
        item_type = entry.get("type", "?")
        title_hint = entry.get("title", "")

        err = validate_entry(entry)
        if err:
            print(f"[SKIP] #{item_id}  invalid: {err}")
            skip_count += 1
            continue

        # Type verification (fetch item, confirm type matches)
        if not args.skip_type_check and not args.dry_run:
            ok, info = verify_item_type(wit_client, item_id, item_type)
            if not ok:
                print(f"[SKIP] #{item_id}  {info}")
                skip_count += 1
                continue

        patch = build_patch(entry)
        summary = summarize_patch(entry)

        if args.dry_run:
            print(f"[DRY]  #{item_id}  {item_type}: {summary}")
            if title_hint:
                print(f"        title-hint: {title_hint!r}")
            continue

        try:
            wi = wit_client.update_work_item(document=patch, id=item_id)
            wi_title = wi.fields.get("System.Title", "?")
            print(f"[OK]   updated #{wi.id}  {item_type}: {wi_title}")
            ok_count += 1
        except AzureDevOpsServiceError as exc:
            print(f"[ERROR] #{item_id}  {exc}")
            err_count += 1

    print()
    print(f"Summary: {ok_count} updated, {err_count} errors, {skip_count} skipped, total {len(mods)}")
    return 0 if err_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
