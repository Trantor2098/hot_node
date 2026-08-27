# Hot Node Upgrade Plan

## Goals

1. Preserve all Hot Node 1.x user data. Data compatibility has priority over features and refactors.
2. Support Blender 4.2 LTS, 4.5 LTS, 5.0, and 5.2 LTS. Use current development builds as an early-warning target only.
3. Keep the STG serialization model while making special-node adaptations easy to inspect, implement, and test.
4. Separate shared asset state from UI selection state, then improve service lifecycle, history, and multi-window behavior incrementally.

## Compatibility Baseline

Hot Node 0.x data is no longer supported. The 0.x parser, setter, pack conversion operator, and legacy recovery UI will be removed. Imports that contain `.metadata.json` or do not contain the current `.meta` file must be rejected explicitly and removed from the destination directory.

Hot Node 1.0.0 is the oldest supported data version. Future migrations must operate on JSON in memory and must not mutate Blender node trees merely to convert a file.

## Phase 1: Remove 0.x Compatibility

- Delete `utils/legacy` and all production/development imports of it.
- Remove the legacy pack conversion operator and upgrade information UI.
- Remove support for old `_autosave_` and `_deprecated_` archive naming.
- Reject legacy pack archives explicitly instead of allowing `Pack` to create a new empty `.meta` for them.
- Keep `VersioningService` as the owner of future 1.x+ JSON migrations.
- Add a version check before `PresetMeta` applies defaults, so missing, malformed, 0.x, and future versions cannot be silently interpreted as current data.

Acceptance criteria:

- No `legacy` module or 0.x conversion symbol remains in runtime code.
- Current-format packs still import successfully.
- A legacy archive is rejected without leaving an extracted directory behind.
- Existing 1.x presets load without being rewritten.

## Phase 2: STG Adaptation Foundation

The STG architecture remains. It already provides the correct extension points: generic RNA handling, ordered type dispatch, and special STGs for exceptional nodes. The upgrade focuses on reducing registration errors and making AI-assisted adaptations reproducible.

- Replace repeated adapter wiring with a small declarative registry.
- A registration entry names the STG factory and its dispatch roles (`core`, `node`, `interface_item`, `hn`, `all`).
- Validate duplicate names, missing strategies, and fallback ordering at startup.
- Preserve named access such as `stgs.node_tree` and `stgs.node_zone_output` to avoid changing serializer code.
- Add Blender background tests for registry order and representative serialize/deserialize operations.
- Add structured diagnostics for skipped properties, failed node construction, collection factory failures, and socket fallback matching.

AI adaptation workflow:

1. Create a minimal Blender node-tree fixture for the affected node.
2. Capture the node's RNA properties, dynamic collections, sockets, and defaults.
3. Add one special STG and one registry entry, or adjust an existing STG.
4. Run save/load round-trip tests in each affected Blender version.
5. Compare semantic results: node type, properties, collection items, sockets, links, interface, and nested groups.

Acceptance criteria:

- Adding a special node strategy requires one STG class and one registry entry.
- Registry tests detect wrong list returns, wrong ordering, missing fallback, and duplicate names.
- Failed property assignments are observable in development/test mode.

## Phase 3: Blender 5.2 Compatibility

- Adapt Compositor File Output for `file_output_items`, `directory`, and `file_name` while retaining the 4.2-4.5 path.
- Set `ImageFormatSettings.media_type` before format-dependent properties where required.
- Resolve links by socket identifier first, then type/name, then index as a last resort.
- Cover changed Compare and Random Value socket identifiers in Blender 5.2.
- Test Bundle, Closure, dynamic Viewer, Menu sockets, node panel state, and compositor replacements.
- Fix handler signatures and ensure all timers and handlers are unregistered cleanly.

Do not update the published compatibility claim until the version matrix passes.

Implementation status on the upgrade branch:

- Completed capability-based File Output restore for the old and 5.0+ APIs.
- Completed ordered `ImageFormatSettings` restore.
- Completed identifier-first socket matching with type/name and index fallbacks.
- Added explicit factories for Blender 5.2 Bundle, Closure, Evaluate Closure, and Viewer collections.
- Added Closure input/output pairing to the zone strategy.
- Fixed the autosave handler signature and made synchronization, history, UI initialization, and menu timers removable.
- Added Blender 5.2 background regression coverage for these paths.
- Remaining release gate: execute the same suite and cross-version preset fixtures in Blender 4.2, 4.5, and 5.0 before changing compatibility metadata.

## Phase 4: Refresh and Service Lifecycle

The draw-time freshness check stays because Blender has no reliable event that always runs when the user returns to another project/window before the next Hot Node action.

- Keep draw as a lightweight trigger that only compares a revision or metadata timestamp.
- Register at most one debounced synchronization timer with a `sync_pending` guard.
- Perform disk loading outside draw and skip synchronization while the interface is locked.
- Run `ensure_fresh()` immediately before every mutating or data-dependent operator as the final correctness barrier.
- Replace timestamp process IDs with monotonic repository revisions and optimistic write checks.
- Centralize service creation and disposal so handlers, timers, and subscriptions have one lifecycle owner.

## Phase 5: Multi-Window UI State

Asset packs remain shared within a Blender process. Selection and temporary UI state become window-scoped.

Blender 5.2 does not allow writable custom properties or dynamically writable RNA state directly on `bpy.types.Window`. Use a runtime `WindowSessionService` keyed by `context.window.as_pointer()` instead.

- Move selected pack, selected preset, list index, and creation fields into `WindowSession`.
- Resolve the session from the operator/draw context rather than from global `Context` fields.
- Keep a temporary compatibility facade while operators and panels are migrated.
- Remove sessions whose pointer is no longer present in `window_manager.windows`.
- Broadcast repository refreshes to all sessions while preserving each valid selection independently.

Acceptance criteria:

- Two Blender windows can select and display different packs/presets.
- Editing shared pack data updates both windows without forcing their selections to match.
- Closing a window releases its session state.

## Phase 6: History and Storage Safety

- Write JSON atomically through a same-directory temporary file and `os.replace`.
- Store history as operation type, payload, and expected repository revision rather than Python callback names.
- Isolate history by process/session and reject stale operations after an external revision change.
- Quarantine malformed presets instead of deleting their references and immediately rewriting pack metadata.
- Keep migration backups and produce a per-file migration report.

## Test Matrix

Run Blender in background mode for 4.2 LTS, 4.5 LTS, 5.0, and 5.2 LTS.

Required suites:

- Add-on import, register, unregister, and repeated reload.
- Pack import/rejection and 1.x version validation.
- Shader, Geometry, and Compositor round trips.
- Frames, nested groups, interfaces, links, menu sockets, and dynamic collections.
- Simulation, Repeat, Foreach, File Output, Color Balance, Bundle, and Closure special nodes.
- Refresh after another Blender process writes the repository.
- Two-window independent selection and shared repository updates.
- Failure cleanup for temporary node trees, context stacks, timers, handlers, and extracted files.

## Delivery Order

1. Remove 0.x compatibility and establish the supported-data boundary.
2. Add the STG registry and Blender background tests.
3. Complete Blender 5.2 node adaptations.
4. Harden refresh and service lifecycle.
5. Implement per-window sessions.
6. Replace history persistence and atomic storage.
