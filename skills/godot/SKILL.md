---
name: godot
description: >-
  Godot 4.x game development expert. GDScript and C# scripting, scene/node
  architecture, 2D/3D rendering, physics, shaders, UI, multiplayer,
  GDExtension, and export. Use PROACTIVELY for any Godot development,
  debugging, or optimization.
---

# Godot 4.x Game Development Expert

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, `brain/knowledge/coding-gamedev.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the engine-specific guidance below.
> **Language-Specific Testing**: See `testing-guidelines.md` in this skill folder for framework-specific testing patterns.

Build polished, performant games in Godot 4.x using its node/scene architecture, GDScript, and the engine's built-in tooling.

## When to Use This Skill

- Writing or reviewing GDScript or C# scripts for Godot
- Architecting game systems using Godot's scene tree and node composition
- Working with Godot's 2D engine (TileMaps, CharacterBody2D, AnimationPlayer)
- Building 3D games with Godot's Vulkan-based renderer
- Writing custom shaders in Godot's shading language
- Setting up multiplayer with Godot's high-level networking API
- Creating editor plugins, tool scripts, or GDExtensions
- Optimizing Godot performance (rendering, physics, GDScript)
- Exporting to desktop, mobile, web, or console
- Migrating from Godot 3.x to 4.x

## Do Not Use This Skill When

- Designing game mechanics before implementation; use `game-developer` first
- Working in Unity or Unreal; use `unity` or `unreal-engine`
- Writing general Python; GDScript looks similar but is a different language

## Instructions

1. Identify the Godot version (this skill targets 4.6.1 and the 4.x branch).
2. Use Godot's scene/node composition: prefer small, reusable scenes over monolithic scripts.
3. Leverage GDScript for gameplay; use C# or GDExtension (C/C++/Rust) for performance-critical systems.
4. Profile with Godot's built-in monitors, debugger, and profiler before optimizing.
5. Follow the Godot documentation conventions and GDScript style guide.

---

## 1. Scene & Node Architecture

### Godot's Core Principle: Everything Is a Node

Nodes form a tree. Scenes are reusable sub-trees. This replaces the component pattern used in other engines.

```
Main (Node)
├── World (Node3D)
│   ├── Player (CharacterBody3D)       ← player.tscn
│   │   ├── CollisionShape3D
│   │   ├── MeshInstance3D
│   │   ├── AnimationPlayer
│   │   └── Camera3D
│   ├── Enemies (Node3D)
│   │   └── Enemy (CharacterBody3D)    ← enemy.tscn (instanced)
│   └── Level (Node3D)                 ← level_01.tscn
├── UI (CanvasLayer)
│   └── HUD (Control)                  ← hud.tscn
└── GameManager (Node)                 ← autoload singleton
```

### Scene Composition Rules

1. **One script per scene root**: The root node owns the scene's behavior.
2. **Scenes are self-contained**: A scene should work when instanced anywhere.
3. **Communicate up via signals, down via calls**: see `coding-gamedev.md` §2.
4. **Use groups for broadcast**: `get_tree().call_group("enemies", "on_alert")`.
5. **Keep scenes small**: If a scene has more than ~5-7 direct children or 100+ lines of script, split it.

---

## 2. GDScript Best Practices

### Code Style (Godot Style Guide)

Full player controller demonstrating the style (type hints, `@export`, `@onready`, signals, doc-comments): see `references/patterns.md` → "Player Character Controller".

### GDScript Style Rules

- **snake_case** for variables, functions, signals.
- **PascalCase** for class names and node types.
- **UPPER_SNAKE_CASE** for constants and enums.
- Prefix private members with `_` (convention, not enforced).
- Use **type hints everywhere**: `var speed: float = 5.0`, `func take_damage(amount: int) -> void:`.
- Use `@export` for inspector-editable values, `@onready` for cached node references.
- Use `##` doc-comments above exported vars and public functions.

### Typed Arrays and Dictionaries (4.x)

```gdscript
# Typed arrays: catch errors at parse time
var enemies: Array[Enemy] = []
var scores: Array[int] = [10, 20, 30]

# Typed dictionaries (Godot 4.4+)
var inventory: Dictionary[String, int] = {"wood": 10, "stone": 5}

# Static typing for function signatures
func find_nearest_enemy(position: Vector3) -> Enemy:
    var nearest: Enemy = null
    var min_dist: float = INF
    for enemy in enemies:
        var dist := position.distance_to(enemy.global_position)
        if dist < min_dist:
            min_dist = dist
            nearest = enemy
    return nearest
```

