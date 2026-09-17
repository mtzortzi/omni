# [Engagement] EY - Robots in Action

- **ID:** [#537616](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/537616)
- **State:** Active
- **Assignee:** Unassigned

## [Epic] Foundations & Governance

- **ID:** [#463420](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/463420)
- **State:** Active
- **Assignee:** Marianna Tzortzi

**Description**

Narrow to the executable foundations that must exist before any
capability code lands: shared_kernel/ primitives, bootstrap/
skeleton and composition root, import-linter guardrails, CI
Basic-Checks green, per-capability README seeds, pre-commit, and
gitleaks. Was "Core Autonomous Robotics Framework" — retitled and
rescoped as Epic 1 per docs/05 §shared_kernel + §bootstrap and
AGENTS.md 'Ports before adapters, always'. Most work is already
Closed or in progress; this epic tracks completion of the
governance surface, not new capability work.

### [Feature] Shared Kernel Foundations

- **ID:** [#581342](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581342)
- **State:** Active
- **Assignee:** Marianna Tzortzi

**Description**

Establish `src/shared_kernel/` as the leaf package that provides the __universal primitives every capability is allowed to import:__ 
- stable identifier value types,
- time & measurement primitives, 
- the generic Result type, and
- the SkynetError exception hierarchy. 

Everyone imports FROM shared_kernel; 
shared_kernel imports from nothing except the Python standard library. 
No business concepts, no DTOs, no enums with business meaning live here _(docs/05 §5.2, docs/06 §3.3)._

This Feature is a prerequisite for every downstream capability, application services, ports, and adapters all depend on these primitives being stable and typed.

**Acceptance Criteria**

`src/shared_kernel/` exposes identifiers, time/measurement primitives, Result, and SkynetError as documented in AGENTS.md. 
shared_kernel modules import only from the Python standard library (enforced by an architecture test). 
No capability defines its own RobotId/MissionId/Timestamp/Duration/Percentage/Result — all references resolve to shared_kernel. 
shared_kernel contains zero DTOs, zero business enums, and zero spatial types (Pose/Position/Orientation live in world_model or robot_abstraction per docs/05 §5.2). 
Public API is re-exported from `shared_kernel/__init__.py` and covered by unit tests with ≥90% coverage.

#### [User Story] Identifier value types in shared_kernel

- **ID:** [#581343](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581343)
- **State:** Active
- **Assignee:** Marianna Tzortzi

**Description**

Introduce the universal identifier value objects used by every capability to reference domain entities without leaking storage-specific keys:  
__RobotId, MissionId, ActionId, CommandId, plus the cross-cutting CorrelationId and CausationId used by the event envelope__ (docs/06 §6.5).  

 
Implemented as frozen, hashable value types (e.g. `NewType` over `str` or frozen dataclasses) with explicit constructors that validate format and reject empty/whitespace values. No ORM coupling, no serialization logic beyond `__str__`.

**Acceptance Criteria**

`shared_kernel/identifiers.py` defines RobotId, MissionId, ActionId, CommandId, CorrelationId, CausationId. 
All identifier types are immutable and hashable (usable as dict keys and set members). 
Constructors reject empty strings and whitespace-only strings with a typed error from the SkynetError hierarchy. 
Equality is by wrapped value; two RobotId('r1') instances compare equal; RobotId('r1') != MissionId('r1') (type-distinct). 
Factories produce UUID4 by default and accept overrides for deterministic tests. 
Type checker rejects assigning a RobotId where a MissionId is expected (verified with a mypy reveal_type test). 
Unit tests cover construction, equality, hashing, and rejection cases. 
No identifier is defined outside shared_kernel (verified by the leaf-import architecture test).

##### [Task] Re-export identifiers from shared_kernel package

- **ID:** [#581345](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581345)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Update `src/shared_kernel/__init__.py` to re-export the identifier types so downstream code writes `from shared_kernel import RobotId`.

##### [Task] Unit tests for identifiers

- **ID:** [#581346](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581346)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Add `tests/unit/shared_kernel/test_identifiers.py` covering construction, equality, hashing, type-distinctness, and validation errors.

##### [Task] Add CorrelationId + CausationId and switch identifier validation to SkynetError hierarchy

- **ID:** [#581344](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581344)
- **State:** In Review
- **Assignee:** Antonis Daniil

**Description**

Close the two remaining gaps in `src/shared_kernel/identifiers.py`:

1. Add `CorrelationId` and `CausationId` as NewType[str] with matching `new_correlation_id`, `new_causation_id`, `generate_correlation_id`, `generate_causation_id` factories.
Cross-cutting identifiers propagated across all capabilities per docs/06 §6.5 (universal primitives in shared_kernel). First consumers are the EventEnvelope (Feature #589131) and the observability layer (Epic 7).

2. Replace the current `ValueError` / `TypeError` raised by `_validated()` with `ValidationError` from `shared_kernel.errors`, so identifier construction failures are typed under the SkynetError hierarchy per the US #581343 AC. Update `tests/unit/shared_kernel/test_identifiers.py` accordingly.

Also update `src/shared_kernel/__init__.py` to re-export the two new identifiers and their factories.

#### [User Story] Architecture test: shared_kernel is a leaf

- **ID:** [#581355](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581355)
- **State:** Active
- **Assignee:** Marianna Tzortzi

**Description**

Add the architecture test that enforces shared_kernel's leaf status: no module inside `src/shared_kernel/` may import from any other `src/` package, and no capability may re-implement the primitives that shared_kernel owns. This is the single non-negotiable structural invariant of the package (docs/05 §5.2, §6.1). The test lives under `tests/architecture/` and fails fast in CI with a message that points at the offending import site.

**Acceptance Criteria**

`tests/architecture/test_shared_kernel_is_leaf.py` walks the AST of every module under `src/shared_kernel/` and asserts no import references any other top-level package under `src/`. 
The test also asserts that no capability defines its own RobotId/MissionId/ActionId/CommandId/Timestamp/Duration/Percentage/Result/SkynetError (name-collision scan). 
Failure messages include the offending file, line number, and a link to docs/05 §5.2. 
Test runs in <1 second and is part of the required CI check for every PR.

##### [Task] Name-collision scan for shared primitives

- **ID:** [#581357](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581357)
- **State:** Active
- **Assignee:** Artemis Lazanaki

**Description**

Implement a scan over `src/*/` that fails when a capability defines a class or NewType with the same name as any shared_kernel primitive (RobotId, MissionId, ActionId, CommandId, CorrelationId, CausationId, Timestamp, Duration, Percentage, Result, Ok, Err, SkynetError and subclasses, EventEnvelope once added). 
Note: `.importlinter` already enforces that shared_kernel is a leaf and that capability internals are private (see `.importlinter`).  

 
Name-collision detection is a separate concern — a capability could still define its own `RobotId` class without importing shared_kernel. This task adds that missing guarantee, either as a new import-linter custom contract or as a pytest AST walk under `tests/architecture/`. 
Fixture lists the shared primitives so adding a new one updates the check in a single place.

##### [Task] AST-walk leaf-import test

- **ID:** [#581356](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581356)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Implement the AST scan that fails when a shared_kernel module imports from any other `src/` package. Include a fixture that discovers `src/shared_kernel/` dynamically so new files are covered automatically.

##### [Task] Wire architecture tests into the required CI check

- **ID:** [#581358](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581358)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Ensure `pytest tests/architecture/` runs on every PR and blocks merge on failure. Coordinate with the existing architecture test job if one already exists (see arch_enforcement_restructure.yaml).

#### [User Story] SI unit primitives (minimal): Meters, Radians, MetersPerSecond, RadiansPerSecond

- **ID:** [#590882](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590882)
- **State:** Active
- **Assignee:** Marianna Tzortzi

**Description**

Introduce the four unit types that will appear in the first two sprints as __NewType[float]__ with construction-time validation (finite, non-NaN, appropriate sign / range where  
applicable). Explicitly NOT full unit safety, NewType does not prevent cross-unit arithmetic in Python. 

_Additional units (Newtons, Volts, Amperes, Celsius) are added only when a specific capability adapter needs them, per  `AGENTS.md` 'add on demand'.

- _NewType[float]_ is zero-runtime-cost, it's not a class, just a documentation-tag for type checker. Meters + Radians not blocked in compile time. Full unit safety (with pint) is a ready migration path whenever this is needed, but it has runtime overhead and adapter friction.

**Acceptance Criteria**

- [ ] Four NewType[float] units defined in shared_kernel with validating constructors.
    1. Meters (position x/y/z, target range), 
    2. Radians (yaw, pitch, roll, joint angles), 
    3. MetersPerSecond (robot forward speed), 
    4. RadiansPerSecond (robot turn rate, joint speed)
- [ ] Re-exported from shared_kernel/__init__.py.
- [ ] ADR records the arithmetic-safety limitation and future migration path (pint).

##### [Task] Author unit types + validating constructors

- **ID:** [#590883](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590883)
- **State:** In Review
- **Assignee:** Marianna Tzortzi

**Description**

The four SI-adjacent units below are ``NewType[float]`` aliases. This gives callers a documentation-level intent tag but does NOT prevent cross-unit arithmetic (Python's structural typing lets ``m + rad`` compile).

**See the ADR under ``docs/adr/`` for the pint migration trigger.**  

  

_Meters, Radians, MetersPerSecond, RadiansPerSecond as NewType[float]._

  

  

src/shared_kernel/units.py: 4 NewType[float] + factory functions meters(), radians(), meters_per_second(), radians_per_second() με _finite() helper (rejects NaN, ±inf, bool). 

Re-export από shared_kernel/__init__.py.

##### [Task] ADR: NewType limitations and pint deferral trigger

- **ID:** [#590884](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590884)
- **State:** In Review
- **Assignee:** Marianna Tzortzi

**Description**

We need cross-capability unit vocabulary for velocities, distances, angles.
Full unit safety (e.g. `pint`) has runtime cost and adapter friction.
 

 
Written ADR noting Python's structural typing does not prevent m + rad.

##### [Task] Reject NaN / infinite at construction

- **ID:** [#590885](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590885)
- **State:** In Review
- **Assignee:** Marianna Tzortzi

**Description**

__Unit tests__ in `tests/unit/shared_kernel/test_units.py`: refuses  NaN, +inf, -inf, bool, out-of-range angulars.  

_Unit tests cover NaN, +inf, -inf, and out-of-range angular values._

#### [User Story] Time and measurement primitives in shared_kernel

- **ID:** [#581347](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581347)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Introduce the small set of universal time and measurement primitives used across capabilities: Timestamp (UTC-anchored), Duration (non-negative, unit-explicit), and Percentage (0.0–100.0, bounded). These primitives eliminate naive datetimes and unit ambiguity from ports and DTOs. They are value objects — immutable, comparable, with explicit constructors that reject invalid inputs. No timezone-naive datetimes are ever accepted; a `now()` helper returns UTC.

**Acceptance Criteria**

`shared_kernel/time.py` defines Timestamp with UTC enforcement and a `Timestamp.now()` helper. 
`shared_kernel/measurement.py` (or equivalent) defines Duration and Percentage. 
Timestamp rejects timezone-naive datetimes; Duration rejects negative values; Percentage rejects values outside [0.0, 100.0]. 
All three types are immutable, hashable, and support natural ordering (`<`, `<=`, `>=`, `>`). 
Unit tests cover valid construction, boundary values, rejection of invalid inputs, and ordering semantics.

##### [Task] Implement Timestamp with UTC enforcement

- **ID:** [#581348](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581348)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Create `src/shared_kernel/time.py` with a Timestamp value type that wraps a timezone-aware datetime, rejects naive datetimes, and exposes `Timestamp.now()` returning UTC.

##### [Task] Implement Duration and Percentage

- **ID:** [#581349](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581349)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Add Duration (non-negative, seconds-based with clear unit semantics) and Percentage (bounded 0.0–100.0) as immutable value types with validation in the constructor.

##### [Task] Unit tests for time and measurement primitives

- **ID:** [#581350](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581350)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Add `tests/unit/shared_kernel/test_time.py` and `test_measurement.py` covering construction, boundaries, invalid inputs, and ordering.

#### [User Story] Result type and SkynetError hierarchy in shared_kernel

- **ID:** [#581351](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581351)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Introduce the two error-handling primitives that let application services and ports return typed outcomes without leaking exceptions across module boundaries. `Result[T, E]` is a generic success/failure discriminated union used by port methods that can fail with a domain-meaningful error. `SkynetError` is the root of a small exception hierarchy for the cases where raising is genuinely appropriate (e.g. programmer errors, invariant violations). Together they give every capability a consistent vocabulary for failure without coupling to any framework.

**Acceptance Criteria**

`shared_kernel/result.py` defines a generic Result[T, E] with `Ok` and `Err` variants, `is_ok()`, `is_err()`, `unwrap()`, `unwrap_err()`, and safe mapping helpers. 
Result variants are immutable and covered by type hints usable with mypy strict. 
`shared_kernel/errors.py` defines SkynetError as the root and at least one concrete subclass for validation errors (used by identifiers and primitives). 
The hierarchy is documented with a short docstring at the root explaining when to raise vs when to return an Err. 
Unit tests cover Ok/Err construction, discrimination, unwrapping behaviour on both variants, and mypy type inference on a representative example.

##### [Task] Implement Result[T, E]

- **ID:** [#581352](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581352)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Create `src/shared_kernel/result.py` with a generic Result and Ok/Err variants. Ensure it type-checks under mypy strict.

##### [Task] Implement SkynetError hierarchy

- **ID:** [#581353](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581353)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Create `src/shared_kernel/errors.py` with SkynetError as the root exception plus a ValidationError subclass used by identifier and primitive constructors.

##### [Task] Unit tests for Result and errors

- **ID:** [#581354](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581354)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Description**

Add `tests/unit/shared_kernel/test_result.py` and `test_errors.py` covering variant behaviour and the hierarchy.

#### [User Story] RandomSource port + SystemRandom + DeterministicRandom adapters

- **ID:** [#590886](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590886)
- **State:** New
- **Assignee:** Antonis Daniil

**Description**

Cross-cutting deterministic-testing primitive.
- __RandomSource port__ lives in shared_kernel; 
- SystemRandom adapter wraps random.SystemRandom for production; 
- DeterministicRandom takes a seed for tests. 

_No capability calls random.random() directly._

**Acceptance Criteria**

- [ ] RandomSource port defined in shared_kernel/random_source.py.
- [ ] Two adapters ship day 0 (SystemRandom + DeterministicRandom).
- [ ] Import-linter forbids direct random.* calls outside adapters and bootstrap.

##### [Task] Author RandomSource Protocol

- **ID:** [#590887](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590887)
- **State:** New
- **Assignee:** Antonis Daniil

**Description**

Protocol στο `src/shared_kernel/random_source.py`: Methods `uniform`, `randint`, `choice`, `bytes`; return `Result` on invalid input.

##### [Task] SystemRandom adapter

- **ID:** [#590888](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590888)
- **State:** New
- **Assignee:** Antonis Daniil

**Description**

Trivial delegation to random.SystemRandom; unit tests.

##### [Task] DeterministicRandom adapter

- **ID:** [#590889](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590889)
- **State:** New
- **Assignee:** Antonis Daniil

**Description**

Seeded random.Random; reproducibility test.

##### [Task] Import-linter rule for random.* usage

- **ID:** [#590890](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590890)
- **State:** New
- **Assignee:** Antonis Daniil

**Description**

Whitelist adapters, bootstrap, tests only.

 (only `adapters/`, `bootstrap/`, `tests/` can import `random.*` directly.)

### [Feature] Composition Root and Bootstrap

- **ID:** [#581476](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581476)
- **State:** New
- **Assignee:** Unassigned

**Description**

__Establish `src/bootstrap/` as the composition root of the framework:__

the single module allowed to import from any capability's `adapters/` subtree. Bootstrap reads configuration (env vars, `.env.dev`), instantiates the chosen adapter implementations, injects them into application services through port-typed constructor parameters, and assembles entry points (FastAPI, MCP, CLI, Dagster) as inbound adapters of `operator_interface/`. No other module in `src/` may reach into `adapters/` — this is what makes every external dependency swappable by configuration rather than by code change. This Feature is a prerequisite for every capability that follows: without a composition root, capabilities either instantiate their own concrete adapters (breaking swappability) or invent ad-hoc wiring per entry point (breaking consistency).

**Acceptance Criteria**

`src/bootstrap/` exists with a documented `compose()` (or equivalent) entry point that returns fully wired application services. 
Bootstrap is the only module in `src/` that imports from any `*/adapters/` subtree, verified by an architecture test in `tests/architecture/`. 
Configuration is loaded via `pydantic-settings` from environment variables (and `.env.dev` in local runs), with typed Settings classes validated at load time. 
Adapter selection (e.g. in-memory vs Redis blackboard, mock vs simulator robot) is controlled by a single environment variable per port, resolved inside bootstrap. 
A bootstrap smoke test builds the full container in a default 'in-memory' profile and asserts every application service receives typed ports (no None, no concrete leaks). 
Bootstrap imports zero business logic from capability `domain/` or `application/` layers directly — it only wires them.

#### [User Story] Introduce pydantic-settings and per-capability Settings classes

- **ID:** [#578633](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578633)
- **State:** New
- **Assignee:** Unassigned

**Description**

Each capability declares its Settings dataclass; bootstrap composes them into AppSettings.

**Acceptance Criteria**

Settings validated at boot; missing required env vars fail fast with a SkynetConfigurationError. 
.env.dev.example lists every required key.

##### [Task] Add pydantic-settings dependency and root AppSettings

- **ID:** [#578634](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578634)
- **State:** New
- **Assignee:** Unassigned

**Description**

AppSettings composes RuntimeStateSettings, RobotAbstractionSettings, OperatorInterfaceSettings, MissionPlanningSettings.

##### [Task] Author .env.dev.example with every required key

- **ID:** [#578635](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578635)
- **State:** New
- **Assignee:** Unassigned

**Description**

Documents each env var and its capability owner.

#### [User Story] Wire every capability's application services through port-typed constructors

- **ID:** [#578637](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578637)
- **State:** New
- **Assignee:** Unassigned

**Description**

Container builds capability graphs; adapter choice driven by AppSettings.

**Acceptance Criteria**

Container returns a typed AppContext exposing inbound ports only. 
Unit test proves bootstrap is the only importer of any `adapters/*`.

##### [Task] Implement container.build_app_context(settings)

- **ID:** [#578638](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578638)
- **State:** New
- **Assignee:** Unassigned

**Description**

Returns AppContext with inbound ports of every capability.

##### [Task] Implement bridge-adapter wiring between capabilities

- **ID:** [#578639](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578639)
- **State:** New
- **Assignee:** Unassigned

**Description**

Bridge adapters (docs/06 §3.6) instantiated here — never in capability code.

#### [User Story] Implement startup/shutdown orchestration

- **ID:** [#578641](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578641)
- **State:** New
- **Assignee:** Unassigned

**Description**

AppContext exposes async start() / stop(); adapters register lifecycle hooks.

**Acceptance Criteria**

Integration test: start, submit mission, stop — no leaks.

##### [Task] Signal-handling and graceful drain

- **ID:** [#578642](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578642)
- **State:** New
- **Assignee:** Unassigned

**Description**

Standard asyncio signal handlers wired at entry point.

#### [User Story] Implement `python -m skynet` multi-mode entry point

- **ID:** [#578644](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578644)
- **State:** New
- **Assignee:** Unassigned

**Description**

Sub-commands `http`, `cli`, `mcp`; each mounts the corresponding operator_interface inbound adapter.

**Acceptance Criteria**

Startup time under 3s with in-memory adapters.

##### [Task] Author `src/bootstrap/__main__.py` and mode dispatch

- **ID:** [#578645](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578645)
- **State:** New
- **Assignee:** Unassigned

**Description**

Argument parsing + AppContext build + adapter mount.

#### [User Story] Bootstrap package skeleton and composition root entry point

- **ID:** [#581477](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581477)
- **State:** New
- **Assignee:** Marianna Tzortzi

**Description**

Create the `src/bootstrap/` package with the single public entry point that composes the running system. The composition function takes a Settings object, instantiates each capability's chosen adapters, and constructs each application service by passing ports through the constructor. No business logic lives in bootstrap \u2014 only wiring. The composed container is returned as a typed object (dataclass or similar) so entry points (HTTP, CLI, MCP) can pull out the services they need. This is the seam that turns the target hexagonal architecture from an aspiration into an executable pattern.

**Acceptance Criteria**

`src/bootstrap/__init__.py` exists and re-exports the public entry point. 
`src/bootstrap/compose.py` (or equivalent) defines a `compose(settings: Settings) -> Container` function that returns a typed container of application services. 
The Container type lists every application service by name with its port-typed dependencies visible in the signature. 
Composition is deterministic: calling `compose()` twice with the same Settings returns two containers with equivalent (but independent) service instances. 
Unit test covers a minimal composition path with fake adapters and asserts services are wired correctly. 
Composition function has zero side effects outside constructing objects (no I/O, no logging setup, no signal handlers).

##### [Task] Create bootstrap package layout

- **ID:** [#581478](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581478)
- **State:** New
- **Assignee:** Unassigned

**Description**

Create `src/bootstrap/__init__.py`, `compose.py`, and `container.py`. Define the empty `Container` dataclass and the `compose()` signature.

##### [Task] Implement compose() with fake adapters for one capability

- **ID:** [#581479](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581479)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire a single capability end-to-end (choose the simplest, e.g. shared_kernel-only application service if none of the business capabilities has an application service yet, otherwise a fake mission_planning strategy) to prove the pattern. Fake adapters live under `tests/` — not in `src/`.

##### [Task] Unit test the composition path

- **ID:** [#581480](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581480)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add `tests/unit/bootstrap/test_compose.py` verifying that compose() returns a Container with the expected services, and that each service holds port-typed references (no concrete leaks).

#### [User Story] Configuration via pydantic-settings

- **ID:** [#581481](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581481)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce the Settings class hierarchy under `src/bootstrap/config.py` (or equivalent) that reads all runtime configuration from environment variables using `pydantic-settings`. Settings are grouped by capability so each capability has its own typed sub-settings object, discoverable and documented. `.env.dev` provides local defaults; production runs receive values from the environment. All secrets and endpoint URLs are validated at load time \u2014 the process fails fast on missing or invalid config, before any adapter is instantiated.

**Acceptance Criteria**

`src/bootstrap/config.py` defines a top-level Settings class that composes per-capability sub-settings (e.g. `runtime_state`, `robot_abstraction`, `operator_interface`). 
All Settings classes are `pydantic-settings.BaseSettings` subclasses with typed fields, defaults where safe, and validators where needed. 
Settings are loaded via `Settings()` with `.env.dev` picked up automatically in local runs (through `SettingsConfigDict(env_file='.env.dev', ...)`). 
Loading fails fast with a clear error message when a required env var is missing or malformed. 
`.env.dev.example` is updated to list every setting with a placeholder value and a one-line comment describing it. 
Unit tests cover: successful load with all defaults, failure on missing required var, failure on invalid value.

##### [Task] Define top-level Settings class

- **ID:** [#581482](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581482)
- **State:** New
- **Assignee:** Unassigned

**Description**

Create `src/bootstrap/config.py` with a `Settings` class using `pydantic-settings.BaseSettings`. Wire `SettingsConfigDict` to read `.env.dev` in local runs.

##### [Task] Define per-capability sub-settings

- **ID:** [#581483](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581483)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add sub-settings classes for capabilities that need config today (e.g. RuntimeStateSettings with `backend: Literal['in_memory', 'redis']`). Keep them minimal — grow as capabilities need them.

##### [Task] Update .env.dev.example

- **ID:** [#581484](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581484)
- **State:** New
- **Assignee:** Unassigned

**Description**

List every setting with a placeholder and comment. Ensure the file remains gitignored-safe (no real secrets).

##### [Task] Unit tests for Settings loading

- **ID:** [#581485](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581485)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add `tests/unit/bootstrap/test_config.py` covering happy path, missing required var, and invalid value cases using `monkeypatch` on environment variables.

#### [User Story] Adapter selection driven by configuration

- **ID:** [#581486](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581486)
- **State:** New
- **Assignee:** Unassigned

**Description**

Establish the pattern by which bootstrap chooses which concrete adapter to instantiate for each port based on Settings. For each outbound port that has multiple implementations (e.g. `BlackboardStore` \u2192 in-memory / Redis; `RobotDriver` \u2192 mock / simulator / vendor SDK), bootstrap reads a single env var and constructs the corresponding adapter. Swapping implementations is a config change, never a code change. Downstream capabilities remain unaware of which adapter is active \u2014 they only see the port interface. This is the executable expression of "swappability first" from AGENTS.md.

**Acceptance Criteria**

For every port with multiple adapters, bootstrap contains a small factory function that returns the port-typed instance based on a Settings field. 
Factory functions live in `src/bootstrap/factories/` (one file per port or per capability) and are the only place that imports from `*/adapters/`. 
The default profile (all env vars unset) yields a fully in-memory, single-process container suitable for tests and local runs. 
Selecting a non-default adapter (e.g. `RUNTIME_STATE_BACKEND=redis`) instantiates the alternate adapter and no code outside bootstrap changes. 
Unit tests verify that changing a Settings value changes the concrete type returned by the factory, while the port type in the Container remains identical.

##### [Task] Design the factory pattern

- **ID:** [#581487](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581487)
- **State:** New
- **Assignee:** Unassigned

**Description**

Document the convention: one factory function per port, named `build_<port_name>(settings) -> <PortType>`. Add a short docstring in `src/bootstrap/factories/__init__.py`.

##### [Task] Implement the first factory as a reference

- **ID:** [#581488](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581488)
- **State:** New
- **Assignee:** Unassigned

**Description**

Pick one port that already has (or will soon have) two adapters — e.g. BlackboardStore — and implement `build_blackboard_store(settings)`. Even if the second adapter doesn't exist yet, the factory should raise NotImplementedError for that branch with a clear message.

##### [Task] Unit tests for factory selection

- **ID:** [#581489](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581489)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add `tests/unit/bootstrap/test_factories.py` covering: default selection, explicit selection, invalid selection raises typed error.

#### [User Story] Architecture test: only bootstrap imports from adapters

- **ID:** [#581490](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581490)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add the architecture test that enforces bootstrap's exclusive right to import from concrete adapters. This is the twin of the shared_kernel leaf test and the single most important structural invariant of the composition root: if any capability's `domain/`, `application/`, or `ports/` module imports from any `*/adapters/` subtree, the test fails. Without this enforcement the "swappability first" principle degrades silently over time. The test walks the AST of every module under `src/` (excluding `src/bootstrap/`) and fails on any import from an `adapters` package.

**Acceptance Criteria**

A new `.importlinter` contract (or equivalent mechanism) forbids every source module OUTSIDE `src/bootstrap/` from importing any `*/adapters/*` module. 
Source coverage explicitly includes `shared_kernel`, `mission_planning`, `mission_execution`, `fleet_coordination`, `runtime_state`, `robot_abstraction`, `operator_interface`, `perception`, `world_model`. 
Positive control: `src/bootstrap/` retains the right to import from any adapter (verified with at least one real adapter import once bootstrap has wiring). 
Failure output includes the offending file, the specific import, and a link to docs/05 §6.1. 
Contract runs in pre-commit and in CI (already true for the existing `.importlinter` config).

##### [Task] Implement the adapter-import scan

- **ID:** [#581491](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581491)
- **State:** New
- **Assignee:** Unassigned

**Description**

AST walker under `tests/architecture/`. Discover capabilities dynamically from `src/*/`. Skip `src/bootstrap/` and skip test files. Fail with rich diagnostics.

##### [Task] Positive-control test

- **ID:** [#581492](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581492)
- **State:** New
- **Assignee:** Unassigned

**Description**

A minimal test that confirms bootstrap is exempted from the rule by verifying at least one legitimate adapter import in `src/bootstrap/` is not flagged. Prevents the rule from being accidentally applied to bootstrap itself.

##### [Task] Wire into CI

- **ID:** [#581493](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/581493)
- **State:** New
- **Assignee:** Unassigned

**Description**

Ensure the new test is picked up by the existing `pytest tests/architecture/` job and blocks merge on failure.

### [Feature] CI Basic-Checks pipeline

- **ID:** [#589177](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589177)
- **State:** New
- **Assignee:** Unassigned

**Description**

Mandatory CI job set on every PR — `uv sync --dev`, pre-commit
(ruff-format, ruff, mypy, gitleaks), pytest, diff-cover >= 80%.
AGENTS.md, implementation_plan.md Epic 0. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Pipeline runs on every PR and blocks on any hook failure. 
gitleaks runs server-side (works around local Zscaler pain). 
Failure output points at the offending file and hook.

#### [User Story] Wire pre-commit hooks server-side

- **ID:** [#589178](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589178)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire the pre-commit hook set into CI so hooks execute server-side
with the same versions used locally. Guarantees gitleaks blocks
on secrets even when developers commit with SKIP=gitleaks.

**Acceptance Criteria**

Hook versions pinned; CI reproduces local outcome. 
Secret smoke test blocks.

##### [Task] Author CI YAML for pre-commit stage

- **ID:** [#589179](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589179)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the CI YAML stage that runs pre-commit against the full tree with pinned hook versions.

##### [Task] Pin hook versions and cache the uv environment

- **ID:** [#589180](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589180)
- **State:** New
- **Assignee:** Unassigned

**Description**

Pin every hook version in .pre-commit-config.yaml and cache the uv-managed environment in CI to keep runtime bounded.

##### [Task] Fake-secret smoke test

- **ID:** [#589181](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589181)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add a test that introduces a fake secret and verifies the gitleaks hook blocks the PR.

#### [User Story] diff-cover 80% patch coverage gate

- **ID:** [#589182](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589182)
- **State:** New
- **Assignee:** Unassigned

**Description**

Enforce a diff-cover 80% patch-coverage gate against the merge
base so every PR keeps changed lines covered.

**Acceptance Criteria**

`pytest --cov=src` emits coverage.xml. 
diff-cover fails PR under 80% vs merge base.

##### [Task] Coverage config in pyproject.toml

- **ID:** [#589185](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589185)
- **State:** New
- **Assignee:** Unassigned

**Description**

Configure pytest-cov coverage settings in pyproject.toml to emit coverage.xml against src/.

##### [Task] poe check task chaining lint + test + cover

- **ID:** [#589190](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589190)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add a `poe check` task that chains lint, tests and coverage into a single reproducible command.

##### [Task] Wire diff-cover into CI

- **ID:** [#589191](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589191)
- **State:** New
- **Assignee:** Unassigned

**Description**

Invoke diff-cover in CI against the merge base and fail the PR under the 80% threshold.

### [Feature] Per-capability README and doc governance seeds

- **ID:** [#589192](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589192)
- **State:** New
- **Assignee:** Unassigned

**Description**

Minimal README per capability under `src/` stating purpose, owned
concepts, inbound ports, outbound ports, non-responsibilities per
docs/00 §23. Prevents drift. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

`src/<capability>/README.md` exists for every capability folder. 
Cross-linked from `docs/04_component_responsibilities.md`.

#### [User Story] Author READMEs for all eight capability folders

- **ID:** [#589193](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589193)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author minimum README seeds for every capability folder so the
docs/00 §23 Definition-of-Done for new modules holds from
day 0.

**Acceptance Criteria**

README exists in every capability folder with the docs/00 §23 section list. 
docs/04 cross-links each README.

##### [Task] shared_kernel + bootstrap README seeds

- **ID:** [#589194](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589194)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author README seeds for shared_kernel and bootstrap with purpose, owned concepts, and non-responsibilities.

##### [Task] mission_planning / mission_execution / fleet_coordination / runtime_state / robot_abstraction / operator_interface READMEs

- **ID:** [#589195](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589195)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author README seeds for each of the six active capabilities matching the docs/00 §23 section list.

##### [Task] perception + world_model reserved READMEs

- **ID:** [#589197](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589197)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author README seeds for the two reserved capabilities marking them Reserved with the port surface deferred.

##### [Task] Cross-link from docs/04

- **ID:** [#589198](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589198)
- **State:** New
- **Assignee:** Unassigned

**Description**

Update docs/04_component_responsibilities.md to link to every capability README.

### [Feature] Clock port + adapters

- **ID:** [#590828](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590828)
- **State:** New
- **Assignee:** Marianna Tzortzi

**Description**

__Pre-Epic-2 blocker:__ BT ticks, watchdogs, action deadlines and
sim playback all need a single time authority. Without a Clock 
port, datetime.now() leaks into domain code and tests become  
time-dependent. 
- Port lives in shared_kernel (universal primitive per AGENTS.md);
- WallClock adapter in bootstrap;  
- FrozenClock test double for unit tests; 
- SimClock deferred as placeholder until sim harness needs accelerated / pausable time.

**Acceptance Criteria**

Clock port defined in shared_kernel. 
WallClock instantiated in bootstrap; no domain module calls datetime.now() directly. 
FrozenClock available as a test double. 
SimClock story exists but is marked deferred with a decision trigger.

#### [User Story] Clock port in shared_kernel

- **ID:** [#590829](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590829)
- **State:** New
- **Assignee:** Marianna Tzortzi

**Description**

Define the Clock Protocol in shared_kernel/clock.py with
now() -> Timestamp and monotonic() -> Duration. No timezone
logic in the port; adapters resolve it. Re-exported from
shared_kernel/__init__.py.

**Acceptance Criteria**

Clock Protocol exists with now() and monotonic(). 
Import-linter forbids datetime.now() / time.time() calls outside adapters and bootstrap.

##### [Task] Author Clock Protocol + re-export

- **ID:** [#590830](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590830)
- **State:** New
- **Assignee:** Unassigned

**Description**

Protocol module + __init__ update.

##### [Task] Import-linter rule against direct time.* / datetime.now() usage

- **ID:** [#590831](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590831)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add contract in importlinter config; whitelist adapters + bootstrap + tests.

#### [User Story] WallClock adapter in bootstrap

- **ID:** [#590832](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590832)
- **State:** New
- **Assignee:** Dimitris Chatzakis

**Description**

__Concrete WallClock implementation of the Clock port,__ instantiated in bootstrap and injected into every capability that needs time. 
Uses time.monotonic() for the monotonic method and datetime.now(timezone.utc) for now().

**Acceptance Criteria**

- [ ] WallClock lives in bootstrap (or a bootstrap-adjacent adapter package).
- [ ] Bootstrap wires WallClock into every capability constructor that requires Clock.

##### [Task] WallClock implementation + unit tests

- **ID:** [#590833](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590833)
- **State:** New
- **Assignee:** Unassigned

**Description**

Trivial delegation to stdlib; unit tests assert monotonic ≥ previous.

##### [Task] Wire into bootstrap composition root

- **ID:** [#590834](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590834)
- **State:** New
- **Assignee:** Unassigned

**Description**

Update bootstrap/wiring to construct WallClock and pass to services.

#### [User Story] FrozenClock test double

- **ID:** [#590835](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590835)
- **State:** New
- **Assignee:** Artemis Lazanaki

**Description**

Test-only Clock implementation whose time is frozen at a caller-provided instant and advanced by explicit.advance(duration) calls. Enables deterministic tests of  
timeouts, watchdogs and BT ticks.

**Acceptance Criteria**

- [ ] FrozenClock available for import from a shared test-helpers module.
- [ ] Unit tests demonstrate deterministic advancement.

##### [Task] FrozenClock implementation

- **ID:** [#590836](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590836)
- **State:** New
- **Assignee:** Unassigned

**Description**

Constructor takes initial Timestamp; .advance(Duration) mutates internal state.

##### [Task] Test-helper module publish + docs

- **ID:** [#590837](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590837)
- **State:** New
- **Assignee:** Unassigned

**Description**

Publish under tests/fixtures or a dedicated shared_kernel/testing/ module; document usage.

#### [User Story] SimClock: deferred placeholder

- **ID:** [#590838](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590838)
- **State:** New
- **Assignee:** Unassigned

**Description**

Placeholder story for a future SimClock adapter offering accelerated / pausable / rewindable time for sim scenarios. Deferred until Epic 9 sim harness requires it. Kept in the backlog so the port shape can accommodate it.

**Acceptance Criteria**

Story remains in Backlog state with a decision-trigger comment.

## [Epic] Robot Procurement Management

- **ID:** [#467945](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/467945)
- **State:** Active
- **Assignee:** Stelios Vachaviolos

**Description**

Defines and manages the end‑to‑end process for identifying, evaluating, selecting, and procuring robots in alignment with business, technical, and operational requirements.

### [Feature] Robotics Procurement

- **ID:** [#467957](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/467957)
- **State:** Active
- **Assignee:** Stelios Vachaviolos

**Description**

Establishes and executes the procurement strategy required to acquire robots aligned with business and operational needs.

#### [User Story] Monitor Robot Purchasing Progress

- **ID:** [#467962](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/467962)
- **State:** Active
- **Assignee:** Stelios Vachaviolos

**Description**

As a Product owner I want to define and track the robot procurement process, so that I have clear visibility into purchasing decisions, progress, and approvals

##### [Task] DJI Mini 4 Pro (Standard) Drone

- **ID:** [#467976](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/467976)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

**Description**

DJI Mini 4 Pro (Standard) Drone
2.4 GHz με Κάμερα 4K 60fps. Μοντέλο
χειριστηρίου: DJI RN-N2 - Ordered Placed - (696 Euros)  
https://www.skroutz.gr/s/46364303/DJI-Mini-4-Pro-Standard-Drone-2-4-GHz-me-Kamera-4K-60fps.html

##### [Task] Sunnylife Propeller Guard for DJI Mini 4 Pro

- **ID:** [#467981](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/467981)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

**Description**

Purchase tracking for Sunnylife Προφυλακτήρας για DJI Mini 4 Pro - Ordered placed - 9.15 Euros - https://www.skroutz.gr/s/48781911/Sunnylife-Profylaktiras-gia-DJI-Mini-4-Pro-N4P-KC712.html?product_id=186283052&sponsored=listing

##### [Task] Wifi Antenna Extension Cable

- **ID:** [#467989](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/467989)
- **State:** Closed
- **Assignee:** Artemis Lazanaki

**Description**

Rp-sma Female To 2 Ts9 R Wifi
Antenna Extension Cable Rg316 Extension Adapter Cable 30m - Ordered Placed - (19.38 Euros) -
 
 
Rp-sma Female To 2 Ts9 R Wifi Antenna Extension Cable Rg316 Extension Adapter Cable 30cm | Skroutz.gr

##### [Task] DJI Mini 4 Pro Intelligent Flight Battery

- **ID:** [#468066](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/468066)
- **State:** Closed
- **Assignee:** Artemis Lazanaki

##### [Task] ROBOTIS AI WORKER FF-SG2 (Mobility Version)

- **ID:** [#477675](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/477675)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

**Description**

Vendor που έχουμε εντοπίσει: 

 Kiefer – A. Stavridis: a.stavridis@kiefer.gr (65.000€ - including Transportation + custom fees)

##### [Task] Unitree G1 EDU U6 Humanoid Robot

- **ID:** [#477688](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/477688)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

**Description**

Αγοράστηκε από vendor: Kiefer – A.
Stavridis: a.stavridis@kiefer.gr

##### [Task] Unitree Go2 EDU Plus U4

- **ID:** [#477701](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/477701)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

**Description**

Αγοράστηκε από vendor: Kiefer – A. Stavridis: a.stavridis@kiefer.gr

##### [Task] Purchase spare part for crashed drone

- **ID:** [#489034](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/489034)
- **State:** Closed
- **Assignee:** Theodore Tsitsimis

##### [Task] DJI NEO2 Fly more combo

- **ID:** [#496896](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/496896)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

**Description**

https://www.germanos.gr/product/wearables-gadgets/drones/camera-drones/dji-neo-2-fly-more-combo/?productId=20444707&fname=skuColor&fvalue=-127973337189519133&ref=bestprice.gr - 409€

##### [Task] DJI Cellular Dongle 2

- **ID:** [#520203](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/520203)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

##### [Task] Unitree As2 Edu Flagship (U4)

- **ID:** [#544813](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/544813)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

**Description**

Unitree As2 Edu Flagship (U4) 15,000.00 AS2 Extended-Range Battery 600.00 Transportation Costs 1,500.00 Customs Fees 900.00

##### [Task] Unitree H2 EDU

- **ID:** [#548355](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/548355)
- **State:** Closed
- **Assignee:** Joanna Karytsioti

**Description**

Unitree H2 EDU                                            41,000.00
 
H2 Dedicated Nvidia Jetson Orin NX             3,000.00
H2 Dedicated Dex3-1 Force-Controlled        11,000.00
Transportation costs, Customs Fees (Έξοδα Εκτελωνιστή) συμπεριλαμβάνονται στου R1-A7-D Flagship Version A

##### [Task] R1-A7-D Flagship Version A

- **ID:** [#548357](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/548357)
- **State:** Closed
- **Assignee:** Artemis Lazanaki

**Description**

R1-A7-D Flagship Version A                    12,000.00
 
Transportation costs                                    5,000.00
Customs Fees (Έξοδα Εκτελωνιστή)           1,000.00

##### [Task] TP-LINK M7350 v1 4G Mobile Hotspot Wi Fi 4

- **ID:** [#467995](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/467995)
- **State:** In Review
- **Assignee:** Artemis Lazanaki

**Description**

TP-LINK LINK M7350 v1 Ασύρματο 4G Φορητό Hotspot Wi‑Fi 4 - Ordered Placed - ( 66 Euros )   
TP-LINK
M7350 v1 Ασύρματο 4G Φορητό Hotspot Wi‑Fi 4 | Skroutz.gr

##### [Task] DJI Mini 4 Pro/Mini 3 Series Two-Way Charging Hub

- **ID:** [#468071](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/468071)
- **State:** In Review
- **Assignee:** Artemis Lazanaki

##### [Task] Server GPUs from DELL (YODA)

- **ID:** [#477694](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/477694)
- **State:** In Review
- **Assignee:** Stelios Vachaviolos

**Description**

| Product | price in Euros| 
| --- | ----------------- |
 |2 x GPU node R770 - 256 GB RAM|55.700|
| 2 NVIDIA RTX Pro 6000 Blackwell Server Edition Software Kit NVAIE, per GPU, 3 Years |11.400|

In total:  67.100 euros

##### [Task] Thermal AXION Compact XG30

- **ID:** [#496889](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/496889)
- **State:** In Review
- **Assignee:** Artemis Lazanaki

**Description**

PULSAR AXION Compact XG30 Thermal Imaging Scope - Τιμή: 1.689,90€

##### [Task] Purchase Nano GPUs

- **ID:** [#489030](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/489030)
- **State:** New
- **Assignee:** Artemis Lazanaki

##### [Task] Purchase Mac Pro

- **ID:** [#489031](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/489031)
- **State:** New
- **Assignee:** Unassigned

##### [Task] Purchase small training drone

- **ID:** [#489033](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/489033)
- **State:** New
- **Assignee:** Unassigned

##### [Task] Purchase 3 batteries and charger for the drone we already bought

- **ID:** [#489035](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/489035)
- **State:** New
- **Assignee:** Artemis Lazanaki

##### [Task] Evaluate purchase of large GPU laptop (so as not to carry Freddie)

- **ID:** [#489036](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/489036)
- **State:** New
- **Assignee:** Unassigned

## [Epic] Organize and Introducing Lab

- **ID:** [#537965](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/537965)
- **State:** Active
- **Assignee:** Marianna Tzortzi

### [Feature] Trainings

- **ID:** [#460835](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/460835)
- **State:** Active
- **Assignee:** Stelios Vachaviolos

#### [User Story] Certify for ROS2, Drone Flight, Langchain

- **ID:** [#461059](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/461059)
- **State:** Active
- **Assignee:** Stelios Vachaviolos

##### [Task] ROS2, Langchain and Drone certificates

- **ID:** [#524303](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/524303)
- **State:** Active
- **Assignee:** Joanna Karytsioti

**Description**

ROS2: [SuccessFactors Learning: Item Details for ROS 2 for Beginners (ROS Jazzy - 2026)](https://eygsl.plateau.com/learning/user/deeplink.do?linkId=ITEM_DETAILS&componentID=Udemy_59253&componentTypeID=ELEARNING&revisionDate=1684922829000#/92B16144DE0801801800E0FAD16FF324)

Langchain: [SuccessFactors Learning: Item Details for LangChain- Agentic AI Engineering with LangChain & LangGraph](https://eygsl.plateau.com/learning/user/deeplink.do?linkId=ITEM_DETAILS&componentID=Udemy_59026&componentTypeID=ELEARNING&revisionDate=1684922628000#/710C6144DE0801801800E0FAD16FF324)

Drone: [LZ - A1/A3 Course & Examination - UAS Remote Pilot Open Category - [UAS-OPEN-A1+A3]](https://learningzone.eurocontrol.int/ilp/pages/description.jsf#/users/@self/courses/25863224/description?runningLanguage=en-GB)

##### [Task] ROS2, Langchain and Drone certificates

- **ID:** [#524311](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/524311)
- **State:** Active
- **Assignee:** Antonis Daniil

**Description**

- [ ] ROS2: [SuccessFactors Learning: Item Details for ROS 2 for Beginners (ROS Jazzy - 2026)](https://eygsl.plateau.com/learning/user/deeplink.do?linkId=ITEM_DETAILS&componentID=Udemy_59253&componentTypeID=ELEARNING&revisionDate=1684922829000#/92B16144DE0801801800E0FAD16FF324)

- [ ] Langchain: [SuccessFactors Learning: Item Details for LangChain- Agentic AI Engineering with LangChain & LangGraph](https://eygsl.plateau.com/learning/user/deeplink.do?linkId=ITEM_DETAILS&componentID=Udemy_59026&componentTypeID=ELEARNING&revisionDate=1684922628000#/710C6144DE0801801800E0FAD16FF324)

- [X] Drone: [LZ - A1/A3 Course & Examination - UAS Remote Pilot Open Category - [UAS-OPEN-A1+A3]](https://learningzone.eurocontrol.int/ilp/pages/description.jsf#/users/@self/courses/25863224/description?runningLanguage=en-GB)

##### [Task] ROS2, Langchain and Drone certificates

- **ID:** [#574424](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/574424)
- **State:** Active
- **Assignee:** Costas Bampos

**Description**

- [ ] ROS2: [SuccessFactors Learning: Item Details for ROS 2 for Beginners (ROS Jazzy - 2026)](https://eygsl.plateau.com/learning/user/deeplink.do?linkId=ITEM_DETAILS&componentID=Udemy_59253&componentTypeID=ELEARNING&revisionDate=1684922829000#/92B16144DE0801801800E0FAD16FF324)

- [ ] Langchain: [SuccessFactors Learning: Item Details for LangChain- Agentic AI Engineering with LangChain & LangGraph](https://eygsl.plateau.com/learning/user/deeplink.do?linkId=ITEM_DETAILS&componentID=Udemy_59026&componentTypeID=ELEARNING&revisionDate=1684922628000#/710C6144DE0801801800E0FAD16FF324)

- [X] Drone: [LZ - A1/A3 Course & Examination - UAS Remote Pilot Open Category - [UAS-OPEN-A1+A3]](https://learningzone.eurocontrol.int/ilp/pages/description.jsf#/users/@self/courses/25863224/description?runningLanguage=en-GB)

##### [Task] ROS 1&2, Agents (Lang chain) , Drone Certificate

- **ID:** [#460837](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/460837)
- **State:** Closed
- **Assignee:** Dimitris Chatzakis

**Acceptance Criteria**

ROS 1&2  
Agents (Lang chain) 
Drone Certificate

##### [Task] ROS 1&2, Agents (Lang chain) , Drone Certificate

- **ID:** [#460840](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/460840)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

**Acceptance Criteria**

ROS 1&2  
Agents (Lang chain) 
Drone Certificate

##### [Task] ROS 1&2, Agents (Lang chain) , Drone Certificate

- **ID:** [#460842](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/460842)
- **State:** Closed
- **Assignee:** Marios Vardakastanis

**Acceptance Criteria**

ROS 1&2  
Agents (Lang chain) 
Drone Certificate

##### [Task] ROS 1&2, Agents (Lang chain) , Drone Certificate

- **ID:** [#460846](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/460846)
- **State:** Closed
- **Assignee:** Artemis Lazanaki

**Acceptance Criteria**

ROS 1&2  
Agents (Lang chain) 
Drone Certificate

##### [Task] ROS 1&2, Agents (Lang chain) , Drone Certificate

- **ID:** [#466961](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/466961)
- **State:** Closed
- **Assignee:** Alexandros Kelaiditis

##### [Task] Drone Certificate

- **ID:** [#468322](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/468322)
- **State:** Closed
- **Assignee:** Konstantinos Sardelis

##### [Task] ROS2, Langchain and Drone Certificates

- **ID:** [#524299](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/524299)
- **State:** Closed
- **Assignee:** Panos Kolios

**Description**

ROS2: [SuccessFactors Learning: Item Details for ROS 2 for Beginners (ROS Jazzy - 2026)](https://eygsl.plateau.com/learning/user/deeplink.do?linkId=ITEM_DETAILS&componentID=Udemy_59253&componentTypeID=ELEARNING&revisionDate=1684922829000#/92B16144DE0801801800E0FAD16FF324)

Langchain: [SuccessFactors Learning: Item Details for LangChain- Agentic AI Engineering with LangChain & LangGraph](https://eygsl.plateau.com/learning/user/deeplink.do?linkId=ITEM_DETAILS&componentID=Udemy_59026&componentTypeID=ELEARNING&revisionDate=1684922628000#/710C6144DE0801801800E0FAD16FF324)

Drone: [LZ - A1/A3 Course & Examination - UAS Remote Pilot Open Category - [UAS-OPEN-A1+A3]](https://learningzone.eurocontrol.int/ilp/pages/description.jsf#/users/@self/courses/25863224/description?runningLanguage=en-GB)

#### [User Story] Introduction to lab robots as of now 23.6.2026

- **ID:** [#546302](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/546302)
- **State:** Closed
- **Assignee:** Stelios Vachaviolos

**Description**

New members of our robotics lab should be familiar with as of now robots in our lab.

- [X] dimos for go2 pro
- [X] wildbridge for drone dju mini 4 pro

##### [Task] go2 pro dimos

- **ID:** [#546312](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/546312)
- **State:** Closed
- **Assignee:** Marianna Tzortzi

##### [Task] drone dji mini 4 pro

- **ID:** [#546321](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/546321)
- **State:** Closed
- **Assignee:** Dimitris Chatzakis

### [Feature] Reporting status

- **ID:** [#551856](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/551856)
- **State:** Active
- **Assignee:** Antonis Daniil

**Description**

Creating the reporting procedure for our robotics lab

#### [User Story] Automate Azure DevOps Weekly Reporting

- **ID:** [#551996](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/551996)
- **State:** Active
- **Assignee:** Antonis Daniil

**Description**

As a robotics lab team member, I want to build a small codebase that retrieves Azure DevOps work item data using a PAT and generates the weekly sprint/reporting status automatically, so that the team can track completed work, in-progress items, backlog.

##### [Task] Set up Azure DevOps data extraction

- **ID:** [#552001](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/552001)
- **State:** Closed
- **Assignee:** Antonis Daniil

##### [Task] Create Documentation for the Azure DevOps Data Extraction Pipeline

- **ID:** [#561374](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/561374)
- **State:** In Review
- **Assignee:** Antonis Daniil

##### [Task] Validate report output against Azure DevOps Queries

- **ID:** [#552004](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/552004)
- **State:** New
- **Assignee:** Antonis Daniil

### [Feature] Documentations

- **ID:** [#560306](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/560306)
- **State:** New
- **Assignee:** Dimitris Chatzakis

**Description**

All about documenting progress and new processes in: [Welcome | AI & Data Docs](https://super-potato-qzw7en2.pages.github.io/docs/intro/)

#### [User Story] Document the new Devops Workflow

- **ID:** [#560307](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/560307)
- **State:** Active
- **Assignee:** Dimitris Chatzakis

##### [Task] Document the new Devops Workflow

- **ID:** [#560308](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/560308)
- **State:** In Review
- **Assignee:** Dimitris Chatzakis

#### [User Story] Document the implemtation of our solution through freddie

- **ID:** [#560365](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/560365)
- **State:** New
- **Assignee:** Dimitris Chatzakis

##### [Task] Document how to use our solution through freddie

- **ID:** [#560366](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/560366)
- **State:** New
- **Assignee:** Dimitris Chatzakis

## [Epic] PM

- **ID:** [#547748](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547748)
- **State:** New
- **Assignee:** Theodore Tsitsimis

###### [Resource Request] Marianna Tzortzi

- **ID:** [#547749](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547749)
- **State:** Fulfilled
- **Assignee:** Unassigned

###### [Resource Request] Joanna Karytsioti

- **ID:** [#547750](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547750)
- **State:** Fulfilled
- **Assignee:** Unassigned

###### [Resource Request] Alexandros Kelaiditis

- **ID:** [#547751](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547751)
- **State:** Fulfilled
- **Assignee:** Unassigned

###### [Resource Request] Konstantinos Sardelis

- **ID:** [#547752](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547752)
- **State:** Fulfilled
- **Assignee:** Unassigned

###### [Resource Request] Antonis Daniil

- **ID:** [#547754](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547754)
- **State:** Fulfilled
- **Assignee:** Unassigned

###### [Resource Request] Dimitris Chatzakis

- **ID:** [#547755](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547755)
- **State:** Fulfilled
- **Assignee:** Unassigned

###### [Resource Request] Artemis Lazanaki

- **ID:** [#547756](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547756)
- **State:** Fulfilled
- **Assignee:** Unassigned

###### [Resource Request] Antonis Arvanitakis

- **ID:** [#547808](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/547808)
- **State:** Fulfilled
- **Assignee:** Unassigned

## [Epic] Planner + BT Executor End-to-End (thin vertical slice)

- **ID:** [#588871](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588871)
- **State:** New
- **Assignee:** Unassigned

**Description**

Fixture-driven vertical slice proving the hexagonal design executes end-to-end: MissionPlanner produces a Plan; the BT Executor (an inbound adapter of mission_execution per docs/03 §20 and docs/10 §7) ticks it; leaf nodes call RobotOperations routed through robot_abstraction to a zero-dependency logging-fake RobotDriver; state transitions land in an in-memory blackboard (runtime_state's in_memory state_backend adapter per docs/11 §6). Fleet coordination is stubbed to a single always-allocatable robot. No HTTP/CLI/MCP yet; entry point is a pytest integration test under tests/e2e/. Ref implementation_plan.md §2, §5.5.

### [Feature] runtime_state (in-memory blackboard + event bus)

- **ID:** [#588872](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588872)
- **State:** New
- **Assignee:** Unassigned

**Description**

Minimum runtime_state: four inbound ports (current_plan, robot_state, action_state, fleet_decision), the state_backend outbound port, and an in_memory adapter implementing KV + pub/sub per docs/11 §6. All returned values wrapped in Result[T, E] per shared_kernel canon. Import-linter prevents any capability other than runtime_state and bootstrap from importing the in_memory adapter. Ref implementation_plan.md §5.3, §6.

**Acceptance Criteria**

Four inbound ports typed with port-owned DTOs; return `Result[T, E]`. 
`state_backend` port covers `get` / `put` / `subscribe`. 
`in_memory` adapter passes shared contract test suite. 
Import-linter prevents any capability other than `runtime_state` and `bootstrap` from importing the `in_memory` module.

#### [User Story] Define runtime_state inbound port surface

- **ID:** [#588873](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588873)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the four inbound Protocols (current_plan, robot_state, action_state, fleet_decision) and their port-owned DTOs under runtime_state/ports/inbound/*/port.py per docs/11 §6 and docs/06 §Port-owned DTOs. Each Protocol returns Result[T, E] using shared_kernel types. Unit tests use fake state_backend implementations — no adapter code imported from application code per AGENTS.md 'Ports before adapters, always'.

**Acceptance Criteria**

Four Protocols exist under `runtime_state/ports/inbound/*/port.py`. 
Unit tests use fakes for state_backend.

##### [Task] Snapshot value objects in runtime_state/domain/

- **ID:** [#588874](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588874)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce snapshot value objects (Plan / Robot / Action / Fleet) in runtime_state/domain/.

##### [Task] Inbound Protocols + port DTOs

- **ID:** [#588875](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588875)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the four inbound Protocols with port-owned DTOs; no cross-capability imports.

##### [Task] Application service fanning updates to state_backend

- **ID:** [#588876](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588876)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the application service that fans updates from inbound ports out to the state_backend port.

##### [Task] Unit tests with fake state_backend

- **ID:** [#588877](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588877)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add unit tests exercising the application service with a fake state_backend.

#### [User Story] Implement state_backend outbound port + in_memory adapter

- **ID:** [#588878](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588878)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the state_backend outbound Protocol covering get/put/subscribe per docs/11 §6 and provide the dict-backed in_memory adapter with an in-process observer for subscribe. The contract test suite in tests/contract/state_backend/ is parametrisable so future durable adapters (Epic 6) reuse it unchanged. Wired into bootstrap/wiring/runtime_state.py as the default backend.

**Acceptance Criteria**

Dict-backed KV; in-process observer for subscribe. 
Contract test parametrisable over adapters.

##### [Task] Define state_backend Protocol

- **ID:** [#588879](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588879)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the state_backend Protocol with get, put, and subscribe methods.

##### [Task] Implement in_memory adapter

- **ID:** [#588880](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588880)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the dict-backed in_memory adapter with an in-process observer for subscribe.

##### [Task] Contract test suite in tests/contract/state_backend/

- **ID:** [#588881](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588881)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the parametrisable contract test suite that any state_backend adapter must pass.

##### [Task] Wire in bootstrap/wiring/runtime_state.py

- **ID:** [#588882](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588882)
- **State:** New
- **Assignee:** Unassigned

**Description**

Register the runtime_state wiring in bootstrap so the in_memory adapter is selected by default.

### [Feature] robot_abstraction stub (RobotDriver port + logging-fake adapter)

- **ID:** [#588883](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588883)
- **State:** New
- **Assignee:** Unassigned

**Description**

Minimum robot_abstraction to unblock the vertical slice: the robot_operations inbound port, the robot_driver outbound port at slice-sufficient shape (the rich agnostic surface lands in Epic 4 per docs/12), and a zero-dependency logging-fake driver adapter that records commands and synthesises deterministic telemetry. A runtime_state_bridge outbound adapter writes normalized robot_state into runtime_state. Contract test proves the logging-fake satisfies robot_driver; the same harness is reused in Epic 4.

**Acceptance Criteria**

`robot_operations` inbound port with typed commands (move-to, wait, no-op). 
`robot_driver` outbound port implemented by the logging-fake. 
Bridge adapter writes normalized `robot_state` into runtime_state. 
Contract test proves the logging-fake satisfies `robot_driver` (shared harness reused when Epic 4 richens the port).

#### [User Story] Define robot_abstraction ports and application service

- **ID:** [#588885](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588885)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce the minimum robot_abstraction domain (RobotCommand, Telemetry value objects typed with shared_kernel units), the three ports required by the slice (robot_operations inbound, telemetry_ingestion inbound, robot_driver outbound) per docs/12 §Ports, and the application service coordinating them. Application service is unit-tested with a fake driver — no adapter imports per docs/06 §Import rules.

**Acceptance Criteria**

Domain, ports and application service exist and are unit-tested with a fake driver.

##### [Task] Domain: minimum RobotCommand, Telemetry

- **ID:** [#588886](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588886)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce RobotCommand and Telemetry value objects sufficient for the slice; unit-safe types from shared_kernel.

##### [Task] Ports: robot_operations, telemetry_ingestion, robot_driver

- **ID:** [#588891](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588891)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the three port Protocols with port-owned DTOs.

##### [Task] Application service + unit tests with fake driver

- **ID:** [#588892](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588892)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the application service and unit-test it against a fake driver.

#### [User Story] Implement logging-fake driver + runtime_state bridge

- **ID:** [#588893](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588893)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the zero-dependency logging-fake driver adapter that records commands to memory and returns deterministic responses, plus the outbound runtime_state_bridge that writes normalized robot_state into runtime_state via its inbound port. Contract test in tests/contract/robot_drivers/ proves the logging-fake satisfies the robot_driver port per docs/17 §Contract tests. Registered in bootstrap as the default driver.

**Acceptance Criteria**

Logging-fake records commands and emits synthetic telemetry. 
Bridge writes normalized robot_state to runtime_state. 
Contract test for robot_driver passes.

##### [Task] Logging-fake adapter (zero deps, records commands)

- **ID:** [#588894](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588894)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the logging-fake RobotDriver adapter that records commands to memory and returns deterministic responses.

##### [Task] runtime_state_bridge outbound adapter

- **ID:** [#588895](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588895)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the runtime_state_bridge outbound adapter that writes normalized robot_state into runtime_state.

##### [Task] Contract test for robot_driver

- **ID:** [#588896](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588896)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add a contract test proving the logging-fake satisfies the robot_driver port.

##### [Task] Wire in bootstrap/wiring/robot_abstraction.py

- **ID:** [#588898](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588898)
- **State:** New
- **Assignee:** Unassigned

**Description**

Register the robot_abstraction wiring in bootstrap so the logging-fake driver is selected by default.

#### [User Story] ActionHandle port pattern for long-running actions

- **ID:** [#590891](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590891)
- **State:** New
- **Assignee:** Unassigned

**Description**

Non-negotiable port-shape decision: RobotDriver methods
representing long-running actions (go-to-pose, execute-arm-
trajectory, dock) return an ActionHandle rather than a
synchronous Result. Retrofitting async/cancellation later
would rewrite every BT leaf and every adapter. Locked in at
Feature 2.2 so the stub is right the first time.

**Acceptance Criteria**

ActionHandle Protocol has feedback (AsyncIterator[F]), result (Awaitable[R]), cancel (Awaitable[None]). 
RobotDriver.execute signature returns ActionHandle. 
Logging-fake adapter returns a synthetic ActionHandle whose feedback stream is deterministic. 
Contract test asserts cancel() halts progress within N ms.

##### [Task] Author ActionHandle Protocol in robot_abstraction/ports/outbound/

- **ID:** [#590892](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590892)
- **State:** New
- **Assignee:** Unassigned

**Description**

Protocol + typed feedback / result / cancel signatures.

##### [Task] Update RobotDriver port signature to return ActionHandle

- **ID:** [#590893](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590893)
- **State:** New
- **Assignee:** Unassigned

**Description**

Replace synchronous return with ActionHandle across the port.

##### [Task] Update logging-fake adapter to synthesise ActionHandle

- **ID:** [#590894](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590894)
- **State:** New
- **Assignee:** Unassigned

**Description**

Fake yields scripted feedback + resolves result after configurable delay.

##### [Task] Contract test — cancel() causes adapter halt within N ms

- **ID:** [#590895](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590895)
- **State:** New
- **Assignee:** Unassigned

**Description**

Uses FrozenClock; asserts subsequent feedback ceases and result resolves as Cancelled.

### [Feature] fleet_coordination single-robot stub

- **ID:** [#588899](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588899)
- **State:** New
- **Assignee:** Unassigned

**Description**

Minimum fleet_coordination for the slice: inbound query_eligible_robots returns the single configured robot; reserve_robots always succeeds. Marked explicitly as a stub (stub=True in docstring for grep) so it cannot silently survive into Epic 5, which delivers the real eligibility engine and reservation aggregate per docs/09.

**Acceptance Criteria**

Inbound ports exist and are wired. 
Stub is unit-tested; `stub=True` in docstring for grep-ability.

#### [User Story] Implement fleet_coordination single-robot stub

- **ID:** [#588901](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588901)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce the two inbound ports (query_eligible_robots, reserve_robots) with port-owned DTOs, plus a stub application service that always allocates the single configured robot. Marked stub=True in docstring per docs/17 §Stubs so a grep surfaces it before Epic 5 ships the real eligibility engine. Wired through bootstrap on the default profile.

**Acceptance Criteria**

Both ports exist and are wired in bootstrap. 
Stub application service is unit-tested for the two happy paths.

##### [Task] Ports: query_eligible_robots, reserve_robots

- **ID:** [#588902](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588902)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the two inbound Protocols and port-owned DTOs.

##### [Task] Stub application service

- **ID:** [#588903](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588903)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the stub application service that always allocates the single configured robot; mark stub=True in docstring.

##### [Task] Wire in bootstrap/wiring/fleet_coordination.py

- **ID:** [#588904](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588904)
- **State:** New
- **Assignee:** Unassigned

**Description**

Register the fleet_coordination wiring in bootstrap.

##### [Task] Unit tests

- **ID:** [#588905](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588905)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add unit tests covering the two happy paths of the stub.

### [Feature] mission_planning (minimum viable planner)

- **ID:** [#588906](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588906)
- **State:** New
- **Assignee:** Unassigned

**Description**

Produce a validated Plan from a submitted Mission using a fixture / rule-based planner strategy. The submit_mission inbound port returns Result[MissionId, PlanningError] per shared_kernel canon; the planner writes the Plan to runtime_state.current_plan via a runtime_state_bridge outbound adapter. Fleet queries flow through a fleet_bridge to fleet_coordination's inbound ports — never direct imports. Ref docs/08 (planning) and docs/06 §Bridge adapters.

**Acceptance Criteria**

`submit_mission` inbound port: `Mission -> Result[MissionId, PlanningError]`. 
Fixture planner emits a deterministic linear Plan usable by BT. 
Plan written to `runtime_state.current_plan` via bridge.

#### [User Story] Domain: Mission, Plan, Action

- **ID:** [#588907](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588907)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce the mission_planning domain value objects (Mission, Plan, Action) with typed invariants using shared_kernel primitives (MissionId, ActionId, Duration) per docs/05 §shared_kernel canon. Value objects are immutable and validation raises SkynetError subclasses. Unit tests cover construction, validation, and equality — pure stdlib, no adapter dependencies per docs/06 §Domain isolation.

**Acceptance Criteria**

Value objects immutable with typed invariants. 
Unit tests cover construction and validation.

##### [Task] Value objects with invariants

- **ID:** [#588908](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588908)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define Mission, Plan, Action value objects with typed invariants.

##### [Task] Unit tests for construction and validation

- **ID:** [#588909](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588909)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add unit tests covering construction and validation of each value object.

#### [User Story] submit_mission inbound port + fixture planner application service

- **ID:** [#588910](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588910)
- **State:** New
- **Assignee:** Unassigned

**Description**

Deliver the submit_mission inbound port (Mission -> Result[MissionId, PlanningError]) and a fixture / rule-based planner strategy behind it, wired against fleet_coordination and runtime_state via bridge outbound adapters per docs/06 §Bridge adapters. Planner produces a deterministic linear Plan from a fixture Mission and persists it to runtime_state.current_plan. Application service is unit-tested with fakes for every outbound port; no cross-capability domain imports.

**Acceptance Criteria**

Planner produces a deterministic linear Plan from a fixture Mission. 
Plan is persisted to runtime_state via the runtime_state_bridge. 
Application service is unit-tested with fakes for every outbound port.

##### [Task] Inbound Protocol and DTOs

- **ID:** [#588911](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588911)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the submit_mission inbound Protocol and its port-owned DTOs.

##### [Task] Fixture / rule-based planner strategy

- **ID:** [#588912](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588912)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the fixture / rule-based planner strategy producing a deterministic linear Plan.

##### [Task] fleet_bridge outbound adapter

- **ID:** [#588913](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588913)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the fleet_bridge outbound adapter calling fleet_coordination inbound ports.

##### [Task] runtime_state_bridge writing current_plan

- **ID:** [#588914](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588914)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the runtime_state_bridge outbound adapter that writes current_plan into runtime_state.

##### [Task] Unit tests with fakes for every outbound port

- **ID:** [#588915](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588915)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add unit tests exercising the planner application service with fakes for every outbound port.

#### [User Story] MissionStatus aggregate with guard-checked FSM

- **ID:** [#590896](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590896)
- **State:** New
- **Assignee:** Unassigned

**Description**

Make the mission lifecycle explicit and testable:
submitted → planned → allocated → executing →
{completed | failed | aborted}. Guard predicates on every
transition; typed transition errors; no illegal transitions
silently succeed. Aggregate lives in
mission_planning/domain/mission_status.py.

**Acceptance Criteria**

MissionStatus aggregate exists with an explicit state enum. 
transition() rejects illegal transitions with a typed error. 
Unit tests cover every legal and every illegal transition. 
MissionPlanner output includes a MissionStatus with the initial state.

##### [Task] Author MissionStatus enum + guard predicates

- **ID:** [#590897](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590897)
- **State:** New
- **Assignee:** Unassigned

**Description**

Enum + per-transition guard functions in the domain module.

##### [Task] Unit tests for every legal and illegal transition

- **ID:** [#590898](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590898)
- **State:** New
- **Assignee:** Unassigned

**Description**

Parametrised test matrix.

##### [Task] Integrate MissionStatus into MissionPlanner output

- **ID:** [#590899](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590899)
- **State:** New
- **Assignee:** Unassigned

**Description**

Update the Plan DTO to carry MissionStatus at construction.

### [Feature] mission_execution (BT Executor as inbound adapter)

- **ID:** [#588916](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588916)
- **State:** New
- **Assignee:** Unassigned

**Description**

Deliver the execute_plan inbound port and the BT Executor inbound adapter that ticks the Plan; per docs/03 §20 and docs/10 §7 the BT Executor is an inbound adapter of mission_execution, not a capability. Leaf nodes call robot_operations via a robot_abstraction_bridge outbound adapter; each tick emits an action_state update and an event on the runtime_state event bus. Minimum node set (Sequence, Fallback, Action leaf) is sufficient to drive the fixture Plan against the logging-fake.

**Acceptance Criteria**

Executor reads current Plan from runtime_state via `plan_reader`. 
Minimum BT node set (Sequence, Fallback, Action leaf) unit-tested. 
Each tick emits an `action_state` update; event bus fires a `tick` event. 
Fixture Plan drives the logging-fake to completion with `Result.ok`.

#### [User Story] Domain + execute_plan inbound port

- **ID:** [#588920](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588920)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce Execution and PlanCursor value objects with lifecycle invariants, the execute_plan inbound Protocol, and the application service coordinating outbound ports (plan_reader, robot_operations, runtime_state) per docs/10 §Execution model. Application service uses outbound ports only — no adapter imports per docs/06 §Import rules. Unit-tested with fakes for every outbound port.

**Acceptance Criteria**

Execution / PlanCursor value objects defined with invariants. 
Inbound Protocol and DTOs defined. 
Application service uses outbound ports only, no adapter imports.

##### [Task] Execution / PlanCursor value objects

- **ID:** [#588921](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588921)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define Execution and PlanCursor value objects with lifecycle invariants.

##### [Task] Inbound Protocol and DTOs

- **ID:** [#588923](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588923)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the execute_plan inbound Protocol and port-owned DTOs.

##### [Task] Application service using outbound ports

- **ID:** [#588925](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588925)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the application service coordinating plan_reader, robot_operations and runtime_state via outbound ports.

#### [User Story] BT Executor inbound adapter with minimum node set

- **ID:** [#588926](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588926)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the BT Executor as an inbound adapter of mission_execution (per docs/03 §20 and docs/10 §7 — not a capability of its own) with the minimum node set required to complete the fixture Plan: Sequence, Fallback, and Action leaf. Tick loop reads/writes the blackboard via the runtime_state bridge; leaf nodes call robot_operations via the robot_abstraction_bridge. Each node is unit-tested; an integration test drives the fixture Plan against the logging-fake to completion.

**Acceptance Criteria**

Executor drives the fixture Plan to completion against the logging-fake. 
Each node is unit-tested.

##### [Task] Tick loop; blackboard read/write via runtime_state bridge

- **ID:** [#588927](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588927)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the tick loop with blackboard read/write via the runtime_state bridge.

##### [Task] Sequence, Fallback, Action leaf nodes

- **ID:** [#588928](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588928)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the minimum BT node set: Sequence, Fallback, Action leaf.

##### [Task] robot_abstraction_bridge outbound adapter

- **ID:** [#588929](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588929)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the robot_abstraction_bridge outbound adapter routing leaf commands to robot_abstraction.

##### [Task] Unit tests per node + integration test completing the fixture Plan against the logging-fake

- **ID:** [#588931](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588931)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add unit tests per node plus an integration test that completes the fixture Plan end-to-end against the logging-fake driver.

#### [User Story] Mission abort cascade with guaranteed cleanup

- **ID:** [#590900](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590900)
- **State:** New
- **Assignee:** Unassigned

**Description**

Explicit cascade
BT.cancel → RobotDriver.stop_current_action →
Reservation.release → EventBus.emit(MissionAborted)
orchestrated in the mission_execution application service.
Per-step failure isolation: a failure in one step must not
prevent the following steps; failed steps land in a
dead-letter log. Chaos-tested with abort injected at random
tick indices.

**Acceptance Criteria**

Abort cascade implemented in mission_execution application service. 
Every step's failure isolated; subsequent steps still execute. 
Chaos test asserts every abort ends with a released reservation. 
MissionAborted event always emitted (best-effort) or dead-lettered on failure.

##### [Task] Cascade orchestrator implementation

- **ID:** [#590901](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590901)
- **State:** New
- **Assignee:** Unassigned

**Description**

Sequential try/except-isolated calls with per-step logging.

##### [Task] Chaos test: random-tick abort

- **ID:** [#590902](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590902)
- **State:** New
- **Assignee:** Unassigned

**Description**

Parametrised test injects abort at random tick indices; asserts reservation released.

  

_The test works like this: "__run the BT for 100 ticks and at a random one of them, send abort. Verify that the reservation was released.__" If we use real randomness, then every time CI runs, the abort falls on a different tick, so if the test finds a bug, we can't reproduce it. With seeded random, CI always aborts at the same tick with the same seed → reproducible._

##### [Task] Dead-letter sink for failed MissionAborted emissions

- **ID:** [#590903](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590903)
- **State:** New
- **Assignee:** Unassigned

**Description**

If EventBus.emit fails, log to a dead-letter sink for later replay.

### [Feature] bootstrap composition of the slice

- **ID:** [#588934](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588934)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire every port in the slice through bootstrap/compose.py on the default in-memory profile per AGENTS.md 'Configuration' and docs/05 §bootstrap. 

compose(settings) returns a Container exposing every inbound port of the slice as a port-typed attribute, no concrete adapters leak. 

tests/e2e/test_thin_slice.py submits a fixture mission and asserts the executor reaches success in under 5s.

**Acceptance Criteria**

`compose(settings)` returns a Container exposing every inbound port of the slice as port-typed attributes. 
E2E test runs in < 5s.

#### [User Story] Wire the vertical slice in bootstrap and add e2e harness

- **ID:** [#588935](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588935)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire compose(settings) for the full slice on the default in-memory profile so every inbound port of every capability is exposed as a port-typed Container attribute per docs/05 §bootstrap. Add tests/e2e/test_thin_slice.py that submits a fixture mission and asserts the executor reaches success. Runs in under 5 seconds — the executable proof of the hexagonal design per implementation_plan.md §5.5.

**Acceptance Criteria**

compose(settings) returns a Container exposing every inbound port of the slice. 
tests/e2e/test_thin_slice.py runs in under 5s.

##### [Task] Implement compose(settings) for the slice

- **ID:** [#588936](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588936)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement compose(settings) wiring every capability's application service against its ports on the default in-memory profile.

##### [Task] Add tests/e2e/test_thin_slice.py

- **ID:** [#588937](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588937)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add the e2e harness that submits a fixture mission and asserts the executor reaches success.

##### [Task] Document how to run the harness from README

- **ID:** [#588938](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588938)
- **State:** New
- **Assignee:** Unassigned

**Description**

Document how to run the e2e harness from the repo README.

## [Epic] Operator Interface (HTTP + CLI + MCP inbound adapters)

- **ID:** [#588939](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588939)
- **State:** New
- **Assignee:** Unassigned

**Description**

Sequence: Epic 4 (was Epic 3, swapped for port-surface stability). 
HTTP + CLI + MCP inbound adapters over operator_interface's local
inbound ports. Depends on a stable RobotDriver port surface from
Epic 3 (robot_abstraction) — otherwise the operator schemas
(mission submission, telemetry projection, teleop) would be
rewritten once locomotion/manipulation/telemetry/safety are added
to the port. Ref implementation_plan.md §5.6.

### [Feature] operator_interface local ports and mappers

- **ID:** [#588940](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588940)
- **State:** New
- **Assignee:** Unassigned

**Description**

Local outbound ports typed to operator_interface's view (SubmitMission, ViewMissionStatus, AbortMission) plus DTO mappers translating between external schemas and port DTOs. Bridge outbound adapters under operator_interface/adapters/outbound/*_bridge/ are the only code paths reaching into other capabilities' inbound ports per docs/06 §Bridge adapters. Import-linter enforces the isolation so no inbound adapter (HTTP/CLI/MCP) ever imports mission_planning or mission_execution directly.

**Acceptance Criteria**

Three local outbound Protocols exist. 
Bridge adapters under `operator_interface/adapters/outbound/*_bridge/` are the only code paths reaching into other capabilities. 
Import-linter enforces the isolation.

#### [User Story] Define local outbound ports + DTO mappers

- **ID:** [#588941](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588941)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce operator_interface's local outbound port Protocols (SubmitMission, ViewMissionStatus, AbortMission) under operator_interface/ports/outbound/ plus the DTO mapper module translating between external schemas (HTTP JSON, CLI args, MCP tool input) and port DTOs per docs/06 §Port-owned DTOs. Mapper is unit-tested; ports are unit-tested with fake bridge adapters. No cross-capability imports per docs/06 §Import rules.

**Acceptance Criteria**

Three Protocols exist under operator_interface/ports/outbound/. 
Mapper module is unit-tested.

##### [Task] Define Protocols and DTOs

- **ID:** [#588942](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588942)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define SubmitMission, ViewMissionStatus, AbortMission Protocols and their port-owned DTOs.

##### [Task] Author mapper module + unit tests

- **ID:** [#588943](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588943)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the DTO mapper module and unit-test it against representative fixtures.

#### [User Story] Implement bridge outbound adapters to mission_planning, mission_execution, runtime_state

- **ID:** [#588944](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588944)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement three bridge outbound adapters wiring the local
ports to the target capabilities' public inbound ports,
plus contract tests per bridge. Ref docs/03 §Architecture Implementation and AGENTS.md. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Three bridge adapters exist and are the only paths reaching other capabilities. 
Contract tests per bridge under tests/contract/module_bridges/.

##### [Task] mission_planning_bridge

- **ID:** [#588945](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588945)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the mission_planning_bridge outbound adapter.

##### [Task] mission_execution_bridge

- **ID:** [#588946](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588946)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the mission_execution_bridge outbound adapter.

##### [Task] runtime_state_bridge

- **ID:** [#588947](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588947)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the runtime_state_bridge outbound adapter for operator_interface.

##### [Task] Contract tests per bridge under tests/contract/module_bridges/

- **ID:** [#588948](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588948)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add contract tests per bridge asserting the bridge satisfies the local port and calls the target capability's public inbound port.

### [Feature] CLI inbound adapter (typer / click)

- **ID:** [#588951](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588951)
- **State:** New
- **Assignee:** Unassigned

**Description**

Ship an inbound CLI adapter of operator_interface using typer or click per AGENTS.md preferred libraries, exposing submit / status / abort commands that call the local outbound ports. Zero business logic in the adapter — argument parsing, human formatting, and delegation only. Contract-tested against a fake local port set so the CLI stays runnable without any real capability wiring.

**Acceptance Criteria**

`python -m skynet cli submit --fixture minimal.json` prints a MissionId. 
`... cli status <id>` returns state. 
`... cli abort <id>` aborts. 
Errors map to non-zero exit codes with typed messages from SkynetError.

#### [User Story] Implement CLI adapter with submit/status/abort

- **ID:** [#588953](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588953)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the inbound CLI adapter under operator_interface/adapters/inbound/cli/ using typer or click per AGENTS.md preferred libraries, exposing submit / status / abort commands. Adapter contains zero business logic — parsing, formatting, and delegation to local outbound ports only. Unit-tested against fake local ports; smoke-tested end-to-end via bootstrap on the in-memory profile.

**Acceptance Criteria**

Three sub-commands work against the in-memory profile. 
CLI e2e test passes.

##### [Task] Add typer via uv add typer

- **ID:** [#588956](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588956)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add typer as a dependency via `uv add typer`.

##### [Task] Implement three sub-commands

- **ID:** [#588957](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588957)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement submit / status / abort sub-commands calling operator_interface outbound ports.

##### [Task] CLI e2e test on in-memory profile

- **ID:** [#588958](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588958)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add a CLI e2e test running the three commands against the in-memory profile.

### [Feature] HTTP inbound adapter (FastAPI)

- **ID:** [#588959](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588959)
- **State:** New
- **Assignee:** Unassigned

**Description**

Ship an inbound HTTP adapter of operator_interface using FastAPI + uvicorn per AGENTS.md preferred libraries. Routes correspond one-to-one to the local outbound ports (SubmitMission, ViewMissionStatus, AbortMission); pydantic request/response schemas are translated to port DTOs by the mapper module. All errors are mapped to SkynetError subclasses per docs/16 and returned with correlation IDs in headers.

**Acceptance Criteria**

Routes covered by pytest with in-process client. 
OpenAPI at `/docs` pinned via snapshot test. 
Domain errors -> typed HTTP 4xx/5xx with a `SkynetError` code.

#### [User Story] Implement HTTP adapter with routes + schemas

- **ID:** [#588961](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588961)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the inbound HTTP adapter under operator_interface/adapters/inbound/http/ using FastAPI + uvicorn per AGENTS.md preferred libraries. Routes map 1:1 to the local outbound ports; pydantic schemas translate through the mapper module. Errors map to SkynetError subclasses per docs/16 §Errors and surface correlation IDs in response headers per docs/11 §EventEnvelope.

**Acceptance Criteria**

Routes tested with an in-process client. 
OpenAPI schema pinned via snapshot. 
Domain errors mapped to typed HTTP responses.

##### [Task] Add FastAPI + uvicorn

- **ID:** [#588963](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588963)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add FastAPI and uvicorn as dependencies via `uv add`.

##### [Task] routes/missions.py, schemas/, mappers/

- **ID:** [#588964](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588964)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author routes/missions.py, pydantic schemas, and mappers translating between schemas and port DTOs.

##### [Task] Error-mapping middleware

- **ID:** [#588965](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588965)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add middleware translating SkynetError subclasses to typed HTTP 4xx/5xx bodies.

##### [Task] Route tests + OpenAPI snapshot test

- **ID:** [#588966](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588966)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add route tests using an in-process client and pin the OpenAPI schema with a snapshot test.

### [Feature] MCP inbound adapter (FastMCP)

- **ID:** [#588967](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588967)
- **State:** New
- **Assignee:** Unassigned

**Description**

Ship an inbound MCP adapter of operator_interface using FastMCP per AGENTS.md preferred libraries, mirroring the CLI's command surface as MCP tools. Same local outbound ports; same mapper module; different transport. Enables LLM agents to drive missions through the operator interface with identical semantics to the HTTP and CLI adapters.

**Acceptance Criteria**

Three MCP tools registered: `submit_mission`, `mission_status`, `abort_mission`. 
Contract test invokes each tool via an MCP client on the in-memory profile.

#### [User Story] Implement MCP adapter mirroring CLI

- **ID:** [#588968](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588968)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the inbound MCP adapter under operator_interface/adapters/inbound/mcp/ using FastMCP per AGENTS.md preferred libraries, exposing the same command surface as the CLI as MCP tools. Reuses the mapper module and the local outbound ports unchanged — proves the hexagonal boundary by adding a third transport with zero application-code changes.

**Acceptance Criteria**

Three MCP tools registered and callable via an MCP client. 
Contract test passes on the in-memory profile.

##### [Task] Add FastMCP

- **ID:** [#588969](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588969)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add FastMCP as a dependency via `uv add`.

##### [Task] Register three tools; reuse operator_interface app service

- **ID:** [#588971](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588971)
- **State:** New
- **Assignee:** Unassigned

**Description**

Register submit_mission, mission_status and abort_mission MCP tools reusing the operator_interface application service.

##### [Task] MCP contract test

- **ID:** [#588972](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588972)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add a contract test invoking each MCP tool via an MCP client against the in-memory profile.

### [Feature] Operator identity & authorization

- **ID:** [#590839](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590839)
- **State:** New
- **Assignee:** Unassigned

**Description**

Minimal auth surface: an ADR documenting the evolution
TrustLan → token → OIDC, a PrincipalContext port at the
operator boundary, a TrustLan no-op adapter for dev, and an
AuditLog outbound port with in-memory + Loguru adapters. Token
and OIDC adapters deferred until the operator interface is
exposed beyond a trusted LAN.

**Acceptance Criteria**

ADR merged and linked from operator_interface README. 
PrincipalContext port present with TrustLan adapter for dev. 
AuditLog port present with InMemory + Loguru adapters. 
No auth-relevant action executes without an AuditLog entry.

#### [User Story] ADR — auth evolution TrustLan → token → OIDC

- **ID:** [#590840](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590840)
- **State:** New
- **Assignee:** Unassigned

**Description**

Written ADR outlining the three-stage auth evolution, the
triggers for each transition, and the shape of the
PrincipalContext port that all stages must satisfy.

**Acceptance Criteria**

docs/adr/00XX-operator-auth-evolution.md exists.

#### [User Story] PrincipalContext port + TrustLan no-op adapter

- **ID:** [#590841](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590841)
- **State:** New
- **Assignee:** Unassigned

**Description**

PrincipalContext inbound port yields the calling principal
(id, roles, scopes) for the current request. TrustLan
adapter returns a fixed "trusted-lan" principal — safe
default for local dev; explicitly logged at bootstrap so no
one ships it accidentally.

**Acceptance Criteria**

Port defined in operator_interface/ports/inbound/. 
TrustLan adapter under operator_interface/adapters/inbound/. 
Bootstrap logs a WARNING when TrustLan is active.

##### [Task] PrincipalContext port + Principal DTO

- **ID:** [#590842](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590842)
- **State:** New
- **Assignee:** Unassigned

**Description**

Protocol + immutable Principal(id, roles, scopes).

##### [Task] TrustLan adapter with loud-boot warning

- **ID:** [#590843](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590843)
- **State:** New
- **Assignee:** Unassigned

**Description**

Adapter returns fixed principal; bootstrap emits a WARNING log line at startup.

#### [User Story] AuditLog outbound port + InMemory + Loguru adapters

- **ID:** [#590844](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590844)
- **State:** New
- **Assignee:** Unassigned

**Description**

Outbound audit sink for auth-relevant events (login attempt,
mission submit, teleop request, abort). Two day-0 adapters:
InMemory (for tests + local dev) and Loguru (for structured
file/remote sinks). Adapters live in
operator_interface/adapters/outbound/.

**Acceptance Criteria**

{'AuditLog port with append(event': 'AuditEvent) -> Result.'} 
InMemoryAuditLog + LoguruAuditLog adapters. 
Application services take AuditLog by port; call at every auth-relevant boundary.

##### [Task] AuditLog port + AuditEvent DTO

- **ID:** [#590845](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590845)
- **State:** New
- **Assignee:** Unassigned

**Description**

Protocol + immutable AuditEvent(who, what, when, correlation_id).

##### [Task] InMemoryAuditLog adapter + tests

- **ID:** [#590846](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590846)
- **State:** New
- **Assignee:** Unassigned

**Description**

Deque-based sink for tests + local dev.

##### [Task] LoguruAuditLog adapter

- **ID:** [#590847](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590847)
- **State:** New
- **Assignee:** Unassigned

**Description**

Serialises AuditEvent as structured JSON via a dedicated Loguru sink.

##### [Task] Wire AuditLog calls into inbound application services

- **ID:** [#590848](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590848)
- **State:** New
- **Assignee:** Unassigned

**Description**

At each auth-relevant use case, append an AuditEvent.

#### [User Story] Token-based auth adapter — deferred placeholder

- **ID:** [#590849](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590849)
- **State:** New
- **Assignee:** Unassigned

**Description**

Placeholder story for the future token-based
PrincipalContext adapter (e.g. bearer/JWT). Deferred until
the operator interface is exposed beyond a trusted LAN.

**Acceptance Criteria**

Story remains in Backlog with decision trigger noted.

## [Epic] Robot Abstraction & Adapter Framework (agnostic layer)

- **ID:** [#588973](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588973)
- **State:** New
- **Assignee:** Unassigned

**Description**

Sequence: Epic 3 (was Epic 4, promoted so the RobotDriver port
stabilises before operator schemas are built on top of it). 
The vendor-agnostic layer: rich RobotDriver port
(locomotion/manipulation/telemetry/safety), capability/affordance
model, normalised telemetry with QoS, teleop primitives,
safety hooks in the port surface, and the RobotDriver
contract-test suite that every adapter must satisfy. Enforcement
of safety hooks lives in Epic 8's safety contract-test harness.
Ref implementation_plan.md §5.7 and docs/07.

### [Feature] RobotDriver port (rich, agnostic surface)

- **ID:** [#588974](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588974)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend the minimum port from Epic 2 to a vendor-agnostic
surface covering locomotion (walk/trot/fly/hover),
manipulation (grasp/release/bimanual), navigation (go-to-pose,
follow-path), teleop primitives (velocity/joint/twist),
telemetry subscriptions, and safety controls (e-stop, watchdog
reset). Ref docs/03 §Architecture Implementation and AGENTS.md. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Port defined as a Python Protocol with typed methods returning `Result[..., SkynetError-subtype]`. 
Every method has a documented capability precondition referencing the affordance model (Feature 4.2). 
No import from any vendor SDK inside the port module.

#### [User Story] Define locomotion and navigation method surface on RobotDriver port

- **ID:** [#588975](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588975)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend the minimum port from Epic 2 with typed locomotion
primitives (walk, trot, fly, hover, lie_down) and navigation
primitives (go_to_pose, follow_path). Each method is a
Protocol member returning `Result[..., SkynetError-subtype]`.

**Acceptance Criteria**

Locomotion + navigation methods added to the Protocol under `robot_abstraction/ports/outbound/`. 
No vendor SDK import appears in the port module. 
Unit tests exercise the fake adapter through the new methods.

##### [Task] Add locomotion primitives to Protocol

- **ID:** [#588976](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588976)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add walk/trot/fly/hover/lie_down method signatures to the RobotDriver Protocol with typed args.

##### [Task] Add navigation primitives to Protocol

- **ID:** [#588977](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588977)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add go_to_pose and follow_path method signatures with Pose / Path DTOs owned by the port.

##### [Task] Extend logging-fake adapter

- **ID:** [#588978](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588978)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend the logging-fake adapter from Epic 2 to implement the new methods and log invocations.

##### [Task] Unit tests through the fake

- **ID:** [#588979](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588979)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add unit tests exercising each new method via the fake adapter.

#### [User Story] Define manipulation method surface on RobotDriver port

- **ID:** [#588981](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588981)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add manipulation primitives (grasp, release, bimanual_grasp)
to the port. Method signatures are affordance-guarded and
return unit-safe Result types.

**Acceptance Criteria**

Manipulation methods added to the Protocol with typed grasp targets. 
Logging-fake adapter implements them. 
Unit tests cover each method through the fake.

##### [Task] Define manipulation DTOs

- **ID:** [#588984](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588984)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define GraspTarget and BimanualGraspTarget DTOs owned by the port.

##### [Task] Add methods to Protocol

- **ID:** [#588986](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588986)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add grasp / release / bimanual_grasp method signatures.

##### [Task] Extend fake + unit tests

- **ID:** [#588987](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588987)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend logging-fake and add unit tests.

#### [User Story] Wire Result / SkynetError error mapping and per-method capability preconditions

- **ID:** [#588988](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588988)
- **State:** New
- **Assignee:** Unassigned

**Description**

Every port method returns `Result[..., SkynetError-subtype]`
and carries a documented capability precondition referencing
the affordance model (Feature 4.2). Adapters translate vendor
errors into the SkynetError taxonomy.

**Acceptance Criteria**

Each method's docstring lists its required affordance. 
Error taxonomy (Unsupported, PreconditionFailed, HardwareError, Timeout) applied uniformly. 
Unit tests assert error mapping for representative cases.

##### [Task] Extend SkynetError taxonomy for RobotDriver

- **ID:** [#588989](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588989)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add RobotDriver-specific SkynetError subtypes in shared_kernel or robot_abstraction/domain (per docs 06).

##### [Task] Annotate each port method with required affordance

- **ID:** [#588990](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588990)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add docstring precondition on every port method naming the required affordance.

##### [Task] Adapter error-mapping helper

- **ID:** [#588993](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588993)
- **State:** New
- **Assignee:** Unassigned

**Description**

Provide an error-mapping helper module vendor adapters can reuse to translate exceptions into Result.err(...).

##### [Task] Unit tests for error mapping

- **ID:** [#588994](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588994)
- **State:** New
- **Assignee:** Unassigned

**Description**

Unit test the error-mapping helper against representative vendor exceptions.

### [Feature] Capability / affordance model

- **ID:** [#588996](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588996)
- **State:** New
- **Assignee:** Unassigned

**Description**

Each robot declares its affordances (fly, hover, walk, trot,
lie down, grasp, bimanual, ...). Fleet eligibility (Epic 5)
and BT node preconditions (Epic 2.5 + extensions) key off
this. Ref docs/12 §Affordance model and docs/09 §Eligibility.

**Acceptance Criteria**

Enumerated affordance set in `robot_abstraction/domain/`. 
Every adapter registers a static affordance manifest. 
Contract test asserts the adapter refuses commands whose required affordance is not declared.

#### [User Story] Define Affordance enum and AffordanceManifest domain type

- **ID:** [#588998](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588998)
- **State:** New
- **Assignee:** Unassigned

**Description**

Enumerate the affordance set (fly, hover, walk, trot,
lie_down, grasp, bimanual, teleop_velocity, ...) and define
an immutable AffordanceManifest domain type carried by each
adapter.

**Acceptance Criteria**

`Affordance` enum lives under `robot_abstraction/domain/`. 
`AffordanceManifest` is a frozen dataclass with declared_affordances: frozenset[Affordance]. 
Unit tests cover manifest equality and membership queries.

##### [Task] Author Affordance enum

- **ID:** [#588999](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/588999)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the Affordance enum under robot_abstraction/domain/affordances.py.

##### [Task] Author AffordanceManifest dataclass

- **ID:** [#589000](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589000)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the frozen AffordanceManifest dataclass with membership helpers.

##### [Task] Unit tests

- **ID:** [#589001](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589001)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add unit tests for enum stability and manifest membership.

#### [User Story] Adapter affordance registration + precondition guard + contract test

- **ID:** [#589002](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589002)
- **State:** New
- **Assignee:** Unassigned

**Description**

Every adapter registers a static AffordanceManifest at
construction. A precondition guard rejects any port call
whose required affordance is not declared. The behaviour is
enforced by a shared contract test.

**Acceptance Criteria**

Adapter base / mixin exposes `manifest` and applies the guard uniformly. 
Guard returns `Result.err(PreconditionFailed(...))` — no exception raised. 
Contract test parametrised across adapters verifies refusal.

##### [Task] Adapter registration API

- **ID:** [#589003](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589003)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define how an adapter declares its manifest (constructor arg vs class attribute); document in docs 06 update PR.

##### [Task] Precondition guard helper

- **ID:** [#589004](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589004)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the guard helper that inspects the required-affordance metadata and short-circuits with a Result.err(...).

##### [Task] Apply guard on logging-fake

- **ID:** [#589005](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589005)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire the guard into the logging-fake adapter and demonstrate refusal behaviour.

##### [Task] Contract test skeleton

- **ID:** [#589006](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589006)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add a contract-test module under tests/contract/robot_drivers/ parametrised on adapter fixtures, asserting refusal.

### [Feature] Normalized telemetry model

- **ID:** [#589007](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589007)
- **State:** New
- **Assignee:** Unassigned

**Description**

Structured telemetry events (pose, joint states, battery, IMU,
task-progress) with unit-safe types from `shared_kernel`.
Vendor adapters normalize into this model; runtime_state
consumes it. Ref docs/12 §Telemetry and docs/11 §EventEnvelope.

**Acceptance Criteria**

Telemetry types defined; validation rejects malformed inputs. 
Contract test asserts adapters emit at least the mandatory subset (pose, battery, health).

#### [User Story] Define normalized telemetry event types with shared_kernel units

- **ID:** [#589008](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589008)
- **State:** New
- **Assignee:** Unassigned

**Description**

Model PoseEvent, JointStateEvent, BatteryEvent, ImuEvent,
TaskProgressEvent as immutable domain types using unit-safe
primitives from shared_kernel. Validation rejects malformed
inputs at construction.

**Acceptance Criteria**

Event types live under `robot_abstraction/domain/telemetry.py`. 
Constructors validate units and ranges; invalid inputs raise a typed error. 
Unit tests cover valid + invalid construction.

##### [Task] Author telemetry dataclasses

- **ID:** [#589009](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589009)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the five telemetry event dataclasses with unit-safe fields.

##### [Task] Add validation in __post_init__

- **ID:** [#589010](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589010)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add __post_init__ validators rejecting NaN, out-of-range, wrong units.

##### [Task] Unit tests

- **ID:** [#589011](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589011)
- **State:** New
- **Assignee:** Unassigned

**Description**

Cover valid and invalid construction per event type.

#### [User Story] Contract test for mandatory telemetry emission

- **ID:** [#589013](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589013)
- **State:** New
- **Assignee:** Unassigned

**Description**

A shared contract test asserts every adapter emits the
mandatory subset (pose, battery, health) at a documented
minimum rate through the telemetry subscription mechanism.

**Acceptance Criteria**

Contract test parametrised across adapters observes the mandatory events within a bounded window. 
Failure output names the missing event type + adapter fixture.

##### [Task] Telemetry subscription helper on port

- **ID:** [#589015](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589015)
- **State:** New
- **Assignee:** Unassigned

**Description**

Confirm / add the subscribe_telemetry method on the RobotDriver port and its DTO.

##### [Task] Contract test observer

- **ID:** [#589017](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589017)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the contract-test observer that collects events for N seconds and asserts the mandatory subset.

##### [Task] Wire logging-fake to emit synthetic telemetry

- **ID:** [#589018](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589018)
- **State:** New
- **Assignee:** Unassigned

**Description**

Make the logging-fake adapter emit synthetic pose/battery/health so the contract test passes for it.

#### [User Story] QoS profile in TelemetrySubscription

- **ID:** [#590904](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590904)
- **State:** New
- **Assignee:** Unassigned

**Description**

The telemetry port cannot be subscribed to without a QoS
profile: (a) reliability (best-effort | reliable),
(b) rate limit (max Hz), (c) deadline (max inter-sample
duration). Required by any real adapter — ROS2 refuses
subscription without QoS; MAVLink needs stream rates.

**Acceptance Criteria**

QoSProfile DTO defined in the telemetry port module. 
TelemetrySubscription.subscribe() requires a QoSProfile parameter (not optional). 
Contract test asserts adapter honours rate limit + deadline (with FrozenClock).

##### [Task] Author QoSProfile DTO

- **ID:** [#590905](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590905)
- **State:** New
- **Assignee:** Unassigned

**Description**

Immutable dataclass in the telemetry port module.

##### [Task] Update TelemetrySubscription port signature

- **ID:** [#590906](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590906)
- **State:** New
- **Assignee:** Unassigned

**Description**

Make QoSProfile a required parameter.

##### [Task] Contract test for rate limit + deadline enforcement

- **ID:** [#590907](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590907)
- **State:** New
- **Assignee:** Unassigned

**Description**

Uses FrozenClock; asserts sample cadence matches profile.

### [Feature] Teleop primitive abstractions

- **ID:** [#589019](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589019)
- **State:** New
- **Assignee:** Unassigned

**Description**

Velocity/twist/joint teleop primitives usable by both BT nodes
and the operator interface. Adapters translate to vendor
semantics. Ref docs/12 §Teleop primitives.

**Acceptance Criteria**

Primitives typed with rate limits and unit-safe values. 
Contract test asserts adapters honour rate limits or reject cleanly.

#### [User Story] Define velocity / twist / joint teleop primitives with rate limits

- **ID:** [#589020](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589020)
- **State:** New
- **Assignee:** Unassigned

**Description**

Typed teleop primitives (LinearVelocity, Twist, JointVelocity)
with unit-safe values and per-primitive rate-limit metadata.
Usable by both BT nodes and the operator interface.

**Acceptance Criteria**

Primitive dataclasses defined with unit-safe fields. 
Rate-limit metadata is a first-class attribute on each primitive. 
Unit tests cover boundary values.

##### [Task] Author primitive dataclasses

- **ID:** [#589021](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589021)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author LinearVelocity, Twist, JointVelocity dataclasses under robot_abstraction/domain/teleop.py.

##### [Task] Rate-limit metadata model

- **ID:** [#589023](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589023)
- **State:** New
- **Assignee:** Unassigned

**Description**

Attach min/max magnitude and max frequency metadata to each primitive.

##### [Task] Unit tests

- **ID:** [#589025](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589025)
- **State:** New
- **Assignee:** Unassigned

**Description**

Unit test boundary values and immutability.

#### [User Story] Contract test asserting adapters honour rate limits

- **ID:** [#589026](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589026)
- **State:** New
- **Assignee:** Unassigned

**Description**

A shared contract test bombards each adapter with teleop
primitives above declared rate limits and asserts the adapter
either throttles cleanly or returns `Result.err(RateLimited)`
— never raises.

**Acceptance Criteria**

Contract test parametrised across adapters. 
Fake adapter demonstrates both throttling and clean rejection paths.

##### [Task] Add teleop methods to port

- **ID:** [#589027](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589027)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add send_velocity / send_twist / send_joint_velocity to the RobotDriver Protocol.

##### [Task] Wire fake teleop behaviour

- **ID:** [#589028](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589028)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend logging-fake to enforce a declared rate limit and reject cleanly on breach.

##### [Task] Contract test module

- **ID:** [#589029](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589029)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the rate-limit contract-test module under tests/contract/robot_drivers/.

### [Feature] Safety hooks in RobotDriver port

- **ID:** [#589030](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589030)
- **State:** New
- **Assignee:** Unassigned

**Description**

Port-side safety surface only: e-stop request/ack semantics,
watchdog liveness contract, operational-envelope predicates, and
command-timeout signalling — as *shape* on the RobotDriver port
and its DTOs. No enforcement code and no cross-adapter test
harness here; the "must pass safety contract suite" DoD is owned
by Epic 8's new safety contract-test harness Feature, which every
adapter Feature in Epic 3 (robot_abstraction) and Epic 13 (vendor
adapters) is required to satisfy.

**Acceptance Criteria**

`emergency_stop()` mandatory on every adapter. 
Watchdog timeout in Settings; on expiry the driver receives e-stop. 
Contract test asserts fail-safe behaviour under simulated watchdog timeout.

#### [User Story] emergency_stop() mandatory on port with fail-safe default

- **ID:** [#589031](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589031)
- **State:** New
- **Assignee:** Unassigned

**Description**

Make `emergency_stop()` a mandatory method on the RobotDriver
Protocol. Provide a fail-safe default mixin adapters can
reuse. Any adapter missing an override must still refuse
further motion commands.

**Acceptance Criteria**

Port declares `emergency_stop()` returning `Result[None, SkynetError]`. 
Default mixin sets an internal stopped flag and short-circuits subsequent motion calls. 
Contract test asserts post-e-stop motion calls return `Result.err(...)`.

##### [Task] Add emergency_stop to Protocol

- **ID:** [#589032](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589032)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add the emergency_stop method to the RobotDriver Protocol.

##### [Task] Fail-safe mixin

- **ID:** [#589033](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589033)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the fail-safe default mixin under robot_abstraction/adapters/outbound/_common/.

##### [Task] Contract test

- **ID:** [#589034](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589034)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add contract test asserting post-e-stop motion refusal across adapter fixtures.

#### [User Story] Watchdog / heartbeat mechanism driven by Settings

- **ID:** [#589035](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589035)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce a heartbeat contract: adapters must be pinged
within a configured interval or the runtime issues
`emergency_stop()`. Timeout comes from pydantic-settings and
is wired in bootstrap.

**Acceptance Criteria**

Watchdog timeout field on Settings; documented in .env.dev.example. 
Runtime watchdog component in `robot_abstraction/application/` triggers e-stop on expiry. 
Contract test simulates timeout and asserts e-stop path.

##### [Task] Settings field + .env.dev.example entry

- **ID:** [#589036](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589036)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add watchdog_timeout to Settings and document in .env.dev.example.

##### [Task] Watchdog application service

- **ID:** [#589037](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589037)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the watchdog component under robot_abstraction/application/ that emits e-stop on expiry.

##### [Task] Wire watchdog in bootstrap

- **ID:** [#589038](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589038)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire the watchdog into bootstrap composition of the RobotDriver.

##### [Task] Contract test for watchdog timeout

- **ID:** [#589039](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589039)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add the simulated-timeout contract test.

#### [User Story] Safety-envelope hooks (geofence, joint limits)

- **ID:** [#589043](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589043)
- **State:** New
- **Assignee:** Unassigned

**Description**

First-class safety-envelope hooks on the port: geofence for
mobile robots, joint-limit envelope for manipulators. Adapters
may opt out but the default rejects out-of-envelope commands.

**Acceptance Criteria**

Envelope config carried on the AffordanceManifest. 
Guard rejects out-of-envelope commands with `Result.err(EnvelopeBreach)`. 
Unit tests cover geofence + joint-limit cases.

##### [Task] Envelope config model

- **ID:** [#589046](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589046)
- **State:** New
- **Assignee:** Unassigned

**Description**

Model Geofence and JointLimits config carried on the manifest.

##### [Task] Envelope guard helper

- **ID:** [#589047](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589047)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the guard helper wrapping motion + teleop calls.

##### [Task] Unit tests

- **ID:** [#589048](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589048)
- **State:** New
- **Assignee:** Unassigned

**Description**

Unit test geofence + joint-limit rejection paths.

### [Feature] RobotDriver contract-test suite (interchangeability)

- **ID:** [#589049](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589049)
- **State:** New
- **Assignee:** Unassigned

**Description**

SCOPING NOTE — split existing user stories into ≤8 SP items at
the first sprint planning. Current scope (parametrised contract
suite covering port methods + guards + telemetry + safety + error
mapping + adapter registration + diagnostics) was estimated at
13+ SP under the old {3,5} regime and hides that split. Range
now expanded to {1,2,3,5,8}; stories must be re-estimated
individually and any story exceeding 8 SP must be split. 
RobotDriver contract-test suite (interchangeability): a shared
pytest suite that every RobotDriver adapter must pass, proving
that vendor differences are absorbed at the adapter boundary.
Delivered strictly ports-before-adapters per AGENTS.md.

**Acceptance Criteria**

Suite covers every port method, affordance guard, telemetry emission, safety hook, and error-mapping case. 
Failure output identifies port method + expected vs actual. 
Adding a new adapter is a single-line fixture registration.

#### [User Story] Parametrised contract-test suite scaffold under tests/contract/robot_drivers/

- **ID:** [#589050](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589050)
- **State:** New
- **Assignee:** Unassigned

**Description**

Build the shared parametrised contract-test suite covering
every port method, affordance guard, telemetry emission,
safety hook and error-mapping case. Every adapter fixture
must pass identically.

**Acceptance Criteria**

Suite modules cover port methods + guards + telemetry + safety + error mapping. 
Logging-fake adapter passes the whole suite. 
CI runs the suite as part of the basic-checks pipeline.

##### [Task] Suite directory + shared fixtures

- **ID:** [#589051](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589051)
- **State:** New
- **Assignee:** Unassigned

**Description**

Create tests/contract/robot_drivers/ with conftest.py declaring the parametrised adapter fixture.

##### [Task] Port-method coverage module

- **ID:** [#589054](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589054)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author test module covering every RobotDriver Protocol method.

##### [Task] Affordance + safety + telemetry modules

- **ID:** [#589056](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589056)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author separate modules for affordance guards, safety hooks and telemetry emission.

##### [Task] CI wiring

- **ID:** [#589057](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589057)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire the suite into the CI Basic-Checks pipeline so it runs on every PR.

#### [User Story] Single-line fixture registration and structured failure diagnostics

- **ID:** [#589058](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589058)
- **State:** New
- **Assignee:** Unassigned

**Description**

Registering a new adapter into the contract suite must be a
single-line fixture addition. Failures identify port method,
adapter name, expected and actual outcomes.

**Acceptance Criteria**

Adapter registration is a single decorator or fixture entry. 
Failure output includes adapter name, method, expected, actual. 
Documented in docs/12 update PR.

##### [Task] Fixture registry helper

- **ID:** [#589059](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589059)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the fixture registry helper accepting a one-line adapter registration.

##### [Task] Structured failure diagnostics

- **ID:** [#589060](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589060)
- **State:** New
- **Assignee:** Unassigned

**Description**

Customise pytest failure output to include adapter + method + expected/actual.

##### [Task] Docs update PR (docs/12)

- **ID:** [#589061](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589061)
- **State:** New
- **Assignee:** Unassigned

**Description**

Update docs/12 with the registration recipe (docs edit will be raised separately per AGENTS.md scope; ticket only).

## [Epic] Heterogeneous Fleet Coordination

- **ID:** [#589062](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589062)
- **State:** New
- **Assignee:** Unassigned

**Description**

Turn the single-robot stub of Epic 2 into real multi-robot coordination: an affordance-based eligibility engine per docs/09 §Eligibility, a Reservation aggregate with a reservation_repository outbound port per docs/09 §Reservations, heterogeneous BT node semantics (Parallel decorator, per-robot subtree instantiation, tick-time affordance gating) per docs/10 §Heterogeneous nodes, and fleet projections exposed via operator_interface. All wired via inbound ports EvaluateAssignmentPort and GetPlanningCandidatesPort.

### [Feature] Reservation aggregate and repository

- **ID:** [#589063](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589063)
- **State:** New
- **Assignee:** Unassigned

**Description**

Domain aggregate with lifecycle (requested -> held ->
released / expired); `reservation_repository` outbound port +
in-memory adapter. Ref docs/09 §Reservations. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Aggregate invariants unit-tested. 
Repository contract test parametrisable.

#### [User Story] Reservation aggregate with lifecycle and invariants

- **ID:** [#589064](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589064)
- **State:** New
- **Assignee:** Unassigned

**Description**

Domain aggregate under `fleet_coordination/domain/` modelling
the reservation lifecycle: requested -> held -> released /
expired. Invariants: single-holder-at-a-time, non-negative
duration, expiry monotonicity.

**Acceptance Criteria**

Aggregate + state enum defined; transitions guarded. 
Invariants enforced in `__post_init__` and transition methods. 
Unit tests cover every legal + illegal transition.

##### [Task] Aggregate + state enum

- **ID:** [#589065](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589065)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author Reservation aggregate + ReservationState enum.

##### [Task] Transition methods with guards

- **ID:** [#589066](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589066)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement hold(), release(), expire() with invariant guards.

##### [Task] Unit tests for transitions

- **ID:** [#589067](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589067)
- **State:** New
- **Assignee:** Unassigned

**Description**

Unit test legal + illegal transitions and invariant breaches.

#### [User Story] reservation_repository outbound port and in-memory adapter with contract test

- **ID:** [#589068](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589068)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the reservation_repository outbound port under
`fleet_coordination/ports/outbound/` and provide an
in-memory adapter. Add a parametrisable repository contract
test that any future durable adapter can reuse.

**Acceptance Criteria**

Port Protocol defined with save / get / list_active / release methods. 
In-memory adapter under `fleet_coordination/adapters/outbound/in_memory/`. 
Contract test parametrised on repository fixture.

##### [Task] Define repository Protocol + port DTOs

- **ID:** [#589069](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589069)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the reservation_repository Protocol and port-owned DTOs.

##### [Task] In-memory adapter

- **ID:** [#589070](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589070)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the in-memory adapter.

##### [Task] Repository contract test

- **ID:** [#589071](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589071)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the parametrised contract test under tests/contract/.

##### [Task] Bootstrap wiring

- **ID:** [#589073](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589073)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire the in-memory adapter in bootstrap for the default profile.

### [Feature] Affordance-based eligibility engine

- **ID:** [#589076](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589076)
- **State:** New
- **Assignee:** Unassigned

**Description**

Match mission actions to eligible robots by required
affordances declared on adapters (Epic 4.2). Ref docs/12 §Affordance model and docs/09 §Eligibility. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Policies unit-tested. 
`query_eligible_robots` returns typed results with per-robot rationale.

#### [User Story] Eligibility policy domain + query_eligible_robots use case

- **ID:** [#589077](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589077)
- **State:** New
- **Assignee:** Unassigned

**Description**

Model the eligibility policy in `fleet_coordination/domain/`
matching mission-action required-affordance sets to declared
adapter manifests (Epic 4.2). Expose a
`query_eligible_robots` application use case.

**Acceptance Criteria**

Policy pure-function unit-tested against fixture manifests. 
Use case returns typed EligibilityResult with per-robot verdict. 
No dependency on any concrete adapter.

##### [Task] Policy pure function

- **ID:** [#589078](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589078)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the eligibility policy pure function taking required + declared affordance sets.

##### [Task] Use case in application/

- **ID:** [#589081](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589081)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the query_eligible_robots use case wiring the policy over the reservation repository + robot registry ports.

##### [Task] Unit tests over fixtures

- **ID:** [#589083](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589083)
- **State:** New
- **Assignee:** Unassigned

**Description**

Unit test the use case against representative manifest fixtures.

##### [Task] Import-linter contract

- **ID:** [#589084](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589084)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add an import-linter contract asserting fleet_coordination does not import robot_abstraction.adapters.

#### [User Story] Per-robot rationale reporting in eligibility results

- **ID:** [#589085](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589085)
- **State:** New
- **Assignee:** Unassigned

**Description**

Attach a structured rationale to each per-robot verdict
(matched affordances, missing affordances, reservation
conflict, envelope conflict). Consumed by operator_interface
for `GET /fleet` diagnostics.

**Acceptance Criteria**

Rationale is a typed enum + payload, not free text. 
Use case populates rationale on every non-eligible verdict. 
Unit tests cover each rationale category.

##### [Task] Rationale enum + payload types

- **ID:** [#589086](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589086)
- **State:** New
- **Assignee:** Unassigned

**Description**

Model the RationaleCode enum and payload dataclasses.

##### [Task] Populate rationale in use case

- **ID:** [#589087](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589087)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend the eligibility use case to populate rationale.

##### [Task] Unit tests per category

- **ID:** [#589088](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589088)
- **State:** New
- **Assignee:** Unassigned

**Description**

Unit test each rationale category.

### [Feature] Heterogeneous BT node semantics

- **ID:** [#589089](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589089)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend BT nodes (Epic 2.5) with parallel decorator and
per-robot subtree instantiation. Nodes gate on affordances at
tick time. Ref docs/10 §BT nodes.

**Acceptance Criteria**

Two-robot fixture Plan with different affordances completes. 
Propagation policy on subtree failure is configurable and tested.

#### [User Story] Parallel decorator BT node

- **ID:** [#589090](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589090)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend the BT node set from Epic 2.5 with a Parallel
decorator supporting configurable success + failure
thresholds. Ticked deterministically.

**Acceptance Criteria**

Parallel node ticks children per configured policy. 
Unit tests cover success-threshold, failure-threshold, all-must-succeed policies.

##### [Task] Parallel node implementation

- **ID:** [#589091](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589091)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the Parallel decorator BT node.

##### [Task] Policy enum + config

- **ID:** [#589092](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589092)
- **State:** New
- **Assignee:** Unassigned

**Description**

Model the ParallelPolicy enum and configuration.

##### [Task] Unit tests per policy

- **ID:** [#589093](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589093)
- **State:** New
- **Assignee:** Unassigned

**Description**

Unit test each policy variant.

#### [User Story] Per-robot subtree instantiation

- **ID:** [#589094](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589094)
- **State:** New
- **Assignee:** Unassigned

**Description**

Given a Plan with per-action target robots, instantiate one
subtree per robot so the executor can run them under the
Parallel decorator. Bindings are pure; no runtime state
leaks between subtrees.

**Acceptance Criteria**

Subtree factory produces isolated subtrees keyed by RobotId. 
Two-robot fixture Plan executes end-to-end. 
No cross-subtree state leakage under the in-memory blackboard.

##### [Task] Subtree factory

- **ID:** [#589095](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589095)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the subtree factory in mission_execution/application/.

##### [Task] Two-robot fixture Plan

- **ID:** [#589096](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589096)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author a two-robot fixture Plan and integration test.

##### [Task] Isolation assertions

- **ID:** [#589098](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589098)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add assertions guaranteeing no cross-subtree blackboard leakage.

##### [Task] Bootstrap wiring

- **ID:** [#589100](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589100)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire the subtree factory into bootstrap composition.

#### [User Story] Tick-time affordance gating and configurable subtree-failure propagation

- **ID:** [#589101](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589101)
- **State:** New
- **Assignee:** Unassigned

**Description**

BT nodes gate on the RobotDriver's declared affordances at
tick time and short-circuit with a typed failure when the
affordance is missing. Subtree-failure propagation policy
(fail-fast vs continue-others) is configurable and covered
by tests.

**Acceptance Criteria**

Missing-affordance tick returns a typed failure — no exception. 
Propagation policy selectable via Plan metadata or Settings. 
Unit tests cover both propagation policies.

##### [Task] Affordance-gate decorator

- **ID:** [#589103](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589103)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the tick-time affordance-gate decorator node.

##### [Task] Propagation policy plumbing

- **ID:** [#589105](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589105)
- **State:** New
- **Assignee:** Unassigned

**Description**

Thread the propagation policy from Plan metadata into the Parallel node.

##### [Task] Unit tests

- **ID:** [#589107](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589107)
- **State:** New
- **Assignee:** Unassigned

**Description**

Unit test both fail-fast and continue-others policies.

### [Feature] Fleet projections and read APIs

- **ID:** [#589108](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589108)
- **State:** New
- **Assignee:** Unassigned

**Description**

Read-side projections over runtime_state exposing per-robot
occupancy + reservation state to operator_interface. Ref docs/09 §Fleet coordination. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

`GET /fleet` returns projection. 
Refresh latency < 100 ms in in-memory profile.

#### [User Story] Per-robot occupancy projection over runtime_state

- **ID:** [#589109](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589109)
- **State:** New
- **Assignee:** Unassigned

**Description**

Read-side projection materialising per-robot occupancy and
current-reservation state from the runtime_state event bus.
Kept in-memory; refresh on event.

**Acceptance Criteria**

Projection module under `fleet_coordination/application/projections/`. 
Subscribes to runtime_state event bus (via port, not adapter). 
Refresh latency < 100 ms in the in-memory profile (asserted).

##### [Task] Projection model + updater

- **ID:** [#589111](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589111)
- **State:** New
- **Assignee:** Unassigned

**Description**

Author the projection dataclass and event-driven updater.

##### [Task] Event-bus subscription via port

- **ID:** [#589112](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589112)
- **State:** New
- **Assignee:** Unassigned

**Description**

Wire the projection to the runtime_state event-bus port.

##### [Task] Latency assertion test

- **ID:** [#589114](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589114)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add integration test asserting < 100 ms refresh latency in-memory.

#### [User Story] GET /fleet read API on operator_interface

- **ID:** [#589115](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589115)
- **State:** New
- **Assignee:** Unassigned

**Description**

Expose the projection through operator_interface via a local
inbound port and its HTTP inbound adapter (Epic 3). Bridge
adapter reaches fleet_coordination's public read port.

**Acceptance Criteria**

Local inbound port `ViewFleet` defined on operator_interface. 
Bridge outbound adapter to fleet_coordination. 
HTTP handler returns projection; contract-test covers the bridge.

##### [Task] Local ViewFleet port + DTO

- **ID:** [#589116](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589116)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the ViewFleet local inbound port and DTO under operator_interface/ports/.

##### [Task] fleet_coordination bridge adapter

- **ID:** [#589117](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589117)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement the outbound bridge adapter to fleet_coordination's public read port.

##### [Task] HTTP handler + contract test

- **ID:** [#589118](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589118)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add the FastAPI handler and the bridge contract test.

### [Feature] SchedulingPolicy port

- **ID:** [#590850](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590850)
- **State:** New
- **Assignee:** Unassigned

**Description**

Complements Feature 5.2 (affordance-based eligibility, which
answers "who CAN"): SchedulingPolicy answers "who SHOULD",
given cost / battery / distance / current load. FirstFit
default adapter suffices while there is only one candidate per
mission; CostBased adapter deferred until a real multi-robot
allocation scenario appears.

**Acceptance Criteria**

SchedulingPolicy port defined in fleet_coordination/ports/outbound/. 
FirstFit default adapter passes contract tests. 
CostBased deferred with a decision trigger.

#### [User Story] SchedulingPolicy outbound port

- **ID:** [#590851](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590851)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the port method
choose(mission: Mission, candidates: Iterable[RobotId]) ->
Result[RobotId, NoEligibleRobot]. No policy logic in
fleet_coordination.application — policy lives in adapters.

**Acceptance Criteria**

Port lives in fleet_coordination/ports/outbound/scheduling_policy/port.py. 
Return type uses shared_kernel Result.

##### [Task] Author SchedulingPolicy Protocol

- **ID:** [#590852](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590852)
- **State:** New
- **Assignee:** Unassigned

**Description**

Protocol definition + return type.

#### [User Story] FirstFit default adapter

- **ID:** [#590853](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590853)
- **State:** New
- **Assignee:** Unassigned

**Description**

Trivial adapter returning the first candidate in insertion
order. Documented as intentional baseline; NOT for multi-
robot production use.

**Acceptance Criteria**

Adapter passes the shared contract test. 
README notes it is baseline-only.

##### [Task] FirstFitSchedulingPolicy implementation

- **ID:** [#590854](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590854)
- **State:** New
- **Assignee:** Unassigned

**Description**

Returns next(iter(candidates)) or NoEligibleRobot when empty.

##### [Task] Contract test skeleton for SchedulingPolicy adapters

- **ID:** [#590855](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590855)
- **State:** New
- **Assignee:** Unassigned

**Description**

Shared pytest fixture any adapter can be wired into.

#### [User Story] CostBased adapter — deferred placeholder

- **ID:** [#590856](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590856)
- **State:** New
- **Assignee:** Unassigned

**Description**

Placeholder for a future CostBased adapter combining
battery / distance / current-load / affordance-fit into a
weighted score. Deferred until a real multi-robot scenario
appears.

**Acceptance Criteria**

Story remains in Backlog with decision trigger.

## [Epic] Persistence & Data Architecture

- **ID:** [#589119](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589119)
- **State:** New
- **Assignee:** Unassigned

**Description**

Replace the in-memory state_backend with a durable adapter chosen by ADR (Redis-class KV vs stream-store) and codify a repository-port convention across capabilities per docs/06 §Outbound repository ports and docs/11 §Durability. Any vector store need (planner strategies, semantic search) lands as an outbound adapter behind a VectorStore port using the preferred Qdrant client per AGENTS.md. No relational ORM is introduced; if one becomes necessary it enters behind a capability-owned port, never as shared infrastructure.

### [Feature] ADR: durable state_backend technology

- **ID:** [#589120](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589120)
- **State:** New
- **Assignee:** Unassigned

**Description**

Choose Redis / Valkey / other; record consequences. Ref docs/11 §state_backend. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

ADR merged. 
docs/14 updated.

### [Feature] Durable state_backend adapter

- **ID:** [#589121](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589121)
- **State:** New
- **Assignee:** Unassigned

**Description**

Implement chosen backend under
`runtime_state/adapters/outbound/blackboard/` behind the
existing port. Selection via env var. Ref docs/11 §state_backend.

**Acceptance Criteria**

Passes the existing state_backend contract suite. 
E2E slice runs unchanged.

### [Feature] Repository port convention

- **ID:** [#589122](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589122)
- **State:** New
- **Assignee:** Unassigned

**Description**

Every capability owns its own repository port + adapter; no
shared ORM / schema. Enforced by import-linter. Ref docs/06 §Outbound repository ports.

**Acceptance Criteria**

Contract in `.importlinter`. 
docs/14 updated.

### [Feature] Vector store adapter (behind a port)

- **ID:** [#589123](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589123)
- **State:** New
- **Assignee:** Unassigned

**Description**

When required by a planner strategy, introduce a `VectorStore`
port owned by the consuming capability; Qdrant adapter is the
first implementation. Ref AGENTS.md 'Preferred libraries when the need arises' (Qdrant). Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Adapter passes contract tests. 
No capability imports `qdrant-client` outside its adapter.

## [Epic] Observability & Error Handling (cross-cutting)

- **ID:** [#589124](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589124)
- **State:** New
- **Assignee:** Unassigned

**Description**

Instrument the framework from day 0: declarative Loguru sinks configured in bootstrap per AGENTS.md and docs/16 §Logging, the SkynetError taxonomy applied consistently across capabilities per docs/16 §Errors and shared_kernel canon, CorrelationId/CausationId propagated on every EventEnvelope per docs/11 §EventEnvelope, and OpenTelemetry spans on port boundaries. Runs alongside outcome epics — never retrofitted.

### [Feature] Declarative Loguru sinks in bootstrap

- **ID:** [#589125](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589125)
- **State:** New
- **Assignee:** Unassigned

**Description**

File / stderr / remote sinks declared via Settings;
correlation-id enrichment via contextvars. Ref docs/16 §Logging and AGENTS.md Loguru. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Sinks configurable via `.env.dev`. 
Records carry `correlation_id`, `mission_id`, `robot_id` when in context.

### [Feature] SkynetError taxonomy applied across capabilities

- **ID:** [#589126](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589126)
- **State:** New
- **Assignee:** Unassigned

**Description**

Every port method returns `Result[T, SkynetError-subtype]` or
raises a documented subtype. Mappers translate to CLI exit
codes and HTTP/MCP error bodies. Ref docs/16 §Errors and shared_kernel canon.

**Acceptance Criteria**

Import-linter flags naked `Exception` raises in `domain/`, `application/`, `ports/`.

### [Feature] Correlation IDs propagated across capabilities

- **ID:** [#589127](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589127)
- **State:** New
- **Assignee:** Unassigned

**Description**

`CorrelationId` / `CausationId` from shared_kernel flow
through inbound adapter -> application service -> outbound
adapter via contextvars. Ref docs/11 §EventEnvelope and docs/16 §Correlation. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Integration test asserts propagation across a mission submit -> execute -> telemetry-emit chain.

### [Feature] Tracing spans on port boundaries

- **ID:** [#589128](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589128)
- **State:** New
- **Assignee:** Unassigned

**Description**

Lightweight span decorators on inbound / outbound port
methods; stub tracer initially, OTel later behind a port. Ref docs/16 §Tracing. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Spans visible in logs. 
Overhead < 5% on the E2E harness.

## [Epic] Reliability, Safety & Eventing (cross-cutting)

- **ID:** [#589130](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589130)
- **State:** New
- **Assignee:** Unassigned

**Description**

Cross-cutting reliability primitives (EventEnvelope, retries with
idempotency, backpressure, async conventions) plus the
safety contract-test harness that every robot adapter Feature
must satisfy (e-stop, watchdog, envelope, command timeout,
deadman). Renamed from "Eventing, Concurrency & Reliability" to
surface safety enforcement as a first-class deliverable of this
epic. Port-side safety hooks remain owned by robot_abstraction
(Feature #589030); this epic owns the enforcement mechanism.

### [Feature] EventEnvelope with correlation & causation

- **ID:** [#589131](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589131)
- **State:** New
- **Assignee:** Unassigned

**Description**

Canonical envelope carrying `correlation_id`, `causation_id`,
`occurred_at`, `producer`. All events use it. Ref docs/11 §EventEnvelope.

**Acceptance Criteria**

Contract test asserts propagation across a chain of two consumers.

#### [User Story] EventRecorder outbound adapter

- **ID:** [#590908](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590908)
- **State:** New
- **Assignee:** Unassigned

**Description**

Cheap debugging investment: subscribe to the EventBus and
append every envelope to a durable sink. Day 0 ships one
concrete adapter (JsonlFileEventRecorder) writing JSON
Lines to a UPath-managed file. Replay harness lives in
Epic 9 (linked). Every envelope recorded exactly once
(verified by contract test).

**Acceptance Criteria**

EventRecorder outbound port defined next to the EventBus port. 
JsonlFileEventRecorder ships day 0 and passes contract test. 
Contract test asserts every emitted envelope is recorded exactly once. 
Replay harness explicitly deferred to Epic 9 with a linked story.

##### [Task] Author EventRecorder outbound port

- **ID:** [#590909](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590909)
- **State:** New
- **Assignee:** Unassigned

**Description**

Port method: append(envelope: EventEnvelope) -> Result.

##### [Task] JsonlFileEventRecorder adapter

- **ID:** [#590910](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590910)
- **State:** New
- **Assignee:** Unassigned

**Description**

Append-only JSONL sink using UPath for local/remote paths.

##### [Task] Contract test — every envelope recorded exactly once

- **ID:** [#590911](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590911)
- **State:** New
- **Assignee:** Unassigned

**Description**

Publish N envelopes; assert JSONL sink has N lines with matching correlation ids.

##### [Task] Link replay harness follow-up to Epic 9

- **ID:** [#590912](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590912)
- **State:** New
- **Assignee:** Unassigned

**Description**

Create a comment / linked work-item note under the SIL suite feature.

##### [Task] Author EventBus port + envelope schema

- **ID:** [#578700](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/578700)
- **State:** New
- **Assignee:** Unassigned

**Description**

Typed on the payload; carries correlation/causation ids.

##### [Task] Unit tests for EventEnvelope

- **ID:** [#591737](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/591737)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add tests/unit/shared_kernel/test_envelope.py covering:
- construction and immutability
- validation (missing correlation_id, naive timestamp)
- causation-chain semantics (envelope B causes envelope C, etc.)
- a generic-payload example exercising the type parameter

Replaces deleted task #581456.

### [Feature] Retry utility and idempotency keys

- **ID:** [#589132](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589132)
- **State:** New
- **Assignee:** Unassigned

**Description**

Reusable retry decorator with typed backoff;
idempotency-key mechanism for outbound calls that must not
double-effect. Ref docs/16 §Retries. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Applied to at least one adapter (e.g. vendor RobotDriver). 
Covered by unit tests.

### [Feature] Backpressure and ordering guarantees

- **ID:** [#589133](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589133)
- **State:** New
- **Assignee:** Unassigned

**Description**

Bounded queues on the event bus with defined overflow policy;
per-key FIFO on state_backend subscriptions. Ref docs/11 §Backpressure. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Load test proves bounded memory. 
Ordering test proves per-key FIFO.

### [Feature] Async concurrency conventions

- **ID:** [#589134](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589134)
- **State:** New
- **Assignee:** Unassigned

**Description**

Standardised asyncio patterns (task supervision, cancellation
propagation) documented and enforced. Ref AGENTS.md 'Async concurrency conventions'. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Convention doc merged. 
Lint rule blocks bare `asyncio.create_task` without supervisor.

### [Feature] Safety contract-test harness

- **ID:** [#590857](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590857)
- **State:** New
- **Assignee:** Unassigned

**Description**

Cross-cutting enforcement mechanism for the port-side safety
hooks defined in Feature #589030. A shared pytest suite under
tests/contract/robot_drivers/safety/ that every RobotDriver
adapter (in Epic 3 and every vendor in Epic 13) must pass:
e-stop cascade, watchdog liveness, envelope violation, command
timeout, deadman switch. DoD update recorded on adapter
Features so no adapter is Done without passing the suite.

**Acceptance Criteria**

Suite lives under tests/contract/robot_drivers/safety/. 
All five test templates present and parametrised. 
Epic 3 & Epic 13 Feature templates updated with the DoD line.

#### [User Story] Author safety contract-test suite skeleton

- **ID:** [#590858](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590858)
- **State:** New
- **Assignee:** Unassigned

**Description**

Skeleton module with a parametrised pytest harness that
any RobotDriver adapter can plug into via a conftest
fixture. No test bodies yet — just the wiring.

**Acceptance Criteria**

Skeleton module exists; a null-adapter dummy test passes.

##### [Task] Author harness module + adapter-factory fixture

- **ID:** [#590859](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590859)
- **State:** New
- **Assignee:** Unassigned

**Description**

Module skeleton + pytest fixture protocol.

#### [User Story] E-stop cascade test template

- **ID:** [#590860](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590860)
- **State:** New
- **Assignee:** Unassigned

**Description**

Template verifying that .estop() on the RobotDriver port
causes the adapter to halt all motion within a configured
deadline and to report ESTOPPED state.

**Acceptance Criteria**

Template asserts halt-within-deadline and state transition.

##### [Task] Author e-stop test template

- **ID:** [#590861](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590861)
- **State:** New
- **Assignee:** Unassigned

**Description**

Parametrised test asserting halt semantics.

#### [User Story] Watchdog liveness test template

- **ID:** [#590862](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590862)
- **State:** New
- **Assignee:** Unassigned

**Description**

Template verifying that when the operator stops sending
heartbeats for longer than the configured watchdog window,
the adapter transitions to a safe state and emits the
expected event.

**Acceptance Criteria**

Template asserts safe-state transition and event emission on missed heartbeat.

##### [Task] Author watchdog test template

- **ID:** [#590863](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590863)
- **State:** New
- **Assignee:** Unassigned

**Description**

Uses FrozenClock to simulate elapsed time.

#### [User Story] Envelope violation test template

- **ID:** [#590864](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590864)
- **State:** New
- **Assignee:** Unassigned

**Description**

Template verifying that commands violating the
operational envelope (velocity / acceleration / workspace
bounds) are rejected at the port boundary, not silently
clamped by the adapter.

**Acceptance Criteria**

Template asserts rejection with a typed EnvelopeViolation error.

##### [Task] Author envelope violation test template

- **ID:** [#590865](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590865)
- **State:** New
- **Assignee:** Unassigned

**Description**

Parametrised over sample violation cases.

#### [User Story] Command timeout & deadman-switch test templates

- **ID:** [#590866](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590866)
- **State:** New
- **Assignee:** Unassigned

**Description**

Two templates:
(a) A command whose execution exceeds the configured
    timeout is cancelled and reports TimedOut.
(b) A teleop stream whose deadman is released halts motion
    within one control period.

**Acceptance Criteria**

Both templates present and pass against a reference adapter.

##### [Task] Author command timeout template

- **ID:** [#590867](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590867)
- **State:** New
- **Assignee:** Unassigned

**Description**

Uses FrozenClock to trigger the timeout deterministically.

##### [Task] Author deadman-switch template

- **ID:** [#590868](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590868)
- **State:** New
- **Assignee:** Unassigned

**Description**

Simulates release; asserts motion halt within one control period.

#### [User Story] DoD update — every robot adapter Feature must pass the safety suite

- **ID:** [#590869](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590869)
- **State:** New
- **Assignee:** Unassigned

**Description**

Textual DoD update recorded on Epic 3 (robot_abstraction)
adapter-facing Features and on every Feature under Epic 13
(Robot Adapter Onboarding). No adapter Feature can be
marked Done without the safety contract suite passing.

**Acceptance Criteria**

DoD line added to each targeted Feature description. 
Followed up by a discussion comment referencing this suite.

## [Epic] Simulation & Test Harness (cross-cutting)

- **ID:** [#589135](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589135)
- **State:** New
- **Assignee:** Unassigned

**Description**

Sim-first testing is first-class: logging-fake RobotDriver from day 0, generic fake-port fixtures reused across unit tests per docs/17 §Fakes, a RobotDriver contract-test harness run identically against real and sim adapters per docs/12 §Contract tests, per-vendor sim integrations, a SIL suite, and deferred HIL hooks. CI matrix runs logging-sim on every PR, vendor sim nightly, and HIL on-demand per AGENTS.md CI conventions.

### [Feature] Day-0 fake RobotDriver adapters (logging + kinematic)

- **ID:** [#589136](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589136)
- **State:** New
- **Assignee:** Unassigned

**Description**

Two day-0 fake RobotDriver adapters shipped alongside the port
surface so no capability code ever waits on real hardware to
make progress. Logging-fake records commands and synthesises
deterministic telemetry (proves wiring). Kinematic-fake Euler-
integrates pose from velocity commands (proves the framework
respects spatial semantics). Both live under
robot_abstraction/adapters/outbound/ and are wired via bootstrap
profiles. Delivered strictly ports-before-adapters per AGENTS.md
'Ports before adapters, always'. Renamed from "Logging-fake
RobotDriver (day 0)" after v2 backlog added the kinematic-fake
story #590913.

**Acceptance Criteria**

Passes the RobotDriver contract suite (Epic 4.6 once available). 
Usable as the default adapter in `bootstrap`.

#### [User Story] Kinematic-fake RobotDriver adapter (day-0 second adapter)

- **ID:** [#590913](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590913)
- **State:** New
- **Assignee:** Unassigned

**Description**

Second day-0 adapter alongside logging-fake. Euler-
integrates pose from velocity commands using a WallClock or
FrozenClock. Cheap to build, huge value: proves the
framework respects pose composition and velocity integration
— the logging-fake proves nothing about spatial semantics.
Wired into a 'kinematic-fake' bootstrap profile.

**Acceptance Criteria**

KinematicFakeDriver adapter lives under robot_abstraction/adapters/outbound/kinematic_fake/. 
Commanded velocity yields expected pose after Δt (unit-tested with FrozenClock). 
Bootstrap profile 'kinematic-fake' wires it in. 
Passes RobotDriver contract-test suite + safety contract-test suite.

##### [Task] KinematicFakeDriver implementation

- **ID:** [#590914](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590914)
- **State:** New
- **Assignee:** Unassigned

**Description**

Integrator maintains (x, y, theta) or (x, y, z, quat); commanded velocity produces expected pose after Δt.

##### [Task] Unit tests — pose after Δt matches integrator

- **ID:** [#590915](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590915)
- **State:** New
- **Assignee:** Unassigned

**Description**

FrozenClock-driven; multiple velocity profiles.

##### [Task] Bootstrap profile 'kinematic-fake'

- **ID:** [#590916](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590916)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend Settings + wiring; documented in bootstrap README.

##### [Task] Wire into RobotDriver + safety contract suites

- **ID:** [#590917](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590917)
- **State:** New
- **Assignee:** Unassigned

**Description**

Two conftest fixtures instantiating the adapter.

### [Feature] Generic fake-port fixtures for unit tests

- **ID:** [#589137](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589137)
- **State:** New
- **Assignee:** Unassigned

**Description**

A reusable fixtures library under `tests/fixtures/` providing
typed fakes for any port. Application services are unit-tested
without touching adapters. Ref docs/03 §Architecture Implementation and AGENTS.md.

**Acceptance Criteria**

Every port has a fake fixture registered. 
Template documented.

### [Feature] RobotDriver contract-test harness (real + sim identical)

- **ID:** [#589138](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589138)
- **State:** New
- **Assignee:** Unassigned

**Description**

Shared harness (see Epic 4.6) executed against every adapter
— real and sim — so interchangeability is proven, not
asserted. Ref docs/12 §Contract tests and AGENTS.md 'Simulation'. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Adapter passes => green. 
No adapter-specific carve-outs.

### [Feature] Per-vendor sim integrations

- **ID:** [#589139](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589139)
- **State:** New
- **Assignee:** Unassigned

**Description**

As each vendor adapter onboards in Epic 13, a sim sibling is
added: Unitree Gazebo for Go2/Go2 EDU, MuJoCo for G1/H1
humanoids, MAVLink SITL (PX4/ArduPilot) for drones. All real
technologies; no invented sims. Ref docs/17 §Integration and E2E suites.

**Acceptance Criteria**

Each sim adapter passes the RobotDriver contract suite. 
Sim adapter shares the vendor's affordance manifest.

### [Feature] SIL integration test suite

- **ID:** [#589140](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589140)
- **State:** New
- **Assignee:** Unassigned

**Description**

Software-in-the-loop integration tests exercising the E2E
slice with each available sim adapter as the driver. Ref docs/17 §Integration and E2E suites. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Suite tagged `sil`. 
Runs nightly.

### [Feature] HIL test hooks (deferred)

- **ID:** [#589141](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589141)
- **State:** New
- **Assignee:** Unassigned

**Description**

Placeholder hooks and documented procedure for
hardware-in-the-loop tests; execution deferred until hardware
is routinely available in CI-controlled cells. Ref docs/17 §HIL hooks. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Hooks defined. 
On-demand runner documented.

### [Feature] CI wiring: logging-sim always, vendor-sim nightly, HIL on-demand

- **ID:** [#589142](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589142)
- **State:** New
- **Assignee:** Unassigned

**Description**

CI pipelines split into three tiers with clear cost /
reliability trade-offs. Ref docs/16 §Logging and AGENTS.md Loguru. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

PR pipeline green in < 10 min with logging-sim. 
Nightly pipeline runs vendor sims. 
HIL pipeline runs manually.

## [Epic] Testing & Architecture Enforcement (deepening, cross-cutting)

- **ID:** [#589143](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589143)
- **State:** New
- **Assignee:** Unassigned

**Description**

Deepen the enforcement layer beyond import-linter: a contract-test harness per port under tests/contract/ per docs/17 §Contract tests, integration and E2E suites covering multi-capability flows, architecture tests asserting DTO ownership and adapter isolation per docs/17 §Architecture tests, and coverage gating tightened as capabilities stabilise. Every rule is executable in CI so 'the docs are right' becomes 'the build proves it'.

### [Feature] Contract-test harness per port

- **ID:** [#589144](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589144)
- **State:** New
- **Assignee:** Unassigned

**Description**

Parametrised harness under `tests/contract/<port_name>/` that
every adapter must pass. Ref docs/03 §Architecture Implementation and AGENTS.md. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Every outbound port has a contract harness. 
Adding a new adapter is a one-file registration.

### [Feature] Integration and E2E suites

- **ID:** [#589145](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589145)
- **State:** New
- **Assignee:** Unassigned

**Description**

Multi-capability integration tests + full happy-path E2E
extending the Epic 2 harness with fleet + operator scenarios. Ref docs/17 §Integration and E2E suites. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Suites tagged and runnable independently. 
E2E gated on main.

### [Feature] Architecture tests beyond import-linter

- **ID:** [#589146](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589146)
- **State:** New
- **Assignee:** Unassigned

**Description**

AST walkers under `tests/architecture/` enforcing port-DTO
isolation, name-collision on shared primitives, one-way
domain -> ports imports. Ref docs/17 §Architecture tests. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Tests run in < 2s. 
Failure messages include file, line, and link to the offending rule.

### [Feature] Coverage gating deepening

- **ID:** [#589147](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589147)
- **State:** New
- **Assignee:** Unassigned

**Description**

Extend the diff-cover 80% baseline with per-capability
coverage floors; track drift. Ref AGENTS.md 'Coverage gating deepening'. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

CI reports per-capability coverage. 
Regressions block PRs.

## [Epic] Deployment & Config Hardening (cross-cutting)

- **ID:** [#589148](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589148)
- **State:** New
- **Assignee:** Unassigned

**Description**

Grow pydantic-settings models per new adapter in bootstrap/config.py per AGENTS.md, produce a container image honouring the Zscaler corporate-cert quirk per AGENTS.md 'Corporate cert', pick a deployment target via ADR (k8s vs systemd vs edge), and codify environment profiles (in-memory, sim, HIL, production) each selecting a coherent adapter set. Config changes never require code changes to application services.

### [Feature] Grow Settings model per new adapter

- **ID:** [#589149](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589149)
- **State:** New
- **Assignee:** Unassigned

**Description**

Each adapter onboarded in Lane A or Epic 13 adds its typed
Settings subclass and `.env.dev.example` entry. Ref AGENTS.md 'Configuration' and docs/05 §bootstrap. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Missing required keys fail fast with a typed `SkynetConfigurationError`.

### [Feature] Container image with corporate cert

- **ID:** [#589150](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589150)
- **State:** New
- **Assignee:** Unassigned

**Description**

Dockerfile using `uv` with the Zscaler cert baked in; CI
publishes an image per tag. Ref AGENTS.md 'Container image'. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Image runs the HTTP entry point in default profile. 
< 1 GB compressed.

### [Feature] Deployment target ADR + manifests

- **ID:** [#589151](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589151)
- **State:** New
- **Assignee:** Unassigned

**Description**

Choose deployment target (Azure Container Apps, AKS, on-prem)
and record consequences; author manifests. Ref AGENTS.md 'Deployment' and docs/00 ADR framework. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

ADR merged. 
Manifest under `deploy/`.

### [Feature] Profiles: in-memory, sim, HIL, production

- **ID:** [#589152](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589152)
- **State:** New
- **Assignee:** Unassigned

**Description**

Named Settings profiles selectable via one env var, each
pre-configuring adapter selection consistently. Ref docs/12 §Contract tests and AGENTS.md 'Simulation'. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Profiles documented. 
Tests exercise each profile boot.

## [Epic] Documentation & Governance (ongoing, cross-cutting)

- **ID:** [#589153](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589153)
- **State:** New
- **Assignee:** Unassigned

**Description**

Establish and maintain the governance surface: an ADR framework and index per docs/00 §ADRs, automated change-matrix keeping docs and code in step, a terminology-governance PR check preventing drift from the shared vocabulary in shared_kernel, diagram governance, and a per-capability README currency check per AGENTS.md 'Per-capability README'. Runs as a continuous background task, never as a one-off.

### [Feature] ADR framework and index

- **ID:** [#589156](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589156)
- **State:** New
- **Assignee:** Unassigned

**Description**

ADR template under `docs/adr/`, auto-generated index, PR
checklist requiring an ADR link for architecture-affecting
changes. Ref docs/00 §ADRs. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Template merged. 
ADR-001 (per-capability hexagonal architecture) recorded.

### [Feature] Change-matrix automation

- **ID:** [#589157](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589157)
- **State:** New
- **Assignee:** Unassigned

**Description**

Automate the matrix from docs/19 so a change to a normative
doc surfaces the docs / tests it likely invalidates. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Script under `scripts/`. 
CI advisory (non-blocking) job.

### [Feature] Terminology governance PR check

- **ID:** [#589158](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589158)
- **State:** New
- **Assignee:** Unassigned

**Description**

PR check requires a note when touching docs/02 or
docs/terminology.md. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Advisory check active on all PRs.

### [Feature] Diagram governance

- **ID:** [#589160](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589160)
- **State:** New
- **Assignee:** Unassigned

**Description**

Mermaid convention; one system-context diagram; one runtime
sequence for the Epic 2 slice kept in sync with code. Ref docs/00 §Diagram governance. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Diagrams merged under `docs/diagrams/`. 
Referenced from docs/01 and docs/10.

### [Feature] Per-capability README currency check

- **ID:** [#589162](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589162)
- **State:** New
- **Assignee:** Unassigned

**Description**

CI check verifies every capability README lists its current
inbound + outbound ports; fails on drift. Ref AGENTS.md 'Per-capability README' and docs/00 §23. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Check runs. 
Failure output identifies drifted files.

## [Epic] Robot Adapter Onboarding (vendor library, never finishes; cross-cutting)

- **ID:** [#589164](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589164)
- **State:** New
- **Assignee:** Unassigned

**Description**

One Feature per vendor adapter as hardware onboards. Each feature
= an adapter implementing the Epic 4 `RobotDriver` port + its sim
sibling in Epic 9.4 + full compliance with the Epic 4.6 / Epic
9.3 contract test suite. This epic never closes — new vendors
open new features. Ref docs/12 §Per-vendor adapters.

### [Feature] Go2 (Unitree Legged SDK) — hardware in hand

- **ID:** [#589165](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589165)
- **State:** New
- **Assignee:** Unassigned

**Description**

Quadruped adapter using the Unitree Legged SDK; sim sibling
via Unitree Gazebo. Affordances: walk, trot, lie_down, stand,
teleop_velocity, teleop_twist, e-stop. Ref docs/12 §Per-vendor adapters.

**Acceptance Criteria**

Both real and Gazebo adapters pass the shared RobotDriver contract suite. 
Swap is a single env-var change.

### [Feature] Go2 EDU (Unitree Legged SDK, config diff) — hardware in hand

- **ID:** [#589166](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589166)
- **State:** New
- **Assignee:** Unassigned

**Description**

Config variant of the Go2 adapter for the EDU model; shares
codebase, differs in affordance manifest and safety envelopes. Ref docs/12 §Per-vendor adapters. Delivered strictly ports-before-adapters per AGENTS.md 'Ports before adapters, always'; no application code imports a concrete adapter.

**Acceptance Criteria**

Adapter selectable by env var. 
Contract suite green.

### [Feature] Drones (MAVLink; vendor TBD) — hardware in hand

- **ID:** [#589167](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589167)
- **State:** New
- **Assignee:** Unassigned

**Description**

Drone adapter over MAVLink (PX4 / ArduPilot). Sim sibling via
MAVLink SITL. Affordances: takeoff, land, hover, fly_to,
teleop_velocity, e-stop. Ref docs/12 §Per-vendor adapters.

**Acceptance Criteria**

ADR fixes the specific vendor + firmware. 
Real and SITL adapters pass the contract suite.

### [Feature] G1 (Unitree Humanoid SDK) — hardware incoming

- **ID:** [#589168](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589168)
- **State:** New
- **Assignee:** Unassigned

**Description**

Humanoid adapter using the Unitree Humanoid SDK; sim sibling
via MuJoCo. Affordances: walk, stand, sit, grasp, bimanual,
teleop_joint, e-stop. Ref docs/12 §Per-vendor adapters.

**Acceptance Criteria**

Real + MuJoCo adapters pass the contract suite. 
Opened when hardware arrives.

### [Feature] H1 (Unitree Humanoid SDK) — hardware incoming

- **ID:** [#589169](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589169)
- **State:** New
- **Assignee:** Unassigned

**Description**

H1 humanoid adapter using the Unitree Humanoid SDK; sim
sibling via MuJoCo. Affordance manifest differs from G1. Ref docs/12 §Per-vendor adapters.

**Acceptance Criteria**

Real + MuJoCo adapters pass the contract suite. 
Opened when hardware arrives.

### [Feature] Future vendor onboarding (placeholder)

- **ID:** [#589170](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589170)
- **State:** New
- **Assignee:** Unassigned

**Description**

Placeholder for future vendors (Tesla Optimus, Boston Dynamics
Spot / Atlas, ANYmal, ...). Opened as needed. Ref docs/12 §Per-vendor adapters.

**Acceptance Criteria**

New feature per vendor when hardware is committed. 
Must reuse existing port and contract suite unchanged.

### [Feature] ROS2-generic RobotDriver adapter (nav2 action interface) — day-0

- **ID:** [#590870](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590870)
- **State:** New
- **Assignee:** Unassigned

**Description**

First vendor-adjacent adapter, deliberately NOT a Unitree family
member. Maps RobotDriver.execute → nav2 NavigateToPose action.
Purpose: prove cross-family agnosticism of the RobotDriver port
BEFORE the four Unitree adapters land. If the port survives
simultaneous logging-fake + kinematic-fake + ROS2-generic
implementations, the agnostic claim has real evidence.

**Acceptance Criteria**

Adapter under robot_abstraction/adapters/outbound/ros2_generic/. 
Passes RobotDriver contract-test suite + safety contract-test suite. 
Bootstrap 'ros2-generic' profile wires it in. 
Runs against a ros2 humble nav2 sim in CI (nightly or on-demand).

#### [User Story] Ros2GenericDriver adapter mapping execute → nav2 NavigateToPose

- **ID:** [#590871](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590871)
- **State:** New
- **Assignee:** Unassigned

**Description**

Full RobotDriver port implementation over rclpy + nav2 action
client. Command translation, feedback → ActionHandle
feedback stream, cancel → nav2 cancel goal, telemetry via
/tf + /odom topic subscriptions with QoS.

**Acceptance Criteria**

execute() returns an ActionHandle whose feedback stream mirrors nav2 feedback. 
cancel() cancels the nav2 goal within one control period. 
Telemetry subscription honours the QoSProfile parameter.

##### [Task] Set up rclpy node lifecycle in the adapter

- **ID:** [#590872](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590872)
- **State:** New
- **Assignee:** Unassigned

**Description**

Spin executor in a background task; clean shutdown on adapter close.

##### [Task] Map execute() to nav2 NavigateToPose action client

- **ID:** [#590873](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590873)
- **State:** New
- **Assignee:** Unassigned

**Description**

Send goal, propagate feedback, resolve result.

##### [Task] Wire ActionHandle.cancel() to nav2 cancel_goal

- **ID:** [#590874](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590874)
- **State:** New
- **Assignee:** Unassigned

**Description**

Ensure cancel returns only after nav2 confirms.

##### [Task] Telemetry subscription with QoSProfile

- **ID:** [#590875](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590875)
- **State:** New
- **Assignee:** Unassigned

**Description**

Map QoSProfile to rclpy QoS objects; subscribe to /tf, /odom.

#### [User Story] Contract-test suite pass (RobotDriver + safety)

- **ID:** [#590876](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590876)
- **State:** New
- **Assignee:** Unassigned

**Description**

Run the shared RobotDriver contract suite and the safety
contract suite against the Ros2GenericDriver in CI.
Gates: both suites green before merge.

**Acceptance Criteria**

Both suites integrated into CI (nightly by default; on-demand for PRs touching the adapter).

##### [Task] Wire adapter into RobotDriver contract-test conftest

- **ID:** [#590877](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590877)
- **State:** New
- **Assignee:** Unassigned

**Description**

Fixture instantiates the adapter against a nav2 sim.

##### [Task] Wire adapter into safety contract-test conftest

- **ID:** [#590878](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590878)
- **State:** New
- **Assignee:** Unassigned

**Description**

Same, for the safety suite.

#### [User Story] Bootstrap profile 'ros2-generic'

- **ID:** [#590879](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590879)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add a bootstrap profile that selects the ROS2-generic
adapter, wires it into a running fleet with a single robot,
and exposes the standard operator interface on top.

**Acceptance Criteria**

Profile documented in bootstrap README. 
`poe run-profile ros2-generic` (or equivalent) launches end-to-end.

##### [Task] Extend Settings model with profile selection

- **ID:** [#590880](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590880)
- **State:** New
- **Assignee:** Unassigned

**Description**

Add profile enum + adapter wiring branches.

##### [Task] Documentation for the profile

- **ID:** [#590881](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590881)
- **State:** New
- **Assignee:** Unassigned

**Description**

README section listing what the profile ships and its dependencies.

## [Epic] Physics Simulator Integration (deferred; decision required)

- **ID:** [#589171](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589171)
- **State:** New
- **Assignee:** Unassigned

**Description**

Reserved epic pending an ADR to select the physics engine (Gazebo vs Isaac Sim vs Omniverse) per docs/03 §Simulation and the AGENTS.md 'Preferred libraries when the need arises' policy. Physics integration is not required for the Epic 4 contract-test harness (which runs against logging-fake and vendor sims). Kept dormant until a capability surfaces a hard dependency; at that point it becomes an outbound adapter of robot_abstraction or perception, never shared infrastructure.

### [Feature] Choose physics engine (Gazebo vs Isaac Sim vs Omniverse)

- **ID:** [#589172](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589172)
- **State:** New
- **Assignee:** Unassigned

**Description**

Decision on the deeper physics stack once a trigger fires.
Compare against needs: kinematics validation vs photoreal
RL/synthetic data. Ref docs/12 §Contract tests and AGENTS.md 'Simulation'.

**Acceptance Criteria**

ADR merged. 
Integration plan drafted.

## [Epic] Perception (reserved capability)

- **ID:** [#589173](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589173)
- **State:** New
- **Assignee:** Unassigned

**Description**

Reserved. Placeholder for sensor-fusion capability. Not scheduled. Ref docs/04 §Perception.

### [Feature] Establish port surface for sensor fusion

- **ID:** [#589174](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589174)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the port shape perception will expose, without
adapters. Prevents future ad-hoc coupling. Ref docs/03 §Architecture Implementation and AGENTS.md.

**Acceptance Criteria**

Port Protocols and DTO stubs under `src/perception/ports/`. 
Import-linter rules updated. 
No adapters scheduled.

## [Epic] World Model (active foundation)

- **ID:** [#589175](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589175)
- **State:** New
- **Assignee:** Unassigned

**Description**

Promoted from "reserved" to "active foundation" because
Frame / FramedPose / TransformLookup are prerequisites of
Epic 3 (robot_abstraction): the RobotDriver port's Pose-bearing
methods are ambiguous without a Frame tag, and multi-robot
transform lookups belong to the world model per docs/05 §5.2. 
Minimal initial scope: Frame tagged type, FramedPose value type,
TransformLookup port + IdentityAdapter + StaticTreeAdapter.
Explicitly OUT of scope for now: time-varying transforms, tf2
buffer, interpolation — deferred as a separate Feature once a
capability actually needs them.

### [Feature] Establish port surface for environmental model

- **ID:** [#589176](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/589176)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define read/write port shape and spatial-primitive placement
decision (ADR). No adapters. Ref docs/03 §Architecture Implementation and AGENTS.md.

**Acceptance Criteria**

ADR merged. 
Protocol stubs exist. 
Consumers can be typed against them.

### [Feature] Spatial primitives & TransformLookup port (minimal)

- **ID:** [#590813](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590813)
- **State:** New
- **Assignee:** Unassigned

**Description**

Pre-Epic-3 blocker: without a Frame tag on Pose, every RobotDriver
method that takes or returns a pose is ambiguous (map / odom /
base_link / world / robot/{id}/sensor). Minimal spatial layer
per docs/05 §5.2 — types live in world_model, not shared_kernel.
Explicitly excludes tf2 buffer / time-varying transforms /
interpolation; those are a follow-up feature once a real
consumer needs them.

**Acceptance Criteria**

Frame + FramedPose live under world_model/domain/. 
TransformLookup port lives under world_model/ports/outbound/. 
Identity + StaticTree adapters live under world_model/adapters/outbound/. 
Contract-test suite passes for both adapters. 
ADR documents the deferred scope boundary.

#### [User Story] Frame tagged type + FramedPose value type

- **ID:** [#590814](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590814)
- **State:** New
- **Assignee:** Unassigned

**Description**

Introduce Frame as a tagged string type identifying a
coordinate frame (e.g. "map", "odom", "base_link",
"robot/r1/base_link", "world"). Introduce FramedPose as a
value type pairing Pose with Frame; equality by
(pose, frame). Rejects unframed poses across module
boundaries.

**Acceptance Criteria**

Frame is a NewType or frozen value type over str; validates format. 
FramedPose is frozen and hashable. 
Any function receiving a Pose without a Frame at a port boundary is a type error.

##### [Task] Author Frame + FramedPose in world_model/domain/

- **ID:** [#590815](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590815)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the two value types with construction validation and re-export from domain/__init__.py.

##### [Task] Unit tests for Frame + FramedPose

- **ID:** [#590816](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590816)
- **State:** New
- **Assignee:** Unassigned

**Description**

Construction, equality, hashing, rejection of empty / whitespace / malformed frame ids.

#### [User Story] TransformLookup port + IdentityAdapter

- **ID:** [#590817](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590817)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the TransformLookup outbound port with a single
method transform(pose: FramedPose, target: Frame) ->
Result[FramedPose, TransformError]. Ship an IdentityAdapter
that returns the input unchanged when source == target and
raises otherwise — trivial baseline for the day-0 slice.

**Acceptance Criteria**

Port defined in world_model/ports/outbound/transform_lookup/port.py. 
IdentityAdapter under world_model/adapters/outbound/identity_transform/. 
Return type is Result[FramedPose, TransformError] using shared_kernel Result.

##### [Task] Author TransformLookup port protocol

- **ID:** [#590818](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590818)
- **State:** New
- **Assignee:** Unassigned

**Description**

Define the port Protocol + TransformError variants.

##### [Task] IdentityAdapter implementation + unit tests

- **ID:** [#590819](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590819)
- **State:** New
- **Assignee:** Unassigned

**Description**

Adapter returns input on identity, TransformError on mismatch.

#### [User Story] StaticTreeAdapter for tree of static rigid transforms

- **ID:** [#590820](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590820)
- **State:** New
- **Assignee:** Unassigned

**Description**

Adapter that resolves transforms across a statically
configured tree of rigid frames (e.g. base_link → lidar,
base_link → camera, map → odom on init). Configuration
loaded from a YAML at bootstrap. No time dimension.

**Acceptance Criteria**

Adapter composes chains of static transforms. 
Detects cycles and disconnected components at load time. 
Configuration schema documented.

##### [Task] Static tree data structure + cycle detection

- **ID:** [#590821](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590821)
- **State:** New
- **Assignee:** Unassigned

**Description**

Load YAML into an adjacency map, reject cycles / disconnected roots.

##### [Task] Transform composition arithmetic

- **ID:** [#590822](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590822)
- **State:** New
- **Assignee:** Unassigned

**Description**

Compose rigid 4x4 (or SE(3)) transforms across a resolved path.

##### [Task] Bootstrap wiring under a 'static-tree' profile

- **ID:** [#590823](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590823)
- **State:** New
- **Assignee:** Unassigned

**Description**

Read YAML path from Settings and instantiate the adapter.

#### [User Story] Contract-test suite for TransformLookup adapters

- **ID:** [#590824](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590824)
- **State:** New
- **Assignee:** Unassigned

**Description**

Shared pytest suite that both Identity and StaticTree
adapters (and any future adapter) must pass. Covers
identity, chain composition, cycle rejection, missing-frame
error mapping.

**Acceptance Criteria**

Suite lives under tests/contract/world_model/transform_lookup/. 
Both day-0 adapters pass the suite in CI.

##### [Task] Author the shared contract-test module

- **ID:** [#590825](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590825)
- **State:** New
- **Assignee:** Unassigned

**Description**

Parametrised pytest fixture that any adapter can be plugged into.

##### [Task] Wire Identity + StaticTree into the suite

- **ID:** [#590826](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590826)
- **State:** New
- **Assignee:** Unassigned

**Description**

Two conftest fixtures instantiating each adapter.

#### [User Story] ADR — time-varying transforms deferred; scope boundary

- **ID:** [#590827](https://dev.azure.com/EYGS2/graiteam/_workitems/edit/590827)
- **State:** New
- **Assignee:** Unassigned

**Description**

Written ADR documenting why the day-0 TransformLookup is
static-only, what triggers reopening the decision (first
moving-frame consumer, first sim scenario with dynamic
extrinsics), and what an eventual tf2-style buffer would
look like as a third adapter.

**Acceptance Criteria**

docs/adr/00XX-transform-lookup-scope.md exists. 
Linked from world_model README.

