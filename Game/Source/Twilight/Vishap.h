#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Vishap.generated.h"

class UStaticMeshComponent;
class USkeletalMeshComponent;
class UPointLightComponent;
class UFXSystemComponent;
class UMaterialInstanceDynamic;
class UAudioComponent;
class AVahagnCharacter;

UENUM()
enum class EVishapState : uint8
{
	Emerge, Approach, Circle, BreathWindup, Breath, DashWindup, Dash, Spit, Retreat, Dying
};

/** Vishap: a flying serpent-dragon whose body follows the head's path. Boss variant = the Great Vishap. */
UCLASS()
class TWILIGHT_API AVishap : public AActor
{
	GENERATED_BODY()
public:
	AVishap();

	/** Configure before/right after spawn. Tier 0 = normal, 1 = elite (red, faster). */
	void Setup(bool bInBoss, int32 InTier, float HealthMult);

	virtual void Tick(float Dt) override;

	bool IsAlive() const { return State != EVishapState::Dying; }
	bool IsAttacking() const { return State == EVishapState::BreathWindup || State == EVishapState::Breath || State == EVishapState::DashWindup || State == EVishapState::Dash || State == EVishapState::Spit; }
	bool IsBoss() const { return bBoss; }
	float GetHealth() const { return Health; }
	float GetMaxHealth() const { return MaxHealth; }
	FVector GetHeadLocation() const { return HeadPos; }
	FVector GetHeadVelocity() const { return HeadVel; }
	void GetAimPoints(TArray<FVector>& Out) const;
	float DistanceToPoint(const FVector& P) const;

	void ApplyHit(float Damage, const FVector& Where, AVahagnCharacter* Hero, bool bNotify);
	void ApplyHitAtComponent(float Damage, const FVector& Where, UPrimitiveComponent* Comp, AVahagnCharacter* Hero);
	void Knockback(const FVector& From, float Strength);

	/** Boss phase index (0..2) for HUD/announcements. */
	int32 GetPhase() const { return Phase; }
	int32 GetTier() const { return Tier; }

protected:
	virtual void BeginPlay() override;

private:
	void Build();
	void Think(float Dt);
	void Steer(const FVector& Target, float DesiredSpeed, float TurnDegPerSec, float Dt);
	void UpdateBody(float Dt);
	void UpdateDying(float Dt);
	void BeginState(EVishapState S);
	void StartDying(AVahagnCharacter* Killer);
	void DoBreathTick();
	void DoSpit();
	AVahagnCharacter* Player() const;
	FVector MouthLocation() const;
	FVector SampleTrail(float Distance, FVector* OutTangent) const;
	// realistic dragon body (CC-BY skeletal mesh); the sphere segments stay as invisible hit volumes
	void BuildDragon();
	void UpdateDragon(float Dt);
	bool CalibrateDragon();

	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Segments;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> HeadParts;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Skull;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Jaw;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> BreathCone;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BreathMat;
	UPROPERTY() TObjectPtr<UPointLightComponent> EyeLight;
	UPROPERTY() TObjectPtr<UFXSystemComponent> BreathFx;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> SkinMat;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BoneMat;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> EyeMat;
	UPROPERTY() TObjectPtr<UAudioComponent> BreathAudio;

	TArray<float> SegRadius;
	TArray<float> SegDist; // distance along the body from the head
	TArray<FVector> Trail;      // head positions, newest first
	float TrailStep = 40.f;
	float Spacing = 120.f;
	float R0 = 80.f;
	int32 NumSeg = 24;

	bool bBoss = false;
	int32 Tier = 0;
	float Health = 10.f, MaxHealth = 10.f;
	float BaseSpeed = 2300.f;
	float TurnRate = 100.f;
	int32 Phase = 0;

	FVector HeadPos = FVector::ZeroVector;
	FVector HeadVel = FVector::ZeroVector;
	FVector KnockVel = FVector::ZeroVector;

	EVishapState State = EVishapState::Emerge;
	float StateTime = 0.f;
	float StateDur = 0.f;
	float AttackCooldown = 2.f;
	float BreathTick = 0.f;
	float BreathFxTick = 0.f;
	float JawOpen = 0.f;
	float HitFlash = 0.f;
	float Wobble = 0.f;
	float LifeTime = 0.f;
	FVector CircleAxisSeed = FVector::ZeroVector;
	FVector DashDir = FVector::ForwardVector;
	bool bDashHit = false;
	int32 SpitsLeft = 0;

	// dragon visual
	UPROPERTY() TObjectPtr<USkeletalMeshComponent> Dragon;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> DragonMat;
	bool bDragon = false;
	bool bDragonCalibrated = false;
	bool bDragonAnimFrame = false;
	FVector DragonHeadCS = FVector::ZeroVector; // head bone, component space (unscaled)
	FQuat DragonMeshFrame = FQuat::Identity;   // mesh forward/up -> X/Z
	float DragonScale = 1.f;
	FVector DragonFwd = FVector::ForwardVector;
	float DragonBank = 0.f;
	FVector DragonFallVel = FVector::ZeroVector;
	UPROPERTY() TObjectPtr<UFXSystemComponent> DragonFire;

	// dying
	TArray<FVector> DebrisVel;
	float DyingTime = 0.f;
	int32 NextPop = 0;
};
