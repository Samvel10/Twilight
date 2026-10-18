# 03 — C++ gameplay architecture: flight, aim, vishaps, game flow, HUD (UE 5.8, no Blueprint assets)

Date: 2026-10-18. Every engine claim below was checked against the source tree at
`/home/samo/UnrealEngine-5.8`. `E=` = `/home/samo/UnrealEngine-5.8/Engine`. Paths are given with line numbers.
Anything not checked against the source is marked **UNVERIFIED**.

---------------------------------------------------------------------------------------------------

## 0. TL;DR: decisions

| Topic | Decision | Why |
|---|---|---|
| Input | Create `UInputAction` and `UInputMappingContext` at runtime with `NewObject` in the PlayerController, map keys with `MapKey`, and add per-mapping modifiers (`Negate`, `SwizzleAxis`, `DeadZone`). Read state actions by polling (`BindActionValue` + `GetBoundActionValue`). Use event bindings only for mouse look, special and pause. | Verified in the 5.8 source. Epic's own tests create IMCs with `NewObject`. No `.uasset` files are needed. |
| **Required ini** | `DefaultInput.ini`: `DefaultPlayerInputClass=/Script/EnhancedInput.EnhancedPlayerInput` and `DefaultInputComponentClass=/Script/EnhancedInput.EnhancedInputComponent` | The engine default is the **legacy** `UPlayerInput` / `UInputComponent` (`E/Source/Runtime/Engine/Private/UserInterface/InputSettings.cpp:52-53`). Without these lines, every Enhanced Input cast fails. |
| Pawn | `APawn` with a `USphereComponent` root and a custom `UPawnMovementComponent` (`UVahagnFlightMovement`). The flight step is called explicitly from the pawn's Tick. Collision uses `SafeMoveUpdatedComponent` + `SlideAlongSurface`. | We own the whole feel. A sphere root does not change shape when the hero banks or pitches. Sweep and slide use the same engine helpers that `UFloatingPawnMovement` uses, so the hero cannot pass through terrain. `ACharacter` in `MOVE_Flying` is the fallback (see §2.1). |
| Hero mesh | `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple`, single-node animation `MM_Fall_Loop`. The flying pose (lean, bank, bob) is applied to a `VisualRoot` scene component. | `ABP_Unarmed` drives a ground locomotion state machine, so it is wrong for flight. Single-node animation is code-only and verified. |
| Muzzle | Bone `hand_r` (alternate with `hand_l`), read with `GetSocketLocation`. Both bones are verified in `SKM_Manny_Simple`. | The mesh has no weapon socket. Bone names work as socket names. |
| Aim | Trace from the camera through the screen centre, starting at the point on the ray closest to the hero. Aim assist is an analytic cone test against vishap segment spheres. The projectile's direction = (aim point − muzzle). | Shots land where the crosshair is, even with an over-the-shoulder camera offset. |
| Projectile collision | The projectile sphere **blocks only `ECC_WorldStatic`** (terrain and sea) and ignores everything else. Vishap hits are found by an **analytic swept-sphere vs. segment-sphere test**. | The projectile can never hit its owner, no custom channel is needed, and the test is cheap and deterministic. Moving 150+ collision bodies every frame is avoided. |
| Vishap body | N `UStaticMeshComponent`s (engine `/Engine/BasicShapes/Sphere` and `Cone`) with `NoCollision`. They follow a breadcrumb trail left by the head. The head runs steering AI inside the actor (no AIController). | This is robust and needs no assets or navmesh. |
| Game flow | An `AGameModeBase` subclass ticks a phase machine (Intro → Waves → BossIntro → Boss → Victory/Defeat). The timer uses dilated time. Slow motion is timed in real time: `Dt / GetEffectiveTimeDilation()`. | Verified APIs. Timers driven by `FTimerManager` would be stretched by the slow motion. |
| HUD | Text and bars: a **UMG `UUserWidget` built in C++ inside `RebuildWidget()`** (**not** in `NativeConstruct`, see §5.3). Crosshair and off-screen markers: `AHUD::DrawHUD` canvas drawing. | `NativeConstruct` runs **after** the Slate tree has already been built. A tree built there shows nothing until the next rebuild. |
| Armenian font | Build a **runtime `FStandaloneCompositeFont`** in C++. The default typeface is Roboto (Latin and digits). A sub-typeface with Noto Sans Armenian covers U+0530–058F and U+FB13–FB17. | **Noto Sans Armenian has no digits or Latin letters.** `fc-query` shows only `20 2d a0 308 531-556 559-58a 58d-58f 2010 25cc fb13-fb17`, so a timer like "05:32" would render as boxes with Noto alone. The Python import (§5.5) creates a UFont with only one typeface. |

---------------------------------------------------------------------------------------------------

## 1. Enhanced Input fully from C++

### 1.1 Verified facts (5.8 source)

`P=E/Plugins/EnhancedInput/Source/EnhancedInput/Public`

- `UInputAction` is `UCLASS(MinimalAPI, BlueprintType) class UInputAction : public UDataAsset` (`P/InputAction.h:54-55`).
  - `EInputActionValueType ValueType = Boolean;` is public (`InputAction.h:116`).
  - `bool bTriggerWhenPaused` is public (`:92`). It is honoured at `Private/EnhancedPlayerInput.cpp:699`.
  - `bool bConsumeInput = true` (`:96`).
  - `Triggers` and `Modifiers` arrays (`:135`, `:145`).
- `EInputActionValueType { Boolean, Axis1D, Axis2D, Axis3D }` (`P/InputActionValue.h:10-18`).
- `UInputMappingContext::MapKey(const UInputAction*, FKey)` returns `FEnhancedActionKeyMapping&` (`P/InputMappingContext.h:228`). The implementation (`Private/InputMappingContext.cpp:158-162`) calls `RequestRebuildControlMappingsUsingContext(this)` and then `Mappings.Add_GetRef(...)`.
  - **Caution:** the returned reference points into a `TArray`. Use it before the next `MapKey` call, because the array can reallocate.
- `FEnhancedActionKeyMapping::Modifiers` and `Triggers` are public `TArray<TObjectPtr<...>>` (`P/EnhancedActionKeyMapping.h:80,90`). Per-mapping modifiers run **before** the action's own modifiers (`:86`).
- Modifiers, all `UCLASS(NotBlueprintable, MinimalAPI)` with public `UPROPERTY` members:
  - `UInputModifierNegate { bool bX=true, bY=true, bZ=true; }` (`P/InputModifiers.h:252-264`)
  - `UInputModifierSwizzleAxis { EInputAxisSwizzle Order = YXZ; }` (`:411-420`). YXZ moves a 1D key value from X to Y.
  - `UInputModifierDeadZone { LowerThreshold=0.2, UpperThreshold=1, Type=Radial }` (`:169-193`)
  - `UInputModifierScalar` (`:212`)
  - `MinimalAPI` exports `StaticClass()`, so `NewObject<UInputModifierNegate>()` works from the game module.
- `IEnhancedInputSubsystemInterface::AddMappingContext(const UInputMappingContext*, int32 Priority, const FModifyContextOptions& = {})` (`P/EnhancedInputSubsystemInterface.h:265`). Also `ClearAllMappings()` (`:256`) and `RequestRebuildControlMappings` (`:336`). `UEnhancedInputLocalPlayerSubsystem` implements the interface (`P/EnhancedInputSubsystems.h:21`).
- `UEnhancedInputComponent`:
  - `BindAction(const UInputAction*, ETriggerEvent, UserClass*, Func)` (`P/EnhancedInputComponent.h:482`)
  - `BindActionValue(const UInputAction*)` (`:553`)
  - `FInputActionValue GetBoundActionValue(const UInputAction*) const` (`:596`)
- `ETriggerEvent { Triggered, Started, Ongoing, Canceled, Completed }` (`P/InputTriggers.h:37-55`).
- Runtime creation is a supported pattern. Epic's tests do `NewObject<UInputMappingContext>()` (`E/Plugins/EnhancedInput/Source/InputEditor/Private/Tests/InputSystemTest.cpp:395`, `InputTestFramework.cpp:84`).
- Keys exist in `E/Source/Runtime/InputCore/Classes/InputCoreTypes.h`:
  - `Mouse2D` :351
  - `Gamepad_Left2D` :500, `Gamepad_Right2D` :503
  - `Gamepad_LeftThumbstick` :509
  - `Gamepad_Special_Left` :511, `Gamepad_Special_Right` :515
  - `Gamepad_FaceButton_Bottom` :516, `_Right` :517, `_Left` :518
  - `Gamepad_LeftShoulder` :520, `Gamepad_RightShoulder` :521
  - `Gamepad_LeftTrigger` :522, `Gamepad_RightTrigger` :523
- `APlayerController::SetupInputComponent()` is virtual (`E/Source/Runtime/Engine/Classes/GameFramework/PlayerController.h:2011`). The PC ticks while the game is paused (`Private/PlayerController.cpp:204`: `PrimaryActorTick.bTickEvenWhenPaused = true`).
- **Look sign caveat.** `APlayerController::AddPitchInput` multiplies by `InputPitchScale_DEPRECATED` (BaseGame.ini:187 `InputPitchScale=-2.5`) when `bEnableLegacyInputScales` is true (PlayerController.cpp:6080-6083). The TP template sets `bEnableLegacyInputScales=True` (`Templates/TP_ThirdPerson/Config/DefaultInput.ini:69`).
  - To avoid the inverted ×2.5 surprise, **do not use `AddControllerPitchInput`**. Keep our own `AimYaw`/`AimPitch` and call `SetControlRotation` (§2).

### 1.2 Config (project `Config/DefaultInput.ini`): mandatory

```ini
[/Script/Engine.InputSettings]
DefaultPlayerInputClass=/Script/EnhancedInput.EnhancedPlayerInput
DefaultInputComponentClass=/Script/EnhancedInput.EnhancedInputComponent
bEnableLegacyInputScales=False
bCaptureMouseOnLaunch=True
DefaultViewportMouseCaptureMode=CapturePermanently_IncludingInitialMouseDown
```
(Template reference: `Templates/TP_ThirdPerson/Config/DefaultInput.ini:81-82`.)

> **Esc in PIE stops PIE.** The live demo should run as `-game` (standalone), where Esc reaches our action.
> **P** is also mapped to pause as a fallback.

### 1.3 Code: `AVahagnPlayerController`

The PC owns the actions, the IMC and the bindings. The pawn polls the PC. Benefits:
- No ordering problem between possession and `SetupPlayerInputComponent`.
- The `UPROPERTY(Transient)` members keep the runtime objects alive against GC.
- `SetupInputComponent` runs before `BeginPlay` (from `InitInputSystem`), so `BuildInputAssets()` is idempotent and called from both.

```cpp
// Player/VahagnPlayerController.h
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "InputActionValue.h"
#include "VahagnPlayerController.generated.h"

class UInputAction;
class UInputMappingContext;

UCLASS()
class TWILIGHT_API AVahagnPlayerController : public APlayerController
{
	GENERATED_BODY()
public:
	virtual void SetupInputComponent() override;
	virtual void BeginPlay() override;

	// Polled by the pawn every tick.
	FVector2D GetMoveInput() const;      // X = right, Y = forward, each -1..1
	FVector2D GetLookRateInput() const;  // gamepad right stick, -1..1, multiply by deg/s
	float     GetVerticalInput() const;  // +1 up, -1 down
	bool      IsBoostHeld() const;
	bool      IsFireHeld() const;

private:
	void BuildInputAssets();
	FInputActionValue Poll(const UInputAction* Action) const;

	void OnLook(const FInputActionValue& Value);      // mouse delta, Triggered
	void OnSpecial(const FInputActionValue& Value);   // Started
	void OnPause(const FInputActionValue& Value);     // Started

	UPROPERTY(Transient) TObjectPtr<UInputMappingContext> IMC;
	UPROPERTY(Transient) TObjectPtr<UInputAction> IA_Move;
	UPROPERTY(Transient) TObjectPtr<UInputAction> IA_Look;
	UPROPERTY(Transient) TObjectPtr<UInputAction> IA_LookRate;
	UPROPERTY(Transient) TObjectPtr<UInputAction> IA_Vertical;
	UPROPERTY(Transient) TObjectPtr<UInputAction> IA_Boost;
	UPROPERTY(Transient) TObjectPtr<UInputAction> IA_Fire;
	UPROPERTY(Transient) TObjectPtr<UInputAction> IA_Special;
	UPROPERTY(Transient) TObjectPtr<UInputAction> IA_Pause;
};
```

