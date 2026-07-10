---
name: unity
description: >-
  Unity 6.x game development expert. C# scripting, ECS/DOTS, performance
  optimization, rendering pipelines (URP/HDRP), physics, UI Toolkit,
  multiplayer (Netcode for GameObjects), and platform deployment.
  Use PROACTIVELY for any Unity development, debugging, or optimization.
---

# Unity 6.x Game Development Expert

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, `brain/knowledge/coding-gamedev.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the engine-specific guidance below.
> **Language-Specific Testing**: See `testing-guidelines.md` in this skill folder for framework-specific testing patterns.

Build high-performance, maintainable games in Unity 6.3 using modern C# patterns, data-oriented design, and engine best practices.

## When to Use This Skill

- Writing or reviewing Unity C# scripts
- Architecting Unity game systems (player controllers, AI, inventory, UI)
- Optimizing Unity performance (CPU, GPU, memory, GC)
- Configuring rendering pipelines (URP, HDRP, custom SRPs)
- Setting up Unity multiplayer with Netcode for GameObjects
- Working with Unity's ECS / DOTS stack
- Building editor tools, custom inspectors, or asset pipelines
- Deploying to mobile, console, PC, VR/AR, or WebGL
- Debugging Unity-specific issues (serialization, lifecycle, physics)
- Migrating projects to Unity 6.x from older versions

## Do Not Use This Skill When

- Designing game mechanics before implementation: use `game-developer` first
- Working in Godot or Unreal Engine: use `godot` or `unreal-engine`
- Writing pure C# with no Unity dependency: use `csharp` skill

## Instructions

1. Assess the Unity version, render pipeline, and target platform.
2. Apply modern Unity patterns (component architecture, ScriptableObjects, Addressables).
3. Write performant C#: avoid GC allocations in hot paths, use object pooling, cache references.
4. Validate with Profiler, Frame Debugger, and Memory Profiler.
5. Follow Unity's recommended project structure and assembly definitions.

---

## 1. Project Structure & Organization

### Recommended Folder Layout

```
Assets/
├── _Project/              # Project-specific assets (underscore sorts to top)
│   ├── Art/
│   │   ├── Materials/
│   │   ├── Models/
│   │   ├── Textures/
│   │   └── Animations/
│   ├── Audio/
│   │   ├── Music/
│   │   └── SFX/
│   ├── Prefabs/
│   ├── Scenes/
│   ├── Scripts/
│   │   ├── Runtime/
│   │   │   ├── Core/         # Singletons, managers, events
│   │   │   ├── Player/
│   │   │   ├── Enemies/
│   │   │   ├── Systems/      # Inventory, combat, progression
│   │   │   ├── UI/
│   │   │   └── Utilities/
│   │   └── Editor/           # Custom editor scripts
│   ├── ScriptableObjects/
│   ├── Settings/             # Render pipeline, quality, input
│   └── Resources/            # Only for runtime-loaded assets
├── Plugins/
└── StreamingAssets/
```

### Assembly Definitions

Always use `.asmdef` files to control compilation domains:

```
Scripts/Runtime/Core/Core.asmdef           → MyGame.Core
Scripts/Runtime/Player/Player.asmdef       → MyGame.Player (refs: Core)
Scripts/Runtime/UI/UI.asmdef               → MyGame.UI (refs: Core)
Scripts/Editor/Editor.asmdef               → MyGame.Editor (refs: Core; Editor-only)
```

**Benefits:** Faster incremental compilation, enforced dependency boundaries, clearer architecture.

---

## 2. C# Best Practices for Unity

### Performance-Critical Coding Rules

- **RULE 1: Cache component references**. Never GetComponent in Update (cache in Awake).
- **RULE 2: Avoid allocations in hot paths**. Pre-allocate, reuse, cache; clear collections instead of reallocating.
- **RULE 3: Use struct over class for small, short-lived data.**
- **RULE 4: Prefer CompareTag over string comparison**. `other.CompareTag("Player")` is fast/no GC.
- **RULE 5: Use NonAlloc physics queries**. Reuse a preallocated hit buffer.

Code demonstrations for all five rules: see `references/patterns.md` → "Performance-Critical Coding Rules".

### Modern C# Features Safe for Unity 6.x

Unity 6.x supports C# 12 / .NET 8+. Use modern features freely:

```csharp
// Records for immutable game data
public record WeaponStats(string Name, int Damage, float FireRate, float Range);

