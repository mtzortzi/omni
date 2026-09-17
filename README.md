# azure-tokens-programmatic

Programmatic access to Azure DevOps (ADO) work items for the **EY - Robots in Action** engagement (`graiteam` project, org `EYGS2`).

Uses the official [`azure-devops`](https://github.com/microsoft/azure-devops-python-api) Python SDK with PAT authentication, following the pattern documented in [`ai-and-data-documentation`](https://github.com/ey-org/ai-and-data-documentation) → *Accessing Azure DevOps from Code*.

## Setup

Requires **Python 3.10+** and [**uv**](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
# edit .env: paste your PAT into ADO_PAT
```

### Create a PAT

1. Go to https://dev.azure.com/EYGS2/_usersSettings/tokens
2. **+ New Token** → scope:
   - **Work Items → Read** if you only need read scripts.
   - **Work Items → Read & Write** if you plan to run `create_items.py`, `apply_modifications.py`, `update_item.py`, or `delete_items.py`.
3. Short expiration (30–90 days).
4. Copy the token immediately and paste into `.env` as `ADO_PAT`.

> ⚠️ Never commit `.env`, share the PAT in chat, or log it. Revoke and rotate if exposed.

## Environment variables (`.env`)

| Variable       | Example                              |
| -------------- | ------------------------------------ |
| `ADO_ORG_URL`  | `https://dev.azure.com/EYGS2`        |
| `ADO_PAT`      | `<your PAT>`                         |
| `ADO_PROJECT`  | `graiteam`                           |

## Project layout

```
ado_client.py               # AdoConfig.from_env() + get_clients() (WIT + Work clients)
main.py                     # sanity check: 20 most recently changed work items

# Read helpers
engagement_tasks.py         # flat list of all Tasks under an engagement (recursive WIQL)
engagement_tree.py          # full Epic > Feature > User Story > Task tree with descriptions + AC (text)
engagement_markdown.py      # same tree, exported as Markdown

# Write helpers
create_items.py             # bulk creator from a YAML gap-analysis file
update_item.py              # single-item field update (title/description/AC/state/SP/value-area) + --parent re-parenting
apply_modifications.py      # batch modifier driven by a YAML file (SP + ValueArea + descriptions)
delete_items.py             # delete helper
add_comment.py              # add a discussion comment to a work item

# Auxiliary
ado_reconciliation_plan.md      # current authoritative reconciliation plan (v3 + review pass)
ado_reconciliation_plan.yaml    # source of truth for CREATE operations (create_items.py input)
modifications.yaml              # source of truth for MODIFY operations (apply_modifications.py input)
latest_ado_update.md            # last dumped snapshot of the engagement tree (input to reconciliation)

pyproject.toml              # uv-managed deps: azure-devops, python-dotenv, pyyaml
.env / .env.example         # credentials + config (real .env is gitignored)
```

## Usage

All scripts default to engagement **`537616` (EY - Robots in Action)** but accept an ID argument where applicable.

### Read

#### Sanity check — recent work items
```bash
uv run python main.py
```

#### Flat list of Tasks under the engagement
```bash
uv run python engagement_tasks.py 537616
```

#### Full hierarchy tree (text)
```bash
uv run python engagement_tree.py 537616 > tree.txt
```
Prints every descendant work item (Epic → Feature → User Story → Task) with Description and Acceptance Criteria, HTML stripped.

#### Full hierarchy tree (Markdown)
```bash
uv run python engagement_markdown.py 537616 > latest_ado_update.md
```
Same content as `tree.txt`, but as proper Markdown with heading levels per type and clickable ADO links. This is the standard input for building the next reconciliation plan.

### Write

#### Bulk create from YAML
```bash
uv run python create_items.py ado_reconciliation_plan.yaml --dry-run
uv run python create_items.py ado_reconciliation_plan.yaml
```
YAML shape: `new_epics`, `new_features`, `additions_to_existing`. Supports per-User-Story `story_points` and `value_area` overrides; sensible type defaults are applied. See the docstring at the top of the script.

Optional flags:
- `--engagement-id <int>` (default `537616`)
- `--only epics|features|additions` — run one section only.
- `--epic-title-contains <substr>` — filter `new_epics` by title.

#### Single-item update
```bash
uv run python update_item.py 463420 --title "..." --description "..."
uv run python update_item.py 578637 --story-points 5 --value-area Architectural
uv run python update_item.py 578700 --parent 589131   # re-parent a work item
```
Supported flags: `--title`, `--description`, `--acceptance-criteria`, `--state`, `--tags`, `--assigned-to`, `--story-points`, `--value-area`.

#### Batch modify from YAML
```bash
uv run python apply_modifications.py --file modifications.yaml --dry-run
uv run python apply_modifications.py --file modifications.yaml
```
YAML shape (one entry per work item to modify):
```yaml
modifications:
  - id: 463420
    type: Epic
    title: "..."
    description: "..."
    acceptance_criteria: [...]      # optional
  - id: 578637
    type: User Story
    story_points: 5
    value_area: Architectural
```
Pre-flight verifies the `type` matches ADO before applying. SP must be in `{1, 2, 3, 5, 8}` (Fibonacci; hard rule "&gt;8 = split"); ValueArea must be `Architectural`. Per-item errors continue the batch.

#### Delete
```bash
uv run python delete_items.py <id> [<id> ...]
```

#### Add a comment
```bash
uv run python add_comment.py <id> "Comment text"
```

## Standard reconciliation workflow

1. **Dump current ADO state** into a Markdown snapshot:
   ```bash
   uv run python engagement_markdown.py 537616 > latest_ado_update.md
   ```
2. **Author or update** `ado_reconciliation_plan.md` — the human-readable plan tagging every item with `[KEEP #id]`, `[MODIFY #id]`, `[CREATE]`, or `[DELETE #id]`. Hierarchy is strictly Epic → Feature → User Story → Task; every User Story has `story_points ∈ {1, 2, 3, 5, 8}` (Fibonacci; split anything >8) and `value_area = Architectural`.
3. **Generate** `ado_reconciliation_plan.yaml` (CREATE items) and `modifications.yaml` (MODIFY items) from the plan.
4. **Dry-run** both before executing:
   ```bash
   uv run python create_items.py ado_reconciliation_plan.yaml --dry-run
   uv run python apply_modifications.py --file modifications.yaml --dry-run
   ```
5. **Execute live**:
   ```bash
   uv run python create_items.py ado_reconciliation_plan.yaml
   uv run python apply_modifications.py --file modifications.yaml
   ```
6. **Re-dump** to verify:
   ```bash
   uv run python engagement_markdown.py 537616 > latest_ado_update.md
   ```

## How it works

1. **Authentication** — `BasicAuthentication("", PAT)` → `azure.devops.connection.Connection` → SDK clients (`WorkItemTrackingClient`, `WorkClient`).
2. **Recursive WIQL** — `FROM WorkItemLinks ... MODE (Recursive)` with `System.LinkTypes.Hierarchy-Forward` returns all descendant relations of a root work item.
3. **Batch fetching** — WIQL only returns IDs; fields are fetched with `get_work_items(ids, fields=[...])` in batches of 200 (API cap).
4. **Tree reconstruction** — Parent→child relations from the WIQL result are used to walk the hierarchy in `engagement_tree.py` / `engagement_markdown.py`.
5. **Create** — `create_work_item(document=<JsonPatch>, project, type)` with `/relations/-` `System.LinkTypes.Hierarchy-Reverse` for parenting. `AreaPath` and `IterationPath` inherited from the engagement.
6. **Update** — `update_work_item(document=<JsonPatch>, id)`. Field paths follow `/fields/<Reference.Name>` (e.g. `Microsoft.VSTS.Scheduling.StoryPoints`).

## Progress

- [x] Project scaffold with `uv` + `pyproject.toml`
- [x] PAT-based ADO authentication (`ado_client.py`)
- [x] Sanity check script (`main.py`)
- [x] Flat Task listing (`engagement_tasks.py`)
- [x] Full hierarchy tree text (`engagement_tree.py`)
- [x] Markdown export (`engagement_markdown.py`)
- [x] Bulk creator from YAML (`create_items.py`), per-story `story_points` + `value_area` overrides
- [x] Single-item updater (`update_item.py`) with `--story-points`, `--value-area`, and `--parent` re-parenting
- [x] Batch modifier (`apply_modifications.py`) with dry-run and per-item error tolerance
- [x] Delete helper (`delete_items.py`)
- [x] Comment helper (`add_comment.py`)
- [x] Reconciliation workflow productionised — 271 items touched under engagement #537616 (258 created + 13 modified) with zero errors
- [x] Reconciliation v2 (port-shape lockdown + cross-cutting reinforcements) — 111 items touched (6 modified + 105 created, IDs #590811–#590917) with zero errors; SP range expanded to Fibonacci `{1, 2, 3, 5, 8}`
- [ ] Excel export (per-person / per-sprint views)
- [ ] JSON export for downstream automation
- [ ] Filtered views (by assignee, state, iteration)
- [ ] Scheduled weekly reporting

## References

- [Accessing Azure DevOps from Code](https://github.com/ey-org/ai-and-data-documentation/blob/feature/add-programmatic-ado-access/docs/starting-a-project/azure-devops-guide.md) (source doc)
- [`azure-devops` Python SDK](https://github.com/microsoft/azure-devops-python-api)
- [WIQL syntax reference](https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax)
- [Work item link type reference](https://learn.microsoft.com/en-us/azure/devops/boards/queries/link-type-reference)
- [Work item field reference](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/work-item-field)