```cpp
// Player/VahagnPlayerController.cpp
#include "Player/VahagnPlayerController.h"
#include "Player/VahagnPawn.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Engine/LocalPlayer.h"

static UInputAction* MakeAction(UObject* Outer, const TCHAR* Name, EInputActionValueType Type)
{
	UInputAction* A = NewObject<UInputAction>(Outer, FName(Name));
	A->ValueType = Type;
	return A;
}

void AVahagnPlayerController::BuildInputAssets()
{
	if (IMC) { return; }

	IA_Move     = MakeAction(this, TEXT("IA_Move"),     EInputActionValueType::Axis2D);
	IA_Look     = MakeAction(this, TEXT("IA_Look"),     EInputActionValueType::Axis2D);
	IA_LookRate = MakeAction(this, TEXT("IA_LookRate"), EInputActionValueType::Axis2D);
	IA_Vertical = MakeAction(this, TEXT("IA_Vertical"), EInputActionValueType::Axis1D);
	IA_Boost    = MakeAction(this, TEXT("IA_Boost"),    EInputActionValueType::Boolean);
	IA_Fire     = MakeAction(this, TEXT("IA_Fire"),     EInputActionValueType::Boolean);
	IA_Special  = MakeAction(this, TEXT("IA_Special"),  EInputActionValueType::Boolean);
	IA_Pause    = MakeAction(this, TEXT("IA_Pause"),    EInputActionValueType::Boolean);
	IA_Pause->bTriggerWhenPaused = true;   // InputAction.h:92, honoured in EnhancedPlayerInput.cpp:699

	IMC = NewObject<UInputMappingContext>(this, TEXT("IMC_Vahagn"));

	// Each helper uses the mapping reference immediately (MapKey returns a ref into a TArray).
	auto Map = [this](UInputAction* A, const FKey& K) { IMC->MapKey(A, K); };
	auto MapNeg = [this](UInputAction* A, const FKey& K)
	{
		FEnhancedActionKeyMapping& M = IMC->MapKey(A, K);
		M.Modifiers.Add(NewObject<UInputModifierNegate>(IMC));
	};
	auto MapSwz = [this](UInputAction* A, const FKey& K, bool bNegate)
	{
		FEnhancedActionKeyMapping& M = IMC->MapKey(A, K);
		M.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(IMC));      // YXZ: X -> Y
		if (bNegate) { M.Modifiers.Add(NewObject<UInputModifierNegate>(IMC)); }
	};
	auto MapStick = [this](UInputAction* A, const FKey& K, float Dead)
	{
		FEnhancedActionKeyMapping& M = IMC->MapKey(A, K);
		UInputModifierDeadZone* DZ = NewObject<UInputModifierDeadZone>(IMC);
		DZ->LowerThreshold = Dead;
		DZ->Type = EDeadZoneType::Radial;
		M.Modifiers.Add(DZ);
	};

	// Move (2D): X = strafe right, Y = forward
	Map   (IA_Move, EKeys::D);
	MapNeg(IA_Move, EKeys::A);
	MapSwz(IA_Move, EKeys::W, false);
	MapSwz(IA_Move, EKeys::S, true);
	MapStick(IA_Move, EKeys::Gamepad_Left2D, 0.18f);

	// Look: mouse delta (event-driven) and gamepad rate (polled)
	Map(IA_Look, EKeys::Mouse2D);                  // +Y = mouse moved forward/up
	MapStick(IA_LookRate, EKeys::Gamepad_Right2D, 0.15f);

	// Ascend / descend (1D)
	Map   (IA_Vertical, EKeys::SpaceBar);
	MapNeg(IA_Vertical, EKeys::LeftControl);
	MapNeg(IA_Vertical, EKeys::C);
	Map   (IA_Vertical, EKeys::Gamepad_FaceButton_Bottom);   // A / Cross
	MapNeg(IA_Vertical, EKeys::Gamepad_FaceButton_Right);    // B / Circle

	// Buttons
	Map(IA_Boost,   EKeys::LeftShift);
	Map(IA_Boost,   EKeys::Gamepad_LeftTrigger);
	Map(IA_Boost,   EKeys::Gamepad_LeftThumbstick);
	Map(IA_Fire,    EKeys::LeftMouseButton);
	Map(IA_Fire,    EKeys::Gamepad_RightTrigger);
	Map(IA_Special, EKeys::Q);
	Map(IA_Special, EKeys::RightMouseButton);
	Map(IA_Special, EKeys::Gamepad_RightShoulder);
	Map(IA_Pause,   EKeys::Escape);
	Map(IA_Pause,   EKeys::P);
	Map(IA_Pause,   EKeys::Gamepad_Special_Right);           // Start / Options
}

void AVahagnPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	BuildInputAssets();

	UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(InputComponent);
	if (!EIC)
	{
		UE_LOG(LogTemp, Error, TEXT("InputComponent is not UEnhancedInputComponent - fix DefaultInput.ini"));
		return;
	}
	// Polled state (value is 0 when idle, so there are no stale values after release)
	EIC->BindActionValue(IA_Move);
	EIC->BindActionValue(IA_LookRate);
	EIC->BindActionValue(IA_Vertical);
	EIC->BindActionValue(IA_Boost);
	EIC->BindActionValue(IA_Fire);
	// Events
	EIC->BindAction(IA_Look,    ETriggerEvent::Triggered, this, &AVahagnPlayerController::OnLook);
	EIC->BindAction(IA_Special, ETriggerEvent::Started,   this, &AVahagnPlayerController::OnSpecial);
	EIC->BindAction(IA_Pause,   ETriggerEvent::Started,   this, &AVahagnPlayerController::OnPause);
}

void AVahagnPlayerController::BeginPlay()
{
	Super::BeginPlay();
	BuildInputAssets();
	if (UEnhancedInputLocalPlayerSubsystem* Sub =
	        ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		Sub->ClearAllMappings();
		Sub->AddMappingContext(IMC, 0);
	}
	SetInputMode(FInputModeGameOnly());
	bShowMouseCursor = false;
}

FInputActionValue AVahagnPlayerController::Poll(const UInputAction* A) const
{
	const UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(InputComponent);
	return (EIC && A) ? EIC->GetBoundActionValue(A) : FInputActionValue();
}
FVector2D AVahagnPlayerController::GetMoveInput() const     { return Poll(IA_Move).Get<FVector2D>(); }
FVector2D AVahagnPlayerController::GetLookRateInput() const { return Poll(IA_LookRate).Get<FVector2D>(); }
float     AVahagnPlayerController::GetVerticalInput() const { return FMath::Clamp(Poll(IA_Vertical).Get<float>(), -1.f, 1.f); }
bool      AVahagnPlayerController::IsBoostHeld() const      { return Poll(IA_Boost).Get<bool>(); }
bool      AVahagnPlayerController::IsFireHeld() const       { return Poll(IA_Fire).Get<bool>(); }

void AVahagnPlayerController::OnLook(const FInputActionValue& V)
{
	if (AVahagnPawn* P = GetPawn<AVahagnPawn>()) { P->AddLookDelta(V.Get<FVector2D>()); }
}
void AVahagnPlayerController::OnSpecial(const FInputActionValue&)
{
	if (AVahagnPawn* P = GetPawn<AVahagnPawn>()) { P->TriggerSpecial(); }
}
void AVahagnPlayerController::OnPause(const FInputActionValue&)
{
	SetPause(!IsPaused());   // HUD polls IsPaused() to show or hide the pause panel
}
```

---------------------------------------------------------------------------------------------------

## 2. Flight model that cannot go out of control

### 2.1 Pawn type

**Recommended: `APawn` + `USphereComponent` root + `UVahagnFlightMovement : UPawnMovementComponent`.**
The pawn's `Tick` calls `Flight->StepFlight(...)` explicitly, and the component's own tick is disabled. This gives a deterministic order: input → velocity → move → visuals → camera → weapons.

How collision stays safe:
- `UMovementComponent::SafeMoveUpdatedComponent(Delta, Quat, bSweep, Hit)` resolves penetration (`E/Source/Runtime/Engine/Classes/GameFramework/MovementComponent.h:316`).
- `SlideAlongSurface(Delta, Time, Normal, Hit, bHandleImpact)` (`:362`).
- `HandleImpact` (`:272`).
- This is exactly what `UFloatingPawnMovement::TickComponent` does (`E/Source/Runtime/Engine/Private/FloatingPawnMovement.cpp:23-63`).

**Why not `ACharacter` + `MOVE_Flying`?**
- `PhysFlying` (`Private/Components/CharacterMovementComponent.cpp:4429-4487`) calls `CalcVelocity` with `Friction = 0.5 * PhysicsVolume->FluidFriction` (`:4444`).
- `CalcVelocity` (`:3863`) turns velocity toward the acceleration direction using that friction, which is about 0.15/s by default. That gives a "drifty, ice-like" turn unless friction is overridden.
- It also adds step-up logic and a vertical capsule that does not match a horizontal flying body.
- It is a fine fallback (the sweep and slide are equally safe), but tuning the feel is harder.

### 2.2 Control scheme ("camera aims, body follows")

- Mouse or right stick rotates the **aim** (`AimYaw`, `AimPitch`). `AimPitch` is clamped to [-70°, +65°].
- `W`/`S` fly along the aim direction. The aim pitch is scaled by 0.9 so level flight is easy.
- `A`/`D` strafe horizontally.
- `Space`/`Ctrl` move along world up/down.
- With no input, the hero eases to a **hover** with a slight bob. Speed never builds up uncontrollably and there are no loops. The hero can always stop.

### 2.3 Exact algorithm (per frame, `Dt` clamped to ≤ 1/20 s)

```
Wish   = Fwd(AimPitch*0.9, AimYaw)*Move.Y + RightYaw*Move.X + Up*Vert     (|Wish| ≤ 1)

// 1. Soft cylinder bound. It never hard-stops.
d      = horizontal distance from ArenaCenter
if d > R - M:
    t     = clamp((d - (R-M)) / M, 0, 1.5)
    out   = horizontal unit vector away from centre
    Wish -= out * max(0, Wish·out) * min(t,1)    // cancel the outward intent progressively
    Wish -= out * t² * 0.8                        // gentle inward steer, works with zero input

// 2. Altitude band. Floor = max(SeaZ, terrain under hero) + MinAlt (one down-trace per frame).
if z < Floor + Ma:  t = clamp((Floor+Ma - z)/Ma, 0, 2);  if Wish.z<0: Wish.z *= 1-min(t,1);  Wish.z += 0.7t
if z > MaxZ - Ma:   t = clamp((z-(MaxZ-Ma))/Ma, 0, 2);  if Wish.z>0: Wish.z *= 1-min(t,1);  Wish.z -= 0.7t
Wish = ClampToMaxSize(Wish, 1)

// 3. Velocity: constant-rate approach toward the target.
Max    = Boost ? BoostSpeed : CruiseSpeed            (back-pedal is ×0.6)
Target = Wish * Max
Rate   = (|input| > 0.05) ? (Boost ? BoostAccel : Accel) : Decel
Vel   += ClampToMaxSize(Target - Vel, Rate * Dt)

// 4. Terrain look-ahead (sphere sweep along Vel * 0.6 s, ECC_WorldStatic)
if hit:  u = 1 - Hit.Time
         Vel += normalize(N + 0.5*Up) * AvoidAccel * u * Dt
         if Vel·N < 0: Vel -= N * (Vel·N) * min(1, 6u*Dt)   // bleed the into-surface speed

// 5. Move: SafeMoveUpdatedComponent(Vel*Dt, sweep) -> if blocked: HandleImpact + SlideAlongSurface,
//    Vel = VectorPlaneProject(Vel, Hit.Normal)
// 6. Hard safety net: if z < SeaZ + 150 -> snap z to SeaZ + 150 and Vel.z = max(Vel.z, 300)
```

Visual layer (actor yaw plus `VisualRoot` pitch and roll). The collision sphere never rotates, apart from yaw, which a sphere does not care about.

```
ActorYaw   = RInterpTo(ActorYaw, AimYaw, Dt, 10)
YawRate    = smoothed (ΔActorYaw / Dt)          deg/s
FwdA       = clamp( (Vel · ActorFwd) / CruiseSpeed, 0, 1 )
ClimbDeg   = asin(Vel.z / |Vel|) in degrees (0 when |Vel| < 200)
BodyPitch  = clamp( -75*FwdA + 0.6*ClimbDeg*FwdA , -110, 15 )   // lies horizontal at speed, dives head-first
BodyRoll   = clamp( 0.12*YawRate + 22*Move.X , -50, 50 )        // +roll = right wing down (bank right)
VisualRoot.RelativeRotation = RInterpTo(..., (BodyPitch, 0, BodyRoll), Dt, 6)
Hover bob  = VisualRoot.RelativeLocation.Z = sin(t*2.1) * 10 * (1 - FwdA)
```

Signs are derived from the `FRotationMatrix` convention:
- Pitch < 0 moves the up axis toward +X, so the head goes forward.
- Roll > 0 moves the right axis toward −Z.
- **Check visually in the first test run.** The `BankSign` and `LeanSign` tunables exist for that.

Camera (spring arm attached to the **root**, not to `VisualRoot`, so it never rolls):

| Property (`Classes/GameFramework/SpringArmComponent.h`) | Value |
|---|---|
| `TargetArmLength` (:25) | 560 (→ 700 while boosting, FInterpTo 4) |
| `SocketOffset` (:29) | (0, 70, 70): over the right shoulder |
| `bUsePawnControlRotation` | true (we set ControlRotation each tick) |
| `bEnableCameraLag` (:76) / `CameraLagSpeed` (:101) | true / 10 |
| `CameraLagMaxDistance` (:113) | 300 (stops the camera falling far behind while boosting) |
| `bEnableCameraRotationLag` (:83) / `CameraRotationLagSpeed` (:105) | true / **22** (high, so aiming is not floaty) |
| `bDoCollisionTest` (:45) / `ProbeSize` (:37) / `ProbeChannel` (:41) | true / 16 / `ECC_Camera` |
| `UCameraComponent::SetFieldOfView` (`Classes/Camera/CameraComponent.h:46`) | 88° → 102° while boosting (FInterpTo 5) |

Camera shake is procedural "trauma": `Trauma` (0..1) decays at 1.5/s. Offset = `FMath::PerlinNoise1D` (`Core/Public/Math/UnrealMathUtility.h:2463`) × Trauma² on the camera's relative rotation (±2.5°) and location. No `UCameraShakeBase` asset is needed.

### 2.4 Code: flight movement component