// Pattern matching for state logic
public float GetSpeedMultiplier(PlayerState state) => state switch
{
    PlayerState.Idle => 0f,
    PlayerState.Walking => 1f,
    PlayerState.Running => 1.8f,
    PlayerState.Crouching => 0.5f,
    PlayerState.Stunned => 0f,
    _ => 1f,
};

// Span<T> for zero-alloc string/array work in tools & editor code
ReadOnlySpan<char> extension = filePath.AsSpan()[filePath.LastIndexOf('.')..];
```

### Null checks in Unity

Null checks `obj == null` are expensive, and Unity provides a sugar syntax that seems to help with performance:

```csharp
if (!obj) { return "this is null"; }
```

Use this syntax whenever you need to check for nulls.

### Async Patterns in Unity

```csharp
// Use Awaitable (Unity 6+) instead of coroutines for async game logic
public class SceneLoader : MonoBehaviour
{
    public async Awaitable LoadSceneAsync(string sceneName)
    {
        var op = SceneManager.LoadSceneAsync(sceneName, LoadSceneMode.Additive);
        while (!op.isDone)
        {
            OnProgress?.Invoke(op.progress);
            await Awaitable.NextFrameAsync();
        }
    }

    // Awaitable.WaitForSecondsAsync replaces WaitForSeconds coroutines
    public async Awaitable FlashDamage()
    {
        _spriteRenderer.color = Color.red;
        await Awaitable.WaitForSecondsAsync(0.1f);
        _spriteRenderer.color = Color.white;
    }
}

// CAUTION: Awaitables respect destroyCancellationToken automatically
// No need for manual CancellationToken in most MonoBehaviour async methods
```

### SOLID Principles Applied to Unity

```csharp
// SINGLE RESPONSIBILITY: Each component does one thing
[RequireComponent(typeof(Health))]
public class DamageReceiver : MonoBehaviour
{
    private Health _health;

    private void Awake() => _health = GetComponent<Health>();

    public void TakeDamage(DamageEvent evt)
    {
        _health.Subtract(evt.Damage);
        // Does NOT handle: death, VFX, sound; those are separate components
        // listening to Health.OnDepleted event
    }
}

// OPEN/CLOSED: Use ScriptableObjects for extensibility
public abstract class AbilitySO : ScriptableObject
{
    public abstract void Activate(AbilityContext context);
}

[CreateAssetMenu(menuName = "Abilities/Fireball")]
public class FireballAbility : AbilitySO
{
    [SerializeField] private GameObject _projectilePrefab;
    [SerializeField] private float _damage = 50f;

    public override void Activate(AbilityContext context)
    {
        var proj = Instantiate(_projectilePrefab, context.SpawnPoint, context.Rotation);
        proj.GetComponent<Projectile>().Init(_damage, context.Owner);
    }
}

// DEPENDENCY INVERSION: Depend on interfaces, inject via inspector or service locator
public interface IDamageable
{
    void TakeDamage(float amount, DamageType type);
}
```

---

## 3. ScriptableObject Architecture

ScriptableObjects are Unity's most powerful architectural tool. Use them for data, configuration, events, and shared state.

### Data Containers

```csharp
[CreateAssetMenu(fileName = "EnemyData", menuName = "Game/Enemy Data")]
public class EnemyDataSO : ScriptableObject
{
    [Header("Stats")]
    public int maxHealth = 100;
    public float moveSpeed = 3.5f;
    public int attackDamage = 10;

    [Header("Behavior")]
    public float aggroRange = 15f;
    public float attackRange = 2f;
    public float attackCooldown = 1.5f;

    [Header("Loot")]
    public LootTableSO lootTable;
}
```

### Event Channels (Decoupled Communication)

One ScriptableObject event-channel class per payload type (drag-and-drop in the inspector, no hard references). Write `VoidEventSO` once and repeat the pattern per payload type (`IntEventSO`, `FloatEventSO`, …). Channel class + component usage: see `references/patterns.md` → "Event Channels (ScriptableObject)".

### Shared Runtime State

```csharp
[CreateAssetMenu(menuName = "Game/Player Runtime Data")]
public class PlayerRuntimeDataSO : ScriptableObject
{
    [NonSerialized] public int CurrentHealth;
    [NonSerialized] public int Gold;
    [NonSerialized] public Vector3 LastCheckpoint;

