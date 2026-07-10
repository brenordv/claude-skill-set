---
name: unreal-engine
description: >-
  Unreal Engine 5.x game development expert. C++ and Blueprints, Nanite,
  Lumen, World Partition, GAS (Gameplay Ability System), multiplayer
  (Replication), Niagara VFX, MetaSounds, and platform shipping.
  Use PROACTIVELY for any Unreal Engine development, debugging, or optimization.
---

# Unreal Engine 5.x Game Development Expert

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, `brain/knowledge/coding-gamedev.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the engine-specific guidance below.
> **Language-Specific Testing**: See `testing-guidelines.md` in this skill folder for framework-specific testing patterns.

Build AAA-quality games in Unreal Engine 5.x using C++, Blueprints, and the engine's production-grade subsystems.

## When to Use This Skill

- Writing or reviewing UE5 C++ gameplay code (AActors, UObjects, UComponents)
- Building game systems with Blueprints or a C++/Blueprint hybrid approach
- Architecting gameplay with the Gameplay Ability System (GAS)
- Working with Nanite (virtualized geometry) or Lumen (global illumination)
- Setting up multiplayer with Unreal's replication system
- Creating VFX with Niagara or audio with MetaSounds
- Using World Partition for large open worlds
- Optimizing UE5 performance (CPU, GPU, memory, draw calls)
- Packaging and shipping to PC, console, or mobile
- Setting up CI/CD for Unreal projects

## Do Not Use This Skill When

- Designing game mechanics before implementation; use `game-developer` first
- Working in Unity or Godot; use `unity` or `godot`
- Writing general C++ with no Unreal dependency

## Instructions

1. Identify the UE version (this skill targets 5.7) and project type (first-person, third-person, open world, etc.).
2. Use the Unreal Way: work with the engine, not against it. Leverage built-in subsystems before building custom ones.
3. Follow the C++/Blueprint hybrid model: C++ for systems and logic, Blueprints for content and iteration.
4. Profile with Unreal Insights, stat commands, and GPU Visualizer before optimizing.
5. Follow Epic's coding standards and naming conventions.

---

## 1. Project Structure & Naming Conventions

### Folder Structure (Content Browser)

```
Content/
├── _Project/                  # Project-specific (underscore sorts to top)
│   ├── Art/
│   │   ├── Characters/
│   │   ├── Environment/
│   │   ├── UI/
│   │   └── VFX/
│   ├── Audio/
│   ├── Blueprints/
│   │   ├── Core/             # Game mode, game state, player controller
│   │   ├── Characters/
│   │   ├── Weapons/
│   │   └── UI/
│   ├── Data/                 # Data tables, curves, data assets
│   ├── Input/                # Input mapping contexts, input actions
│   ├── Levels/
│   │   ├── Maps/
│   │   └── Sublevels/
│   ├── Materials/
│   └── Meshes/
├── Developers/               # Per-developer sandbox (not shipped)
└── ThirdParty/               # Plugins, marketplace content
```

### Naming Conventions (Epic Standard)

| Asset Type       | Prefix  | Example                 |
| ---------------- | ------- | ----------------------- |
| Blueprint        | `BP_`   | `BP_PlayerCharacter`    |
| Widget Blueprint | `WBP_`  | `WBP_HealthBar`         |
| Material         | `M_`    | `M_RockBase`            |
| Material Inst.   | `MI_`   | `MI_RockMoss`           |
| Texture          | `T_`    | `T_Rock_D` (diffuse)    |
| Static Mesh      | `SM_`   | `SM_Wall_01`            |
| Skeletal Mesh    | `SK_`   | `SK_Character`          |
| Animation        | `A_`    | `A_Walk`                |
| Anim Montage     | `AM_`   | `AM_Attack_01`          |
| Niagara System   | `NS_`   | `NS_Explosion`          |
| Sound Cue        | `SC_`   | `SC_Footstep`           |
| MetaSound        | `MS_`   | `MS_WeaponFire`         |
| Data Table       | `DT_`   | `DT_WeaponStats`        |
| Data Asset        | `DA_`  | `DA_LevelConfig`        |
| Enum             | `E`     | `EWeaponType`           |
| Interface        | `I`     | `IDamageable`           |
| Widget           | `W`     | `WHealthBar`            |

### C++ Module Structure

```
Source/
├── MyGame/
│   ├── MyGame.Build.cs           # Module build rules
│   ├── MyGame.h / .cpp           # Module definition
│   ├── Core/
│   │   ├── MyGameMode.h / .cpp
│   │   ├── MyGameState.h / .cpp
│   │   └── MyPlayerController.h / .cpp
│   ├── Characters/
│   │   ├── MyCharacterBase.h / .cpp
│   │   └── MyPlayerCharacter.h / .cpp
│   ├── Components/
│   │   ├── HealthComponent.h / .cpp
│   │   └── InventoryComponent.h / .cpp
│   ├── Weapons/
│   │   └── WeaponBase.h / .cpp
│   └── UI/
│       └── MyHUD.h / .cpp
```

---

## 2. C++ Gameplay Framework

### The Actor-Component Model

Reusable behavior lives in `UActorComponent` subclasses attachable to any Actor, exposing `UFUNCTION`/`UPROPERTY` members and multicast delegates to Blueprints. Full `UHealthComponent` .h/.cpp pair: see `references/patterns.md` → "Health Component (Actor-Component Model)".

### The Unreal Gameplay Framework

```
UGameInstance          → Persistent across level loads (save data, settings)
  └── AGameModeBase   → Server-only rules (scoring, respawn, match flow)
      ├── AGameStateBase → Replicated match state (scores, time, phase)
      ├── APlayerController → Input handling, HUD, camera management
      │   └── APlayerState → Per-player replicated data (score, name, team)
      └── APawn / ACharacter → The physical entity in the world