```cpp
// Player/VahagnFlightMovement.h
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/PawnMovementComponent.h"
#include "VahagnFlightMovement.generated.h"

UCLASS()
class TWILIGHT_API UVahagnFlightMovement : public UPawnMovementComponent
{
	GENERATED_BODY()
public:
	UVahagnFlightMovement();

	/** WishDir: world space, length <= 1. Call once per frame from the pawn's Tick. */
	void StepFlight(const FVector& WishDir, bool bBoost, bool bHasInput, float DeltaTime);

	UPROPERTY(EditAnywhere, Category="Flight") float CruiseSpeed  = 2400.f;   // cm/s
	UPROPERTY(EditAnywhere, Category="Flight") float BoostSpeed   = 4800.f;
	UPROPERTY(EditAnywhere, Category="Flight") float Accel        = 5200.f;   // cm/s^2
	UPROPERTY(EditAnywhere, Category="Flight") float BoostAccel   = 9000.f;
	UPROPERTY(EditAnywhere, Category="Flight") float Decel        = 3400.f;
	UPROPERTY(EditAnywhere, Category="Bounds") FVector ArenaCenter = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, Category="Bounds") float ArenaRadius  = 60000.f;
	UPROPERTY(EditAnywhere, Category="Bounds") float BoundsMargin = 10000.f;
	UPROPERTY(EditAnywhere, Category="Bounds") float SeaLevelZ    = 0.f;
	UPROPERTY(EditAnywhere, Category="Bounds") float MinAltitude  = 500.f;    // above max(sea, terrain)
	UPROPERTY(EditAnywhere, Category="Bounds") float MaxAltitude  = 25000.f;  // absolute Z
	UPROPERTY(EditAnywhere, Category="Bounds") float AltMargin    = 1500.f;
	UPROPERTY(EditAnywhere, Category="Avoid")  float LookAheadTime = 0.6f;
	UPROPERTY(EditAnywhere, Category="Avoid")  float AvoidAccel    = 14000.f;
	UPROPERTY(EditAnywhere, Category="Avoid")  float AvoidRadius   = 120.f;

private:
	float SampleFloorZ(const FVector& Loc) const;
};
```

```cpp
// Player/VahagnFlightMovement.cpp
#include "Player/VahagnFlightMovement.h"
#include "Engine/World.h"
#include "CollisionQueryParams.h"

UVahagnFlightMovement::UVahagnFlightMovement()
{
	PrimaryComponentTick.bCanEverTick = false;   // driven by AVahagnPawn::Tick
}

float UVahagnFlightMovement::SampleFloorZ(const FVector& Loc) const
{
	float Floor = SeaLevelZ;
	FHitResult H;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(VahagnFloor), false, GetOwner());
	if (GetWorld()->LineTraceSingleByChannel(H, Loc + FVector(0,0,200), Loc - FVector(0,0,50000),
	                                         ECC_WorldStatic, Q))
	{
		Floor = FMath::Max(Floor, (float)H.ImpactPoint.Z);
	}
	return Floor;
}

void UVahagnFlightMovement::StepFlight(const FVector& InWish, bool bBoost, bool bHasInput, float Dt)
{
	if (!UpdatedComponent || !GetWorld() || Dt <= 0.f) { return; }
	Dt = FMath::Min(Dt, 1.f / 20.f);

	const FVector Loc = UpdatedComponent->GetComponentLocation();
	FVector Wish = InWish.GetClampedToMaxSize(1.f);

	// 1) soft cylinder bounds
	FVector Off = Loc - ArenaCenter; Off.Z = 0.f;
	const float D = Off.Size();
	const float Inner = ArenaRadius - BoundsMargin;
	if (D > Inner && D > KINDA_SMALL_NUMBER)
	{
		const FVector Out = Off / D;
		const float T = FMath::Clamp((D - Inner) / BoundsMargin, 0.f, 1.5f);
		const float OutWish = FVector::DotProduct(Wish, Out);
		if (OutWish > 0.f) { Wish -= Out * OutWish * FMath::Min(T, 1.f); }
		Wish -= Out * (T * T * 0.8f);
	}

	// 2) altitude band (sea + terrain floor, absolute ceiling)
	const float Floor = SampleFloorZ(Loc) + MinAltitude;
	if (Loc.Z < Floor + AltMargin)
	{
		const float T = FMath::Clamp((Floor + AltMargin - Loc.Z) / AltMargin, 0.f, 2.f);
		if (Wish.Z < 0.f) { Wish.Z *= 1.f - FMath::Min(T, 1.f); }
		Wish.Z += 0.7f * T;
	}
	if (Loc.Z > MaxAltitude - AltMargin)
	{
		const float T = FMath::Clamp((Loc.Z - (MaxAltitude - AltMargin)) / AltMargin, 0.f, 2.f);
		if (Wish.Z > 0.f) { Wish.Z *= 1.f - FMath::Min(T, 1.f); }
		Wish.Z -= 0.7f * T;
	}
	Wish = Wish.GetClampedToMaxSize(1.f);

	// 3) velocity toward target at a bounded rate
	const float MaxSpd = bBoost ? BoostSpeed : CruiseSpeed;
	const FVector Target = Wish * MaxSpd;
	const float Rate = bHasInput ? (bBoost ? BoostAccel : Accel) : Decel;
	Velocity += (Target - Velocity).GetClampedToMaxSize(Rate * Dt);

	// 4) terrain look-ahead avoidance
	const FVector Ahead = Velocity * LookAheadTime;
	if (Ahead.SizeSquared() > 100.f)
	{
		FHitResult H;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(VahagnAhead), false, GetOwner());
		if (GetWorld()->SweepSingleByChannel(H, Loc, Loc + Ahead, FQuat::Identity, ECC_WorldStatic,
		                                     FCollisionShape::MakeSphere(AvoidRadius), Q) && !H.bStartPenetrating)
		{
			const float U = 1.f - H.Time;
			const FVector N = H.ImpactNormal;
			Velocity += (N + FVector::UpVector * 0.5f).GetSafeNormal() * AvoidAccel * U * Dt;
			const float Into = FVector::DotProduct(Velocity, N);
			if (Into < 0.f) { Velocity -= N * Into * FMath::Min(1.f, 6.f * U * Dt); }
		}
	}

	// 5) swept move + slide (same helpers as UFloatingPawnMovement)
	const FVector Delta = Velocity * Dt;
	if (!Delta.IsNearlyZero(1e-4f))
	{
		FHitResult Hit(1.f);
		SafeMoveUpdatedComponent(Delta, UpdatedComponent->GetComponentQuat(), true, Hit);
		if (Hit.IsValidBlockingHit())
		{
			HandleImpact(Hit, Dt, Delta);
			SlideAlongSurface(Delta, 1.f - Hit.Time, Hit.Normal, Hit, true);
			Velocity = FVector::VectorPlaneProject(Velocity, Hit.Normal);
		}
	}

	// 6) hard safety net: never under the sea
	FVector L2 = UpdatedComponent->GetComponentLocation();
	if (L2.Z < SeaLevelZ + 150.f)
	{
		L2.Z = SeaLevelZ + 150.f;
		UpdatedComponent->SetWorldLocation(L2, false, nullptr, ETeleportType::TeleportPhysics);
		Velocity.Z = FMath::Max(Velocity.Z, 300.f);
	}
	UpdateComponentVelocity();
}
```

### 2.5 Manny assets (verified on disk) and how to pose the hero

Feature-pack source: `/home/samo/UnrealEngine-5.8/Templates/TemplateResources/High/Characters/Content/Mannequins/`.
**The assets reference each other as `/Game/Characters/Mannequins/...`** (strings inside `SKM_Manny_Simple.uasset` and `ABP_Unarmed.uasset`). They must therefore be copied to `<Project>/Content/Characters/Mannequins/` unchanged.

| Asset | Object path |
|---|---|
| Skeletal mesh | `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple` (also `SKM_Quinn_Simple`) |
| Skeleton | `/Game/Characters/Mannequins/Meshes/SK_Mannequin` |
| Materials | `/Game/Characters/Mannequins/Materials/Manny/MI_Manny_01_New`, `MI_Manny_02_New` |
| Fall loop (flying base pose) | `/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Fall_Loop` |
| Others | `Unarmed/MM_Idle`, `Unarmed/Jump/MM_Jump`, `MM_Land`, `MM_Dash`, `MM_WallJump`; `Unarmed/Attack/MM_Attack_01..03`, `MM_ChargedAttack`; `Death/MM_Death_Front_01..03`, `MM_Death_Back_01`, `MM_Death_Left_01`, `MM_Death_Right_01` |
| Anim BP (do **not** use for flight) | `Unarmed/ABP_Unarmed`: a ground locomotion state machine (`BS_Idle_Walk_Run`, `MM_Fall_Loop`, `MM_Jump`, `MM_Land`, `CR_Mannequin_FootIK`) |

There is **no** `MM_Fall_Loop` under `Templates/TemplateResources/Standard/...`. The older UE4 `ThirdPerson*` anims under `High/Mannequin` use the old UE4 skeleton and do not fit `SKM_Manny`.

Bones verified as strings in `SKM_Manny_Simple.uasset`: `root, pelvis, spine_01..05, neck_01, head, upperarm_l/r, lowerarm_l/r, hand_l, hand_r, ik_hand_r, ik_hand_gun`. The only real sockets in `SK_Mannequin` are `foot_l_Socket` and `foot_r_Socket`. Use **bone names** with `GetSocketLocation(TEXT("hand_r"))`; this works because `USkinnedMeshComponent::GetSocketTransform` resolves bone names (`Classes/Components/SkinnedMeshComponent.h:1360`).

**Tier 1 (verified, use first): single-node animation.**
- `USkeletalMeshComponent::SetAnimationMode(EAnimationMode::AnimationSingleNode)` (`Classes/Components/SkeletalMeshComponent.h:1246`)
- `PlayAnimation(UAnimationAsset*, bool bLooping)` (`:1258`)
- `SetPlayRate(float)` (`:1321`)

Play `MM_Fall_Loop` at rate 0.55 while hovering and 0.9 at speed. The flight look comes from the `VisualRoot` pitch, roll and bob. Mesh offset inside `VisualRoot`:
- Relative location (0, 0, −90).
- Relative rotation yaw −90. Manny faces +Y. This matches the template BP convention: the template sets the mesh in the BP; the C++ comment is at `TP_ThirdPersonCharacter.cpp` after the camera creation.

Tier 2 (optional polish, more code):
- **(a)** Hide a second skeletal mesh that plays the anim. Use a visible `UPoseableMeshComponent`:
  - `CopyPoseFromSkeletalComponent` (`Classes/Components/PoseableMeshComponent.h:61`), then
  - `SetBoneRotationByName(TEXT("upperarm_r"), Rot, EBoneSpaces::WorldSpace)` (`:40`) to point the casting arm at the aim point while firing.
- **(b)** A C++ `UAnimInstance` whose `FAnimInstanceProxy` overrides `virtual bool Evaluate(FPoseContext&)` (`Public/Animation/AnimInstanceProxy.h:659`).
  - Native `Evaluate` is called instead of the node graph (`Private/Animation/AnimInstanceProxy.cpp:1447-1451`). This is the same mechanism `FAnimSingleNodeInstanceProxy` uses (`AnimSingleNodeInstanceProxy.cpp:44-49`).
  - Sample two sequences with `UAnimSequence::GetAnimationPose(FAnimationPoseData&, const FAnimExtractContext&)` (`Classes/Animation/AnimSequence.h:427`; `FAnimExtractContext(double Time, bool bRootMotion, FDeltaTimeRecord, bool bLooping)` at `AnimationAsset.h:303`).
  - Blend with `FAnimationRuntime::BlendTwoPosesTogether(const FAnimationPoseData&, const FAnimationPoseData&, float, FAnimationPoseData&)` (`Public/AnimationRuntime.h:301`).
  - Fall-loop plus a `MM_Attack_01` overlay with a real cross-fade. The signatures are verified; **runtime behaviour is UNVERIFIED**, so do this only after Tier 1 works.

### 2.6 Code: pawn

```cpp
// Player/VahagnPawn.h
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "VahagnPawn.generated.h"

class USphereComponent; class USkeletalMeshComponent; class USpringArmComponent;
class UCameraComponent; class UVahagnFlightMovement; class UAnimSequence; class AFireBolt;

UCLASS()
class TWILIGHT_API AVahagnPawn : public APawn
{
	GENERATED_BODY()
public:
	AVahagnPawn();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual UPawnMovementComponent* GetMovementComponent() const override;

	void AddLookDelta(const FVector2D& MouseDelta);
	void TriggerSpecial();
	void ApplyPlayerDamage(float Amount, const FVector& FromWorld);
	void AddTrauma(float Amount) { Trauma = FMath::Clamp(Trauma + Amount, 0.f, 1.f); }

	float GetHP() const { return HP; }
	float GetMaxHP() const { return MaxHP; }
	float GetSpecialCooldown01() const { return SpecialCooldown / SpecialCooldownMax; }
	bool  IsDead() const { return HP <= 0.f; }
	FVector ComputeAimPoint(USceneComponent*& OutHomingTarget) const;

	UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> Collision;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> VisualRoot;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USpringArmComponent> Boom;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UVahagnFlightMovement> Flight;

	UPROPERTY(EditAnywhere, Category="Aim") float MouseSensitivity = 0.12f;   // deg per mouse count
	UPROPERTY(EditAnywhere, Category="Aim") float PadYawRate = 140.f;         // deg/s
	UPROPERTY(EditAnywhere, Category="Aim") float PadPitchRate = 100.f;
	UPROPERTY(EditAnywhere, Category="Aim") float AimAssistDeg = 3.5f;        // gamepad: 6
	UPROPERTY(EditAnywhere, Category="Fire") float FireInterval = 0.14f;
	UPROPERTY(EditAnywhere, Category="Fire") float SpecialCooldownMax = 8.f;
	UPROPERTY(EditAnywhere, Category="Visual") float BankSign = 1.f;          // flip if banking looks inverted
	UPROPERTY(EditAnywhere, Category="Visual") float LeanSign = 1.f;

private:
	void UpdateVisuals(float Dt, const FVector2D& Move);
	void UpdateCamera(float Dt, bool bBoost);
	void TickWeapons(float Dt, bool bFireHeld);
	void FireBolt();

	UPROPERTY() TObjectPtr<UAnimSequence> FlyAnim;
	float AimYaw = 0.f, AimPitch = 0.f;
	float PrevActorYaw = 0.f, SmoothedYawRate = 0.f;
	float FireCooldown = 0.f, SpecialCooldown = 0.f;
	float HP = 100.f, MaxHP = 100.f, Trauma = 0.f, TimeAcc = 0.f;
	bool  bRightHand = true;
	bool  bBoostingVisual = false;
};
```

