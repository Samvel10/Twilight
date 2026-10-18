#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HaykShield.generated.h"

class UStaticMeshComponent;

/** Wooden pavise standing in the valley; blocks arrows, breaks after a few hits. */
UCLASS()
class TWILIGHT_API AHaykShield : public AActor
{
	GENERATED_BODY()
public:
	AHaykShield();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;
	void TakeArrow(const FVector& Where, bool bSpecial);
	bool IsBroken() const { return Hits >= MaxHits; }

private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Board; // collision slab (hidden)
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Parts;
	int32 Hits = 0;
	int32 MaxHits = 3;
	float Shake = 0.f;
	FRotator BaseRot;
};
