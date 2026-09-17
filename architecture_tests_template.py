"""Reference implementation of architecture tests enforcing the rules in
`forbidden_patterns.md`. Drop this into the skynet repo as:

    tests/architecture/test_forbidden_patterns.py

Requires: pytest (already in dev deps).

Run:
    uv run pytest tests/architecture/ -v
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Configuration — adjust these to your actual layout
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"

# Capabilities are the top-level packages under src/ (excluding non-caps).
NON_CAPABILITY_DIRS = {"shared_kernel", "bootstrap", "__pycache__"}


def capabilities() -> list[str]:
    return sorted(
        p.name
        for p in SRC.iterdir()
        if p.is_dir()
        and p.name not in NON_CAPABILITY_DIRS
        and (p / "__init__.py").exists()
    )


def python_files_under(path: Path) -> list[Path]:
    return [p for p in path.rglob("*.py") if "__pycache__" not in p.parts]


def module_imports(file: Path) -> list[str]:
    """Return dotted names imported by `file`."""
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out


# ===========================================================================
# Rule #1 — No global DTO dumping ground
# ===========================================================================


@pytest.mark.parametrize("banned", ["dtos", "shared/dtos", "models"])
def test_no_global_dto_directory(banned: str) -> None:
    forbidden = SRC / banned
    assert not forbidden.exists(), (
        f"Forbidden global DTO dumping ground found at {forbidden}. "
        f"See forbidden_patterns.md #1 — use port-owned DTOs instead."
    )


# ===========================================================================
# Rule #2 — No generic service directory at the src root
# ===========================================================================


def test_no_generic_services_directory() -> None:
    forbidden = SRC / "services"
    assert not forbidden.exists(), (
        "Forbidden `src/services/` directory found. Application services "
        "belong under each capability's `application/services/`. "
        "See forbidden_patterns.md #2."
    )


# ===========================================================================
# Rule #3 — No generic managers directory
# ===========================================================================


def test_no_generic_managers_directory() -> None:
    forbidden = SRC / "managers"
    assert not forbidden.exists(), (
        "Forbidden `src/managers/` directory found. Split responsibilities "
        "by owning capability. See forbidden_patterns.md #3."
    )


# ===========================================================================
# Rule #4 — No technology-first top-level packages
# ===========================================================================

TECHNOLOGY_NAMES = {"ros2", "kafka", "postgres", "redis", "mqtt", "grpc"}


def test_no_technology_first_packages() -> None:
    offenders = [
        p.name for p in SRC.iterdir() if p.is_dir() and p.name in TECHNOLOGY_NAMES
    ]
    assert not offenders, (
        f"Forbidden technology-first top-level packages: {offenders}. "
        f"Technology lives inside a capability's `adapters/outbound/<vendor>/`. "
        f"See forbidden_patterns.md #4."
    )


# ===========================================================================
# Rule #5 — No cross-capability internal imports
# ===========================================================================


@pytest.mark.parametrize("capability", capabilities())
def test_no_cross_capability_internal_imports(capability: str) -> None:
    """A capability may not import from another capability's internals
    (domain/application/adapters). Only bootstrap may reach into adapters.
    Cross-capability contact is via ports + bridge adapters.
    """
    other_caps = [c for c in capabilities() if c != capability]
    offenders: list[tuple[Path, str]] = []
    for py in python_files_under(SRC / capability):
        for imp in module_imports(py):
            for other in other_caps:
                if imp == other or imp.startswith(other + "."):
                    # Allowed: importing the other capability's ports package only
                    if imp.startswith(f"{other}.ports."):
                        continue
                    offenders.append((py.relative_to(REPO_ROOT), imp))
    assert not offenders, (
        f"Capability '{capability}' has forbidden cross-capability imports:\n"
        + "\n".join(f"  {p} imports {i}" for p, i in offenders)
        + "\nUse ports + bridge adapters (docs/06 §3.6). See forbidden_patterns.md #5."
    )


# ===========================================================================
# Rule #6 — Domain must not import from adapters (of anywhere)
# ===========================================================================


@pytest.mark.parametrize("capability", capabilities())
def test_domain_does_not_import_adapters(capability: str) -> None:
    domain = SRC / capability / "domain"
    if not domain.exists():
        pytest.skip(f"{capability}/domain does not exist yet")

    offenders: list[tuple[Path, str]] = []
    for py in python_files_under(domain):
        for imp in module_imports(py):
            if ".adapters." in imp or imp.endswith(".adapters"):
                offenders.append((py.relative_to(REPO_ROOT), imp))
    assert not offenders, (
        f"Domain of '{capability}' imports adapter code:\n"
        + "\n".join(f"  {p} imports {i}" for p, i in offenders)
        + "\nDomain depends on ports only. See forbidden_patterns.md #6."
    )


# ===========================================================================
# Rule #7 — No global blackboard singleton usage
# ===========================================================================

BANNED_BLACKBOARD_IMPORTS = {
    "runtime.blackboard",
    "runtime_state.blackboard",
    "shared.blackboard",
}


def test_no_global_blackboard_singleton() -> None:
    offenders: list[tuple[Path, str]] = []
    for py in SRC.rglob("*.py"):
        # bootstrap may reference the adapter directly at wire-up time
        if "bootstrap" in py.parts:
            continue
        for imp in module_imports(py):
            for banned in BANNED_BLACKBOARD_IMPORTS:
                if imp == banned or imp.startswith(banned + "."):
                    offenders.append((py.relative_to(REPO_ROOT), imp))
    assert not offenders, (
        "Forbidden global blackboard singleton usage:\n"
        + "\n".join(f"  {p} imports {i}" for p, i in offenders)
        + "\nDepend on runtime_state's BlackboardStore port instead. "
        "See forbidden_patterns.md #7."
    )


# ===========================================================================
# Bonus — only bootstrap may import from any capability's adapters/
# ===========================================================================


def test_only_bootstrap_imports_adapters() -> None:
    offenders: list[tuple[Path, str]] = []
    for py in SRC.rglob("*.py"):
        if "bootstrap" in py.parts:
            continue
        # A file may import from its own capability's adapters (rare, but
        # sometimes an adapter imports another adapter's helper). Disallow
        # cross-capability imports of adapters.
        # For strictness we forbid *any* import into `.adapters.` from outside
        # bootstrap:
        for imp in module_imports(py):
            if ".adapters." in imp or imp.endswith(".adapters"):
                offenders.append((py.relative_to(REPO_ROOT), imp))
    assert not offenders, (
        "Only `bootstrap/` may import from any capability's `adapters/`:\n"
        + "\n".join(f"  {p} imports {i}" for p, i in offenders)
    )
