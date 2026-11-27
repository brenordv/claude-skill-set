# Godot Testing Guidelines

Engine-specific testing patterns for Godot projects. These complement the general testing principles in `brain/knowledge/testing.md`.

## Framework

- **GUT** (Godot Unit Test) or **GdUnit4** for automated testing

## Testing Core Game Logic

Test core game logic independently of the scene tree where possible:

```gdscript
# test_inventory.gd
extends GutTest

func test_add_item_increases_count() -> void:
    var inventory: Inventory = Inventory.new()
    
    inventory.add_item("sword", 1)
    
    assert_eq(inventory.get_item_count("sword"), 1)

func test_remove_item_decreases_count() -> void:
    var inventory: Inventory = Inventory.new()
    inventory.add_item("potion", 3)
    
    inventory.remove_item("potion", 1)
    
    assert_eq(inventory.get_item_count("potion"), 2)
```

## Signal-Based Tests

Use `await` for testing signal emissions:

```gdscript
func test_health_depleted_emits_died_signal() -> void:
    var character: Character = Character.new()
    add_child(character)
    watch_signals(character)
    
    character.take_damage(character.max_health)
    
    await wait_frames(1)
    assert_signal_emitted(character, "died")
    character.queue_free()
```

## State Machine Transitions

```gdscript
func test_state_transitions_from_idle_to_running() -> void:
    var state_machine: PlayerStateMachine = PlayerStateMachine.new()
    state_machine.current_state = state_machine.idle_state
    
    state_machine.handle_input(mock_move_input())
    
    assert_eq(state_machine.current_state, state_machine.running_state)

func test_state_transitions_from_running_to_jumping() -> void:
    var state_machine: PlayerStateMachine = PlayerStateMachine.new()
    state_machine.current_state = state_machine.running_state
    
    state_machine.handle_input(mock_jump_input())
    
    assert_eq(state_machine.current_state, state_machine.jumping_state)
```

## Resource Data Loading

```gdscript
func test_weapon_resource_loads_correct_stats() -> void:
    var weapon: WeaponResource = load("res://resources/weapons/iron_sword.tres") as WeaponResource
    
    assert_not_null(weapon)
    assert_eq(weapon.damage, 10)
    assert_eq(weapon.attack_speed, 1.2)
    assert_eq(weapon.weapon_type, WeaponResource.Type.MELEE)
```

## CI Automation

- Automate test runs in CI where feasible using headless mode:
  ```bash
  godot --headless --script res://addons/gut/gut_cmdln.gd -gexit
  ```
- Run tests on every push to catch regressions early

## Test-weakening tells

`brain/knowledge/testing.md` ⛔ Hard Rules 2 and 3 govern any change to an existing test, and
`brain/knowledge/review-heuristics.md` §Testing ("Test integrity") lists the moves. In Godot they
look like this, on a line the diff adds or changes:

- GUT: `pending()` in a test that used to assert. A pending test doesn't change the exit code,
  so a run with nothing else failing still returns 0.
- GUT: `pass_test()` standing in for an assertion.
- GUT: `should_skip_script()` returning true or a string; GUT stops running the script and marks
  it risky.
- GUT command: `-gselect`, `-ginner_class`, `-gunit_test_name`, or a shorter `-gtest` / `-gdir`
  list than the baseline's.
- GdUnit4: a `_do_skip` argument on a test function, or on `before()` to skip the whole suite.
- GdUnit4 command: `-i` / `--ignore`, or fewer `-a` / `--add` entries than the baseline's.

Each is a ledger entry with a disposition and a ground, or it doesn't happen. Reference: GUT's
[GutTest class](https://gut.readthedocs.io/en/latest/class_ref/class_guttest.html) and
[command line](https://gut.readthedocs.io/en/latest/Command-Line.html); GdUnit4's
[skipping tests](https://godot-gdunit-labs.github.io/gdUnit4/latest/advanced_testing/skip-tests/)
and [command line tool](https://godot-gdunit-labs.github.io/gdUnit4/latest/advanced_testing/cmd/).

## Key Principles

- Separate pure logic from scene-tree-dependent behavior for easier testing
- Use `add_child()` and `queue_free()` for nodes that require the scene tree
- Test state machines exhaustively -- cover all valid transitions and edge cases
- Verify signal emissions for event-driven gameplay systems
- Test resource files load correctly with expected default values