```cpp
// Player/VahagnPawn.cpp
#include "Player/VahagnPawn.h"
#include "Player/VahagnFlightMovement.h"
#include "Player/VahagnPlayerController.h"
#include "Combat/FireBolt.h"
#include "Enemies/VishapSubsystem.h"
#include "Components/SphereComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "UObject/ConstructorHelpers.h"

AVahagnPawn::AVahagnPawn()
{
	PrimaryActorTick.bCanEverTick = true;
	AutoPossessPlayer = EAutoReceiveInput::Disabled;   // the GameMode spawns and possesses it

	Collision = CreateDefaultSubobject<USphereComponent>(TEXT("Collision"));
	Collision->InitSphereRadius(60.f);
	Collision->SetCollisionProfileName(TEXT("Pawn"));    // BaseEngine.ini:3110
	RootComponent = Collision;

	VisualRoot = CreateDefaultSubobject<USceneComponent>(TEXT("VisualRoot"));
	VisualRoot->SetupAttachment(Collision);

	Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(VisualRoot);
	Body->SetRelativeLocationAndRotation(FVector(0, 0, -90), FRotator(0, -90, 0));
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> MannyMesh(
		TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	if (MannyMesh.Succeeded()) { Body->SetSkeletalMesh(MannyMesh.Object); }
	static ConstructorHelpers::FObjectFinder<UAnimSequence> FallLoop(
		TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Fall_Loop.MM_Fall_Loop"));
	if (FallLoop.Succeeded()) { FlyAnim = FallLoop.Object; }

	Boom = CreateDefaultSubobject<USpringArmComponent>(TEXT("Boom"));
	Boom->SetupAttachment(Collision);                 // root, so the camera never rolls with the body
	Boom->TargetArmLength = 560.f;
	Boom->SocketOffset = FVector(0.f, 70.f, 70.f);
	Boom->bUsePawnControlRotation = true;
	Boom->bEnableCameraLag = true;          Boom->CameraLagSpeed = 10.f;   Boom->CameraLagMaxDistance = 300.f;
	Boom->bEnableCameraRotationLag = true;  Boom->CameraRotationLagSpeed = 22.f;
	Boom->bDoCollisionTest = true;          Boom->ProbeSize = 16.f;        Boom->ProbeChannel = ECC_Camera;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Boom, USpringArmComponent::SocketName);
	Camera->bUsePawnControlRotation = false;
	Camera->SetFieldOfView(88.f);

	Flight = CreateDefaultSubobject<UVahagnFlightMovement>(TEXT("Flight"));
	Flight->UpdatedComponent = Collision;

	bUseControllerRotationYaw = bUseControllerRotationPitch = bUseControllerRotationRoll = false;
}

UPawnMovementComponent* AVahagnPawn::GetMovementComponent() const { return Flight; }

void AVahagnPawn::BeginPlay()
{
	Super::BeginPlay();
	AimYaw = PrevActorYaw = GetActorRotation().Yaw;
	if (FlyAnim)
	{
		Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		Body->PlayAnimation(FlyAnim, true);
		Body->SetPlayRate(0.6f);
	}
}

void AVahagnPawn::AddLookDelta(const FVector2D& D)
{
	AimYaw   += D.X * MouseSensitivity;
	AimPitch  = FMath::Clamp(AimPitch + D.Y * MouseSensitivity, -70.f, 65.f);   // mouse up = look up
}

void AVahagnPawn::Tick(float Dt)
{
	Super::Tick(Dt);
	TimeAcc += Dt;
	AVahagnPlayerController* PC = GetController<AVahagnPlayerController>();
	FVector2D Move = FVector2D::ZeroVector;
	float Vert = 0.f; bool bBoost = false, bFire = false;
	if (PC && !IsDead())
	{
		Move = PC->GetMoveInput(); Vert = PC->GetVerticalInput();
		bBoost = PC->IsBoostHeld() && Move.Y > 0.3f; bFire = PC->IsFireHeld();
		const FVector2D Rate = PC->GetLookRateInput();
		AimYaw  += Rate.X * PadYawRate * Dt;
		AimPitch = FMath::Clamp(AimPitch + Rate.Y * PadPitchRate * Dt, -70.f, 65.f);
		PC->SetControlRotation(FRotator(AimPitch, AimYaw, 0.f));
	}

	const FVector Fwd   = FRotator(AimPitch * 0.9f, AimYaw, 0.f).Vector();
	const FVector Right = FRotator(0.f, AimYaw, 0.f).RotateVector(FVector::RightVector);
	const float FwdScale = Move.Y < 0.f ? 0.6f : 1.f;               // slower back-pedal
	const FVector Wish = Fwd * (Move.Y * FwdScale) + Right * Move.X + FVector::UpVector * Vert;
	const bool bHasInput = !Wish.IsNearlyZero(0.05f);
	Flight->StepFlight(Wish, bBoost, bHasInput, Dt);

	UpdateVisuals(Dt, Move);
	UpdateCamera(Dt, bBoost);
	TickWeapons(Dt, bFire);
}

void AVahagnPawn::UpdateVisuals(float Dt, const FVector2D& Move)
{
	// yaw: body follows aim
	FRotator R = GetActorRotation();
	R.Yaw = FMath::RInterpTo(FRotator(0, R.Yaw, 0), FRotator(0, AimYaw, 0), Dt, 10.f).Yaw;
	SetActorRotation(FRotator(0.f, R.Yaw, 0.f));
	const float YawRate = FMath::FindDeltaAngleDegrees(PrevActorYaw, R.Yaw) / FMath::Max(Dt, 1e-3f);
	PrevActorYaw = R.Yaw;
	SmoothedYawRate = FMath::FInterpTo(SmoothedYawRate, YawRate, Dt, 8.f);

	const FVector V = Flight->Velocity;
	const float Spd = V.Size();
	const float FwdA = FMath::Clamp(FVector::DotProduct(V, GetActorForwardVector()) / Flight->CruiseSpeed, 0.f, 1.f);
	const float ClimbDeg = Spd > 200.f ? FMath::RadiansToDegrees(FMath::Asin(FMath::Clamp(V.Z / Spd, -1.f, 1.f))) : 0.f;
	const float Pitch = FMath::Clamp(LeanSign * (-75.f * FwdA) + 0.6f * ClimbDeg * FwdA, -110.f, 15.f);
	const float Roll  = FMath::Clamp(BankSign * (0.12f * SmoothedYawRate + 22.f * Move.X), -50.f, 50.f);
	VisualRoot->SetRelativeRotation(FMath::RInterpTo(VisualRoot->GetRelativeRotation(), FRotator(Pitch, 0.f, Roll), Dt, 6.f));
	VisualRoot->SetRelativeLocation(FVector(0, 0, FMath::Sin(TimeAcc * 2.1f) * 10.f * (1.f - FwdA)));
	Body->SetPlayRate(FMath::Lerp(0.55f, 0.95f, FwdA));
}

void AVahagnPawn::UpdateCamera(float Dt, bool bBoost)
{
	Camera->SetFieldOfView(FMath::FInterpTo(Camera->FieldOfView, bBoost ? 102.f : 88.f, Dt, 5.f));
	Boom->TargetArmLength = FMath::FInterpTo(Boom->TargetArmLength, bBoost ? 700.f : 560.f, Dt, 4.f);
	Trauma = FMath::Max(0.f, Trauma - 1.5f * Dt);
	const float S = Trauma * Trauma;
	const float T = TimeAcc * 23.f;
	Camera->SetRelativeRotation(FRotator(FMath::PerlinNoise1D(T) * 2.5f * S,
	                                     FMath::PerlinNoise1D(T + 37.f) * 2.5f * S,
	                                     FMath::PerlinNoise1D(T + 71.f) * 4.f * S));
}
```
(`FireBolt`, `ComputeAimPoint`, `TickWeapons`, `TriggerSpecial` and `ApplyPlayerDamage` are in §3.)

---------------------------------------------------------------------------------------------------

## 3. Aiming and shooting

### 3.1 Aim point (camera trace through the crosshair, assist, fallback)

```cpp
FVector AVahagnPawn::ComputeAimPoint(USceneComponent*& OutHoming) const
{
	OutHoming = nullptr;
	const FVector CamLoc = Camera->GetComponentLocation();
	const FVector Dir    = Camera->GetForwardVector();       // screen centre = crosshair
	const float   Range  = 30000.f;
	// Start the ray beside the hero, so objects between the camera and the hero are ignored
	const float   Skip   = FMath::Max(0.f, FVector::DotProduct(GetActorLocation() - CamLoc, Dir));
	const FVector Start  = CamLoc + Dir * Skip;

	// 1) aim assist / direct hit against vishap segment spheres (analytic, §4.5)
	if (const UVishapSubsystem* VS = GetWorld()->GetSubsystem<UVishapSubsystem>())
	{
		FVishapAimResult R;
		if (VS->FindAimTarget(Start, Dir, Range, AimAssistDeg, R)) { OutHoming = R.Segment; return R.Point; }
	}
	// 2) world (terrain, sea, rocks)
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(VahagnAim), false, this);
	if (GetWorld()->LineTraceSingleByChannel(Hit, Start, Start + Dir * Range, ECC_Visibility, Q))
	{
		return Hit.ImpactPoint;
	}
	// 3) fallback far point
	return Start + Dir * Range;
}
```
(`UWorld::LineTraceSingleByChannel` is at `Classes/Engine/World.h:2161`, `SweepSingleByChannel` at `:2286`.)

### 3.2 Spawning the bolt

```cpp
void AVahagnPawn::TickWeapons(float Dt, bool bFireHeld)
{
	FireCooldown    = FMath::Max(0.f, FireCooldown - Dt);
	SpecialCooldown = FMath::Max(0.f, SpecialCooldown - Dt);
	if (bFireHeld && FireCooldown <= 0.f && !IsDead()) { FireBolt(); FireCooldown = FireInterval; }
}

void AVahagnPawn::FireBolt()
{
	USceneComponent* Homing = nullptr;
	const FVector AimPoint = ComputeAimPoint(Homing);
	const FName Bone = bRightHand ? FName(TEXT("hand_r")) : FName(TEXT("hand_l"));
	bRightHand = !bRightHand;
	const FVector CamDir = Camera->GetForwardVector();
	FVector Muzzle = Body->GetSocketLocation(Bone) + CamDir * 40.f;
	FVector Dir = (AimPoint - Muzzle).GetSafeNormal();
	// Guard: aim point too close or behind the muzzle (wall right in front) -> shoot along the crosshair ray
	if (FVector::DistSquared(AimPoint, Muzzle) < FMath::Square(250.f) || FVector::DotProduct(Dir, CamDir) < 0.25f)
	{
		Dir = CamDir;
	}
	FActorSpawnParameters P;
	P.Owner = this; P.Instigator = this;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (AFireBolt* B = GetWorld()->SpawnActor<AFireBolt>(AFireBolt::StaticClass(), Muzzle, Dir.Rotation(), P))
	{
		B->InitBolt(Homing, 12.f /*damage*/);
	}
	AddTrauma(0.06f);
}
```

### 3.3 Projectile (no hits on the owner, by construction)

Verified `UProjectileMovementComponent` members (`Classes/GameFramework/ProjectileMovementComponent.h`):

| Member | Line |
|---|---|
| `InitialSpeed` | :32 |
| `MaxSpeed` | :36 |
| `bRotationFollowsVelocity` | :40 |
| `bShouldBounce` | :48 |
| `bIsHomingProjectile` | :84 |
| `ProjectileGravityScale` | :162 |
| `OnProjectileStop` (dynamic, `const FHitResult&`) | :28, :212 |
| `HomingAccelerationMagnitude` | :216 |
| `HomingTargetComponent` (TWeakObjectPtr<USceneComponent>, "must be set after the projectile is spawned") | :223, :80 |

`InitializeComponent` rescales the default velocity to `InitialSpeed` along the actor's rotation (`Private/.../ProjectileMovementComponent.cpp` around line 87-104). So spawning with `Dir.Rotation()` is enough.

Collision design:
- The bolt's sphere is `QueryOnly`, object type `WorldDynamic`, **ignores all channels except `WorldStatic` = Block**.
- Result: it stops on terrain and the sea mesh, and it can never touch the hero's `Pawn` sphere.
- Vishap damage is found in `Tick` by an analytic swept test against the segment spheres from the previous position to the current one.

```cpp
// Combat/FireBolt.h
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FireBolt.generated.h"

class USphereComponent; class UProjectileMovementComponent; class UStaticMeshComponent;

UCLASS()
class TWILIGHT_API AFireBolt : public AActor
{
	GENERATED_BODY()
public:
	AFireBolt();
	void InitBolt(USceneComponent* HomingTarget, float InDamage);
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> Sphere;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Core;      // small emissive sphere
	UPROPERTY(VisibleAnywhere) TObjectPtr<UProjectileMovementComponent> Move;
private:
	UFUNCTION() void OnStop(const FHitResult& Hit);
	void Explode(const FVector& Where, bool bHitVishap);
	FVector PrevLoc;
	float Damage = 12.f;
	bool bDone = false;
};
```

