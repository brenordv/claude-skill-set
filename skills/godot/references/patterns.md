# Godot Reference Patterns

Full implementations referenced from `SKILL.md`. These are load-on-demand; the SKILL body links here rather than inlining the listings.

## Player Character Controller (CharacterBody3D)

Canonical player controller; also demonstrates the GDScript style (type hints, `@export`, `@onready`, signals, doc-comments). The 2D variant is the same pattern with `Input.get_axis` and `Vector2` velocity.

```gdscript
class_name Player
extends CharacterBody3D

## The player's movement speed in meters per second.
@export var move_speed: float = 5.0
## Jump velocity applied when the player presses jump.
@export var jump_velocity: float = 4.5

# Private state
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _is_attacking: bool = false

# Signals
signal health_changed(new_health: int)
signal died

# Onready references (cached at _ready)
@onready var _anim: AnimationPlayer = $AnimationPlayer
@onready var _sprite: Sprite3D = $Sprite3D


func _physics_process(delta: float) -> void:
    # Apply gravity
    if not is_on_floor():
        velocity.y -= _gravity * delta

    # Jump
    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    # Movement
    var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    var direction := (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()

    if direction:
        velocity.x = direction.x * move_speed
        velocity.z = direction.z * move_speed
    else:
        velocity.x = move_toward(velocity.x, 0, move_speed)
        velocity.z = move_toward(velocity.z, 0, move_speed)

    move_and_slide()
```

### 2D variant (CharacterBody2D)

Same pattern in 2D: `Input.get_axis` for horizontal input, `Vector2` velocity, gravity added on the Y axis.

```gdscript
class_name Player2D
extends CharacterBody2D

@export var speed: float = 200.0
@export var jump_velocity: float = -350.0

var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y += gravity * delta

    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    var direction := Input.get_axis("move_left", "move_right")
    velocity.x = direction * speed if direction else move_toward(velocity.x, 0, speed)

    move_and_slide()

    # Flip sprite
    if direction != 0:
        $Sprite2D.flip_h = direction < 0
```

## State Machine

Generic, reusable node-based state machine: a `StateMachine` owner, a `State` base class, and one concrete example state (`PlayerIdleState`).

```gdscript
# state_machine.gd: Generic, reusable
class_name StateMachine
extends Node

@export var initial_state: State
var current_state: State

func _ready() -> void:
    for child in get_children():
        if child is State:
            child.state_machine = self
    if initial_state:
        initial_state.enter()
        current_state = initial_state

func _process(delta: float) -> void:
    if current_state:
        current_state.update(delta)

func _physics_process(delta: float) -> void:
    if current_state:
        current_state.physics_update(delta)

func _unhandled_input(event: InputEvent) -> void:
    if current_state:
        current_state.handle_input(event)

func transition_to(target_state_name: StringName) -> void:
    var target: State = get_node_or_null(NodePath(target_state_name))
    if target == null or target == current_state:
        return
    current_state.exit()
    current_state = target
    current_state.enter()
```

```gdscript
# state.gd: Base class for all states
class_name State
extends Node

var state_machine: StateMachine

func enter() -> void:
    pass

func exit() -> void:
    pass

func update(_delta: float) -> void:
    pass

func physics_update(_delta: float) -> void:
    pass

func handle_input(_event: InputEvent) -> void:
    pass
```

```gdscript
# player_idle_state.gd
class_name PlayerIdleState
extends State

func enter() -> void:
    owner.get_node("AnimationPlayer").play("idle")

func handle_input(event: InputEvent) -> void:
    if event.is_action_pressed("jump") and owner.is_on_floor():
        state_machine.transition_to("Jump")

func physics_update(_delta: float) -> void:
    var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
    if input_dir.length() > 0.1:
        state_machine.transition_to("Run")
```