    public void Reset()
    {
        CurrentHealth = 100;
        Gold = 0;
        LastCheckpoint = Vector3.zero;
    }
}
```

---

## 4. Object Pooling

Pool reusable objects per the pooling rule in `coding-gamedev.md` §4. Unity implementation (`SetActive`-based pool with `Get`/`Return`): see `references/patterns.md` → "Object Pool".

---

## 5. Rendering Pipeline Selection

### URP vs HDRP vs Built-in

| Feature           | URP                      | HDRP                    | Built-in (Legacy)    |
| ----------------- | ------------------------ | ----------------------- | -------------------- |
| **Target**        | Mobile, mid-range PC     | High-end PC, console    | Legacy projects only |
| **Performance**   | Optimized for scale      | Feature-rich, heavier   | Unpredictable        |
| **Shader Graph**  | Yes                      | Yes                     | No (ShaderLab only)  |
| **VR/AR**         | Primary choice           | Supported               | Legacy               |
| **2D Renderer**   | Yes (2D Renderer)        | No                      | Sprite Renderer      |
| **Ray Tracing**   | Limited (6.x+)           | Full                    | No                   |

**Rule of thumb:** Start with URP. Switch to HDRP only if you need its specific features (volumetric fog, ray tracing, subsurface scattering). Never start a new project on Built-in.

### URP Shader Best Practices

```hlsl
// Use URP shader library, not legacy CG
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

// Minimize texture samples in fragment shader
// Use _MainTex_ST for tiling/offset (TRANSFORM_TEX macro)
// Prefer half precision on mobile: half4, half3, half2
```

---

## 6. Physics Best Practices

```csharp
// Use FixedUpdate for physics, Update for input
private void FixedUpdate()
{
    _rb.AddForce(_moveDirection * _speed, ForceMode.Acceleration);
}

// Layer-based collision filtering: set in Physics settings, not code
// Use Physics.OverlapSphereNonAlloc for queries
private readonly Collider[] _overlapBuffer = new Collider[32];

int count = Physics.OverlapSphereNonAlloc(
    transform.position, _radius, _overlapBuffer, _enemyLayerMask);

// Rigidbody best practices:
// - Use Rigidbody.MovePosition/MoveRotation for kinematic bodies
// - Never modify transform.position directly on non-kinematic Rigidbodies
// - Set interpolation to "Interpolate" for player-controlled bodies
// - Use continuous collision detection for fast-moving objects
```

---

## 7. UI Toolkit (Recommended over UGUI for Unity 6+)

Runtime UI with USS (like CSS) and UXML (like HTML). Query elements via `root.Q<T>("name")` in `OnEnable`. Full C# controller + UXML + USS listings: see `references/patterns.md` → "UI Toolkit: Runtime UI (UXML / USS)".

---

## 8. ECS / DOTS (Data-Oriented Technology Stack)

Use DOTS for high-entity-count scenarios (thousands of enemies, bullets, particles).

```csharp
// Component: pure data, no logic
public struct MoveSpeed : IComponentData
{
    public float Value;
}

public struct Velocity : IComponentData
{
    public float3 Value;
}

// System: logic that operates on components
[BurstCompile]
public partial struct MovementSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        float dt = SystemAPI.Time.DeltaTime;

        foreach (var (transform, velocity, speed) in
            SystemAPI.Query<RefRW<LocalTransform>, RefRO<Velocity>, RefRO<MoveSpeed>>())
        {
            transform.ValueRW.Position += velocity.ValueRO.Value * speed.ValueRO.Value * dt;
        }
    }
}

// Authoring: bridge between GameObjects and ECS
public class MoveSpeedAuthoring : MonoBehaviour
{
    public float speed = 5f;

    public class Baker : Baker<MoveSpeedAuthoring>
    {
        public override void Bake(MoveSpeedAuthoring authoring)
        {
            var entity = GetEntity(TransformUsageFlags.Dynamic);
            AddComponent(entity, new MoveSpeed { Value = authoring.speed });
        }
    }
}
```

**When to use DOTS:** Thousands of entities, simulation-heavy games, performance-critical paths.
**When NOT to use DOTS:** UI-heavy games, small entity counts, rapid prototyping (use MonoBehaviour).

---

## 9. Multiplayer with Netcode for GameObjects

```csharp
using Unity.Netcode;

public class NetworkedPlayer : NetworkBehaviour
{
    // Synced variable: server-authoritative
    private NetworkVariable<int> _health = new(
        100,
        NetworkVariableReadPermission.Everyone,
        NetworkVariableWritePermission.Server);

    public override void OnNetworkSpawn()
    {
        _health.OnValueChanged += OnHealthChanged;

        if (IsOwner)
            EnableInput();
    }

    // Client calls this, server executes
    [ServerRpc]
    private void MoveServerRpc(Vector3 direction)
    {
        // Server validates and applies movement
        transform.position += direction * _speed * Time.deltaTime;
    }