```cpp
// Combat/FireBolt.cpp
#include "Combat/FireBolt.h"
#include "Enemies/VishapSubsystem.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

AFireBolt::AFireBolt()
{
	PrimaryActorTick.bCanEverTick = true;
	InitialLifeSpan = 3.0f;

	Sphere = CreateDefaultSubobject<USphereComponent>(TEXT("Sphere"));
	Sphere->InitSphereRadius(18.f);
	Sphere->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Sphere->SetCollisionObjectType(ECC_WorldDynamic);
	Sphere->SetCollisionResponseToAllChannels(ECR_Ignore);
	Sphere->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);
	Sphere->SetGenerateOverlapEvents(false);
	RootComponent = Sphere;

	Core = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Core"));
	Core->SetupAttachment(Sphere);
	Core->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Core->SetCastShadow(false);
	Core->SetRelativeScale3D(FVector(0.35f, 0.18f, 0.18f));   // stretched streak
	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (SphereMesh.Succeeded()) { Core->SetStaticMesh(SphereMesh.Object); }

	Move = CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("Move"));
	Move->UpdatedComponent = Sphere;
	Move->InitialSpeed = 9000.f;
	Move->MaxSpeed = 9000.f;
	Move->ProjectileGravityScale = 0.f;
	Move->bRotationFollowsVelocity = true;
	Move->bShouldBounce = false;
	Move->HomingAccelerationMagnitude = 22000.f;
}

void AFireBolt::InitBolt(USceneComponent* HomingTarget, float InDamage)
{
	Damage = InDamage;
	if (HomingTarget)
	{
		Move->HomingTargetComponent = HomingTarget;   // set after spawn (header comment :80)
		Move->bIsHomingProjectile = true;
	}
}

void AFireBolt::BeginPlay()
{
	Super::BeginPlay();
	PrevLoc = GetActorLocation();
	Move->OnProjectileStop.AddDynamic(this, &AFireBolt::OnStop);
	// Belt and braces; IgnoreActorWhenMoving is at Classes/Components/PrimitiveComponent.h:1082
	if (GetOwner()) { Sphere->IgnoreActorWhenMoving(GetOwner(), true); }
	// Niagara trail: UNiagaraFunctionLibrary::SpawnSystemAttached (Plugins/FX/Niagara/.../NiagaraFunctionLibrary.h:96)
}

void AFireBolt::Tick(float Dt)
{
	Super::Tick(Dt);
	if (bDone) { return; }
	const FVector Cur = GetActorLocation();
	if (UVishapSubsystem* VS = GetWorld()->GetSubsystem<UVishapSubsystem>())
	{
		FVishapSweepHit H;
		if (VS->SweepSphere(PrevLoc, Cur, Sphere->GetScaledSphereRadius(), H))
		{
			VS->ApplyHit(H, Damage, GetInstigator());
			Explode(H.Point, true);
			return;
		}
	}
	PrevLoc = Cur;
}

void AFireBolt::OnStop(const FHitResult& Hit) { Explode(Hit.ImpactPoint, false); }

void AFireBolt::Explode(const FVector& Where, bool bHitVishap)
{
	if (bDone) { return; }
	bDone = true;
	// spawn impact VFX + sound here
	Destroy();
}
```

Optional custom channel (only if you later want trace-based hits). Format verified from `Templates/TP_FirstPerson/Config/DefaultEngine.ini:1-4`:
```ini
[/Script/Engine.CollisionProfile]
+DefaultChannelResponses=(Channel=ECC_GameTraceChannel1,Name="Projectile",DefaultResponse=ECR_Block,bTraceType=False,bStaticObject=False)
+Profiles=(Name="Projectile",CollisionEnabled=QueryOnly,ObjectTypeName="Projectile",CustomResponses=((Channel="Pawn",Response=ECR_Ignore)),HelpMessage="Vahagn bolts",bCanModify=True)
```

### 3.4 Special (Q / RMB / RB): "Vahagn's Thunder" area-of-effect attack

```cpp
void AVahagnPawn::TriggerSpecial()
{
	if (SpecialCooldown > 0.f || IsDead()) { return; }
	SpecialCooldown = SpecialCooldownMax;
	USceneComponent* Dummy = nullptr;
	const FVector Center = ComputeAimPoint(Dummy);
	if (UVishapSubsystem* VS = GetWorld()->GetSubsystem<UVishapSubsystem>())
	{
		VS->ApplyRadialDamage(Center, 2600.f, 140.f, this);
	}
	AddTrauma(0.55f);
	// big Niagara burst + thunder sound at Center
}
void AVahagnPawn::ApplyPlayerDamage(float Amount, const FVector& From)
{
	if (IsDead()) { return; }
	HP = FMath::Max(0.f, HP - Amount);
	AddTrauma(FMath::Clamp(Amount / 25.f, 0.15f, 0.8f));
}
```

---------------------------------------------------------------------------------------------------

## 4. Vishap enemies

### 4.1 Body: procedural serpent

- **Head** = the actor location (`USceneComponent` root). It moves by direct `SetActorLocationAndRotation`; vishaps do not collide with the world. They avoid it by steering (altitude keeping), which is never stuck and has no physics cost.
- **Segments** = `N` (small 22, boss 40) `UStaticMeshComponent`s:
  - Created in `BeginPlay` with `NewObject` + `SetupAttachment(Root)` + `SetAbsolute(true,true,true)` (`SceneComponent.h:1237`) + `RegisterComponent()`.
  - Mesh `/Engine/BasicShapes/Sphere` (radius 50 uu at scale 1), with `/Engine/BasicShapes/Cone` for horns, the jaw and the tail tip. Basic shapes exist at `E/Content/BasicShapes/{Sphere,Cone,Cylinder,Cube,Plane}.uasset`.
  - `NoCollision`.
  - `SetCastShadow(false)` on everything except the head and the first 4 segments (iGPU).
- **Breadcrumb trail:**
  - When the head has moved ≥ `TrailStep` (30 uu), push its position to the front of `Trail`.
  - Segment *i* sits at arc length `i * Spacing` behind the head along the polyline (head → Trail[0] → Trail[1] …).
  - One pass walks the polyline once for all segments: O(N + trail).
  - The trail is pre-filled straight behind the head at spawn, so the body is laid out from frame 1.
- **Undulation** is visual only, so hit spheres stay close:
  - `Pos_i += Side_i * sin(Time*ω − i*φ) * Amp * (i/N)^0.7`
  - `Side_i = normalize(Tangent × Up)`
- **Taper:** scale_i = lerp(HeadScale, TailScale, (i/N)^1.3).
- **Orientation:** `FRotationMatrix::MakeFromXZ(Tangent, Up)`.
- **Hit spheres:** cache `SegCenter[i]` and `SegRadius[i] = 50*scale_i*0.9` each frame. These serve every query (aim assist, bolts, the special attack, contact damage to the player).

### 4.2 AI state machine (steering inside the actor)

| State | Desired velocity | Exit |
|---|---|---|
| `Wander` | Orbit a point around the arena centre at a cruise altitude | Player within 9000 → `Approach` |
| `Approach` | Seek the player's predicted position (+0.6 s lead) | dist < 3500 → `Circle` |
| `Circle` | Tangent around the player, radius 2500 ± 400, altitude offset ±800, CW/CCW random | After 3–6 s, roll the dice: 40 % `DiveWindup`, 40 % `BreathAim`, 20 % keep circling |
| `DiveWindup` (1.0 s) | Rise to player.Z + 2000, head glows (material param), roar | → `Dive` |
| `Dive` (≤ 2.5 s) | Seek predicted player at 1.9× speed, turn rate ×1.6 | Head within 450 of the player → damage 18 once → `Retreat`; or timeout |
| `BreathAim` | Hold 1800–2400 from the player, face them, 0.4× speed | Facing within 12° → `Breath`, with a 0.8 s telegraph (mouth glow, head rears back) |
| `Breath` (1.8 s) | Slow drift; spawn the fire-breath Niagara on the head | Player inside the 18° cone and 2600 range → 6 damage every 0.2 s → `Retreat` |
| `Retreat` (2–3 s) | Away from the player and up | → `Approach` |
| `Dying` | AI off; head falls with gravity and spins; segments pop from tail to head every 0.06 s (explosion VFX); then `Destroy` | n/a |

Steering is added to every state's desired velocity:
- **Separation:** for other vishaps within 1500, `+= (me − other).normal * (1 − d/1500) * 1200`.
- **Altitude:** keep ≥ floor + 900 using a down-trace cached every 0.25 s.
- **Bounds:** the same soft cylinder as the player.

The head's velocity is **turn-rate limited** (deg/s), so it always looks serpentine and never snaps:

```cpp
static FVector RotateTowards(const FVector& From, const FVector& To, float MaxRad)
{
	const float Cos = FMath::Clamp(FVector::DotProduct(From, To), -1.f, 1.f);
	const float Ang = FMath::Acos(Cos);
	if (Ang <= MaxRad || Ang < 1e-4f) { return To; }
	const FQuat Q = FQuat::FindBetweenNormals(From, To);       // Core/Public/Math/Quat.h:622
	return FQuat::Slerp(FQuat::Identity, Q, MaxRad / Ang).RotateVector(From);
}
```

### 4.3 Code: `AVishap` (skeleton, compile-oriented)

```cpp
// Enemies/Vishap.h
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Vishap.generated.h"

class UStaticMeshComponent; class UStaticMesh; class UMaterialInstanceDynamic;

UENUM() enum class EVishapState : uint8 { Wander, Approach, Circle, DiveWindup, Dive, BreathAim, Breath, Retreat, Dying };

UCLASS()
class TWILIGHT_API AVishap : public AActor
{
	GENERATED_BODY()
public:
	AVishap();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void Tick(float DeltaSeconds) override;

	virtual void ReceiveHit(int32 SegmentIndex, float Damage, AActor* Instigator);
	bool IsAlive() const { return State != EVishapState::Dying; }
	float GetHP01() const { return HP / MaxHP; }

	// read by UVishapSubsystem
	TArray<FVector> SegCenter;
	TArray<float>   SegRadius;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Segments;   // [0] = head

	// tuning (the boss overrides these in its constructor)
	UPROPERTY(EditAnywhere) int32 NumSegments = 22;
	UPROPERTY(EditAnywhere) float Spacing = 70.f;
	UPROPERTY(EditAnywhere) float HeadScale = 2.2f, TailScale = 0.5f;
	UPROPERTY(EditAnywhere) float MaxHP = 120.f;
	UPROPERTY(EditAnywhere) float CruiseSpeed = 1700.f;
	UPROPERTY(EditAnywhere) float TurnRateDeg = 110.f;
	UPROPERTY(EditAnywhere) float UndAmp = 45.f, UndFreq = 5.f, UndPhase = 0.55f;

protected:
	virtual void TickAI(float Dt, FVector& OutDesiredVel, float& OutSpeedMul, float& OutTurnMul);
	void SetState(EVishapState S, float Duration = 0.f);
	void BuildBody();
	void UpdateTrail();
	void LayoutSegments(float Dt);
	void TickDying(float Dt);
	FVector SteerCommon() const;

	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<UStaticMesh> SphereMesh;
	UPROPERTY() TObjectPtr<UStaticMesh> ConeMesh;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BodyMID;

	TArray<FVector> Trail;          // [0] newest
	FVector Velocity = FVector::ZeroVector;
	float Speed = 0.f, HP = 0.f, StateTime = 0.f, StateDuration = 0.f, Time = 0.f;
	float CircleSign = 1.f, DyingStep = 0.f;
	int32 DyingPopped = 0;
	bool bDiveHitDone = false;
	EVishapState State = EVishapState::Wander;
};
```

