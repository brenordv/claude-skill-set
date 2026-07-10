---
name: game-developer
description: >-
  Game design and development architect. Plans game mechanics, systems,
  progression loops, player experience, and technical architecture.
  Use PROACTIVELY before writing any game code to design, plan, and
  validate game concepts, features, and system interactions.
---

# Game Developer: Design & Architecture Skill

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md` and `brain/knowledge/coding-gamedev.md`. Always apply those principles alongside the design guidance below.

Plan, design, and reason about games before a single line of code is written. This skill thinks about what makes games enjoyable, how systems interact, and what technical approach will deliver the best player experience.

## When to Use This Skill

- Designing a new game or game feature from scratch
- Planning game mechanics, loops, and progression systems
- Evaluating whether a game idea is feasible and fun
- Architecting game systems (inventory, combat, AI, physics, UI)
- Balancing difficulty curves, economy, and player incentives
- Writing a Game Design Document (GDD) or technical design doc
- Choosing the right engine, toolchain, or architecture for a project
- Reviewing an existing game design for quality, coherence, or missing pieces
- Planning multiplayer, networking, or live-service architecture
- Prototyping decisions: deciding what to prototype first and why

## Do Not Use This Skill When

- Writing engine-specific implementation code; use `unity`, `godot`, or `unreal-engine` instead
- Debugging a runtime crash or compiler error in a specific engine
- Performing non-game software engineering (web apps, APIs, CLI tools)

## Instructions

1. Understand the vision: ask what kind of experience the player should have.
2. Identify the core loop: the repeating cycle of actions the player performs.
3. Design systems that serve the core loop, not the other way around.
4. Validate feasibility against scope, team size, and target platform.
5. Produce concrete deliverables (GDD sections, system diagrams, data schemas).
6. When the user is ready to implement, recommend the appropriate engine skill.

---

## 1. The Core Loop

Every great game has a tight core loop. Identify it first; everything else is built around it.

**Core loop template:** identify the action → challenge → reward → progression cycle (defined in `coding-gamedev.md` §1).

**Examples by genre:**

| Genre       | Action          | Challenge         | Reward             | Progression          |
| ----------- | --------------- | ----------------- | ------------------ | -------------------- |
| Platformer  | Run & jump      | Obstacles/enemies | Coins, checkpoints | New levels, abilities |
| RPG         | Explore & fight | Enemy encounters  | XP, loot           | Level up, new areas  |
| Puzzle      | Manipulate      | Logic constraint  | Solution, score     | Harder puzzles       |
| Survival    | Gather & craft  | Environment/hunger | Better gear         | Base building        |
| Roguelike   | Clear rooms     | Permadeath runs   | Meta-currency       | Unlocks for next run |

### Evaluating a Core Loop

Ask these questions:

- **Is the action inherently satisfying?** (Does the button press feel good?)
- **Does the challenge scale?** (Can difficulty grow without becoming unfair?)
- **Are rewards meaningful?** (Do they change how the player plays, not just a number?)
- **Does progression create anticipation?** (Does the player look forward to what's next?)

If any answer is "no", redesign that part before building anything.

---

## 2. Game Systems Design

### System Interaction Map

Before coding, map how systems talk to each other:

```
[Input System] → [Player Controller]
                      ↓
              [Combat System] ←→ [AI System]
                      ↓
              [Health / Damage]
                      ↓
              [Inventory / Loot] ←→ [Economy]
                      ↓
              [Progression / XP] → [UI / HUD]
                      ↓
              [Save / Load]
```

---

## 3. Player Experience & Feel

### Game Feel Checklist

- **Input responsiveness**: < 100ms from button press to visible reaction
- **Visual feedback**: Every action has a visual confirmation (particles, screen shake, animation)
- **Audio feedback**: Hits land with impact sounds; UI clicks confirm interaction
- **Camera behavior**: Smooth follow, screen shake on impact, no disorienting motion
- **Juice**: Squash-and-stretch, easing curves, trails, hit-pause (freeze frames)

### Difficulty & Flow

Target the **flow channel**: the sweet spot between anxiety and boredom.

```
Anxiety (too hard)
    \
     [FLOW ZONE] ← keep the player here
    /
Boredom (too easy)
```

**Techniques:**
- Dynamic difficulty adjustment (DDA): adapt behind the scenes
- Player-chosen difficulty with meaningful trade-offs
- Skill-based progression: teach, then test
- Rubber-banding in competitive games: keep races close

---

## 4. Economy & Balance

### Economy Types

| Type       | Description                              | Example                        |
| ---------- | ---------------------------------------- | ------------------------------ |
| **Closed** | Fixed resources, no generation or sinks  | Chess, Settlers of Catan       |
| **Open**   | Resources generated and destroyed        | Most RPGs, MMOs                |
| **Hybrid** | Some fixed, some generated               | Roguelikes with meta-currency  |

### Balancing Framework

1. Define **sources** (where currency/items come from)
2. Define **sinks** (where they go: shops, upgrades, consumables)
3. Model the **flow rate**: how fast does a player earn vs. spend?
4. Simulate or spreadsheet the first 10 hours of play
5. Playtest and adjust; math alone never catches feel problems

### Loot & Reward Distribution

- **Fixed drops**: Predictable, good for story items
- **Weighted random**: Common/rare/epic/legendary tiers
- **Pity system**: Guarantee a rare drop after N attempts
- **Contextual drops**: Drop what the player needs (subtly)

---

## 5. Technical Architecture Patterns

### Entity-Component-System (ECS)

Best for data-heavy games with many similar entities (bullets, enemies, particles).

```
Entity: just an ID (uint)
Component: pure data (Position, Velocity, Health)
System: logic that operates on components (MovementSystem, DamageSystem)
```

**When to use ECS:** High entity counts, performance-critical, data-oriented design.
**When NOT to use ECS:** Small games, heavily OOP engines, narrative-driven games with few entities.

### Component-Based Architecture

Most engines default to this. GameObjects/Nodes have attached components/scripts.

**Best practices:**
- Favor composition over inheritance
- Keep components small and focused
- Communicate via events, not GetComponent chains
- Avoid deep inheritance hierarchies for game entities

### State Machines

State machines for player states, AI, and UI flow (see `coding-gamedev.md` §3). A concrete transition example:

```
[Idle] --input--> [Running] --jump--> [Airborne] --land--> [Idle]
                                          |
                                       --hit--> [Stunned] --timer--> [Idle]
