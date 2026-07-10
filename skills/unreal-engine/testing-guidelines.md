# Unreal Engine Testing Guidelines

Engine-specific testing patterns for Unreal Engine projects. These complement the general testing principles in `brain/knowledge/testing.md`.

## Automation Framework

### FAutomationTestBase

The core testing framework in Unreal Engine:

```cpp
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDamageCalculationTest,
    "Game.Combat.DamageCalculation",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter)

bool FDamageCalculationTest::RunTest(const FString& Parameters)
{
    // Arrange
    FDamageParams Params;
    Params.BaseDamage = 100.f;
    Params.DamageMultiplier = 1.5f;

    // Act
    float Result = UDamageCalculator::CalculateDamage(Params);

    // Assert
    TestEqual(TEXT("Damage should be base * multiplier"), Result, 150.f);

    return true;
}
```

### Complex Automation Tests

```cpp
IMPLEMENT_COMPLEX_AUTOMATION_TEST(FInventorySystemTest,
    "Game.Inventory.AddRemoveItems",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter)

void FInventorySystemTest::GetTests(TArray<FString>& OutBeautifiedNames,
                                     TArray<FString>& OutTestCommands) const
{
    OutBeautifiedNames.Add(TEXT("Add Single Item"));
    OutTestCommands.Add(TEXT("AddSingle"));

    OutBeautifiedNames.Add(TEXT("Add Stack Overflow"));
    OutTestCommands.Add(TEXT("AddOverflow"));
}

bool FInventorySystemTest::RunTest(const FString& Parameters)
{
    if (Parameters == TEXT("AddSingle"))
    {
        // Test adding a single item
    }
    else if (Parameters == TEXT("AddOverflow"))
    {
        // Test adding beyond stack limit
    }
    return true;
}
```

## Functional Tests

For gameplay verification in a live world context:

```cpp
UCLASS()
class AFunctionalTest_PlayerSpawn : public AFunctionalTest
{
    GENERATED_BODY()

public:
    virtual void StartTest() override
    {
        Super::StartTest();

        APlayerCharacter* Player = GetWorld()->SpawnActor<APlayerCharacter>();
        TestNotNull(TEXT("Player should spawn"), Player);
        TestTrue(TEXT("Player should be alive"), Player->IsAlive());

        FinishTest(EFunctionalTestResult::Succeeded, TEXT("Player spawn test passed"));
    }
};
```

## Unit Tests for Pure C++ Logic

Test pure C++ logic without engine dependencies where possible:

```cpp
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FPathfindingTest,
    "Game.AI.Pathfinding.BasicPath",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter)

bool FPathfindingTest::RunTest(const FString& Parameters)
{
    FGridGraph Graph(10, 10);
    TArray<FIntPoint> Path = Graph.FindPath(FIntPoint(0, 0), FIntPoint(9, 9));

    TestTrue(TEXT("Path should not be empty"), Path.Num() > 0);
    TestEqual(TEXT("Path should end at target"), Path.Last(), FIntPoint(9, 9));

    return true;
}
```

## Blueprint Testing via Automation Specs

```cpp
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBlueprintFunctionTest,
    "Game.Blueprints.UtilityFunctions",
    EAutomationTestFlags::ApplicationContextMask | EAutomationTestFlags::ProductFilter)

bool FBlueprintFunctionTest::RunTest(const FString& Parameters)
{
    UBlueprint* BP = LoadObject<UBlueprint>(nullptr,
        TEXT("/Game/Blueprints/BP_GameUtilities.BP_GameUtilities"));
    TestNotNull(TEXT("Blueprint should load"), BP);
    if (BP == nullptr)
    {
        return false;
    }

    UObject* CDO = BP->GeneratedClass->GetDefaultObject();
    TestNotNull(TEXT("Blueprint CDO should be valid"), CDO);

    return true;
}
```

## Network Testing

Test with multiple PIE (Play In Editor) instances:

- Use dedicated multiplayer test maps
- Verify property replication with authority checks
- Test RPC execution on server vs client

## Gauntlet for CI/CD

Gauntlet enables running automation tests from the command line for CI/CD integration:

```bash
# Run all game tests
RunUAT.bat RunUnreal -project=MyGame -test="Game.*" -platform=Win64

# Run specific test category
RunUAT.bat Gauntlet -project=MyGame -testfilter="Game.Combat.*" -build=local
```

## Performance Tests

Capture performance metrics with the `PerfFilter` automation flag and latent commands: load the map (`FLoadMap`), wait for streaming (`FWaitForMapToLoad`), capture frame-time stats over N frames (`FCapturePerformanceStats`), and assert the frame time stays within budget.

## Key Principles

- Use `IMPLEMENT_SIMPLE_AUTOMATION_TEST` for straightforward tests
- Use `IMPLEMENT_COMPLEX_AUTOMATION_TEST` for parameterized/data-driven tests
- Use Functional Tests for in-world gameplay verification
- Test pure C++ logic separately from engine-dependent code
- Use Gauntlet for CI/CD pipeline integration
- Always include performance tests for rendering and gameplay systems
- Use meaningful test paths (e.g., "Game.Combat.DamageCalculation") for organization
