# Unreal Engine Reference Patterns

Full implementations referenced from `SKILL.md`. These are load-on-demand; the SKILL body keeps the framework diagrams and "Key rule" lines and links here for the long listings.

## Health Component (Actor-Component Model)

Reusable component attachable to any Actor (SKILL.md §2).

```cpp
// HealthComponent.h: Reusable across any Actor
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HealthComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(
    FOnHealthChanged, float, CurrentHealth, float, MaxHealth);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnDeath);

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class MYGAME_API UHealthComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UHealthComponent();

    UFUNCTION(BlueprintCallable, Category = "Health")
    void TakeDamage(float DamageAmount);

    UFUNCTION(BlueprintCallable, Category = "Health")
    void Heal(float HealAmount);

    UFUNCTION(BlueprintPure, Category = "Health")
    float GetHealthPercent() const { return CurrentHealth / MaxHealth; }

    UPROPERTY(BlueprintAssignable, Category = "Health")
    FOnHealthChanged OnHealthChanged;

    UPROPERTY(BlueprintAssignable, Category = "Health")
    FOnDeath OnDeath;

protected:
    virtual void BeginPlay() override;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Health")
    float MaxHealth = 100.f;

private:
    float CurrentHealth;
};
```

```cpp
// HealthComponent.cpp
#include "Components/HealthComponent.h"

UHealthComponent::UHealthComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UHealthComponent::BeginPlay()
{
    Super::BeginPlay();
    CurrentHealth = MaxHealth;
}

void UHealthComponent::TakeDamage(float DamageAmount)
{
    if (CurrentHealth <= 0.f) return;

    CurrentHealth = FMath::Clamp(CurrentHealth - DamageAmount, 0.f, MaxHealth);
    OnHealthChanged.Broadcast(CurrentHealth, MaxHealth);

    if (CurrentHealth <= 0.f)
    {
        OnDeath.Broadcast();
    }
}

void UHealthComponent::Heal(float HealAmount)
{
    CurrentHealth = FMath::Clamp(CurrentHealth + HealAmount, 0.f, MaxHealth);
    OnHealthChanged.Broadcast(CurrentHealth, MaxHealth);
}
```

## Enhanced Input Controller

Player controller wiring the Enhanced Input system (SKILL.md §3).

```cpp
// MyPlayerController.h
UCLASS()
class MYGAME_API AMyPlayerController : public APlayerController
{
    GENERATED_BODY()

protected:
    virtual void SetupInputComponent() override;

    UPROPERTY(EditDefaultsOnly, Category = "Input")
    TObjectPtr<UInputMappingContext> DefaultMappingContext;

    UPROPERTY(EditDefaultsOnly, Category = "Input")
    TObjectPtr<UInputAction> MoveAction;

    UPROPERTY(EditDefaultsOnly, Category = "Input")
    TObjectPtr<UInputAction> JumpAction;

    UPROPERTY(EditDefaultsOnly, Category = "Input")
    TObjectPtr<UInputAction> LookAction;

private:
    void OnMove(const FInputActionValue& Value);
    void OnJump(const FInputActionValue& Value);
    void OnLook(const FInputActionValue& Value);
};

// MyPlayerController.cpp
void AMyPlayerController::SetupInputComponent()
{
    Super::SetupInputComponent();

    if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
        ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
    {
        Subsystem->AddMappingContext(DefaultMappingContext, 0);
    }

    if (UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(InputComponent))
    {
        EIC->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AMyPlayerController::OnMove);
        EIC->BindAction(JumpAction, ETriggerEvent::Started, this, &AMyPlayerController::OnJump);
        EIC->BindAction(LookAction, ETriggerEvent::Triggered, this, &AMyPlayerController::OnLook);
    }
}

void AMyPlayerController::OnMove(const FInputActionValue& Value)
{
    const FVector2D MoveInput = Value.Get<FVector2D>();
    if (APawn* ControlledPawn = GetPawn())
    {
        const FRotator YawRotation(0.f, GetControlRotation().Yaw, 0.f);
        const FVector Forward = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);
        const FVector Right = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);
        ControlledPawn->AddMovementInput(Forward, MoveInput.Y);
        ControlledPawn->AddMovementInput(Right, MoveInput.X);
    }
}
```

## Attribute Set (GAS)

Full attribute set (SKILL.md §4). The body shows two attributes (Health, MaxHealth); this adds Mana. Each attribute repeats the `UPROPERTY` + `ATTRIBUTE_ACCESSORS` + `OnRep_` block.

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

    UPROPERTY(BlueprintReadOnly, ReplicatedUsing = OnRep_Mana, Category = "Attributes")
    FGameplayAttributeData Mana;
    ATTRIBUTE_ACCESSORS(UMyAttributeSet, Mana)

    virtual void PreAttributeChange(const FGameplayAttribute& Attribute, float& NewValue) override;
    virtual void PostGameplayEffectExecute(const FGameplayEffectModCallbackData& Data) override;

    UFUNCTION() void OnRep_Health(const FGameplayAttributeData& OldHealth);
    UFUNCTION() void OnRep_MaxHealth(const FGameplayAttributeData& OldMaxHealth);
    UFUNCTION() void OnRep_Mana(const FGameplayAttributeData& OldMana);

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
};
```