---

## 3. Signals & Communication

### Defining and Connecting Signals

```gdscript
# In Health component
class_name HealthComponent
extends Node

signal health_changed(current: int, max_health: int)
signal died

@export var max_health: int = 100
var _current: int

func _ready() -> void:
    _current = max_health

func take_damage(amount: int) -> void:
    _current = maxi(_current - amount, 0)
    health_changed.emit(_current, max_health)
    if _current <= 0:
        died.emit()

func heal(amount: int) -> void:
    _current = mini(_current + amount, max_health)
    health_changed.emit(_current, max_health)
```

```gdscript
# In Enemy scene root: connect in code
func _ready() -> void:
    $HealthComponent.health_changed.connect(_on_health_changed)
    $HealthComponent.died.connect(_on_died)

func _on_health_changed(current: int, max_health: int) -> void:
    $HealthBar.value = float(current) / float(max_health) * 100.0

func _on_died() -> void:
    # Play death animation, drop loot, queue_free
    $AnimationPlayer.play("death")
    await $AnimationPlayer.animation_finished
    queue_free()
```

### Autoload Singletons for Global Events

```gdscript
# events.gd: Add as Autoload in Project Settings
extends Node

signal game_paused
signal game_resumed
signal score_changed(new_score: int)
signal player_died
signal level_completed(level_id: int)
```

```gdscript
# Any script can emit or connect
Events.score_changed.emit(new_score)
Events.player_died.connect(_on_player_died)
```

---

## 4. Resources & Data-Driven Design

Resources are Godot's equivalent of ScriptableObjects.

```gdscript
# weapon_data.gd
class_name WeaponData
extends Resource

@export var name: String = "Sword"
@export var damage: int = 10
@export var attack_speed: float = 1.0
@export var range: float = 2.0
@export var icon: Texture2D
@export var attack_animation: StringName = &"slash"
```

```gdscript
# Usage in weapon system
class_name Weapon
extends Node3D

@export var data: WeaponData

func attack(target: Node3D) -> void:
    if target.has_method("take_damage"):
        target.take_damage(data.damage)
    $AnimationPlayer.play(data.attack_animation)
```

Create weapon variants in the inspector by creating new `.tres` files from the WeaponData resource.

### Resource Preloading

```gdscript
# Preload for small, always-needed resources
const EXPLOSION_SCENE: PackedScene = preload("res://scenes/effects/explosion.tscn")

# Load for large or conditional resources
func _load_level(level_id: int) -> void:
    var path := "res://scenes/levels/level_%d.tscn" % level_id
    var scene: PackedScene = load(path)
    get_tree().change_scene_to_packed(scene)

# ResourceLoader for async loading (loading screens)
func _load_level_async(level_id: int) -> void:
    var path := "res://scenes/levels/level_%d.tscn" % level_id
    ResourceLoader.load_threaded_request(path)
    # Poll in _process or use a timer
    while ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
        await get_tree().process_frame
    var scene: PackedScene = ResourceLoader.load_threaded_get(path)
    get_tree().change_scene_to_packed(scene)
```

---

## 5. State Machines

Use a generic node-based state machine: a `StateMachine` owner, a `State` base class, and concrete state nodes (enter/exit/update/physics_update/handle_input). Full implementation (`StateMachine` + `State` + `PlayerIdleState`): see `references/patterns.md` → "State Machine".

---

## 6. 2D Game Development

### TileMapLayer (4.3+)

Godot 4.3 replaced `TileMap` with `TileMapLayer`: each layer is its own node.

```
Level (Node2D)
├── Ground (TileMapLayer)       ← terrain, grass
├── Walls (TileMapLayer)        ← collision geometry
├── Decoration (TileMapLayer)   ← flowers, rocks (no collision)
└── Player (CharacterBody2D)
```

### 2D Physics Character

Same pattern as the 3D controller: `Input.get_axis` for horizontal input and `Vector2` velocity with gravity on the Y axis. See `references/patterns.md` → "2D variant (CharacterBody2D)".