```

**Key rule:** Put logic at the correct level.
- Match rules → GameMode
- Per-player persistent data → PlayerState
- Input processing → PlayerController
- Movement & physics → Character/Pawn
- Shared game state → GameState

---

## 3. Enhanced Input System

Add an `UInputMappingContext` via `UEnhancedInputLocalPlayerSubsystem` in `SetupInputComponent`, then `BindAction` each `UInputAction` to a handler on the `UEnhancedInputComponent`. Full player-controller .h/.cpp: see `references/patterns.md` → "Enhanced Input Controller".

---

## 4. Gameplay Ability System (GAS)

GAS is Unreal's built-in framework for abilities, attributes, and gameplay effects.

### Core Concepts

```
UAbilitySystemComponent (ASC)  → Lives on Actor, manages everything
├── FGameplayAttributeSet      → Health, Mana, Strength, etc.
├── UGameplayAbility           → Fireball, Dash, Block, Heal
├── UGameplayEffect            → Modify attributes (deal damage, buff, debuff)
└── FGameplayTag               → Hierarchical labels (State.Dead, Ability.Fire)
```

### Attribute Set

```cpp
UCLASS()
class MYGAME_API UMyAttributeSet : public UAttributeSet
{
    GENERATED_BODY()

public:
    UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Health, Category = "Attributes")
    FGameplayAttributeData Health;
    ATTRIBUTE_ACCESSORS(UMyAttributeSet, Health)

    UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_MaxHealth, Category = "Attributes")
    FGameplayAttributeData MaxHealth;
    ATTRIBUTE_ACCESSORS(UMyAttributeSet, MaxHealth)
    // Repeat the UPROPERTY + ATTRIBUTE_ACCESSORS + OnRep_ block per additional attribute (Mana, Strength, …)

    virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;
    virtual void PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data) override;

    UFUNCTION() void OnRep_Health(const FGameplayAttributeData& OldHealth);
    UFUNCTION() void OnRep_MaxHealth(const FGameplayAttributeData& OldMaxHealth);

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
};
```

Full attribute set with an added `Mana` attribute: see `references/patterns.md` → "Attribute Set (GAS)".

### Gameplay Ability

```cpp
UCLASS()
class MYGAME_API UGA_FireballAbility : public UGameplayAbility
{
    GENERATED_BODY()

public:
    UGA_FireballAbility();

