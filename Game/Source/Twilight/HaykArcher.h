#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HaykArcher.generated.h"

class USkeletalMeshComponent;
class USphereComponent;
class UCapsuleComponent;
class UProceduralMeshComponent;
class UPointLightComponent;
class UStaticMeshComponent;
class UTwPoseAnimInstance;
class UAnimSequence;
class UMaterialInstanceDynamic;

UENUM()
enum class EArcherZone : uint8 { None, Head, Torso, Legs };

/** A duelist: Hayk (hero) or Bel (giant king). Skeletal mannequin + procedural bow + hit zones. */
UCLASS()
class TWILIGHT_API AHaykArcher : public AActor
{
	GENERATED_BODY()
public:
	AHaykArcher();

	void Setup(bool bInBel, float InMaxHealth, bool bInSoldier = false);
	/** Bel's shield-bearers: while true, arrows on him are blocked by the shield wall. */
	void SetShielded(bool b) { bShielded = b; }
	bool IsShielded() const { return bShielded; }
	bool IsSoldier() const { return bSoldier; }
	void SetHealth(float H) { MaxHealth = Health = H; }
	virtual void Tick(float Dt) override;

	/** Aim the body (yaw) and bow (pitch) in degrees, world yaw. */
	void SetAim(float Yaw, float Pitch);
	float GetAimYaw() const { return AimYaw; }
	float GetAimPitch() const { return AimPitch; }
	void SetDraw(float Power01);
	void Release();
	FVector GetArrowSpawn() const;
	FVector GetChestTarget() const;
	FVector GetHeadTarget() const;

	EArcherZone ZoneOf(const UPrimitiveComponent* C) const;
	/** Returns damage actually applied. */
	float ApplyHit(EArcherZone Zone, bool bSpecial, const FVector& Where);
	bool IsDead() const { return Health <= 0.f; }
	bool IsBel() const { return bBel; }
	float GetScale() const { return Scale; }
	float GetHealth() const { return Health; }
	float GetMaxHealth() const { return MaxHealth; }
	float GetHurtFlash() const { return HurtFlash; }
	void Celebrate();

	USkeletalMeshComponent* GetBody() const { return Body; }

protected:
	virtual void BeginPlay() override;

private:
	void BuildBow();
	void UpdateBowAndZones();
	FVector BowTip(bool bTop) const;

	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> HeadZone;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> TorsoZone;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> LegsZone;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UProceduralMeshComponent> Bow;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> StringTop;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> StringBottom;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> NockedArrow;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Rim;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Regalia;
	TArray<FVector> RegaliaOffset;
	TArray<FRotator> RegaliaRot;
	// clothing that follows a bone (tunic at the pelvis, cape at the neck): no more bare mannequins
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Garments;
	TArray<FName> GarmentBone;
	TArray<FVector> GarmentOffset;
	TArray<FRotator> GarmentRot;
	UPROPERTY() TObjectPtr<UTwPoseAnimInstance> Poser;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> BodyMat;
	UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> HumanMats;
	bool bRealHuman = false;

	UPROPERTY() TObjectPtr<UAnimSequence> AnimIdle;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimAim;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimShoot;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimHit;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimHitHeavy;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimDeath;
	UPROPERTY() TObjectPtr<UAnimSequence> AnimCheer;

	bool bBel = false;
	bool bSoldier = false;
	bool bShielded = false;
	float Health = 100.f, MaxHealth = 100.f;
	float AimYaw = 0.f, AimPitch = 0.f;
	float Draw = 0.f;
	float HurtFlash = 0.f;
	float Scale = 1.f;
	bool bAiming = false;
};
