#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "VahagnCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UPointLightComponent;
class UAudioComponent;
class UFXSystemComponent;
class UTwPoseAnimInstance;
class UAnimSequence;
class UMaterialInstanceDynamic;
class AVishap;
class UInstancedStaticMeshComponent;
struct FInputActionValue;

/** Vahagn, the fire-born. Superhero flight, fireballs, charged shot and the Sun Nova. */
UCLASS()
class TWILIGHT_API AVahagnCharacter : public ACharacter
{
	GENERATED_BODY()
public:
	AVahagnCharacter();

	virtual void Tick(float Dt) override;
	virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
	virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* Instigator, AActor* Causer) override;

	// --- state for HUD/game mode
	float GetHealth() const { return Health; }
	float GetMaxHealth() const { return MaxHealth; }
	float GetNova() const { return Nova; }
	float GetCharge() const { return Charge; }
	float GetBoostEnergy() const { return BoostEnergy; }
	float GetDamageFlash() const { return DamageFlash; }
	float GetHitMarker() const { return HitMarker; }
	bool IsDead() const { return bDead; }
	bool IsBoosting() const { return bBoosting; }
	/** Aim point (world) the crosshair is over; also where the next shot goes. */
	FVector GetAimPoint() const { return AimPoint; }
	AVishap* GetAimTarget() const { return AimTarget.Get(); }

	void AddNova(float Amount) { Nova = FMath::Clamp(Nova + Amount, 0.f, 100.f); }
	void Heal(float Amount);
	/** Camera shake impulse (0..1+). */
	void AddShake(float Amount) { Shake = FMath::Min(1.5f, Shake + Amount); }
	void RegisterHit(bool bKill);
	void SetControlEnabled(bool bEnabled);
	/** Menu framing: hero off to the right of the menu panel. */
	void SetMenuFraming(bool bMenu);
	/** Autopilot used by the automated play-test (-TwAutoPlay). */
	void SetAutopilot(bool bOn) { bAutopilot = bOn; }
	/** Myth intro: rise out of the purple sea through the burning reed. */
	void BeginBirth(const FVector& ReedTop, float Duration);
	bool IsBeingBorn() const { return BirthLeft > 0.f; }
	bool IsAutopilot() const { return bAutopilot; }

	// --- input handlers (bound by the controller)
	void InMove(const FInputActionValue& V);
	void InLook(const FInputActionValue& V);
	void InUpDown(const FInputActionValue& V);
	void InFireStart();
	void InFireStop();
	void InChargeStart();
	void InChargeRelease();
	void InBoostStart();
	void InBoostStop();
	void InNova();
	// camera: hold = free 360 orbit around the hero; toggle = front view; quick cinematic 360 spin
	void InFreeLook(bool bOn) { bFreeLook = bOn; }
	void InFrontView() { bFrontView = !bFrontView; }
	void InSpin() { if (SpinLeft <= 0.f) SpinLeft = 1.f; }
	bool IsCameraOffAxis() const { return FMath::Abs(FRotator::NormalizeAxis(CamYawNow)) > 25.f || FMath::Abs(CamPitchNow) > 25.f; }

	static constexpr float ArenaRadius = 52000.f;
	static constexpr float MinAltitude = 800.f;
	static constexpr float MaxAltitude = 26000.f;

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<USpringArmComponent> Boom;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Glow;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> FlameLoop;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> WindLoop;
	UPROPERTY() TArray<TObjectPtr<UFXSystemComponent>> Auras;
	UPROPERTY() TObjectPtr<UTwPoseAnimInstance> Poser;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BodyMat;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BodyMat2;
	// "hair of fire, beard of flame, eyes like suns": flame-tongue mesh on the head bone + its light
	UPROPERTY() TObjectPtr<class UStaticMeshComponent> FireHair;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> FireHairMat;
	UPROPERTY() TObjectPtr<UPointLightComponent> FireHairLight;
	FVector FireWind = FVector::ZeroVector;
	bool bRealHero = false;
	bool bFreeLook = false, bFrontView = false, bMenuFraming = false;
	float OrbitYaw = 0.f, OrbitPitch = 0.f; // free-look offset from the flight direction
	float SpinLeft = 0.f;                   // >0 while a cinematic 360 spin plays
	float CamYawNow = 0.f, CamPitchNow = 0.f; // smoothed applied offset
	void UpdateCameraRig(float Dt);
	void GetAimView(FVector& OutLoc, FVector& OutFwd) const;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> FireTrail;
	TArray<float> TrailBirth;
	int32 TrailNext = 0;
	float TrailTimer = 0.f;
	float Shake = 0.f;
	float SteamTimer = 0.f;

	UPROPERTY() TObjectPtr<UAnimSequence> AnimHover;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimFly;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimCastA;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimCastB;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimNova;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimHit;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimDeath;

	void UpdateFlight(float Dt);
	void UpdateAim(float Dt);
	void UpdateVisuals(float Dt);
	void UpdateAutopilot(float Dt);
	void FireOnce();
	void FireCharged();
	void CallLightning(float Power);
	float AutoBolt = 2.f;
	float NovaTestT = 0.f;
	void SpawnFireball(const FVector& Muzzle, const FVector& Target, float Power, bool bCharged);
	FVector MuzzleLocation(bool bRight) const;
	void Die();

	// input state
	FVector2D MoveInput = FVector2D::ZeroVector;
	float UpInput = 0.f;
	bool bFireHeld = false;
	bool bChargeHeld = false;
	bool bBoosting = false;
	bool bControl = true;
	bool bAutopilot = false;

	// combat state
	float Health = 100.f, MaxHealth = 100.f;
	float Nova = 0.f;
	float Charge = 0.f;
	float BoostEnergy = 100.f;
	float FireCooldown = 0.f;
	float LastDamageTime = -100.f;
	float DamageFlash = 0.f;
	float HitMarker = 0.f;
	bool bRightHand = true;
	bool bDead = false;

	// flight feel
	float VisualPitch = 0.f, VisualRoll = 0.f;
	float LastYaw = 0.f;
	float BaseFov = 88.f;
	float Bob = 0.f;
	bool bFlyPose = false;

	FVector AimPoint = FVector::ZeroVector;
	TWeakObjectPtr<AVishap> AimTarget;

	// birth
	FVector BirthFrom = FVector::ZeroVector, BirthTo = FVector::ZeroVector;
	float BirthLeft = 0.f, BirthDur = 1.f;
	int32 BirthStage = 0;

	// autopilot
	float AutoFireTimer = 0.f;
	FVector AutoWander = FVector::ZeroVector;
	float AutoWanderTimer = 0.f;
};