```cpp
// Enemies/Vishap.cpp (key parts)
#include "Enemies/Vishap.h"
#include "Enemies/VishapSubsystem.h"
#include "Player/VahagnPawn.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

AVishap::AVishap()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> S(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> C(TEXT("/Engine/BasicShapes/Cone.Cone"));
	SphereMesh = S.Object; ConeMesh = C.Object;
}

void AVishap::BeginPlay()
{
	Super::BeginPlay();
	HP = MaxHP;
	Speed = CruiseSpeed;
	Velocity = GetActorForwardVector() * Speed;
	CircleSign = FMath::RandBool() ? 1.f : -1.f;
	BuildBody();
	if (UVishapSubsystem* VS = GetWorld()->GetSubsystem<UVishapSubsystem>()) { VS->Register(this); }
}

void AVishap::EndPlay(const EEndPlayReason::Type R)
{
	if (UVishapSubsystem* VS = GetWorld()->GetSubsystem<UVishapSubsystem>()) { VS->Unregister(this); }
	Super::EndPlay(R);
}

void AVishap::BuildBody()
{
	const FVector Back = -GetActorForwardVector();
	const int32 TrailCount = FMath::CeilToInt(NumSegments * Spacing / 30.f) + 8;
	for (int32 i = 0; i < TrailCount; ++i) { Trail.Add(GetActorLocation() + Back * (i + 1) * 30.f); }
	for (int32 i = 0; i < NumSegments; ++i)
	{
		UStaticMeshComponent* M = NewObject<UStaticMeshComponent>(this);
		M->SetupAttachment(Root);
		M->SetAbsolute(true, true, true);
		M->SetStaticMesh(i == NumSegments - 1 ? ConeMesh.Get() : SphereMesh.Get());
		M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		M->SetCastShadow(i < 5);
		M->RegisterComponent();
		Segments.Add(M);
	}
	SegCenter.SetNum(NumSegments);
	SegRadius.SetNum(NumSegments);
	// BodyMID = UMaterialInstanceDynamic::Create(<vishap material>, this); apply it to all segments
}

void AVishap::UpdateTrail()
{
	const FVector Head = GetActorLocation();
	if (FVector::DistSquared(Head, Trail[0]) >= FMath::Square(30.f))
	{
		Trail.Insert(Head, 0);
		const int32 MaxTrail = FMath::CeilToInt(NumSegments * Spacing / 30.f) + 16;
		while (Trail.Num() > MaxTrail) { Trail.RemoveAt(Trail.Num() - 1); }
	}
}

void AVishap::LayoutSegments(float Dt)
{
	// single pass along the polyline: head -> Trail[0] -> Trail[1] -> ...
	FVector A = GetActorLocation();
	int32 TIdx = 0;
	float Acc = 0.f;       // arc length at A
	for (int32 i = 0; i < NumSegments; ++i)
	{
		const float Want = i * Spacing;
		FVector Pos = A, Tan = Velocity.GetSafeNormal();
		while (TIdx < Trail.Num())
		{
			const FVector B = Trail[TIdx];
			const float L = FVector::Dist(A, B);
			if (Acc + L >= Want && L > KINDA_SMALL_NUMBER)
			{
				Tan = (A - B) / L;   // points toward the head
				Pos = FMath::Lerp(A, B, (Want - Acc) / L);
				break;
			}
			Acc += L; A = B; ++TIdx;
		}
		if (TIdx >= Trail.Num()) { Pos = A - Tan * (Want - Acc); }

		const float U = (float)i / FMath::Max(1, NumSegments - 1);
		const FVector Side = FVector::CrossProduct(Tan, FVector::UpVector).GetSafeNormal();
		Pos += Side * FMath::Sin(Time * UndFreq - i * UndPhase) * UndAmp * FMath::Pow(U, 0.7f);
		const float Scale = FMath::Lerp(HeadScale, TailScale, FMath::Pow(U, 1.3f));
		const FRotator Rot = FRotationMatrix::MakeFromXZ(Tan, FVector::UpVector).Rotator();
		FVector S3(Scale * 1.25f, Scale, Scale);                         // slightly elongated beads
		if (i == NumSegments - 1) { S3 = FVector(Scale, Scale, Scale * 2.f); }   // cone tail; rotate the cone in Rot if needed
		Segments[i]->SetWorldLocationAndRotation(Pos, Rot);
		Segments[i]->SetWorldScale3D(S3);
		SegCenter[i] = Pos;
		SegRadius[i] = 50.f * Scale * 0.9f;
	}
}

void AVishap::Tick(float Dt)
{
	Super::Tick(Dt);
	Time += Dt; StateTime += Dt;
	if (State == EVishapState::Dying) { TickDying(Dt); return; }

	FVector Desired; float SpeedMul = 1.f, TurnMul = 1.f;
	TickAI(Dt, Desired, SpeedMul, TurnMul);
	Desired += SteerCommon();
	const FVector Fwd = Velocity.GetSafeNormal(0.01f, GetActorForwardVector());
	const FVector NewDir = RotateTowards(Fwd, Desired.GetSafeNormal(0.01f, Fwd),
	                                     FMath::DegreesToRadians(TurnRateDeg * TurnMul) * Dt);
	Speed = FMath::FInterpTo(Speed, CruiseSpeed * SpeedMul, Dt, 2.5f);
	Velocity = NewDir * Speed;
	SetActorLocationAndRotation(GetActorLocation() + Velocity * Dt,
	                            FRotationMatrix::MakeFromXZ(NewDir, FVector::UpVector).Rotator());
	UpdateTrail();
	LayoutSegments(Dt);
}

void AVishap::ReceiveHit(int32 Seg, float Damage, AActor* Inst)
{
	if (State == EVishapState::Dying) { return; }
	HP -= (Seg == 0 ? 2.f : 1.f) * Damage;          // the head is the weak point
	// flash: BodyMID->SetScalarParameterValue("HitFlash", 1)  and decay it in Tick
	if (HP <= 0.f) { SetState(EVishapState::Dying); /* notify GameMode: kills++ */ }
}
```
`TickAI` is a `switch(State)` that implements the table in §4.2. Player position: `UGameplayStatics::GetPlayerPawn(this, 0)`. Contact and breath damage use `AVahagnPawn::ApplyPlayerDamage`.

### 4.4 Great Vishap (boss): `AGreatVishap : AVishap`

Constructor values:

| Property | Value |
|---|---|
| `NumSegments` | 40 |
| `Spacing` | 150 |
| `HeadScale` / `TailScale` | 6 / 1.2 |
| `MaxHP` | 2500 |
| `CruiseSpeed` | 1900 |
| `TurnRateDeg` | 70 |
| `UndAmp` | 120 |

`TickAI` override with phases by HP:

| Phase | HP | Behaviour |
|---|---|---|
| **P1** | 100–66 % | Circle + breath; every 20 s summons 2 small vishaps |
| **P2** | 66–33 % | Adds dives and **fireball volleys**: 5 slow `AVishapFireball` projectiles (homing weakly at the player, 1200 uu/s) that the player can shoot down. Each is registered in the subsystem as a 1-segment target. |
| **P3** | < 33 % | Enraged: speed ×1.25, a breath that **sweeps** (head yaw oscillates), emissive goes red. GameMode darkens the sky and adds lightning. |

Phase transition:
- 2.5 s invulnerable (`ReceiveHit` returns early).
- Roar and `AddTrauma(0.7)` on the player.
- Shockwave VFX.
- HUD banner via the GameMode.

Boss death: GameMode → slow motion (§5.1); the segment explosion chain runs at 0.04 s per segment.

### 4.5 Code: `UVishapSubsystem` (registry and analytic hit tests)

```cpp
// Enemies/VishapSubsystem.h
#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "VishapSubsystem.generated.h"

class AVishap;
struct FVishapAimResult  { FVector Point; USceneComponent* Segment = nullptr; AVishap* Vishap = nullptr; };
struct FVishapSweepHit   { FVector Point; int32 SegmentIndex = INDEX_NONE; AVishap* Vishap = nullptr; float T = 1.f; };

UCLASS()
class TWILIGHT_API UVishapSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	void Register(AVishap* V)   { Vishaps.AddUnique(V); }
	void Unregister(AVishap* V) { Vishaps.Remove(V); }
	int32 NumAlive() const;
	const TArray<TWeakObjectPtr<AVishap>>& GetAll() const { return Vishaps; }

	bool FindAimTarget(const FVector& O, const FVector& Dir, float Range, float ConeDeg, FVishapAimResult& Out) const;
	bool SweepSphere(const FVector& A, const FVector& B, float R, FVishapSweepHit& Out) const;
	void ApplyHit(const FVishapSweepHit& H, float Damage, AActor* Inst);
	void ApplyRadialDamage(const FVector& C, float Radius, float Damage, AActor* Inst);
private:
	TArray<TWeakObjectPtr<AVishap>> Vishaps;
};
```

```cpp
// Enemies/VishapSubsystem.cpp
#include "Enemies/VishapSubsystem.h"
#include "Enemies/Vishap.h"
#include "Components/StaticMeshComponent.h"

int32 UVishapSubsystem::NumAlive() const
{
	int32 N = 0;
	for (const TWeakObjectPtr<AVishap>& W : Vishaps) { if (W.IsValid() && W->IsAlive()) { ++N; } }
	return N;
}

bool UVishapSubsystem::FindAimTarget(const FVector& O, const FVector& Dir, float Range, float ConeDeg, FVishapAimResult& Out) const
{
	float BestScore = TNumericLimits<float>::Max();
	const float ConeRad = FMath::DegreesToRadians(ConeDeg);
	for (const TWeakObjectPtr<AVishap>& W : Vishaps)
	{
		AVishap* V = W.Get();
		if (!V || !V->IsAlive()) { continue; }
		for (int32 i = 0; i < V->SegCenter.Num(); ++i)
		{
			const FVector ToC = V->SegCenter[i] - O;
			const float T = FVector::DotProduct(ToC, Dir);
			if (T <= 0.f || T > Range) { continue; }
			const float Perp = (ToC - Dir * T).Size();
			const float Ang = FMath::Atan2(FMath::Max(0.f, Perp - V->SegRadius[i]), T);   // 0 = direct hit
			if (Ang > ConeRad) { continue; }
			const float Score = Ang + (T / Range) * 0.02f + (i == 0 ? -0.004f : 0.f);       // nearer, then head
			if (Score < BestScore)
			{
				BestScore = Score;
				Out.Vishap = V;
				Out.Segment = V->Segments.IsValidIndex(i) ? V->Segments[i].Get() : nullptr;
				Out.Point = (Perp <= V->SegRadius[i]) ? O + Dir * (T - FMath::Sqrt(FMath::Max(0.f, FMath::Square(V->SegRadius[i]) - Perp * Perp)))
				                                      : V->SegCenter[i];
			}
		}
	}
	return Out.Vishap != nullptr;
}

bool UVishapSubsystem::SweepSphere(const FVector& A, const FVector& B, float R, FVishapSweepHit& Out) const
{
	const FVector AB = B - A;
	const float Len2 = FMath::Max(AB.SizeSquared(), 1e-4f);
	bool bHit = false;
	for (const TWeakObjectPtr<AVishap>& W : Vishaps)
	{
		AVishap* V = W.Get();
		if (!V || !V->IsAlive()) { continue; }
		for (int32 i = 0; i < V->SegCenter.Num(); ++i)
		{
			const float T = FMath::Clamp(FVector::DotProduct(V->SegCenter[i] - A, AB) / Len2, 0.f, 1.f);
			const FVector P = A + AB * T;
			if (FVector::DistSquared(P, V->SegCenter[i]) <= FMath::Square(R + V->SegRadius[i]) && T < Out.T)
			{
				Out.T = T; Out.Point = P; Out.SegmentIndex = i; Out.Vishap = V; bHit = true;
			}
		}
	}
	return bHit;
}

void UVishapSubsystem::ApplyHit(const FVishapSweepHit& H, float Damage, AActor* Inst)
{
	if (H.Vishap) { H.Vishap->ReceiveHit(H.SegmentIndex, Damage, Inst); }
}

void UVishapSubsystem::ApplyRadialDamage(const FVector& C, float Radius, float Damage, AActor* Inst)
{
	TArray<TWeakObjectPtr<AVishap>> Copy = Vishaps;   // ReceiveHit may change the list
	for (const TWeakObjectPtr<AVishap>& W : Copy)
	{
		AVishap* V = W.Get();
		if (!V || !V->IsAlive()) { continue; }
		int32 Best = INDEX_NONE; float BestD = Radius;
		for (int32 i = 0; i < V->SegCenter.Num(); ++i)
		{
			const float D = FVector::Dist(C, V->SegCenter[i]) - V->SegRadius[i];
			if (D < BestD) { BestD = D; Best = i; }
		}
		if (Best != INDEX_NONE) { V->ReceiveHit(Best, Damage * (1.f - 0.5f * FMath::Max(0.f, BestD) / Radius), Inst); }
	}
}
```
Cost: 8 vishaps × 22 segments + boss 40 = about 220 spheres. 15 live bolts × 220 = 3.3k distance tests per frame, which is negligible.

---------------------------------------------------------------------------------------------------

## 5. Game flow and HUD

### 5.1 `AVahagnGameMode : AGameModeBase`

Verified APIs:
- `UGameplayStatics::SetGlobalTimeDilation(const UObject*, float)` (`Classes/Kismet/GameplayStatics.h:393`)
- `SetGamePaused` (`:401`)
- `OpenLevel(const UObject*, FName, bool, FString)` (`:340`)
- `AWorldSettings::GetEffectiveTimeDilation()` (`Classes/GameFramework/WorldSettings.h:860`). Dilation is clamped by `MinGlobalTimeDilation` / `MaxGlobalTimeDilation` (`:755`, `:759`).
- Actor `Tick` `DeltaSeconds` is **dilated**. `FTimerManager` timers are dilated as well. Real time = `Dt / GetEffectiveTimeDilation()`.
- A paused game stops the GameMode tick, so the match timer pauses for free.

```cpp
// Game/VahagnGameMode.h
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "VahagnGameMode.generated.h"

class AVishap; class AGreatVishap;

UENUM(BlueprintType) enum class EMatchPhase : uint8 { Intro, Waves, BossIntro, Boss, Victory, Defeat };

USTRUCT() struct FWaveDef
{
	GENERATED_BODY()
	UPROPERTY() int32 Count = 3;
	UPROPERTY() float SpeedMul = 1.f;
	UPROPERTY() float HPMul = 1.f;
};

UCLASS()
class TWILIGHT_API AVahagnGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	AVahagnGameMode();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	EMatchPhase GetPhase() const { return Phase; }
	float GetTimeLeft() const { return TimeLeft; }
	int32 GetWaveIndex() const { return WaveIndex; }
	int32 GetKills() const { return Kills; }
	AGreatVishap* GetBoss() const { return Boss.Get(); }
	const FText& GetBanner() const { return Banner; }
	float GetBannerAlpha() const { return FMath::Clamp(BannerTime, 0.f, 1.f); }

	void NotifyVishapKilled(AVishap* V);
	void NotifyBossKilled();

	UPROPERTY(EditAnywhere) float MatchSeconds = 480.f;
	UPROPERTY(EditAnywhere) float BossNoLaterThan = 210.f;  // the boss starts by TimeLeft <= this
	UPROPERTY(EditAnywhere) TArray<FWaveDef> Waves;

private:
	void SetPhase(EMatchPhase P);
	void SpawnWave(const FWaveDef& W);
	void SpawnBoss();
	void ShowBanner(const FText& T, float Seconds = 3.f) { Banner = T; BannerTime = Seconds; }

	EMatchPhase Phase = EMatchPhase::Intro;
	float TimeLeft = 480.f, PhaseTime = 0.f, SlowMoReal = 0.f, BannerTime = 0.f;
	int32 WaveIndex = -1, Kills = 0;
	FText Banner;
	TWeakObjectPtr<AGreatVishap> Boss;
};
```