### AnimationTree for Complex Animation

```gdscript
# Use AnimationTree with a StateMachine or BlendTree for complex characters
@onready var anim_tree: AnimationTree = $AnimationTree

func _process(_delta: float) -> void:
    var state_machine: AnimationNodeStateMachinePlayback = anim_tree["parameters/playback"]

    if is_on_floor():
        if velocity.length() > 10:
            state_machine.travel("run")
        else:
            state_machine.travel("idle")
    else:
        state_machine.travel("jump" if velocity.y < 0 else "fall")
```

---

## 7. 3D Rendering & Shaders

### Shader Language Basics

```glsl
shader_type spatial;

// Uniforms exposed to inspector
uniform vec4 albedo_color : source_color = vec4(1.0);
uniform sampler2D albedo_texture : filter_linear_mipmap;
uniform float metallic : hint_range(0.0, 1.0) = 0.0;
uniform float roughness : hint_range(0.0, 1.0) = 0.5;

// Vertex shader
void vertex() {
    // Wave animation for vegetation
    VERTEX.x += sin(TIME * 2.0 + VERTEX.y) * 0.1;
}

// Fragment shader
void fragment() {
    vec4 tex = texture(albedo_texture, UV);
    ALBEDO = tex.rgb * albedo_color.rgb;
    METALLIC = metallic;
    ROUGHNESS = roughness;
    ALPHA = tex.a * albedo_color.a;
}
```

### Visual Shader

For artists and rapid iteration, use Godot's Visual Shader editor. Convert to code only for performance-critical shaders.

### Environment & Lighting

```gdscript
# Configure in WorldEnvironment node
# Key settings:
# - Tonemap: Use ACES or Filmic for cinematic look
# - SSAO: Enable for ambient occlusion (medium cost)
# - SSR: Screen-space reflections (high cost; use sparingly)
# - SDFGI / VoxelGI: Global illumination for static scenes
# - Glow: Bloom effect with threshold and intensity
# - Fog: Volumetric fog for atmosphere
```

---

## 8. Multiplayer Networking

### High-Level Multiplayer API

```gdscript
# Lobby / connection setup
extends Node

func host_game(port: int = 9999) -> void:
    var peer := ENetMultiplayerPeer.new()
    peer.create_server(port)
    multiplayer.multiplayer_peer = peer
    multiplayer.peer_connected.connect(_on_peer_connected)

func join_game(address: String, port: int = 9999) -> void:
    var peer := ENetMultiplayerPeer.new()
    peer.create_client(address, port)
    multiplayer.multiplayer_peer = peer

func _on_peer_connected(id: int) -> void:
    print("Player connected: ", id)
    # Spawn player for this peer
    _spawn_player(id)
```

### Synchronized Game Objects

```gdscript
class_name NetworkPlayer
extends CharacterBody3D

# MultiplayerSynchronizer node handles replication
# Configure in inspector: which properties to sync

func _physics_process(delta: float) -> void:
    # Only the authority (owner) processes input
    if not is_multiplayer_authority():
        return

    var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    velocity = Vector3(input_dir.x, 0, input_dir.y) * speed
    move_and_slide()

# RPC for actions that need server validation
@rpc("any_peer", "call_local", "reliable")
func take_damage(amount: int) -> void:
    if not multiplayer.is_server():
        return  # Only server processes damage
    health -= amount
    if health <= 0:
        die.rpc()

@rpc("authority", "call_local", "reliable")
func die() -> void:
    queue_free()
```

---

## 9. Performance Optimization

### GDScript Performance Tips

```gdscript
# 1. Use @onready instead of find_node / get_node in _process
@onready var _sprite: Sprite2D = $Sprite2D  # Cached once

# 2. Avoid string operations in hot loops
# BAD:
for enemy in enemies:
    enemy.call("take_damage", 10)  # String lookup every call

# GOOD:
for enemy in enemies:
    enemy.take_damage(10)  # Direct call, much faster

# 3. Use StringName for frequently compared strings
const ACTION_JUMP: StringName = &"jump"
if Input.is_action_just_pressed(ACTION_JUMP):
    jump()

# 4. Object pooling: avoid queue_free / instantiate in gameplay
var _bullet_pool: Array[Bullet] = []

func get_bullet() -> Bullet:
    for bullet in _bullet_pool:
        if not bullet.active:
            bullet.activate()
            return bullet
    # Pool exhausted; grow it
    var new_bullet: Bullet = BULLET_SCENE.instantiate()
    add_child(new_bullet)
    _bullet_pool.append(new_bullet)
    return new_bullet

# 5. Use _physics_process only when needed; disable when idle
set_physics_process(false)  # Disable
set_physics_process(true)   # Re-enable when needed
```

