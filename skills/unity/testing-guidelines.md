# Unity Testing Guidelines

Engine-specific testing patterns for Unity projects. These complement the general testing principles in `brain/knowledge/testing.md`.

## Test Modes

### Edit Mode Tests (Pure Logic)

No scene required. Use for testing classes that don't depend on MonoBehaviour lifecycle:

```csharp
[Test]
public void CalculateDamage_WithCriticalHit_DoublesBaseDamage()
{
    // Arrange
    var calculator = new DamageCalculator();

    // Act
    var result = calculator.Calculate(baseDamage: 50, isCritical: true);

    // Assert
    Assert.AreEqual(100, result);
}
```

### Play Mode Tests (Runtime Behavior)

For testing MonoBehaviour lifecycle, physics, coroutines, and scene interactions:

```csharp
[UnityTest]
public IEnumerator PlayerHealth_TakeDamage_TriggersDeathAtZero()
{
    // Arrange
    var go = new GameObject();
    var health = go.AddComponent<PlayerHealth>();
    // Configure serialized-private fields through a public test hook; no public fields
    health.Initialize(maxHealth: 100, currentHealth: 10);

    // Act
    health.TakeDamage(10);
    yield return null; // wait one frame for events to process

    // Assert
    Assert.IsTrue(health.IsDead);

    Object.Destroy(go);
}
```

## Assembly Isolation

- Test assemblies reference production assemblies (not the other way around)
- Create separate assembly definitions: `MyGame.Tests.EditMode.asmdef` and `MyGame.Tests.PlayMode.asmdef`
- Reference only the assemblies you are testing

## Assertions

Use NUnit assertions (Unity's built-in test framework):

```csharp
Assert.AreEqual(expected, actual);
Assert.IsTrue(condition);
Assert.IsNotNull(obj);
Assert.That(value, Is.InRange(0f, 1f));
Assert.Throws<ArgumentException>(() => method.Call(invalidArg));
```

## Testing ScriptableObject Data Integrity

```csharp
[UnityTest]
public IEnumerator WeaponData_AllWeapons_HavePositiveDamage()
{
    // Load via Addressables (never Resources.Load in production)
    var handle = Addressables.LoadAssetsAsync<WeaponData>("Weapons", null);
    yield return handle;

    foreach (var weapon in handle.Result)
    {
        Assert.IsTrue(weapon.damage > 0,
            $"Weapon '{weapon.name}' has non-positive damage: {weapon.damage}");
    }

    Addressables.Release(handle);
}

[UnityTest]
public IEnumerator LevelConfig_ProgressionOrder_IsSequential()
{
    var handle = Addressables.LoadAssetsAsync<LevelConfig>("Levels", null);
    yield return handle;

    var levels = handle.Result.OrderBy(l => l.levelIndex).ToArray();

    for (int i = 0; i < levels.Length - 1; i++)
    {
        Assert.IsTrue(levels[i].difficulty <= levels[i + 1].difficulty,
            $"Level {levels[i].levelIndex} difficulty exceeds next level");
    }

    Addressables.Release(handle);
}
```

## Testing Component Interactions

Use mock GameObjects to test component relationships:

```csharp
[UnityTest]
public IEnumerator PickupItem_OnTriggerEnter_AddsToInventory()
{
    // Arrange
    var player = new GameObject();
    player.AddComponent<BoxCollider>().isTrigger = false;
    var inventory = player.AddComponent<Inventory>();
    var rb = player.AddComponent<Rigidbody>();

    var pickup = new GameObject();
    pickup.AddComponent<BoxCollider>().isTrigger = true;
    var item = pickup.AddComponent<PickupItem>();
    // Configure the serialized-private id through a public test hook; no public fields
    item.Initialize("health_potion");

    pickup.transform.position = player.transform.position;

    yield return new WaitForFixedUpdate();

    // Assert
    Assert.IsTrue(inventory.HasItem("health_potion"));

    Object.Destroy(player);
    Object.Destroy(pickup);
}
```

## Performance Considerations

- Profile tests to ensure they don't introduce frame budget issues
- Play Mode tests run in a real game loop -- keep them fast
- Avoid tests that require many frames unless testing time-dependent behavior
- Clean up all created GameObjects with `Object.Destroy()`

## Key Principles

- Use Edit Mode tests for pure logic (faster, no scene overhead)
- Use Play Mode tests only when you need MonoBehaviour lifecycle or physics
- Always clean up instantiated GameObjects after tests
- Test ScriptableObject data integrity to catch configuration errors
- Keep test assemblies separate from production assemblies
- Avoid testing Unity engine behavior -- focus on your game logic