```cpp
// Game/VahagnGameMode.cpp (core)
#include "Game/VahagnGameMode.h"
#include "Player/VahagnPawn.h"
#include "Player/VahagnPlayerController.h"
#include "UI/VahagnHUD.h"
#include "Enemies/Vishap.h"
#include "Enemies/GreatVishap.h"
#include "Enemies/VishapSubsystem.h"
#include "GameFramework/WorldSettings.h"
#include "Kismet/GameplayStatics.h"

AVahagnGameMode::AVahagnGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	DefaultPawnClass      = AVahagnPawn::StaticClass();
	PlayerControllerClass = AVahagnPlayerController::StaticClass();
	HUDClass              = AVahagnHUD::StaticClass();
	Waves = { {3, 1.0f, 1.0f}, {5, 1.05f, 1.0f}, {6, 1.15f, 1.2f}, {7, 1.2f, 1.3f} };
}

void AVahagnGameMode::BeginPlay()
{
	Super::BeginPlay();
	TimeLeft = MatchSeconds;
	SetPhase(EMatchPhase::Intro);
}

void AVahagnGameMode::Tick(float Dt)
{
	Super::Tick(Dt);
	const float Dil = FMath::Max(GetWorldSettings()->GetEffectiveTimeDilation(), 1e-3f);
	const float RealDt = Dt / Dil;
	PhaseTime += Dt;
	BannerTime -= RealDt;

	if (SlowMoReal > 0.f)                               // timed in real seconds
	{
		SlowMoReal -= RealDt;
		if (SlowMoReal <= 0.f) { UGameplayStatics::SetGlobalTimeDilation(this, 1.f); SetPhase(EMatchPhase::Victory); }
	}

	const AVahagnPawn* P = Cast<AVahagnPawn>(UGameplayStatics::GetPlayerPawn(this, 0));
	const bool bFighting = Phase == EMatchPhase::Waves || Phase == EMatchPhase::BossIntro || Phase == EMatchPhase::Boss;
	if (bFighting)
	{
		TimeLeft = FMath::Max(0.f, TimeLeft - Dt);
		if ((P && P->IsDead()) || TimeLeft <= 0.f) { SetPhase(EMatchPhase::Defeat); return; }
	}
	switch (Phase)
	{
	case EMatchPhase::Intro:
		if (PhaseTime > 3.f) { SetPhase(EMatchPhase::Waves); }
		break;
	case EMatchPhase::Waves:
	{
		const UVishapSubsystem* VS = GetWorld()->GetSubsystem<UVishapSubsystem>();
		const bool bCleared = VS && VS->NumAlive() == 0;
		if (TimeLeft <= BossNoLaterThan || (bCleared && WaveIndex + 1 >= Waves.Num())) { SetPhase(EMatchPhase::BossIntro); }
		else if (bCleared && PhaseTime > 2.f)
		{
			++WaveIndex; PhaseTime = 0.f; SpawnWave(Waves[WaveIndex]);
			ShowBanner(FText::FromString(FString::Printf(TEXT("Ալիք %d"), WaveIndex + 1)));
		}
		break;
	}
	case EMatchPhase::BossIntro:
		if (PhaseTime > 4.f) { SetPhase(EMatchPhase::Boss); }
		break;
	default: break;
	}
}

void AVahagnGameMode::SetPhase(EMatchPhase NewPhase)
{
	Phase = NewPhase; PhaseTime = 0.f;
	switch (NewPhase)
	{
	case EMatchPhase::Intro:     ShowBanner(FText::FromString(TEXT("Վահագն Վիշապաքաղ")), 3.f); break;
	case EMatchPhase::BossIntro: ShowBanner(FText::FromString(TEXT("Մեծ վիշապը գալիս է")), 4.f); SpawnBoss(); break;
	case EMatchPhase::Victory:   ShowBanner(FText::FromString(TEXT("Հաղթանակ")), 999.f); break;
	case EMatchPhase::Defeat:    ShowBanner(FText::FromString(TEXT("Պարտություն")), 999.f); break;
	default: break;
	}
}

void AVahagnGameMode::NotifyBossKilled()
{
	UGameplayStatics::SetGlobalTimeDilation(this, 0.2f);   // GameplayStatics.h:393
	SlowMoReal = 2.5f;                                      // real seconds, then Victory
}
```
`SpawnWave` picks spawn points on a ring of radius 0.8·ArenaRadius, ±60° around the player's heading (in front, so the player sees them arrive), at altitude 2000–6000 above the floor. It uses `GetWorld()->SpawnActor<AVishap>(...)` with `SpawnCollisionHandlingOverride = AlwaysSpawn`, then applies the `SpeedMul`/`HPMul` values.

Restart (R key or a button on the result screen): `UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)))`.

Config (`DefaultEngine.ini`):
```ini
[/Script/EngineSettings.GameMapsSettings]
GlobalDefaultGameMode=/Script/Twilight.VahagnGameMode
GameDefaultMap=/Game/Maps/L_Arena.L_Arena
EditorStartupMap=/Game/Maps/L_Arena.L_Arena
```
Format reference: `Templates/TP_ThirdPerson/Config/DefaultEngine.ini:4`. The engine default is at `E/Config/BaseEngine.ini:17`.

### 5.2 HUD split

- **`AVahagnHUD : AHUD`**:
  - Creates the UMG widget in `BeginPlay`: `CreateWidget<UVahagnHUDWidget>(GetOwningPlayerController(), UVahagnHUDWidget::StaticClass())` + `AddToViewport()`.
  - Draws on the canvas in `DrawHUD()` (`Classes/GameFramework/HUD.h:503`), using `DrawRect` (`:257`), `DrawTexture` (`:278`) and `Canvas->K2_DrawLine`:
    - **crosshair** (4 short lines + a dot; it turns red when `FindAimTarget` returns a target);
    - **hit markers**;
    - **off-screen arrows** for vishaps, via `PlayerOwner->ProjectWorldLocationToScreen(...)` (`PlayerController.h:742`) and clamping to the screen border.
  - The canvas needs no font for these.
- **`UVahagnHUDWidget : UUserWidget`**: all text (Armenian) and bars. It polls the GameMode and the pawn in `NativeTick`, and shows the pause and result panels.

### 5.3 UMG built purely in C++: correct lifecycle (verified)

`E/Source/Runtime/UMG/Private/UserWidget.cpp`:
- `UUserWidget::Initialize()` (`:135`): for a **native (non-Blueprint) class** it calls `InitializeNativeClassData()` (`:157`) and **creates `WidgetTree` if it is null** (`:160-163`). Then it calls `NativeOnInitialized()` if there is a player context (`:173-176`). `CreateWidget` runs `Initialize()`.
- `RebuildWidget()` (`:1190-1216`) calls `Initialize()` if needed and then returns `WidgetTree->RootWidget->TakeWidget()`. If `RootWidget` is null, it returns an **`SSpacer`** (`:1214`).
- `OnWidgetRebuilt()` (`:1219-1235`) calls `NativePreConstruct()` and then **`NativeConstruct()` after** the Slate widget has been built.

**Therefore build the tree in an override of `RebuildWidget()`, before calling `Super`.** `NativeOnInitialized` also works. **Do not build it in `NativeConstruct`**, because that is too late for the first build. `WidgetTree->ConstructWidget<T>(Class, Name)` is at `UMG/Public/Blueprint/WidgetTree.h:106`.

```cpp
// UI/VahagnHUDWidget.h
#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Fonts/SlateFontInfo.h"
#include "VahagnHUDWidget.generated.h"

class UTextBlock; class UProgressBar; class UCanvasPanel; class UBorder;

UCLASS()
class TWILIGHT_API UVahagnHUDWidget : public UUserWidget
{
	GENERATED_BODY()
protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
private:
	UTextBlock* MakeText(UCanvasPanel* Root, FName Name, float Size, FVector2D Anchor, FVector2D Align, FVector2D Pos);
	UPROPERTY() TObjectPtr<UTextBlock>  TimerText;
	UPROPERTY() TObjectPtr<UTextBlock>  WaveText;
	UPROPERTY() TObjectPtr<UTextBlock>  BannerText;
	UPROPERTY() TObjectPtr<UTextBlock>  HPLabel;
	UPROPERTY() TObjectPtr<UProgressBar> HPBar;
	UPROPERTY() TObjectPtr<UProgressBar> BossBar;
	UPROPERTY() TObjectPtr<UTextBlock>  BossName;
	UPROPERTY() TObjectPtr<UProgressBar> SpecialBar;
	UPROPERTY() TObjectPtr<UTextBlock>  PauseText;
};
```

```cpp
// UI/VahagnHUDWidget.cpp
#include "UI/VahagnHUDWidget.h"
#include "UI/VahagnFonts.h"
#include "Game/VahagnGameMode.h"
#include "Player/VahagnPawn.h"
#include "Enemies/GreatVishap.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/ProgressBar.h"
#include "Kismet/GameplayStatics.h"

UTextBlock* UVahagnHUDWidget::MakeText(UCanvasPanel* Root, FName Name, float Size, FVector2D Anchor, FVector2D Align, FVector2D Pos)
{
	UTextBlock* T = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), Name);
	T->SetFont(VahagnFonts::Get(Size, true));                       // TextBlock.h:156
	T->SetColorAndOpacity(FSlateColor(FLinearColor(1.f, 0.86f, 0.6f)));
	T->SetShadowOffset(FVector2D(2, 2));
	T->SetShadowColorAndOpacity(FLinearColor(0, 0, 0, 0.8f));
	UCanvasPanelSlot* S = Root->AddChildToCanvas(T);                // CanvasPanel.h:33
	S->SetAnchors(FAnchors(Anchor.X, Anchor.Y));                     // CanvasPanelSlot.h:128
	S->SetAlignment(Align);                                          // :136
	S->SetPosition(Pos);                                             // :104
	S->SetAutoSize(true);                                            // :144
	return T;
}

TSharedRef<SWidget> UVahagnHUDWidget::RebuildWidget()
{
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		UCanvasPanel* Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
		WidgetTree->RootWidget = Root;

		TimerText  = MakeText(Root, TEXT("Timer"),  40, {0.5f, 0.f}, {0.5f, 0.f}, {0, 20});
		WaveText   = MakeText(Root, TEXT("Wave"),   24, {0.f, 0.f},  {0.f, 0.f},  {32, 24});
		BannerText = MakeText(Root, TEXT("Banner"), 64, {0.5f, 0.3f}, {0.5f, 0.5f}, {0, 0});
		HPLabel    = MakeText(Root, TEXT("HPLbl"),  22, {0.f, 1.f},  {0.f, 1.f},  {32, -64});
		PauseText  = MakeText(Root, TEXT("Pause"),  56, {0.5f, 0.5f}, {0.5f, 0.5f}, {0, 0});
		HPLabel->SetText(FText::FromString(TEXT("Կյանք")));
		PauseText->SetText(FText::FromString(TEXT("Դադար")));
		PauseText->SetVisibility(ESlateVisibility::Collapsed);

		HPBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("HP"));
		HPBar->SetFillColorAndOpacity(FLinearColor(1.f, 0.35f, 0.05f));        // ProgressBar.h:114
		UCanvasPanelSlot* HS = Root->AddChildToCanvas(HPBar);
		HS->SetAnchors(FAnchors(0.f, 1.f)); HS->SetAlignment({0.f, 1.f});
		HS->SetPosition({32, -32}); HS->SetSize({420, 22});

		BossBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("Boss"));
		BossBar->SetFillColorAndOpacity(FLinearColor(0.55f, 0.1f, 0.9f));
		UCanvasPanelSlot* BS = Root->AddChildToCanvas(BossBar);
		BS->SetAnchors(FAnchors(0.5f, 0.f)); BS->SetAlignment({0.5f, 0.f});
		BS->SetPosition({0, 110}); BS->SetSize({900, 18});
		BossBar->SetVisibility(ESlateVisibility::Collapsed);
		BossName = MakeText(Root, TEXT("BossName"), 26, {0.5f, 0.f}, {0.5f, 0.f}, {0, 76});
		BossName->SetText(FText::FromString(TEXT("Մեծ վիշապ")));
		BossName->SetVisibility(ESlateVisibility::Collapsed);

		SpecialBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("Special"));
		UCanvasPanelSlot* SS = Root->AddChildToCanvas(SpecialBar);
		SS->SetAnchors(FAnchors(1.f, 1.f)); SS->SetAlignment({1.f, 1.f});
		SS->SetPosition({-32, -32}); SS->SetSize({220, 14});
	}
	return Super::RebuildWidget();
}

void UVahagnHUDWidget::NativeTick(const FGeometry& G, float Dt)
{
	Super::NativeTick(G, Dt);
	const AVahagnGameMode* GM = GetWorld() ? GetWorld()->GetAuthGameMode<AVahagnGameMode>() : nullptr;
	const AVahagnPawn* P = Cast<AVahagnPawn>(GetOwningPlayerPawn());
	if (GM)
	{
		const int32 S = FMath::CeilToInt(GM->GetTimeLeft());
		TimerText->SetText(FText::FromString(FString::Printf(TEXT("%02d:%02d"), S / 60, S % 60)));
		TimerText->SetColorAndOpacity(FSlateColor(S <= 30 ? FLinearColor(1, 0.2f, 0.1f) : FLinearColor(1.f, 0.86f, 0.6f)));
		WaveText->SetText(FText::FromString(FString::Printf(TEXT("Ալիք %d · Սպանված՝ %d"), FMath::Max(1, GM->GetWaveIndex() + 1), GM->GetKills())));
		BannerText->SetText(GM->GetBanner());
		BannerText->SetRenderOpacity(GM->GetBannerAlpha());
		const AGreatVishap* B = GM->GetBoss();
		const ESlateVisibility BV = B ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed;
		BossBar->SetVisibility(BV); BossName->SetVisibility(BV);
		if (B) { BossBar->SetPercent(B->GetHP01()); }                    // ProgressBar.h:82
	}
	if (P)
	{
		HPBar->SetPercent(P->GetHP() / P->GetMaxHP());
		SpecialBar->SetPercent(1.f - P->GetSpecialCooldown01());
	}
	const APlayerController* PC = GetOwningPlayer();
	PauseText->SetVisibility(PC && PC->IsPaused() ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
}
```
Armenian strings in `TEXT("...")`:
- On Linux, `PLATFORM_TCHAR_IS_CHAR16 = 1` (`Core/Public/Unix/UnixPlatform.h:46`).
- `TEXT` therefore becomes a `u"..."` literal, and clang reads UTF-8 source by default.
- **Save the .cpp as UTF-8 without a BOM.** For a large amount of text, put the strings in a UTF-8 file under `Content/Text/` and load it with `FFileHelper::LoadFileToString`.