```

---

## 6. Multiplayer & Networking Considerations

### Architecture Models

| Model              | Latency | Security | Complexity | Best For                 |
| ------------------ | ------- | -------- | ---------- | ------------------------ |
| **Peer-to-peer**   | Low     | Low      | Medium     | Fighting games, co-op    |
| **Client-server**  | Medium  | High     | High       | Shooters, MMOs           |
| **Rollback**       | Lowest  | Medium   | Very High  | Fighting games, platformers |
| **Lockstep**       | Variable| Medium   | Medium     | RTS, turn-based          |

### Key Decisions

The authority and latency rules live in `coding-gamedev.md` §7. Game-planning specifics:

- **Tick rate**: 20-64 Hz typical; higher = more bandwidth, smoother feel.
- **State synchronization**: Full-state snapshots vs. delta compression vs. event-based.
- **Lag compensation**: Interpolation for visual smoothness, extrapolation for prediction.

---

## 7. Game Design Document (GDD) Template

When asked to produce a GDD, use this structure:

```markdown
# [Game Title]: Game Design Document

## 1. Vision Statement
One paragraph: what is this game and why will players love it?

## 2. Core Loop
Diagram and description of the primary gameplay cycle.

## 3. Mechanics
Detailed breakdown of every interactive system.

## 4. Progression
How the player advances: XP, unlocks, story gates, skill trees.

## 5. Content Plan
Levels, enemies, items, abilities: scope and quantity.

## 6. Art & Audio Direction
Visual style, color palette, sound design pillars.

## 7. Technical Requirements
Target platforms, performance targets, engine choice, networking model.

## 8. Scope & Milestones
Prototype → Vertical Slice → Alpha → Beta → Release timeline.

## 9. Risks & Mitigations
What could go wrong and how to handle it.
```

---

## 8. Prototyping Strategy

### What to Prototype First

1. **The core mechanic**: If this isn't fun in a grey-box, the game won't be fun with art.
2. **The riskiest technical feature**: Networking, procedural generation, physics interactions.
3. **The most uncertain design question**: "Is this fun?" can only be answered by playing it.

### Prototyping Rules

Follow the scope discipline in `coding-gamedev.md` §8 (time-box prototypes, kill what doesn't work). Additionally:

- Use placeholder art (colored shapes, free assets). Art is NOT what you're testing.
- Record playtests. Watch players, don't explain. If they're confused, the design is wrong.

---

## 9. Platform & Performance Targets

### Performance Budgets

| Platform     | Target FPS | Frame Budget | RAM Budget |
| ------------ | ---------- | ------------ | ---------- |
| Mobile       | 30-60      | 16-33 ms     | 1-2 GB     |
| Console      | 60 (120)   | 8-16 ms      | 4-12 GB    |
| PC (mid)     | 60-144     | 7-16 ms      | 8-16 GB    |
| VR           | 72-120     | 8-14 ms      | 4-8 GB     |

### Common Performance Pitfalls

Beyond the engine-agnostic pitfalls in `coding-gamedev.md` §4, watch for:

- Too many draw calls (batch your geometry)
- Expensive physics with too many colliders
- Uncompressed textures on mobile
- No LOD (Level of Detail) system for 3D games

---

## 10. Handoff to Engine Skills

Once design is validated, hand off to the appropriate engine skill:

| Decision Factor    | Unity (`unity`)        | Godot (`godot`)           | Unreal (`unreal-engine`) |
| ------------------ | ---------------------- | ------------------------- | ------------------------ |
| **Language**       | C#                     | GDScript, C#, C++         | C++, Blueprints          |
| **2D games**       | Good                   | Excellent                 | Capable but heavy        |
| **3D AAA**         | Good                   | Improving                 | Industry standard        |
| **Mobile**         | Strong                 | Good                      | Heavy but capable        |
| **Open source**    | No                     | Yes (MIT)                 | Source available          |
| **Team size**      | Indie to mid           | Solo to mid               | Mid to AAA               |
| **Learning curve** | Moderate               | Gentle                    | Steep                    |

Recommend the engine that fits the project's scope, team, and goals, not personal preference.

---

## Limitations

- This skill does not write engine-specific code. Use `unity`, `godot`, or `unreal-engine` for implementation.
- Game design advice is general; genre-specific nuances may require domain expertise (e.g., competitive FPS netcode, MMO world design).
- Economy balancing and difficulty tuning ultimately require playtesting; no amount of theory replaces real player data.
