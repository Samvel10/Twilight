#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TwLightning.generated.h"

class UInstancedStaticMeshComponent;
class UPointLightComponent;
class UMaterialInstanceDynamic;

/** A forked lightning bolt: jagged core + soft halo, flickers twice and fades (~0.5 s). */
UCLASS()
class TWILIGHT_API ATwLightning : public AActor
{
	GENERATED_BODY()
public:
	ATwLightning();
	/** Spawns a bolt from From to To; Width in cm for the core. */
	static ATwLightning* Strike(UWorld* World, const FVector& From, const FVector& To, float Width = 60.f, int32 Seed = 0);
	virtual void Tick(float Dt) override;

private:
	void Build(const FVector& From, const FVector& To, float Width, int32 Seed);
	void AddBranch(FRandomStream& R, const FVector& A, const FVector& B, float Width, int32 Depth);
	void AddSeg(const FVector& A, const FVector& B, float Width);

	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Core;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Halo;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Light;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> CoreMat;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> HaloMat;
	float Age = 0.f;
};
