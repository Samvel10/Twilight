#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TwEnvironment.generated.h"

class UDirectionalLightComponent;
class USkyAtmosphereComponent;
class USkyLightComponent;
class UExponentialHeightFogComponent;
class UPostProcessComponent;
class UAudioComponent;
class UInstancedStaticMeshComponent;
class UProceduralMeshComponent;
class UMaterialInterface;

/** Mood of a level: sun, fog, grading. */
struct FTwSkyPreset
{
	FRotator SunRot = FRotator(-7.f, 20.f, 0.f);
	FLinearColor SunColor = FLinearColor(1.f, 0.62f, 0.38f);
	float SunIntensity = 9.f;
	FRotator MoonRot = FRotator(-35.f, 200.f, 0.f);
	FLinearColor MoonColor = FLinearColor(0.55f, 0.45f, 1.f);
	float MoonIntensity = 0.6f;
	FLinearColor FogColor = FLinearColor(0.32f, 0.10f, 0.38f);
	FLinearColor FogSunColor = FLinearColor(1.f, 0.42f, 0.18f);
	float FogDensity = 0.012f;
	float FogFalloff = 0.08f;
	float FogMaxOpacity = 0.92f;
	float FogStart = 4500.f;
	float Exposure = 0.f;
	FLinearColor EmberColor = FLinearColor(1.f, 0.42f, 0.12f);
	/** Embers below this Z are mirrored above it (sea level). Lowest() disables it (caves). */
	float EmberFloorZ = TNumericLimits<float>::Lowest();
	FVector4 GainShadows = FVector4(0.95f, 0.85f, 1.15f, 1.f);
	FVector4 GainHighlights = FVector4(1.08f, 0.98f, 0.9f, 1.f);
	float SkyLightIntensity = 1.2f;
	FLinearColor SkyLightColor = FLinearColor(0.9f, 0.75f, 1.f);
	float ShadowDistance = 12000.f;
	/** SkyAtmosphere luminance tint: low values turn a lit atmosphere into a night sky. */
	FLinearColor SkyLuminance = FLinearColor(1.05f, 0.85f, 1.2f);
	/** Night skies: number of stars on a far dome (0 = none) and a moon disc opposite the key light. */
	int32 Stars = 0;
	/** SkyAtmosphere aerial perspective distance scale: >1 makes distant terrain fade into the sky sooner. */
	float AerialPerspectiveScale = 1.f;
	bool bMoonDisc = false;
};

/** Shared, fully procedural environment: sunset sky, fog, grading, music, ember motes. Games subclass it to add terrain. */
UCLASS()
class TWILIGHT_API ATwEnvironment : public AActor
{
	GENERATED_BODY()
public:
	ATwEnvironment();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;

	void PlayMusic(const TCHAR* Name);

	/** Height of a procedural island/hill at local (X,Y). */
	static float HillHeight(float X, float Y, float R, float H, int32 Seed, bool bTwin);
	/** Builds a heightfield mesh (island, hill, Masis) as a procedural mesh component. */
	UProceduralMeshComponent* BuildHeightfield(const FVector& Center, float Radius, float Height, int32 Seed, int32 Res, bool bTwin, UMaterialInterface* Mat, bool bCollide);
	/** Generic terrain grid: Z = HeightFn(localX, localY). */
	UProceduralMeshComponent* BuildTerrain(const FVector& Center, float HalfX, float HalfY, int32 ResX, int32 ResY, TFunctionRef<float(float, float)> HeightFn, UMaterialInterface* Mat, bool bCollide, float UVScale = 1500.f);

protected:
	/** Subclasses: return the sky mood and build their terrain. */
	virtual FTwSkyPreset GetSkyPreset() const { return FTwSkyPreset(); }
	virtual void BuildLevel() {}
	virtual const TCHAR* GetStartMusic() const { return TEXT("music_menu"); }

	UPROPERTY(VisibleAnywhere) TObjectPtr<UDirectionalLightComponent> Sun;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UDirectionalLightComponent> Moon;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkyAtmosphereComponent> Atmosphere;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkyLightComponent> SkyLight;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UExponentialHeightFogComponent> Fog;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPostProcessComponent> Post;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> Music;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> MusicB;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Embers;
	UPROPERTY() TArray<TObjectPtr<UProceduralMeshComponent>> Heightfields;

private:
	void BuildSky(const FTwSkyPreset& P);
	void BuildEmbers(const FLinearColor& Color);
	void BuildNightSky(const FTwSkyPreset& P);
	void UpdateEmbers(float Dt);

	TArray<FVector> EmberPos;
	TArray<float> EmberSize;
	float EmberFloorZ = TNumericLimits<float>::Lowest();
	float SkyRecaptureTimer = 0.3f;
	int32 SkyCaptures = 0;
	bool bMusicA = true;
};
