#pragma once

#include "CoreMinimal.h"
#include "TwEnvironment.h"
#include "AralezField.generated.h"

class USkeletalMeshComponent;
class UPointLightComponent;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UAnimSequence;
class AAralezSpirit;

/** «Արայի դաշտը»: the battlefield of Ara the Beautiful and Queen Shamiram at dusk, Masis on the horizon. */
UCLASS()
class TWILIGHT_API AAralezField : public ATwEnvironment
{
	GENERATED_BODY()
public:
	AAralezField();
	/** Ground height of the plain (cm). */
	static float GroundZ(float X, float Y);
	static constexpr float FieldRadius = 45000.f; // playable radius (cm, 450 m); the plain itself is much bigger
	static FVector AraSpot() { return FVector(0.f, 0.f, GroundZ(0.f, 0.f)); }

protected:
	virtual FTwSkyPreset GetSkyPreset() const override;
	virtual void BuildLevel() override;
	virtual const TCHAR* GetStartMusic() const override { return TEXT("music_aralez"); }
	virtual void Tick(float Dt) override;

private:
	void BuildSkyDome();
	void BuildGround();
	void BuildMasis();
	void BuildDressing();

	UPROPERTY() TArray<FVector> SmokeSpots;
	float SmokeTimer = 0.f;
};

/** A fallen warrior of Ara's army (or Ara himself). The Aralez revive him by lingering close ("licking his wounds"). */
UCLASS()
class TWILIGHT_API AFallenWarrior : public AActor
{
	GENERATED_BODY()
public:
	AFallenWarrior();
	void Setup(bool bInAra) { bAra = bInAra; }
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;

	/** Adds healing; returns true on the frame he rises. */
	bool Heal(float Amount);
	bool IsRevived() const { return bRevived; }
	bool IsAra() const { return bAra; }
	float GetProgress() const { return Progress; }
	FVector GetChest() const;
	void SetLocked(bool b) { bLocked = b; }
	bool IsLocked() const { return bLocked; }

private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Glow;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimDeath;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimIdle;
	UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> Mats;
	bool bAra = false;
	bool bRevived = false;
	bool bLocked = false;
	float Progress = 0.f;
	float RiseTime = -1.f;
	float LastHeal = -10.f;
};

/** One of Queen Shamiram's soldiers: guards the fallen and strikes an Aralez that flies down too low. */
UCLASS()
class TWILIGHT_API AShamiramSoldier : public AActor
{
	GENERATED_BODY()
public:
	AShamiramSoldier();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;
	void SetPost(const FVector& P) { Post = P; }
	void Repel(const FVector& From);

private:
	void PlayLoop(UAnimSequence* A, float Rate);

	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimIdle;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimRun;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimWalk;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimStrike;
	UPROPERTY() TObjectPtr<UAnimSequence> CurrentAnim;
	FVector Post = FVector::ZeroVector;
	float StrikeCd = 0.f;
	float Stagger = 0.f;
	float Wander = 0.f;
	FVector WanderGoal = FVector::ZeroVector;
};