    // Server calls this, clients execute
    [ClientRpc]
    private void PlayHitEffectClientRpc()
    {
        _vfxController.PlayHitEffect();
    }

    private void OnHealthChanged(int previous, int current)
    {
        _healthBar.UpdateHealth(current, 100);
    }
}
```

---

## 10. Addressables & Asset Management

```csharp
using UnityEngine.AddressableAssets;
using UnityEngine.ResourceManagement.AsyncOperations;

public class AssetLoader : MonoBehaviour
{
    [SerializeField] private AssetReference _enemyPrefabRef;

    private AsyncOperationHandle<GameObject> _handle;

    public async Awaitable<GameObject> LoadAndInstantiate(Vector3 position)
    {
        _handle = Addressables.InstantiateAsync(_enemyPrefabRef, position, Quaternion.identity);
        await _handle.Task;
        return _handle.Result;
    }

    private void OnDestroy()
    {
        if (_handle.IsValid())
            Addressables.Release(_handle);
    }
}
```

**Addressables rules:**
- Never use `Resources.Load` in production; use Addressables.
- Group assets by loading pattern (level-based, always-loaded, on-demand).
- Release handles when done to prevent memory leaks.
- Use labels for bulk loading (`Addressables.LoadAssetsAsync<T>("level-1", ...)`).

---

## 11. Profiling & Optimization Workflow

### The Optimization Loop

The profile-before-optimizing principle is in `coding-gamedev.md` §4. In Unity, use the Unity Profiler (CPU, GPU, Memory):

1. **Identify the bottleneck**: Is it CPU-bound, GPU-bound, or memory-bound?
2. **Fix the biggest offender**: One change at a time, re-profile after each.
3. **Stop when targets are met**: Don't optimize past your frame budget.

### Common Performance Fixes

| Problem                       | Solution                                            |
| ----------------------------- | --------------------------------------------------- |
| GC spikes (stutters)          | Object pooling, avoid LINQ in Update, cache strings |
| Too many draw calls           | Static/dynamic batching, GPU instancing, atlasing   |
| Expensive Update loops        | Use `InvokeRepeating`, timer-based, or Jobs         |
| Physics overhead              | Simplify colliders, use layers, reduce FixedUpdate rate |
| Shader complexity (GPU)       | LOD shaders, reduce overdraw, bake lighting         |
| Large scene loading           | Additive scene loading, Addressables, streaming     |
| Memory leaks                  | Release Addressables, unsubscribe events, null refs |

### Frame Budget Breakdown

Frame-budget allocation is a design concern owned by the `game-developer` skill (see its Platform & Performance Targets) and `coding-gamedev.md` §4.

---

## 12. Input System (New Input System)

Enable the action map and subscribe action callbacks in `OnEnable`; unsubscribe and disable in `OnDisable` (symmetry prevents leaks and double-fires). Full `PlayerInput` boilerplate: see `references/patterns.md` → "Input System (New Input System)".

---

## Best Practices Summary

| Area               | Do                                              | Don't                                        |
| ------------------ | ----------------------------------------------- | -------------------------------------------- |
| **Architecture**   | ScriptableObject events, composition            | Singletons everywhere, deep inheritance      |
| **Performance**    | Cache references, pool objects, NonAlloc queries | GetComponent in Update, Instantiate/Destroy  |
| **Code Style**     | Assembly definitions, namespaces                | All scripts in one folder, no .asmdef        |
| **Assets**         | Addressables, asset bundles                     | Resources.Load in production                 |
| **Physics**        | Layers, simplified colliders, FixedUpdate       | MeshColliders everywhere, Update physics     |
| **Rendering**      | URP for most projects, LOD, batching            | Built-in pipeline for new projects           |
| **UI**             | UI Toolkit for complex UI                       | Immediate-mode OnGUI in builds               |
| **Async**          | Awaitable (Unity 6+), async/await               | Nested coroutines, callback hell             |
| **Serialization**  | [SerializeField] private, [field: SerializeField] | Public fields everywhere               |
| **Testing**        | Play Mode + Edit Mode tests, assembly isolation | No tests, untestable architecture            |

## Limitations

- This skill targets Unity 6.x (LTS and latest). Some APIs differ in Unity 5.x or 2020-2022 LTS.
- DOTS/ECS coverage is introductory; deeply specialized ECS architectures may need additional research.
- Platform-specific deployment (console SDK integration, platform certification) requires NDA documentation not covered here.
- Multiplayer architecture for large-scale games (MMO, battle royale) requires dedicated server infrastructure beyond Netcode for GameObjects.
