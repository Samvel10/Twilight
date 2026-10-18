#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HaykArrow.generated.h"

class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UPointLightComponent;
class AHaykArcher;

UENUM()
enum class EArrowResult : uint8 { Flying, HitArcher, HitShield, HitGround, Lost };

/** Ballistic arrow with wind, optional player steering (the three-feathered arrow) and a glowing trail. */
UCLASS()
class TWILIGHT_API AHaykArrow : public AActor
{
	GENERATED_BODY()
public:
	AHaykArrow();

	static constexpr float MaxSpeed = 7200.f;
	static constexpr float Gravity = 980.f;
	static constexpr float WindK = 70.f; // cm/s^2 per m/s of wind

	void Launch(AHaykArcher* InShooter, const FVector& Dir, float Power01, const FVector& Wind, bool bInSpecial);
	virtual void Tick(float Dt) override;

	/** Steering input for the special arrow (-1..1 each axis). */
	void Steer(const FVector2D& In) { SteerInput = (SteerInput + In).ClampAxes(-1.f, 1.f); }

	EArrowResult GetResult() const { return Result; }
	bool IsSpecial() const { return bSpecial; }
	FVector GetVelocity() const override { return Vel; }
	FVector GetImpactPoint() const { return Impact; }
	AHaykArcher* GetHitArcher() const { return HitArcher.Get(); }
	float GetDamageDealt() const { return DamageDealt; }
	bool WasHeadshot() const { return bHeadshot; }
	float TimeToReach(const FVector& Point) const;
	float GetFlightTime() const { return Age; }

	/** Simulate a shot without spawning; returns closest distance to Target and the time of closest approach. */
	static float SimulateMiss(UWorld* World, const FVector& Start, const FVector& Vel0, const FVector& Wind, const FVector& Target, float& OutT, const AActor* Ignore);

private:
	void Resolve(const FHitResult& Hit);

	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Shaft;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Tip;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Feathers;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> TrailDots;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Light;

	TWeakObjectPtr<AHaykArcher> Shooter;
	TWeakObjectPtr<AHaykArcher> HitArcher;
	FVector Vel = FVector::ZeroVector;
	FVector Wind = FVector::ZeroVector;
	FVector2D SteerInput = FVector2D::ZeroVector;
	FVector Impact = FVector::ZeroVector;
	EArrowResult Result = EArrowResult::Flying;
	bool bSpecial = false;
	bool bHeadshot = false;
	float DamageDealt = 0.f;
	float Age = 0.f;
	float TrailTimer = 0.f;
	int32 TrailNext = 0;
	TArray<float> TrailBirth;
	TArray<float> TrailLen;
	FVector PrevTrail = FVector::ZeroVector;
};
