#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FireOrb.generated.h"

class UStaticMeshComponent;
class UPointLightComponent;
class UMaterialInstanceDynamic;

/** Glowing ember left by a slain vishap. Flies to the hero when near: heals and charges the Sun Nova. */
UCLASS()
class TWILIGHT_API AFireOrb : public AActor
{
	GENERATED_BODY()
public:
	AFireOrb();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;

private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Mesh;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Light;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Mat;
	FVector Vel = FVector::ZeroVector;
	float Age = 0.f;
	float Phase = 0.f;
};
