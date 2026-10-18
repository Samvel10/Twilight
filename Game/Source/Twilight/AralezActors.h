#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AralezActors.generated.h"

class UStaticMeshComponent;
class UPointLightComponent;
class UMaterialInstanceDynamic;
class AAralezSpirit;

/** A fragment of Ara's soul: a floating golden light any Aralez can collect. */
UCLASS()
class TWILIGHT_API ASoulLight : public AActor
{
	GENERATED_BODY()
public:
	ASoulLight();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;
	bool IsTaken() const { return bTaken; }
	void PullTo(AAralezSpirit* S) { Puller = S; }
	void Scatter(const FVector& Impulse) { Drift = Impulse; }
private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Mesh;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Light;
	TWeakObjectPtr<AAralezSpirit> Puller;
	FVector Home = FVector::ZeroVector;
	FVector Drift = FVector::ZeroVector;
	float Phase = 0.f;
	bool bTaken = false;
};

/** Shamiram's shadow: hunts the Aralez that carries the most light and steals some on touch. */
UCLASS()
class TWILIGHT_API AShadowWraith : public AActor
{
	GENERATED_BODY()
public:
	AShadowWraith();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;
	void SetPatrol(float InT) { PatrolT = InT; }
	void Repel(const FVector& From);
private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Body;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Wisps;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> EyeLight;
	FVector Vel = FVector::ZeroVector;
	float PatrolT = 0.5f;
	float Age = 0.f;
	float Cooldown = 0.f;
	float RepelTime = 0.f;
};
