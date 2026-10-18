#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Fireball.generated.h"

class USphereComponent;
class UStaticMeshComponent;
class UProjectileMovementComponent;
class UPointLightComponent;
class UFXSystemComponent;
class UMaterialInstanceDynamic;

/** Fire projectile. Player version hits vishaps; hostile version (vishap spit) hits the player. */
UCLASS()
class TWILIGHT_API AFireball : public AActor
{
	GENERATED_BODY()
public:
	AFireball();
	static constexpr float Speed = 10500.f;

	/** Damage: direct hit damage. Aoe: explosion radius (0 = direct only). Scale: visual size. */
	void Launch(const FVector& Dir, float Damage, float AoeRadius, float Scale, bool bHostile, float SpeedOverride = 0.f);

	virtual void Tick(float Dt) override;

private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> Sphere;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Core;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UProjectileMovementComponent> Move;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Light;
	UPROPERTY() TObjectPtr<UFXSystemComponent> Flame;
	UPROPERTY() TObjectPtr<UFXSystemComponent> Trail;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> CoreMat;

	UFUNCTION() void OnOverlap(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool bFromSweep, const FHitResult& Sweep);
	UFUNCTION() void OnHit(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, FVector Impulse, const FHitResult& Hit);

	void Explode(const FVector& Where, AActor* DirectActor, UPrimitiveComponent* DirectComp);

	float Damage = 1.f;
	float Aoe = 0.f;
	float VisualScale = 1.f;
	bool bHostile = false;
	bool bDone = false;
	float Age = 0.f;
};