    virtual void ActivateAbility(
        const FGameplayAbilitySpecHandle Handle,
        const FGameplayAbilityActorInfo* ActorInfo,
        const FGameplayAbilityActivationInfo ActivationInfo,
        const FGameplayEventData* TriggerEventData) override;

protected:
    UPROPERTY(EditDefaultsOnly, Category = "Fireball")
    TSubclassOf<AProjectile> ProjectileClass;

    UPROPERTY(EditDefaultsOnly, Category = "Fireball")
    TSubclassOf<UGameplayEffect> DamageEffect;

    UPROPERTY(EditDefaultsOnly, Category = "Fireball")
    float ManaCost = 25.f;
};
```

**When to use GAS:** Any game with abilities, RPG stats, buffs/debuffs, cooldowns, or multiplayer combat.
**When NOT to use GAS:** Simple games without stat systems (puzzle, casual, pure platformer).

---

## 5. Nanite & Lumen

### Nanite (Virtualized Geometry)

Nanite automatically handles LOD for static meshes. Enable per-mesh in mesh settings.

```
Suitable for Nanite:
- Static meshes (environment, props, architecture)
- Foliage (instanced static meshes)
- High-poly scanned assets (photogrammetry)

NOT suitable for Nanite:
- Skeletal meshes (characters, animated objects)
- Translucent materials
- Masked materials with complex alpha (use with care)
- Meshes that need per-vertex animation (cloth, water surface)
```

### Lumen (Global Illumination)

```
Lumen modes:
- Software ray tracing (default): works on all hardware, good quality
- Hardware ray tracing: RTX/RDNA2+, higher quality, higher cost

Key settings (Project Settings > Rendering > Global Illumination):
- Lumen Scene Lighting Quality: 1-4 (higher = better GI, more cost)
- Final Gather Quality: 1-4 (affects indirect lighting smoothness)
- Ray Lighting Mode: Surface Cache (fast) or Hit Lighting (accurate)
```

### Virtual Shadow Maps (VSM)

Enabled by default with Lumen. Provides high-resolution shadows without traditional cascaded shadow maps.

**Performance tip:** Set `r.Shadow.Virtual.MaxPhysicalPages` based on GPU VRAM.

---

## 6. World Partition (Open World)

### Setup

```cpp
// World Partition replaces World Composition
// Enable in World Settings > World Partition > Enable

// Key concepts:
// - Data Layers: Group actors by purpose (gameplay, audio, lighting)
// - HLOD (Hierarchical LOD): Auto-generated simplified representations
// - Level Instances: Reusable level chunks (like prefabs)
// - One File Per Actor (OFPA): Each actor saved separately (better source control)
```

### Streaming Configuration

```
World Settings:
├── Runtime Grid: Set cell size (default 12800 = 128m)
│   └── Loading range: How far to stream in (default 25600 = 256m)
├── Data Layers:
│   ├── Default: Always loaded
│   ├── Gameplay: Loaded around player
│   └── Audio: Loaded with wider range
└── HLOD:
    ├── Generate for distant geometry
    └── Configure merge distance and poly count
```

**Key rule:** Test streaming on target hardware. PC streaming hides loading; consoles with HDDs will expose hitches.

---

## 7. Multiplayer & Replication

### Replicated Properties

```cpp
UCLASS()
class MYGAME_API AMyCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    virtual void GetLifetimeReplicatedProps(
        TArray<FLifetimeProperty>& OutLifetimeProps) const override;

protected:
    // Replicated with notification
    UPROPERTY(ReplicatedUsing = OnRep_Health)
    float Health = 100.f;

    UFUNCTION()
    void OnRep_Health();

    // Replicated, condition-based
    UPROPERTY(Replicated)
    FVector AimDirection;
};

// In .cpp
void AMyCharacter::GetLifetimeReplicatedProps(
    TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);

    DOREPLIFETIME(AMyCharacter, Health);
    DOREPLIFETIME_CONDITION(AMyCharacter, AimDirection, COND_SkipOwner);
}
```

### RPCs (Remote Procedure Calls)

```cpp
// Server RPC: client calls, server executes (validated)
UFUNCTION(Server, Reliable, WithValidation)
void ServerRPC_Fire(FVector Direction);
bool ServerRPC_Fire_Validate(FVector Direction);
void ServerRPC_Fire_Implementation(FVector Direction);