### Rendering Performance

| Technique                  | When to Use                           |
| -------------------------- | ------------------------------------- |
| Visibility notifiers       | Disable logic for off-screen nodes    |
| LOD (Level of Detail)      | Reduce mesh complexity at distance    |
| Occlusion culling          | Skip rendering of hidden objects      |
| MultiMesh / GPUParticles   | Thousands of identical objects        |
| Baked lightmaps            | Static scenes with complex lighting   |
| Shader LOD                 | Simpler shaders at distance           |
| Viewport texture           | Render complex UI to texture, sample  |

### Monitoring Performance

```gdscript
# Built-in performance monitors
print("FPS: ", Engine.get_frames_per_second())
print("Static memory: ", OS.get_static_memory_usage())
print("Objects: ", Performance.get_monitor(Performance.OBJECT_NODE_COUNT))
print("Draw calls: ", Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
```

Use **Debugger > Profiler** tab and **Debugger > Monitors** tab for frame-by-frame analysis.

---

## 10. GDExtension (C/C++/Rust)

For performance-critical code that GDScript can't handle.

```
project/
├── src/              # C++ or Rust source
│   └── my_extension.cpp
├── SConstruct        # Build configuration
├── my_extension.gdextension  # Extension manifest
└── bin/              # Compiled libraries
```

**When to use GDExtension:**
- Heavy math (pathfinding, procedural generation, physics)
- Wrapping existing C/C++ libraries (audio DSP, image processing)
- Performance-critical inner loops (thousands of entities)

**When NOT to use GDExtension:**
- Normal gameplay logic: GDScript is fast enough
- Prototyping: iteration speed matters more than runtime speed

---

## 11. Export & Deployment

### Export Presets

```
Project > Export > Add Preset:
  - Windows Desktop (x86_64)
  - Linux (x86_64)
  - macOS (universal)
  - Android (arm64-v8a)
  - iOS (arm64)
  - Web (WebAssembly)
```

### Export Best Practices

- **Exclude debug symbols** for release builds (smaller binary).
- **Enable texture compression** per platform (ETC2 for mobile, S3TC for desktop).
- **Strip unused features** via custom build templates to reduce binary size.
- **Test on target hardware**: desktop performance does not predict mobile performance.
- **Use PCK files** for DLC or modding support.

---

## Best Practices Summary

| Area              | Do                                          | Don't                                     |
| ----------------- | ------------------------------------------- | ----------------------------------------- |
| **Architecture**  | Small scenes, signals up / calls down       | One giant scene, direct node path strings |
| **Scripting**     | Type hints, @export, @onready               | Untyped vars, get_node in _process        |
| **Communication** | Signals, groups, Autoload event bus         | Direct cross-scene node references        |
| **Data**          | Custom Resources (.tres), JSON for content  | Hard-coded values in scripts              |
| **Performance**   | Object pools, StringName, visibility gates  | Instantiate/queue_free every frame        |
| **Shaders**       | Godot shader language, visual shaders       | Raw GLSL (not portable across backends)   |
| **Multiplayer**   | MultiplayerSynchronizer, @rpc annotations   | Manual packet serialization for basic sync|
| **Testing**       | GUT or GdUnit4 for unit tests               | No automated tests                        |
| **Version ctrl**  | Text-based .tscn/.tres, .gitignore .godot/  | Binary scene format                       |

## Limitations

- This skill targets Godot 4.x. Godot 3.x APIs differ significantly (no typed arrays, different physics nodes, GDScript syntax changes).
- Console export (PlayStation, Xbox, Switch) requires third-party porting solutions (W4 Games), not available in the open-source editor.
- C# support in Godot is via .NET 8 and is solid but has fewer community resources than GDScript.
- GDScript performance is good for most games but will not match C++/Rust for compute-heavy tasks; use GDExtension for those.
