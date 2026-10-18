#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VahagnWorld.generated.h"

class UDirectionalLightComponent;
class USkyAtmosphereComponent;
class USkyLightComponent;
class UExponentialHeightFogComponent;
class UPostProcessComponent;
class UStaticMeshComponent;
class UProceduralMeshComponent;
class UAudioComponent;
class UMaterialInterface;

/** Builds the whole «Ծիրանի ծով» level procedurally at runtime: sunset sky, purple sea, islands, Masis, vishapakar stones. */
UCLASS()
class TWILIGHT_API AVahagnWorld : public AActor
{
	GENERATED_BODY()
public:
	AVahagnWorld();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;

	void PlayMusic(const TCHAR* Name);

private:
	void BuildSky();
	void BuildSea();
	void BuildIslands();
	UProceduralMeshComponent* BuildIsland(const FVector& Center, float Radius, float Height, int32 Seed, int32 Res, bool bTwinPeak, UMaterialInterface* Mat, bool bCollide);
	void BuildVishapakar(const FVector& Base, float Yaw, float Scale);

	UPROPERTY(VisibleAnywhere) TObjectPtr<UDirectionalLightComponent> Sun;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UDirectionalLightComponent> Moon;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkyAtmosphereComponent> Atmosphere;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkyLightComponent> SkyLight;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UExponentialHeightFogComponent> Fog;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPostProcessComponent> Post;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Sea;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> SkyDome;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> Music;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> MusicB;
	UPROPERTY() TArray<TObjectPtr<UProceduralMeshComponent>> Islands;

	float SkyRecaptureTimer = 0.f;
	int32 SkyCaptures = 0;
	bool bMusicA = true;
};