// Client RPC: server calls, owning client executes
UFUNCTION(Client, Reliable)
void ClientRPC_PlayHitReaction();
void ClientRPC_PlayHitReaction_Implementation();

// Multicast RPC: server calls, ALL clients execute
UFUNCTION(NetMulticast, Unreliable)
void MulticastRPC_PlayExplosionVFX(FVector Location);
void MulticastRPC_PlayExplosionVFX_Implementation(FVector Location);
```

### Authority Model

The server-authority / never-trust-the-client rules are in `coding-gamedev.md` §7. UE specifics:

```
Server = Authority (owns game state, validates actions)
Client = Autonomous Proxy (local prediction) or Simulated Proxy (remote)

- Validate all ServerRPCs
- Client predicts movement (CharacterMovementComponent handles this)
- Server corrects client on mismatch (rubber-banding)
```

---

## 8. Niagara VFX System

```
Niagara hierarchy:
NiagaraSystem         → The complete effect (spawned by gameplay)
├── NiagaraEmitter    → One particle type (sparks, smoke, fire)
│   ├── Modules       → Logic (spawn rate, velocity, color over life)
│   └── Renderer      → How to draw (sprite, mesh, ribbon)
└── NiagaraEmitter    → Another particle type
```

### Spawning VFX from C++

```cpp
// Spawn a Niagara system at location
#include "NiagaraFunctionLibrary.h"

UNiagaraComponent* VFX = UNiagaraFunctionLibrary::SpawnSystemAtLocation(
    GetWorld(),
    ExplosionNiagaraSystem,  // UNiagaraSystem* (set via UPROPERTY)
    HitLocation,
    HitNormal.Rotation(),
    FVector(1.f),
    true,                    // Auto destroy
    true                     // Auto activate
);

// Set parameters at runtime
VFX->SetFloatParameter(FName("ExplosionRadius"), 500.f);
VFX->SetColorParameter(FName("Color"), FLinearColor::Red);
```

---

## 9. Performance Optimization

### Stat Commands (In-Game Profiling)

```
stat fps:            Frame rate and frame time
stat unit:           Game thread, render thread, GPU time breakdown
stat unitgraph:      Visual graph of thread timings
stat scenerendering: Draw calls, triangle count, mesh draw commands
stat rhi:            GPU memory, resource counts
stat game:           Gameplay systems timing
stat physics:        Physics simulation cost
stat memory:         Memory allocation overview
```

### Unreal Insights (Deep Profiling)

```
Launch with: -trace=cpu,gpu,frame,memory
Open: UnrealInsights.exe → load .utrace file
```

### Common Optimization Techniques

| Problem                    | Solution                                               |
| -------------------------- | ------------------------------------------------------ |
| High draw calls            | Enable Nanite, use instanced meshes, merge actors      |
| GI too expensive           | Lower Lumen quality, use baked for static scenes       |
| Physics overhead           | Simplify collision, reduce physics substeps             |
| Tick overhead              | Disable tick on inactive actors, use timers instead     |
| Memory pressure            | Texture streaming, reduce mip levels, compress assets  |
| Shader compilation hitches | Pre-compile PSO cache, use PSO precaching              |
| Blueprint overhead         | Nativize hot Blueprints or move to C++                 |
| Network bandwidth          | Reduce replicated properties, use relevancy, net cull  |

### Actor Tick Best Practices

Disable processing when idle (`coding-gamedev.md` §4). In UE, default tick off in the constructor and toggle it at runtime with `SetActorTickEnabled`; use timers for periodic work.

```cpp
// Default tick OFF; enable on demand via SetActorTickEnabled(true/false)
PrimaryActorTick.bCanEverTick = false;

// For periodic work, use timers instead of tick
GetWorldTimerManager().SetTimer(
    TimerHandle, this, &AMyActor::CheckForEnemies, 0.5f, true);
