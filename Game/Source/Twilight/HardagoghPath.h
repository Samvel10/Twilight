#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HardagoghPath.generated.h"

class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;

/** «Հարդագողի ճանապարհը» (the Milky Way): the straw Vahagn stole from Barsham, spilled across the sky.
 *  A band of golden straw and dust that unrolls from horizon to horizon after the victory. */
UCLASS()
class TWILIGHT_API AHardagoghPath : public AActor
{
	GENERATED_BODY()
public:
	AHardagoghPath();
	/** Center = the viewer; Fwd = horizontal direction the band leans toward. */
	void Build(const FVector& Center, const FVector& Fwd, float Radius = 300000.f);
	virtual void Tick(float Dt) override;
	static constexpr float RevealTime = 6.f;

private:
	static constexpr int32 Segs = 14;
	UPROPERTY() TArray<TObjectPtr<UInstancedStaticMeshComponent>> Parts;
	UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> Mats;
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> HazeIsm;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> HazeMat;
	TArray<FTransform> Haze;
	TArray<int32> HazeSeg;
	float Age = 0.f;
};