### 5.4 Armenian font at runtime (primary, all C++, verified)

Facts:
- `FSlateFontInfo(TSharedPtr<const FCompositeFont>, float Size, ...)` (`SlateCore/Public/Fonts/SlateFontInfo.h:227`). The old filename constructor is `UE_DEPRECATED(5.6)` (`:245-246`).
- `FStandaloneCompositeFont` (an FGCObject) (`SlateCore/Public/Fonts/CompositeFont.h:494-502`). The engine itself builds fonts this way: `MakeShared<FStandaloneCompositeFont>(NAME_None, Path, EFontHinting::Default, EFontLoadingPolicy::LazyLoad)` (`SlateCore/Private/Fonts/LegacySlateFontInfoCache.cpp:89,300`).
- `FCompositeFont` members:
  - `DefaultTypeface` (`:461`)
  - `FallbackTypeface` (`:465`)
  - `TArray<FCompositeSubFont> SubTypefaces` (`:469`)
  - `FCompositeSubFont::CharacterRanges` (TArray<FInt32Range>) (`:413`)
  - `FTypeface::AppendFont(Name, Filename, Hinting, LoadingPolicy)` (`:366-370`)
- Coverage checked with `fc-query`:
  - Noto Sans Armenian covers U+0531–0556, 0559–058A, 058D–058F and FB13–FB17, but has **no digits or Latin letters**.
  - Engine Roboto/DroidSansFallback: no Armenian.
  - So a composite font is required.

```cpp
// UI/VahagnFonts.h
#pragma once
#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
namespace VahagnFonts
{
	FSlateFontInfo Get(float Size, bool bBold);
	void Shutdown();   // call from the module's ShutdownModule or the GameInstance's Shutdown
}
```

```cpp
// UI/VahagnFonts.cpp
#include "UI/VahagnFonts.h"
#include "Fonts/CompositeFont.h"
#include "Styling/CoreStyle.h"
#include "Misc/Paths.h"

namespace
{
	TSharedPtr<FStandaloneCompositeFont> GFont[2];
	TSharedPtr<FStandaloneCompositeFont> Build(bool bBold)
	{
		const FString Dir   = FPaths::ProjectContentDir() / TEXT("Fonts");
		const FString Latin = Dir / (bBold ? TEXT("Roboto-Bold.ttf") : TEXT("Roboto-Regular.ttf"));
		const FString Arm   = Dir / (bBold ? TEXT("NotoSansArmenian-Bold.ttf") : TEXT("NotoSansArmenian-Regular.ttf"));
		if (!FPaths::FileExists(Latin) || !FPaths::FileExists(Arm)) { return nullptr; }
		TSharedPtr<FStandaloneCompositeFont> F = MakeShared<FStandaloneCompositeFont>();
		F->DefaultTypeface.AppendFont(TEXT("Regular"), Latin, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		FCompositeSubFont& Sub = F->SubTypefaces.AddDefaulted_GetRef();
		Sub.Typeface.AppendFont(TEXT("Regular"), Arm, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		Sub.CharacterRanges.Add(FInt32Range(FInt32Range::BoundsType::Inclusive(0x0530), FInt32Range::BoundsType::Inclusive(0x058F)));
		Sub.CharacterRanges.Add(FInt32Range(FInt32Range::BoundsType::Inclusive(0xFB13), FInt32Range::BoundsType::Inclusive(0xFB17)));
		return F;
	}
}

FSlateFontInfo VahagnFonts::Get(float Size, bool bBold)
{
	TSharedPtr<FStandaloneCompositeFont>& F = GFont[bBold ? 1 : 0];
	if (!F.IsValid()) { F = Build(bBold); }
	if (F.IsValid()) { return FSlateFontInfo(StaticCastSharedPtr<const FCompositeFont>(F), Size); }
	return FCoreStyle::GetDefaultFontStyle(bBold ? TEXT("Bold") : TEXT("Regular"), Size);   // CoreStyle.h:51 (no Armenian!)
}

void VahagnFonts::Shutdown() { GFont[0].Reset(); GFont[1].Reset(); }
```

Files to copy (shell, by the main agent):
```
mkdir -p Game/Content/Fonts
cp /usr/share/fonts/truetype/noto/NotoSansArmenian-{Regular,Bold}.ttf Game/Content/Fonts/
cp /home/samo/UnrealEngine-5.8/Engine/Content/Slate/Fonts/Roboto-{Regular,Bold}.ttf Game/Content/Fonts/
```
Packaged build: `DefaultGame.ini`, key verified in `Developer/DeveloperToolSettings/Classes/Settings/ProjectPackagingSettings.h:591`:
```ini
[/Script/UnrealEd.ProjectPackagingSettings]
+DirectoriesToAlwaysStageAsUFS=(Path="Fonts")
+DirectoriesToAlwaysCook=(Path="/Game/Characters")
```
Notes:
- The `GFont` shared pointers are reset in `Shutdown()` to avoid an FGCObject being destroyed during static teardown. The static-teardown risk itself is **UNVERIFIED**; resetting is simply the safe option.
- Canvas text: `FCanvasTextItem(const FVector2D&, const FText&, const FSlateFontInfo&, const FLinearColor&)` exists (`Engine/Public/CanvasItem.h:514`), so the same composite font can be used inside `DrawHUD`.

### 5.5 Optional: headless asset import of a TTF (Python)

Verified:
- `UFontFileImportFactory` (`Editor/UnrealEd/Classes/Factories/FontFileImportFactory.h:31`) supports ttf, ttc, otf and otc and creates a `UFontFace` (`Private/Factories/EditorFactories.cpp`, constructor + `FactoryCreateBinary`).
- When `BatchCreateFontAsset == Yes` it also creates `<Name>_Font` (a `UFont`, `FontCacheType=Runtime`, default typeface = the face).
- In automated imports no dialog appears (`bShowImportDialog = Unknown && !bIsAutomated`).
- With a **specified factory** plus `automated`, AssetTools uses the given factory instance and does **not** call `ConfigureProperties` (`Developer/AssetTools/Private/AssetTools.cpp:3672`, `:4005-4007`). The preset `Yes` therefore survives.
- `EBatchCreateFontAsset` is `UENUM(BlueprintType)` (`FontFileImportFactory.h:15`) and the property is `BlueprintReadWrite`.
- `UAssetImportTask` fields: `Filename, DestinationPath, DestinationName, bReplaceExisting, bAutomated, bSave, Factory` (`Editor/UnrealEd/Public/AssetImportTask.h:36-68`).

```python
# Tools/import_fonts.py  -> UnrealEditor-Cmd Twilight.uproject -run=pythonscript -script=Tools/import_fonts.py
import unreal
tasks = []
for src, name in [("/usr/share/fonts/truetype/noto/NotoSansArmenian-Bold.ttf", "NotoSansArmenianBold")]:
    f = unreal.FontFileImportFactory()
    f.set_editor_property("batch_create_font_asset", unreal.BatchCreateFontAsset.YES)   # enum name in Python: UNVERIFIED (see note)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", src)
    t.set_editor_property("destination_path", "/Game/UI/Fonts")
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("factory", f)
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
unreal.EditorAssetLibrary.save_directory("/Game/UI/Fonts")   # the *_Font UFont package is only dirtied, not saved
```
Caveats:
- Python strips the leading `E` of enum names, so the enum is most likely `unreal.BatchCreateFontAsset.YES`. If that fails, try `unreal.EBatchCreateFontAsset.YES`. Both are **UNVERIFIED**.
- The created UFont contains **only Noto Armenian**, so digits and Latin would be missing. `FCompositeFont`/`FTypeface` are plain `USTRUCT()` without `BlueprintType`, so editing the sub-typefaces from Python is **UNVERIFIED** and probably not possible.
- **Use §5.4 for the HUD.** Use the asset only where a `UFont*` is strictly needed.

---------------------------------------------------------------------------------------------------

## 6. File layout and build

```
Game/Source/Twilight/
  Twilight.Build.cs
  Twilight.h / Twilight.cpp                 (module; ShutdownModule -> VahagnFonts::Shutdown())
  Player/VahagnPlayerController.h/.cpp      §1.3
  Player/VahagnPawn.h/.cpp                  §2.6, §3
  Player/VahagnFlightMovement.h/.cpp        §2.4
  Combat/FireBolt.h/.cpp                    §3.3
  Enemies/VishapSubsystem.h/.cpp            §4.5
  Enemies/Vishap.h/.cpp                     §4.3
  Enemies/GreatVishap.h/.cpp                §4.4
  Enemies/VishapFireball.h/.cpp             (boss P2; a 1-segment AVishap-like target that damages the player on contact)
  Game/VahagnGameMode.h/.cpp                §5.1
  UI/VahagnHUD.h/.cpp                       §5.2 (AHUD: crosshair, markers, creates the widget)
  UI/VahagnHUDWidget.h/.cpp                 §5.3
  UI/VahagnFonts.h/.cpp                     §5.4
Game/Content/Characters/Mannequins/...      (copied from TemplateResources/High/Characters/Content/Mannequins)
Game/Content/Fonts/*.ttf                    (4 TTFs)
Game/Config/DefaultInput.ini / DefaultEngine.ini / DefaultGame.ini
```

```csharp
// Twilight.Build.cs
using UnrealBuildTool;
public class Twilight : ModuleRules
{
	public Twilight(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicIncludePaths.Add(ModuleDirectory);      // allows #include "Player/VahagnPawn.h"
		PublicDependencyModuleNames.AddRange(new string[] {
			"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
			"UMG", "Slate", "SlateCore", "Niagara" });
	}
}
```
`AnimGraphRuntime` is only needed for the optional proxy blending in §2.5(b), and even that is **UNVERIFIED**. `FAnimationRuntime` lives in the Engine module.

`.uproject` plugins: EnhancedInput (`"EnabledByDefault": true`, `E/Plugins/EnhancedInput/EnhancedInput.uplugin:13`) and Niagara are on by default. Add them explicitly anyway:
`{"Name":"EnhancedInput","Enabled":true},{"Name":"Niagara","Enabled":true}`

---------------------------------------------------------------------------------------------------

## 7. Tuning table (starting values) and self-test checklist

| Param | Value | Feel check |
|---|---|---|
| Cruise / Boost speed | 2400 / 4800 cm/s | Crossing a 1 km valley takes ~4 s at cruise |
| Accel / BoostAccel / Decel | 5200 / 9000 / 3400 | Full speed in ~0.5 s, full stop in ~0.7 s |
| AimPitch clamp | −70 … +65 | Cannot loop |
| Mouse sens | 0.12 deg/count | |
| Pad look | 140 / 100 deg/s | |
| Fire interval | 0.14 s, bolt 9000 cm/s, 12 dmg | Small vishap (120 HP) dies in ~1.4 s of body hits or ~0.7 s of head hits |
| Aim assist cone | 3.5° mouse, 6° pad | |
| Small vishap | 22 seg, 1700 cm/s, 110°/s | Slower than the player at cruise, so the player can always escape |
| Boss | 40 seg, 2500 HP, 1900 cm/s, 70°/s | ~2 min at ~70 % accuracy |
| Arena | R 60000, margin 10000, floor +500, ceiling 25000 | |

Self-test checklist (to run after the build, all automatable with `-game` + `-ExecCmds` / a test mode):
1. Hold W for 60 s while steering toward the arena edge. The hero should curve back smoothly, with no stop and no wall.
2. Dive at full boost into the sea and into a mountain face. The hero should never go below the sea or through rock; it slides and pulls up.
3. Release all input at full boost. The hero should reach a hover in under 1 s with no oscillation.
4. Fire at a far mountain, then at a near rock right beside the hero. Bolts should land on the crosshair; the near-wall guard should prevent sideways shots.
5. The hero's own bolts must never damage him. They cannot by construction, since they ignore `Pawn`.
6. Pause with Esc (in `-game`) and with Start. Resume with the same key.
7. Check the boss kill: slow motion for 2.5 s of real time, then the Victory banner. Time dilation must return to 1.
8. Check Armenian text: «Վահագն Վիշապաքաղ», «Ալիք 1», «Կյանք», «Դադար», «Հաղթանակ», «Պարտություն». The timer digits "07:59" must render (composite font).

Open items, all **UNVERIFIED** until the first run:
- The visual signs of lean and bank (`LeanSign`, `BankSign`).
- Whether the `MM_Fall_Loop` limb motion looks good when the body is horizontal. Fallback: `MM_Dash` or a static frame (`SetPosition` + `SetPlayRate(0)`).
- The Python enum name for `EBatchCreateFontAsset`.
- The Tier-2 animation proxy.