```

---

## 10. C++ / Blueprint Hybrid Workflow

### The Rule

- **C++** for: Base classes, systems, performance-critical code, interfaces, data structures.
- **Blueprints** for: Content creation, rapid iteration, prototyping, designer-facing tuning, VFX/audio triggers.

### Exposing C++ to Blueprints

```cpp
// BlueprintCallable: callable from Blueprint graphs
UFUNCTION(BlueprintCallable, Category = "Combat")
void ApplyDamage(AActor* Target, float Amount);

// BlueprintImplementableEvent: C++ declares, Blueprint implements
UFUNCTION(BlueprintImplementableEvent, Category = "Combat")
void OnDeath();

// BlueprintNativeEvent: C++ provides default, Blueprint can override
UFUNCTION(BlueprintNativeEvent, Category = "Combat")
float CalculateDamage(float BaseDamage);
float CalculateDamage_Implementation(float BaseDamage) { return BaseDamage; }

// BlueprintPure: no side effects, used as expression node
UFUNCTION(BlueprintPure, Category = "Combat")
bool IsAlive() const { return Health > 0.f; }

// EditAnywhere: editable in Blueprint defaults AND per-instance
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Combat")
float BaseDamage = 10.f;

// EditDefaultsOnly: editable in Blueprint defaults only
UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Combat")
TSubclassOf<UGameplayEffect> DamageEffectClass;
```

---

## 11. Common Subsystems Reference

| Subsystem                     | Purpose                            | Key Class/Module           |
| ----------------------------- | ---------------------------------- | -------------------------- |
| Enhanced Input                | Input mapping and processing       | `UInputMappingContext`     |
| Gameplay Ability System       | Abilities, attributes, effects     | `UAbilitySystemComponent`  |
| AI (Behavior Trees)           | NPC decision-making                | `UBehaviorTree`            |
| Navigation System             | Pathfinding (NavMesh)              | `UNavigationSystemV1`      |
| Niagara                       | VFX / particles                    | `UNiagaraSystem`           |
| MetaSounds                    | Procedural audio                   | `UMetaSoundSource`         |
| Common UI                     | Cross-platform UI framework        | `UCommonActivatableWidget` |
| PCG (Procedural Content Gen)  | Procedural world building          | `UPCGGraph`                |
| Motion Matching               | Animation (replaced AnimMontages)  | `UPoseSearch`              |
| Chaos (Physics)               | Destruction, cloth, physics        | `UChaosDestructionComponent`|

---

## Best Practices Summary

| Area              | Do                                              | Don't                                         |
| ----------------- | ----------------------------------------------- | --------------------------------------------- |
| **Architecture**  | Gameplay Framework hierarchy, GAS for abilities  | Custom frameworks that fight the engine        |
| **C++**           | UCLASS/UPROPERTY macros, Epic coding standard    | Raw `new`/`delete`, manual memory management   |
| **Blueprints**    | Content and tuning, call into C++ base classes   | Complex game logic in sprawling Blueprint graphs|
| **Performance**   | Disable tick by default, use timers, profile     | Tick on every actor, optimize without profiling|
| **Rendering**     | Nanite for static meshes, Lumen for GI           | Per-object LOD for Nanite meshes               |
| **Multiplayer**   | Server-authoritative, validate RPCs              | Trust client data, replicate everything        |
| **Testing**       | Automation & Functional tests (see `testing-guidelines.md`) | No automated tests             |
| **Assets**        | Follow naming conventions, use Data Assets       | Random naming, hard-coded asset paths          |
| **Source Control** | One File Per Actor, lock binary assets           | Monolithic level files, merge conflicts on .umap|
| **Packaging**     | Cook only needed content, strip debug data       | Ship debug builds, include dev-only content    |

## Limitations

- This skill targets UE 5.x. Some APIs and subsystems differ in UE 4.x or early 5.x versions.
- GAS is powerful but has a steep learning curve; the introductory coverage here is a starting point, not a complete reference.
- Console-specific optimizations (PlayStation, Xbox, Switch) depend on NDA SDKs not documented here.
- Dedicated server deployment, backend services (EOS, PlayFab), and live-ops infrastructure are beyond engine-level concerns.
- Large teams will need Perforce or similar for binary asset locking; Git LFS has limitations at scale for Unreal projects.
