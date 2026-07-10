# Game Development Coding Best Practices

These guidelines apply to all game development coding skills regardless of engine. They cover the intersection of code quality and game-specific concerns.

---

## 1. Design Before Code

- **Design the experience first**, then the systems, then the code.
- Identify the core loop before building anything: `[Action] → [Challenge] → [Reward] → [Progression] → repeat`.
- Every system must answer: "How does this make the game more enjoyable?"
- Prototype the fun before polishing the graphics.

---

## 2. Architecture Principles

### Composition Over Inheritance

- Favor attaching behaviors (components/scripts/nodes) over deep class hierarchies.
- Keep components small and focused on a single concern.
- Game entities should be assemblies of behaviors, not monolithic classes.

### Loose Coupling via Events

- Systems communicate through events/signals/message buses, not direct references.
- Children emit signals; parents call children's methods (up via events, down via calls).
- Global event buses for cross-system communication (e.g., `score_changed`, `player_died`).

### Data-Driven Design

- Stats, levels, loot tables, dialogue, and tuning values live in data files (JSON, CSV, ScriptableObjects, Resources), not hard-coded in logic.
- Separate data from behavior; designers iterate without recompiling.
- Use resource/asset patterns provided by the engine for configuration.

### Single Responsibility Per System

- Combat calculates damage; Health tracks HP; UI displays it.
- Each system owns one concern and delegates the rest.
- Avoid "god objects" that manage everything.

---

## 3. State Machines

- Use state machines for player states, AI behavior, UI flow, and game phases.
- States should be small, self-contained, and transitionable.
- Hierarchical state machines for complex behaviors (e.g., Combat > Melee > Combo).
- Each state handles: enter, update, exit, and input.

---

## 4. Performance as a Feature

### Platform Awareness

- Plan for the target platform's constraints from day one.
- Respect frame budgets: 16.6ms at 60 FPS, 8.3ms at 120 FPS.
- Performance is a feature, not an afterthought.

### Common Pitfalls to Avoid

- Allocating memory every frame (causes GC spikes/stutters).
- Expensive operations in per-frame callbacks (find by name, string operations).
- Not caching references looked up repeatedly.
- Physics running at higher frequency than needed.
- No object pooling for frequently spawned/destroyed objects.
- AI running every frame instead of on intervals.

### Optimization Discipline

- **Profile before optimizing**: Use the engine's built-in profiler.
- **Disable processing when idle**: Turn off tick/update for inactive entities.
- **Use object pooling**: Avoid instantiate/destroy cycles in gameplay.
- **Cache frequently accessed references** at initialization time.
- **Use LOD (Level of Detail)**: Reduce quality for distant objects.
- **Batch similar operations**: Draw calls, physics queries, AI updates.

---

## 5. Testability

- Core game logic (damage formulas, economy math, AI decisions) should be testable without rendering a frame.
- Separate pure logic from engine/rendering concerns.
- Use the engine's testing framework (GUT/GdUnit4 for Godot, Play Mode/Edit Mode for Unity, automation tests for Unreal).

---

## 6. Determinism

- For replays, networking, or debugging, prefer deterministic logic.
- Seed your RNG; never rely on system time for game logic randomness.
- Avoid frame-rate-dependent calculations; use delta time consistently.

---

## 7. Multiplayer Considerations

- **Server is authority**: Never trust the client in competitive games.
- **Validate inputs server-side**: Clients only suggest; the server decides.
- **Design for latency**: Client prediction + server reconciliation.
- **Minimize network traffic**: Replicate only what's necessary; use delta compression.

---

## 8. Scope Discipline

- A finished small game beats an abandoned large one.
- Kill prototypes that don't work; sunk cost is the enemy.
- Playtest early, playtest often; assumptions are wrong until validated.
- Time-box prototypes (1-3 days). If it's not fun by then, pivot.

---

## 9. Engine-Agnostic Best Practices

| Area | Do | Don't |
|------|----|----|
| Architecture | Small, composable components | Monolithic god scripts |
| Communication | Events/signals for decoupling | Direct cross-scene references |
| Data | External config files, resources | Hard-coded values in logic |
| Performance | Pool objects, cache refs, profile | Instantiate/destroy every frame |
| State | State machines for complex behavior | Nested if/else chains for state |
| Testing | Test logic independently of rendering | Skip testing game systems |
| Version Control | Text-based formats where possible | Binary formats that can't merge |
